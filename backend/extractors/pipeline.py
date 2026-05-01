"""Unified post extraction pipeline — replaces 4 duplicated ~30-line blocks."""

from extractors.text import (
    extract_emails, extract_phones, extract_hashtags, extract_skills, extract_roles,
    extract_location, extract_experience, normalize_experience, score_domain_relevance,
    is_hiring_post,
)
from extractors.fitness import is_good_fit
from llm.extraction import llm_extract, llm_extract_emails
from db import content_hash, DedupCache, post_exists


def process_single_post(
    raw: dict,
    dedup: DedupCache | None = None,
    conn=None,
    query: str = "",
    on_event=None,
    skip_fitness: bool = False,
) -> dict | None:
    """Unified post processing: emails + LLM + roles + fitness + domain scoring.

    Returns a processed post dict, or None if post should be skipped
    (duplicate, bad fit, too short, etc.).

    Args:
        raw: Raw post dict with keys like content, authorName, postUrl, emails, etc.
        dedup: DedupCache for in-memory dedup. If None, uses conn for SQL dedup.
        conn: DB connection for SQL dedup fallback.
        query: Search query that found this post.
        on_event: Event callback for logging.
        skip_fitness: If True, skip fitness check (for feed scraper etc.).
    """
    def emit(event):
        if on_event:
            try:
                on_event(event)
            except Exception:
                pass

    content = raw.get("content", "").strip()
    if not content or len(content) < 20:
        return None

    # Dedup
    c_hash = content_hash(content)
    post_url = raw.get("postUrl", raw.get("post_url", ""))

    if dedup:
        if dedup.exists(post_url, c_hash, content):
            emit({"type": "dedup", "author": raw.get("authorName", raw.get("author_name", "Unknown"))})
            return None
    elif conn:
        if post_exists(conn, post_url, c_hash):
            return None

    # Emails: JS extraction + regex + LLM deobfuscation
    emails = raw.get("emails", raw.get("email", ""))
    regex_emails = extract_emails(content)
    if regex_emails and regex_emails not in emails:
        emails = ", ".join(filter(None, [emails, regex_emails]))
    if not emails:
        llm_emails = llm_extract_emails(content)
        if llm_emails:
            emails = ", ".join(llm_emails)

    # LLM extraction (role, company, location, experience)
    emit({"type": "llm", "author": raw.get("authorName", raw.get("author_name", "Unknown")),
          "content_preview": content[:80]})
    llm = llm_extract(content)
    roles = llm.get("role") or extract_roles(content)
    location = llm.get("location") or extract_location(content)
    experience = llm.get("experience") or extract_experience(content)
    company = llm.get("company", "")

    if experience and not any(c.isdigit() for c in experience[:3]):
        experience = normalize_experience(experience)

    work_mode = llm.get("work_mode", "")
    domain = score_domain_relevance(content)

    # Fitness check
    if not skip_fitness:
        fit, reason = is_good_fit(roles, experience)
        if not fit:
            emit({"type": "skip",
                  "author": raw.get("authorName", raw.get("author_name", ""))[:20],
                  "reason": f"{roles[:20]} | {reason}"})
            return None

    author_url = raw.get("authorUrl", raw.get("author_profile", ""))

    data = {
        "author_name":     raw.get("authorName", raw.get("author_name", "")) or "Unknown",
        "author_profile":  author_url,
        "author_headline": raw.get("headline", raw.get("author_headline", "")),
        "post_url":        post_url,
        "content":         content,
        "role_hiring_for": roles,
        "company":         company,
        "email":           emails,
        "phone":           extract_phones(content),
        "hashtags":        extract_hashtags(content),
        "skills":          extract_skills(content),
        "location":        location,
        "experience":      experience,
        "work_mode":       work_mode,
        "domain_relevance": domain,
        "post_date":       raw.get("postDate", raw.get("post_date", "")),
        "keyword_matched": query,
        "is_hiring":       is_hiring_post(content),
    }

    # Register in dedup cache
    if dedup:
        dedup.add(post_url, c_hash, content)

    return data


def process_raw_posts(raw_posts: list[dict], conn, query: str = "") -> list[dict]:
    """Batch process raw scraped posts. Works with output from any scraper."""
    from rich.console import Console
    console = Console()
    processed = []
    sno = 1

    for raw in raw_posts:
        data = process_single_post(raw, conn=conn, query=query)
        if data is None:
            continue

        data["sno"] = sno
        processed.append(data)
        sno += 1

        console.print(
            f"  [bold green]#{data['sno']}[/] "
            f"[white]{data['author_name'][:20]}[/] | "
            f"[cyan]{str(data['role_hiring_for'])[:20]}[/] | "
            f"Email: [yellow]{(data['email'] or 'none')[:30]}[/]"
        )

    return processed
