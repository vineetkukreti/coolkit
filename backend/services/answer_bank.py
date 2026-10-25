"""Answer bank for custom application questions.

Commercial autofill tools (Simplify, Jobright) fill free-text, dropdown and radio questions with an LLM
on every application. coolkit adds a learning layer on top:

  1. Look the question up in a per-user answer bank (your own past answers, normalized and fuzzy-matched).
  2. Send only the misses to the LLM, in ONE batched call, with the profile + JD as context.
  3. When you correct a field and click "Remember", your final answer goes into the bank, so the next
     form with the same question uses your wording instead of the model's.

Company-specific answers ("Why Acme?") are only reused for the same company.
"""

import difflib
import re
import sqlite3

from services.ai_tools import CANDIDATE_PROFILE
from services.career_copilot import _llm_json

FUZZY_THRESHOLD = 0.88
CHOICE_TYPES = ("select", "radio", "checkbox")


def _ensure_table(conn: sqlite3.Connection):
    conn.execute(
        """CREATE TABLE IF NOT EXISTS answer_bank (
               id          INTEGER PRIMARY KEY AUTOINCREMENT,
               question    TEXT NOT NULL,
               normalized  TEXT NOT NULL,
               answer      TEXT NOT NULL,
               company     TEXT DEFAULT '',
               source      TEXT DEFAULT 'user' CHECK(source IN ('user', 'llm')),
               uses        INTEGER DEFAULT 0,
               updated_at  TEXT DEFAULT (datetime('now')),
               UNIQUE(normalized, company)
           )"""
    )


def normalize(question: str) -> str:
    q = question.lower()
    q = re.sub(r"\(required\)|\brequired\b|\*", " ", q)
    q = re.sub(r"[^a-z0-9 ]+", " ", q)
    return re.sub(r"\s+", " ", q).strip()


def _match_option(answer: str, options: list) -> str | None:
    """Map an answer onto one of the field's options (exact, then case-insensitive, then fuzzy)."""
    if not options:
        return answer
    if answer in options:
        return answer
    lower = {o.lower().strip(): o for o in options}
    if answer.lower().strip() in lower:
        return lower[answer.lower().strip()]
    close = difflib.get_close_matches(answer.lower().strip(), list(lower), n=1, cutoff=0.6)
    return lower[close[0]] if close else None


def _is_company_specific(answer: str, company: str) -> bool:
    return bool(company) and company.lower() in answer.lower()


def lookup(conn: sqlite3.Connection, question: str, company: str = "") -> dict | None:
    _ensure_table(conn)
    norm = normalize(question)
    if not norm:
        return None
    rows = conn.execute(
        "SELECT id, normalized, answer, company, source FROM answer_bank WHERE company IN ('', ?) "
        "ORDER BY (company = ?) DESC, (source = 'user') DESC, uses DESC",
        (company, company),
    ).fetchall()
    best, best_ratio = None, 0.0
    for row in rows:
        ratio = 1.0 if row[1] == norm else difflib.SequenceMatcher(None, row[1], norm).ratio()
        if ratio > best_ratio:
            best, best_ratio = row, ratio
        if ratio == 1.0:
            break
    if best is None or best_ratio < FUZZY_THRESHOLD:
        return None
    conn.execute("UPDATE answer_bank SET uses = uses + 1 WHERE id = ?", (best[0],))
    return {"answer": best[2], "source": f"bank:{best[4]}", "match": round(best_ratio, 2)}


def remember(conn: sqlite3.Connection, items: list, company: str = "", source: str = "user") -> int:
    """Store answers. Company-specific answers are scoped to that company; the rest are global."""
    _ensure_table(conn)
    saved = 0
    for item in items:
        question, answer = (item.get("question") or "").strip(), str(item.get("answer") or "").strip()
        norm = normalize(question)
        if not norm or not answer:
            continue
        scope = company if _is_company_specific(answer, company) else ""
        conn.execute(
            """INSERT INTO answer_bank (question, normalized, answer, company, source) VALUES (?, ?, ?, ?, ?)
               ON CONFLICT(normalized, company) DO UPDATE SET
                 answer = excluded.answer, question = excluded.question,
                 source = excluded.source, updated_at = datetime('now')
               WHERE answer_bank.source = 'llm' OR excluded.source = 'user'""",
            (question, norm, answer, scope, source),
        )
        saved += 1
    conn.commit()
    return saved


def _llm_answer(questions: list, company: str, role: str, jd_text: str) -> dict:
    listing = "\n".join(
        f'- id={q["id"]} type={q.get("type", "text")} question="{q["question"]}"'
        + (f' options={q["options"]}' if q.get("options") else "")
        for q in questions
    )
    prompt = f"""You are filling a job application form on behalf of this candidate. Answer truthfully from the profile.

━━━ CANDIDATE ━━━
{CANDIDATE_PROFILE}

━━━ JOB ━━━
Company: {company or "(unknown)"}   Role: {role or "(unknown)"}
{jd_text[:3000]}

━━━ QUESTIONS ━━━
{listing}

━━━ RULES ━━━
- For select/combo/radio/checkbox, "answer" MUST be copied exactly from options (checkbox: options joined with " | ").
- Free text: first person, specific, 40-120 words for open questions, a few words for factual ones.
- Never claim a skill, license, degree or authorization the profile doesn't show. If unknown, set confidence "low".

Return ONLY JSON: {{"answers": [{{"id": "<id>", "answer": "<text>", "confidence": "high|medium|low"}}]}}"""
    return _llm_json(prompt, max_tokens=2500, temperature=0.3)


def answer_questions(conn: sqlite3.Connection, questions: list, company: str = "", role: str = "",
                     jd_text: str = "") -> dict:
    """questions: [{id, question, type, options?}] -> {answers: [{id, answer, source, confidence}]}"""
    answers, misses = [], []
    for q in questions:
        if not q.get("question"):
            continue
        hit = lookup(conn, q["question"], company)
        value = hit and _match_option(hit["answer"], q.get("options") or [])
        if value:
            answers.append({"id": q["id"], "answer": value, "source": hit["source"], "confidence": "high"})
        else:
            misses.append(q)

    error = None
    if misses:
        result = _llm_answer(misses, company, role, jd_text)
        error = result.get("error")
        by_id = {q["id"]: q for q in misses}
        for a in result.get("answers", []):
            q = by_id.get(str(a.get("id")))
            if not q or not a.get("answer"):
                continue
            if q.get("type") == "checkbox":
                picks = [_match_option(p.strip(), q.get("options") or []) for p in str(a["answer"]).split("|")]
                value = " | ".join(p for p in picks if p)
            else:
                value = _match_option(str(a["answer"]), q.get("options") or [])
            if value:
                answers.append({"id": q["id"], "answer": value, "source": "llm",
                                "confidence": a.get("confidence", "medium")})
    conn.commit()
    return {"status": "ok" if not error else "partial", "answers": answers,
            "from_bank": sum(a["source"].startswith("bank") for a in answers),
            "from_llm": sum(a["source"] == "llm" for a in answers),
            **({"message": error} if error else {})}


def list_answers(conn: sqlite3.Connection) -> list:
    _ensure_table(conn)
    rows = conn.execute(
        "SELECT id, question, answer, company, source, uses, updated_at FROM answer_bank ORDER BY uses DESC, updated_at DESC"
    ).fetchall()
    keys = ("id", "question", "answer", "company", "source", "uses", "updated_at")
    return [dict(zip(keys, r)) for r in rows]


def delete_answer(conn: sqlite3.Connection, answer_id: int) -> bool:
    _ensure_table(conn)
    cur = conn.execute("DELETE FROM answer_bank WHERE id = ?", (answer_id,))
    conn.commit()
    return cur.rowcount > 0
