"""
Skills Intelligence Service.

Extracts skills from saved jobs, computes market demand stats,
identifies resume gaps, and researches current trends.

Usage:
    from services.skills_intel import start_analysis, get_dashboard_data, compute_gap_analysis
"""

import os
import re
import json
import time
import random
import threading
import sqlite3
import logging
from datetime import datetime, timedelta

import requests

log = logging.getLogger("skills_intel")

# ─── Tech Taxonomy ─────────────────────────────────────────────────────────
# Maps canonical skill name → (category, [regex patterns])
# Patterns are compiled at module load for speed.

_RAW_TAXONOMY = {
    "Languages": {
        "python":       [r"\bpython\b", r"\bpython3\b"],
        "java":         [r"\bjava\b(?!\s*script)"],
        "javascript":   [r"\bjavascript\b", r"\bnode\.?js\b", r"\bnodejs\b"],
        "typescript":   [r"\btypescript\b"],
        "r":            [r"\bR\b(?!\s*&)", r"\br programming\b"],
        "sql":          [r"\bsql\b"],
        "scala":        [r"\bscala\b"],
        "rust":         [r"\brust\b"],
        "golang":       [r"\bgolang\b", r"\bgo\b(?:\s+language|\s+programming)"],
        "c++":          [r"\bc\+\+\b", r"\bcpp\b"],
        "julia":        [r"\bjulia\b(?:\s+lang)?"],
        "shell/bash":   [r"\bbash\b", r"\bshell\s*script"],
    },
    "AI_ML": {
        "pytorch":              [r"\bpytorch\b", r"\btorch\b"],
        "tensorflow":           [r"\btensorflow\b", r"\btf\b(?:\s+\d|\.|\s+model)"],
        "scikit-learn":         [r"\bscikit[\-\s]?learn\b", r"\bsklearn\b"],
        "hugging face":         [r"\bhugging\s*face\b", r"\btransformers\b(?:\s+library)?"],
        "langchain":            [r"\blangchain\b"],
        "llamaindex":           [r"\bllama\s*index\b"],
        "rag":                  [r"\brag\b", r"\bretrieval[\-\s]augmented\b"],
        "fine-tuning":          [r"\bfine[\-\s]?tun"],
        "computer vision":      [r"\bcomputer\s*vision\b", r"\bimage\s+classif", r"\bobject\s+detect"],
        "nlp":                  [r"\bnlp\b", r"\bnatural\s+language\s+processing\b"],
        "deep learning":        [r"\bdeep\s+learning\b"],
        "reinforcement learning": [r"\breinforcement\s+learning\b"],
        "llm":                  [r"\bllm\b", r"\blarge\s+language\s+model"],
        "genai":                [r"\bgen\s*ai\b", r"\bgenerative\s+ai\b"],
        "mlops":                [r"\bmlops\b", r"\bml\s+ops\b"],
        "vector database":      [r"\bvector\s*(db|database)\b", r"\bpinecone\b", r"\bweaviate\b",
                                 r"\bqdrant\b", r"\bmilvus\b", r"\bchromadb\b", r"\bchroma\b"],
        "embeddings":           [r"\bembedding"],
        "agents":               [r"\bai\s+agent", r"\bagentic\b", r"\bmulti[\-\s]agent",
                                 r"\bcrewai\b", r"\bautogen\b", r"\blanggraph\b"],
        "prompt engineering":   [r"\bprompt\s+engineer"],
        "feature engineering":  [r"\bfeature\s+engineer", r"\bfeature\s+store"],
        "model deployment":     [r"\bmodel\s+deploy", r"\bmodel\s+serving", r"\btriton\b",
                                 r"\bvllm\b", r"\btgi\b", r"\bbentoml\b"],
        "openai":               [r"\bopenai\b", r"\bgpt[\-\s]?[34]\b", r"\bchatgpt\b"],
        "claude":               [r"\bclaude\b(?:\s+api|\s+model)?"],
        "gemini":               [r"\bgemini\b(?:\s+api|\s+model)?"],
        "stable diffusion":     [r"\bstable\s+diffusion\b", r"\bdiffusion\s+model"],
        "xgboost":              [r"\bxgboost\b"],
        "lightgbm":             [r"\blightgbm\b"],
        "keras":                [r"\bkeras\b"],
        "jax":                  [r"\bjax\b"],
        "spacy":                [r"\bspacy\b"],
        "opencv":               [r"\bopencv\b"],
        "pandas":               [r"\bpandas\b"],
        "numpy":                [r"\bnumpy\b"],
        "matplotlib":           [r"\bmatplotlib\b"],
        "dspy":                 [r"\bdspy\b"],
    },
    "Frameworks": {
        "fastapi":      [r"\bfastapi\b"],
        "flask":        [r"\bflask\b"],
        "django":       [r"\bdjango\b"],
        "react":        [r"\breact\b(?:\.?js)?"],
        "next.js":      [r"\bnext\.?js\b"],
        "spring boot":  [r"\bspring\s*boot\b"],
        "streamlit":    [r"\bstreamlit\b"],
        "gradio":       [r"\bgradio\b"],
        "pydantic":     [r"\bpydantic\b"],
        "celery":       [r"\bcelery\b"],
        "ray":          [r"\bray\b(?:\s+serve|\s+cluster|\s+framework)?"],
    },
    "Cloud": {
        "aws":          [r"\baws\b", r"\bamazon\s+web\s+services\b", r"\bsagemaker\b",
                         r"\bs3\b", r"\bec2\b", r"\blambda\b(?:\s+function)?", r"\bbedrock\b"],
        "gcp":          [r"\bgcp\b", r"\bgoogle\s+cloud\b", r"\bvertex\s*ai\b", r"\bbigquery\b"],
        "azure":        [r"\bazure\b"],
        "databricks":   [r"\bdatabricks\b"],
        "snowflake":    [r"\bsnowflake\b"],
        "huggingface hub": [r"\bhuggingface\s+hub\b", r"\bhf\s+hub\b"],
    },
    "Databases": {
        "postgresql":   [r"\bpostgre"],
        "mongodb":      [r"\bmongo"],
        "neo4j":        [r"\bneo4j\b"],
        "redis":        [r"\bredis\b"],
        "elasticsearch": [r"\belastic\s*search\b"],
        "mysql":        [r"\bmysql\b"],
        "dynamodb":     [r"\bdynamo\s*db\b"],
        "cassandra":    [r"\bcassandra\b"],
        "sqlite":       [r"\bsqlite\b"],
    },
    "DevOps": {
        "docker":       [r"\bdocker\b"],
        "kubernetes":   [r"\bkubernetes\b", r"\bk8s\b"],
        "ci/cd":        [r"\bci\s*/?\s*cd\b", r"\bjenkins\b", r"\bgithub\s+actions\b",
                         r"\bgitlab\s+ci\b", r"\bcircle\s*ci\b"],
        "terraform":    [r"\bterraform\b"],
        "airflow":      [r"\bairflow\b"],
        "kafka":        [r"\bkafka\b"],
        "spark":        [r"\bspark\b", r"\bpyspark\b"],
        "mlflow":       [r"\bmlflow\b"],
        "dvc":          [r"\bdvc\b"],
        "wandb":        [r"\bwandb\b", r"\bweights\s+(?:and|&)\s+biases\b"],
        "git":          [r"\bgit\b(?:hub|lab)?"],
        "linux":        [r"\blinux\b"],
        "grafana":      [r"\bgrafana\b"],
        "prometheus":   [r"\bprometheus\b"],
    },
    "Domain": {
        "healthcare ai":    [r"\bhealthcare\s+ai\b", r"\bhealth\s*(?:tech|care)\b",
                             r"\bclinical\s+ai\b", r"\bmedical\s+ai\b"],
        "drug discovery":   [r"\bdrug\s+discovery\b"],
        "ehr/fhir":         [r"\behr\b", r"\bfhir\b", r"\bhl7\b"],
        "hipaa":            [r"\bhipaa\b"],
        "dicom":            [r"\bdicom\b"],
        "genomics":         [r"\bgenomics\b", r"\bbioinformatics\b"],
        "clinical nlp":     [r"\bclinical\s+nlp\b", r"\bmedical\s+nlp\b"],
        "fintech":          [r"\bfintech\b", r"\bfinancial\s+(?:tech|ai)\b"],
        "autonomous":       [r"\bautonomous\b", r"\bself[\-\s]driving\b"],
        "robotics":         [r"\brobotics\b"],
    },
}

# Pre-compile regex patterns
TECH_TAXONOMY = {}
for category, skills in _RAW_TAXONOMY.items():
    for skill_name, patterns in skills.items():
        compiled = [re.compile(p, re.IGNORECASE) for p in patterns]
        TECH_TAXONOMY[skill_name] = (category, compiled)

# Requirement signal words
_REQUIRED_SIGNALS = re.compile(
    r"\b(must\s+have|required|mandatory|essential|minimum|need\s+to\s+know|strong\s+experience)\b",
    re.IGNORECASE,
)
_PREFERRED_SIGNALS = re.compile(
    r"\b(nice\s+to\s+have|preferred|bonus|plus|ideal|desirable|familiarity\s+with|exposure\s+to)\b",
    re.IGNORECASE,
)

# Education patterns
_EDUCATION_PATTERNS = [
    (re.compile(r"\b(?:ph\.?d|doctorate)\b", re.I), "phd"),
    (re.compile(r"\b(?:m\.?s\.?|m\.?sc|master'?s?|mtech|m\.?\s*tech)\b", re.I), "masters"),
    (re.compile(r"\b(?:b\.?s\.?|b\.?sc|bachelor'?s?|btech|b\.?\s*tech|b\.?e\.?)\b", re.I), "bachelors"),
]
_EDU_REQUIRED = re.compile(r"\b(required|mandatory|must|minimum)\b", re.I)
_EDU_PREFERRED = re.compile(r"\b(preferred|ideal|desired|or\s+equivalent|plus)\b", re.I)
_EDU_FIELDS = re.compile(
    r"\bin\s+(computer\s+science|data\s+science|machine\s+learning|ai|"
    r"mathematics|statistics|engineering|electrical|biomedical|physics|"
    r"information\s+technology|computational|related\s+field)",
    re.IGNORECASE,
)

# Experience patterns
_EXP_PATTERN = re.compile(r"(\d+)\s*[\-–to]+\s*(\d+)\s*(?:years?|yrs?)", re.I)
_EXP_SINGLE = re.compile(r"(\d+)\+?\s*(?:years?|yrs?)\s*(?:of)?\s*(?:experience|exp)", re.I)


# ─── Analysis State ────────────────────────────────────────────────────────

analysis_state = {
    "running": False,
    "run_id": None,
    "status": "idle",
    "total": 0,
    "processed": 0,
    "phase": "",
    "log": [],
}
_analysis_lock = threading.Lock()


# ─── Extraction Functions ──────────────────────────────────────────────────

def _infer_requirement_level(text: str, match_start: int) -> str:
    """Check ~150 chars around a skill match for requirement signals."""
    window_start = max(0, match_start - 150)
    window_end = min(len(text), match_start + 150)
    window = text[window_start:window_end]

    if _REQUIRED_SIGNALS.search(window):
        return "required"
    if _PREFERRED_SIGNALS.search(window):
        return "preferred"
    return "mentioned"


def regex_extract_skills(text: str) -> list[dict]:
    """Fast regex scan of text against TECH_TAXONOMY.

    Returns: [{"skill": "pytorch", "category": "AI_ML", "required_level": "mentioned"}, ...]
    """
    if not text:
        return []

    found = []
    seen = set()

    for skill_name, (category, patterns) in TECH_TAXONOMY.items():
        for pattern in patterns:
            m = pattern.search(text)
            if m and skill_name not in seen:
                seen.add(skill_name)
                level = _infer_requirement_level(text, m.start())
                found.append({
                    "skill": skill_name,
                    "category": category,
                    "required_level": level,
                })
                break

    return found


def regex_extract_education(text: str) -> list[dict]:
    """Extract education requirements from text.

    Returns: [{"degree_level": "masters", "requirement": "preferred", "field": "computer science"}]
    """
    if not text:
        return []

    found = []
    seen = set()

    for pattern, degree_level in _EDUCATION_PATTERNS:
        m = pattern.search(text)
        if m and degree_level not in seen:
            seen.add(degree_level)
            window = text[max(0, m.start() - 100):min(len(text), m.end() + 100)]
            if _EDU_REQUIRED.search(window):
                req = "required"
            elif _EDU_PREFERRED.search(window):
                req = "preferred"
            else:
                req = "preferred"

            field_match = _EDU_FIELDS.search(window)
            field = field_match.group(1).strip() if field_match else None

            found.append({
                "degree_level": degree_level,
                "requirement": req,
                "field": field,
            })

    return found


def _parse_experience(text: str) -> str | None:
    """Extract experience range from text. Returns '2-4' or '5+' or None."""
    if not text:
        return None
    m = _EXP_PATTERN.search(text)
    if m:
        return f"{m.group(1)}-{m.group(2)}"
    m = _EXP_SINGLE.search(text)
    if m:
        return f"{m.group(1)}+"
    return None


def _experience_bucket(exp_str: str) -> str:
    """Convert experience string to bucket."""
    if not exp_str:
        return "not_specified"
    nums = re.findall(r'\d+', exp_str)
    if not nums:
        return "not_specified"
    low = int(nums[0])
    if low <= 2:
        return "0-2 years"
    if low <= 5:
        return "2-5 years"
    if low <= 10:
        return "5-10 years"
    return "10+ years"


# ─── LLM Extraction ────────────────────────────────────────────────────────

_SKILLS_PROMPT = """Analyze this job posting and extract ALL technical skills and requirements.

Job posting:
{content}

Return a JSON object with exactly this structure:
{{
    "skills": [
        {{"name": "Python", "category": "Languages", "level": "required"}},
        {{"name": "PyTorch", "category": "AI_ML", "level": "preferred"}}
    ],
    "education": {{
        "degree": "masters",
        "requirement": "preferred",
        "field": "computer science"
    }},
    "experience_years": "2-4"
}}

Valid categories: Languages, Frameworks, Cloud, AI_ML, Databases, DevOps, Domain
Valid levels: required, preferred, mentioned
Reply ONLY with valid JSON, no markdown."""


def llm_extract_skills(content: str) -> dict | None:
    """Use Gemini to extract structured skills from job content."""
    api_key = os.getenv("GEMINI_API_KEY", "")
    if not api_key:
        return None

    try:
        resp = requests.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-lite:generateContent?key={api_key}",
            json={
                "contents": [{"parts": [{"text": _SKILLS_PROMPT.format(content=content[:3000])}]}],
                "generationConfig": {"temperature": 0.1, "maxOutputTokens": 800},
            },
            timeout=15,
        )
        if resp.status_code != 200:
            return None

        text = resp.json()["candidates"][0]["content"]["parts"][0]["text"]
        text = text.strip()
        if text.startswith("```"):
            text = re.sub(r"^```\w*\n?", "", text)
            text = re.sub(r"\n?```$", "", text)
        return json.loads(text)
    except Exception as e:
        log.debug(f"LLM extraction error: {e}")
        return None


# ─── Full Analysis (Background Thread) ─────────────────────────────────────

def run_full_analysis(conn: sqlite3.Connection, use_llm: bool = False, llm_sample: int = 100):
    """Phase 1: regex scan all jobs → Phase 2: optional LLM → Phase 3: aggregate."""
    global analysis_state

    try:
        # Get all jobs with their post content
        rows = conn.execute(
            """SELECT j.id as job_id, j.role, j.company, j.experience,
                      COALESCE(p.full_content, p.content) as content
               FROM jobs j
               JOIN posts p ON p.id = j.post_id
               WHERE p.is_hiring = 1""",
        ).fetchall()

        total = len(rows)
        with _analysis_lock:
            analysis_state["total"] = total
            analysis_state["phase"] = "regex_scan"

        # Clear old data
        conn.execute("DELETE FROM skill_mentions")
        conn.execute("DELETE FROM education_demands")
        conn.commit()

        # Phase 1: Regex scan
        for i, row in enumerate(rows):
            row = dict(row)
            job_id = row["job_id"]
            text = (row.get("content") or "") + " " + (row.get("role") or "")

            # Extract skills
            skills = regex_extract_skills(text)
            for s in skills:
                try:
                    conn.execute(
                        """INSERT OR IGNORE INTO skill_mentions (job_id, skill_name, category, required_level, source)
                           VALUES (?, ?, ?, ?, 'regex')""",
                        (job_id, s["skill"], s["category"], s["required_level"]),
                    )
                except Exception:
                    pass

            # Extract education
            edu = regex_extract_education(text)
            for e in edu:
                try:
                    conn.execute(
                        "INSERT INTO education_demands (job_id, degree_level, requirement, field) VALUES (?, ?, ?, ?)",
                        (job_id, e["degree_level"], e["requirement"], e.get("field")),
                    )
                except Exception:
                    pass

            if (i + 1) % 50 == 0:
                conn.commit()
                with _analysis_lock:
                    analysis_state["processed"] = i + 1

        conn.commit()
        with _analysis_lock:
            analysis_state["processed"] = total

        # Phase 2: LLM enrichment (optional)
        if use_llm and os.getenv("GEMINI_API_KEY"):
            with _analysis_lock:
                analysis_state["phase"] = "llm_enrichment"
                analysis_state["processed"] = 0

            # Pick top posts by smart_score or domain_relevance
            llm_rows = conn.execute(
                """SELECT j.id as job_id, COALESCE(p.full_content, p.content) as content
                   FROM jobs j JOIN posts p ON p.id = j.post_id
                   WHERE p.is_hiring = 1
                   ORDER BY p.smart_score DESC NULLS LAST, p.domain_relevance = 'High' DESC
                   LIMIT ?""",
                (llm_sample,),
            ).fetchall()

            for i, lrow in enumerate(llm_rows):
                lrow = dict(lrow)
                result = llm_extract_skills(lrow["content"])
                if result and "skills" in result:
                    for s in result["skills"]:
                        name = s.get("name", "").lower().strip()
                        cat = s.get("category", "AI_ML")
                        level = s.get("level", "mentioned")
                        if name:
                            try:
                                conn.execute(
                                    """INSERT OR REPLACE INTO skill_mentions
                                       (job_id, skill_name, category, required_level, source)
                                       VALUES (?, ?, ?, ?, 'llm')""",
                                    (lrow["job_id"], name, cat, level),
                                )
                            except Exception:
                                pass
                if (i + 1) % 10 == 0:
                    conn.commit()
                    with _analysis_lock:
                        analysis_state["processed"] = i + 1
                time.sleep(1.0)
            conn.commit()

        # Phase 3: Rebuild aggregates
        with _analysis_lock:
            analysis_state["phase"] = "aggregation"

        conn.execute("DELETE FROM skill_demand_summary")

        conn.execute(
            """INSERT INTO skill_demand_summary (skill_name, category, mention_count, percentage,
                   required_count, preferred_count, last_updated)
               SELECT
                   sm.skill_name,
                   sm.category,
                   COUNT(DISTINCT sm.job_id) as mention_count,
                   ROUND(COUNT(DISTINCT sm.job_id) * 100.0 / ?, 1) as percentage,
                   SUM(CASE WHEN sm.required_level = 'required' THEN 1 ELSE 0 END) as required_count,
                   SUM(CASE WHEN sm.required_level = 'preferred' THEN 1 ELSE 0 END) as preferred_count,
                   datetime('now')
               FROM skill_mentions sm
               GROUP BY sm.skill_name, sm.category
               ORDER BY mention_count DESC""",
            (total,),
        )
        conn.commit()

        # Update run record
        if analysis_state.get("run_id"):
            conn.execute(
                "UPDATE skills_analysis_runs SET status='completed', processed=?, finished_at=datetime('now') WHERE id=?",
                (total, analysis_state["run_id"]),
            )
            conn.commit()

        with _analysis_lock:
            analysis_state["status"] = "completed"
            analysis_state["phase"] = "done"
            analysis_state["running"] = False

        log.info(f"Skills analysis complete: {total} jobs processed")

    except Exception as e:
        log.error(f"Skills analysis error: {e}")
        with _analysis_lock:
            analysis_state["status"] = "failed"
            analysis_state["running"] = False
            analysis_state["log"].append(f"ERROR: {e}")
        if analysis_state.get("run_id"):
            try:
                conn.execute(
                    "UPDATE skills_analysis_runs SET status='failed', finished_at=datetime('now') WHERE id=?",
                    (analysis_state["run_id"],),
                )
                conn.commit()
            except Exception:
                pass


def start_analysis(use_llm: bool = False, llm_sample: int = 100) -> dict:
    """Start background skills analysis. Returns status dict."""
    from db import init_db

    with _analysis_lock:
        if analysis_state["running"]:
            return {"status": "error", "message": "Analysis already running"}

    conn = init_db()
    total = conn.execute("SELECT COUNT(*) FROM jobs j JOIN posts p ON p.id = j.post_id WHERE p.is_hiring = 1").fetchone()[0]

    cur = conn.execute("INSERT INTO skills_analysis_runs (total_jobs) VALUES (?)", (total,))
    run_id = cur.lastrowid
    conn.commit()

    with _analysis_lock:
        analysis_state.update({
            "running": True,
            "run_id": run_id,
            "status": "running",
            "total": total,
            "processed": 0,
            "phase": "starting",
            "log": [],
        })

    def _worker():
        wconn = init_db()
        try:
            run_full_analysis(wconn, use_llm=use_llm, llm_sample=llm_sample)
        finally:
            wconn.close()

    threading.Thread(target=_worker, daemon=True).start()
    return {"status": "started", "run_id": run_id, "total_jobs": total}


def get_analysis_status() -> dict:
    with _analysis_lock:
        return {
            "running": analysis_state["running"],
            "status": analysis_state["status"],
            "phase": analysis_state["phase"],
            "total": analysis_state["total"],
            "processed": analysis_state["processed"],
        }


# ─── Dashboard Data ────────────────────────────────────────────────────────

def get_dashboard_data(conn: sqlite3.Connection) -> dict:
    """Return aggregated skills data for the dashboard."""
    # Check if we have data
    count = conn.execute("SELECT COUNT(*) FROM skill_demand_summary").fetchone()[0]
    if count == 0:
        return {"has_data": False}

    # Top skills
    top_skills = conn.execute(
        """SELECT skill_name, category, mention_count, percentage, required_count, preferred_count
           FROM skill_demand_summary
           ORDER BY mention_count DESC
           LIMIT 50""",
    ).fetchall()

    # By category
    by_category = {}
    for row in top_skills:
        row = dict(row)
        cat = row["category"]
        if cat not in by_category:
            by_category[cat] = []
        by_category[cat].append(row)

    # Education stats
    total_edu_jobs = conn.execute("SELECT COUNT(DISTINCT job_id) FROM education_demands").fetchone()[0]
    edu_stats = {}
    if total_edu_jobs > 0:
        for level in ["bachelors", "masters", "phd"]:
            req = conn.execute(
                "SELECT COUNT(DISTINCT job_id) FROM education_demands WHERE degree_level=? AND requirement='required'",
                (level,),
            ).fetchone()[0]
            pref = conn.execute(
                "SELECT COUNT(DISTINCT job_id) FROM education_demands WHERE degree_level=? AND requirement='preferred'",
                (level,),
            ).fetchone()[0]
            total_jobs = conn.execute("SELECT COUNT(DISTINCT job_id) FROM skill_mentions").fetchone()[0] or 1
            edu_stats[f"{level}_required_pct"] = round(req * 100.0 / total_jobs, 1)
            edu_stats[f"{level}_preferred_pct"] = round(pref * 100.0 / total_jobs, 1)

    # Experience distribution
    exp_rows = conn.execute(
        """SELECT j.experience FROM jobs j
           JOIN posts p ON p.id = j.post_id
           WHERE p.is_hiring = 1 AND j.experience IS NOT NULL AND j.experience != ''""",
    ).fetchall()
    exp_buckets = {"0-2 years": 0, "2-5 years": 0, "5-10 years": 0, "10+ years": 0, "not_specified": 0}
    for r in exp_rows:
        bucket = _experience_bucket(r[0])
        exp_buckets[bucket] = exp_buckets.get(bucket, 0) + 1
    total_exp = sum(exp_buckets.values()) or 1
    exp_dist = {k: round(v * 100.0 / total_exp, 1) for k, v in exp_buckets.items()}

    # Last analysis
    last_run = conn.execute(
        "SELECT started_at, total_jobs, processed FROM skills_analysis_runs WHERE status='completed' ORDER BY id DESC LIMIT 1"
    ).fetchone()

    total_jobs_analyzed = conn.execute("SELECT COUNT(DISTINCT job_id) FROM skill_mentions").fetchone()[0]
    unique_skills = conn.execute("SELECT COUNT(*) FROM skill_demand_summary").fetchone()[0]

    return {
        "has_data": True,
        "total_jobs_analyzed": total_jobs_analyzed,
        "unique_skills": unique_skills,
        "last_analysis": dict(last_run)["started_at"] if last_run else None,
        "top_skills": [dict(r) for r in top_skills],
        "by_category": by_category,
        "education_stats": edu_stats,
        "experience_distribution": exp_dist,
    }


# ─── Gap Analysis ──────────────────────────────────────────────────────────

def compute_gap_analysis(conn: sqlite3.Connection) -> dict:
    """Compare RESUME_SKILLS against market demands."""
    from config import RESUME_SKILLS

    # Normalize resume skill names
    resume_skills_lower = {k.lower(): v for k, v in RESUME_SKILLS.items()}

    # Alias map for common name differences (resume name → taxonomy name)
    _SKILL_ALIASES = {
        "generative ai": "genai",
        "machine learning": "deep learning",
        "knowledge graph": "neo4j",
        "graph database": "neo4j",
        "data pipeline": "airflow",
        "etl": "spark",
    }

    # Build a set of all terms the user "knows" (including aliases)
    user_terms = set(resume_skills_lower.keys())
    for rsk in list(resume_skills_lower.keys()):
        if rsk in _SKILL_ALIASES:
            user_terms.add(_SKILL_ALIASES[rsk])

    # Get market demands
    market = conn.execute(
        "SELECT skill_name, category, mention_count, percentage, required_count, preferred_count FROM skill_demand_summary ORDER BY mention_count DESC"
    ).fetchall()

    if not market:
        return {"has_data": False}

    strengths = []
    gaps = []
    underutilized = []

    market_skills_set = set()
    for row in market:
        row = dict(row)
        skill = row["skill_name"]
        market_skills_set.add(skill)

        # Check if user has this skill (exact, alias, or partial match)
        has_skill = skill in user_terms
        if not has_skill:
            for ut in user_terms:
                if ut in skill or skill in ut:
                    has_skill = True
                    break

        if has_skill:
            strengths.append({
                "skill": skill,
                "category": row["category"],
                "market_pct": row["percentage"],
                "mention_count": row["mention_count"],
                "user_weight": resume_skills_lower.get(skill, 1),
            })
        else:
            # Only flag as a gap if it appears in > 3% of jobs
            if row["percentage"] >= 3.0:
                req_ratio = row["required_count"] / max(row["mention_count"], 1)
                if row["percentage"] >= 20:
                    priority = 1
                elif row["percentage"] >= 10:
                    priority = 2
                else:
                    priority = 3
                gaps.append({
                    "skill": skill,
                    "category": row["category"],
                    "market_pct": row["percentage"],
                    "mention_count": row["mention_count"],
                    "required_pct": round(req_ratio * 100, 1),
                    "priority": priority,
                })

    # Find underutilized resume skills
    for rsk, weight in resume_skills_lower.items():
        # Check if any market skill matches this resume skill
        matched = rsk in market_skills_set
        if not matched:
            for ms in market_skills_set:
                if rsk in ms or ms in rsk:
                    matched = True
                    break
            if not matched and rsk in _SKILL_ALIASES:
                matched = _SKILL_ALIASES[rsk] in market_skills_set
        if not matched:
            underutilized.append({
                "skill": rsk,
                "user_weight": weight,
                "note": "Not seen in job postings",
            })

    # Readiness score: % of top-20 market skills the user has
    top_20 = [dict(r) for r in market[:20]]
    top_20_matched = sum(1 for s in top_20 if s["skill_name"] in user_terms
                         or any(ut in s["skill_name"] or s["skill_name"] in ut for ut in user_terms))
    readiness_pct = round(top_20_matched / max(len(top_20), 1) * 100, 1)

    # Education insight
    edu_stats = {}
    total_jobs = conn.execute("SELECT COUNT(DISTINCT job_id) FROM skill_mentions").fetchone()[0] or 1
    for level in ["masters", "phd"]:
        req = conn.execute(
            "SELECT COUNT(DISTINCT job_id) FROM education_demands WHERE degree_level=? AND requirement='required'",
            (level,),
        ).fetchone()[0]
        edu_stats[f"{level}_required_pct"] = round(req * 100.0 / total_jobs, 1)

    ms_req = edu_stats.get("masters_required_pct", 0)
    phd_req = edu_stats.get("phd_required_pct", 0)
    edu_insight = f"Only {ms_req}% strictly require a Master's, {phd_req}% require PhD. A B.Tech is sufficient for {round(100 - ms_req - phd_req)}% of roles."

    # Top gap
    top_gap = gaps[0]["skill"] if gaps else None

    return {
        "has_data": True,
        "readiness_score": readiness_pct,
        "top_gap": top_gap,
        "strengths": sorted(strengths, key=lambda x: x["market_pct"], reverse=True),
        "gaps": sorted(gaps, key=lambda x: (-x["priority"], -x["market_pct"])),
        "underutilized": underutilized,
        "education_insight": edu_insight,
        "education_stats": edu_stats,
    }


# ─── Trends & News (Gemini-powered) ────────────────────────────────────────

_trend_cache = {"data": None, "fetched_at": None}
_news_cache = {"data": None, "fetched_at": None}
_CACHE_TTL = timedelta(hours=24)


def _call_gemini(prompt: str, max_tokens: int = 2000) -> str | None:
    api_key = os.getenv("GEMINI_API_KEY", "")
    if not api_key:
        return None
    try:
        resp = requests.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-lite:generateContent?key={api_key}",
            json={
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": 0.7, "maxOutputTokens": max_tokens},
            },
            timeout=30,
        )
        if resp.status_code == 200:
            return resp.json()["candidates"][0]["content"]["parts"][0]["text"]
    except Exception as e:
        log.debug(f"Gemini call error: {e}")
    return None


def get_trend_data() -> dict:
    """Return cached trends or generate fresh data."""
    if _trend_cache["data"] and _trend_cache["fetched_at"] and \
       datetime.now() - _trend_cache["fetched_at"] < _CACHE_TTL:
        return _trend_cache["data"]
    return {"has_data": False, "message": "Click Refresh to fetch latest trends"}


def refresh_trends() -> dict:
    """Fetch fresh trend data from Gemini."""
    prompt = """You are an AI/ML industry analyst. It's April 2026. List the most trending tools, frameworks, and AI models RIGHT NOW for AI/ML Engineers, especially those working in healthcare AI.

Return a JSON object with this exact structure:
{
    "hot_tools": [
        {"name": "Tool Name", "description": "What it does in 1 sentence", "why_hot": "Why it's trending now", "relevance": "High/Medium/Low relevance for Healthcare AI Engineer"}
    ],
    "rising_models": [
        {"name": "Model Name", "description": "What it is", "why_hot": "Why it matters", "relevance": "High/Medium/Low"}
    ],
    "must_know_frameworks": [
        {"name": "Framework", "description": "What it does", "why_hot": "Why learn it", "relevance": "High/Medium/Low"}
    ]
}

Include 5-7 items per section. Focus on what's genuinely new and in-demand in 2026, not just classics. Reply ONLY with valid JSON."""

    text = _call_gemini(prompt)
    if not text:
        return {"has_data": False, "message": "Could not fetch trends (Gemini API error)"}

    try:
        text = text.strip()
        if text.startswith("```"):
            text = re.sub(r"^```\w*\n?", "", text)
            text = re.sub(r"\n?```$", "", text)
        data = json.loads(text)
        data["has_data"] = True
        data["fetched_at"] = datetime.now().isoformat()
        _trend_cache["data"] = data
        _trend_cache["fetched_at"] = datetime.now()
        return data
    except json.JSONDecodeError as e:
        log.error(f"Trend JSON parse error: {e}")
        return {"has_data": False, "message": f"Failed to parse trend data: {e}"}


def get_news_data() -> dict:
    """Return cached news or generate fresh."""
    if _news_cache["data"] and _news_cache["fetched_at"] and \
       datetime.now() - _news_cache["fetched_at"] < _CACHE_TTL:
        return _news_cache["data"]
    return {"has_data": False, "message": "Click Refresh to fetch latest news"}


def refresh_news() -> dict:
    """Fetch fresh industry news from Gemini."""
    prompt = """You are an AI industry journalist. It's April 2026. List the most important recent news and developments in:
1. Healthcare AI / Clinical AI
2. AI/ML Engineering (tools, frameworks, deployment)
3. AI job market and hiring trends

Return a JSON object:
{
    "articles": [
        {
            "title": "Article title",
            "summary": "2-3 sentence summary",
            "source": "Publication name",
            "date": "2026-04-XX",
            "tags": ["Healthcare AI", "LLMs"],
            "url": ""
        }
    ]
}

Include 8-12 items. Focus on real, significant developments from 2026. Reply ONLY with valid JSON."""

    text = _call_gemini(prompt)
    if not text:
        return {"has_data": False, "message": "Could not fetch news (Gemini API error)"}

    try:
        text = text.strip()
        if text.startswith("```"):
            text = re.sub(r"^```\w*\n?", "", text)
            text = re.sub(r"\n?```$", "", text)
        data = json.loads(text)
        data["has_data"] = True
        data["fetched_at"] = datetime.now().isoformat()
        _news_cache["data"] = data
        _news_cache["fetched_at"] = datetime.now()
        return data
    except json.JSONDecodeError as e:
        log.error(f"News JSON parse error: {e}")
        return {"has_data": False, "message": f"Failed to parse news data: {e}"}
