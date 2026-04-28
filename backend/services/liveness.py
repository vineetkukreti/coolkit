"""
liveness.py — Python port of career-ops liveness checking.

Classifies job posting URLs as active, expired, or uncertain
using HTTP checks and regex pattern matching.
"""

import re
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

from utils.network import is_private_ip

logger = logging.getLogger(__name__)

USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

# ---------------------------------------------------------------------------
# Patterns (ported from liveness-core.mjs)
# ---------------------------------------------------------------------------

EXPIRATION_PATTERNS = [
    re.compile(r"job (is )?no longer available", re.IGNORECASE),
    re.compile(r"job.*no longer open", re.IGNORECASE),
    re.compile(r"position has been filled", re.IGNORECASE),
    re.compile(r"this job has expired", re.IGNORECASE),
    re.compile(r"job posting has expired", re.IGNORECASE),
    re.compile(r"no longer accepting applications", re.IGNORECASE),
    re.compile(r"this (position|role|job) (is )?no longer", re.IGNORECASE),
    re.compile(r"this job (listing )?is closed", re.IGNORECASE),
    re.compile(r"job (listing )?not found", re.IGNORECASE),
    re.compile(r"the page you are looking for doesn.t exist", re.IGNORECASE),
    re.compile(r"diese stelle (ist )?(nicht mehr|bereits) besetzt", re.IGNORECASE),
    re.compile(r"offre (expir[ée]e|n'est plus disponible)", re.IGNORECASE),
]

LISTING_PAGE_PATTERNS = [
    re.compile(r"\d+\s+jobs?\s+found", re.IGNORECASE),
    re.compile(r"search for jobs page is loaded", re.IGNORECASE),
]

EXPIRED_URL_PATTERNS = [
    re.compile(r"[?&]error=true", re.IGNORECASE),
]

APPLY_PATTERNS = [
    re.compile(r"\bapply\b", re.IGNORECASE),
    re.compile(r"\bsolicitar\b", re.IGNORECASE),
    re.compile(r"\bbewerben\b", re.IGNORECASE),
    re.compile(r"\bpostuler\b", re.IGNORECASE),
    re.compile(r"submit application", re.IGNORECASE),
    re.compile(r"easy apply", re.IGNORECASE),
    re.compile(r"start application", re.IGNORECASE),
    re.compile(r"ich bewerbe mich", re.IGNORECASE),
]

MIN_CONTENT_CHARS = 300

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _first_match(patterns: list[re.Pattern], text: str = "") -> re.Pattern | None:
    """Return the first pattern that matches text, or None."""
    for p in patterns:
        if p.search(text):
            return p
    return None


def _has_apply_control(controls: list[str] | None = None) -> bool:
    """Return True if any control label matches an apply pattern."""
    if not controls:
        return False
    return any(
        p.search(ctrl)
        for ctrl in controls
        for p in APPLY_PATTERNS
    )


# ---------------------------------------------------------------------------
# Classification
# ---------------------------------------------------------------------------


def classify_liveness(
    status_code: int,
    final_url: str,
    body_text: str,
    apply_controls: list[str] | None = None,
) -> dict:
    """
    Classify a job posting as active, expired, or uncertain.

    Returns dict with keys "result" and "reason".
    """
    if status_code in (404, 410):
        return {"result": "expired", "reason": f"HTTP {status_code}"}

    expired_url = _first_match(EXPIRED_URL_PATTERNS, final_url)
    if expired_url:
        return {"result": "expired", "reason": f"redirect to {final_url}"}

    expired_body = _first_match(EXPIRATION_PATTERNS, body_text)
    if expired_body:
        return {"result": "expired", "reason": f"pattern matched: {expired_body.pattern}"}

    if _has_apply_control(apply_controls):
        return {"result": "active", "reason": "visible apply control detected"}

    listing_page = _first_match(LISTING_PAGE_PATTERNS, body_text)
    if listing_page:
        return {"result": "expired", "reason": f"pattern matched: {listing_page.pattern}"}

    if len(body_text.strip()) < MIN_CONTENT_CHARS:
        return {"result": "expired", "reason": "insufficient content — likely nav/footer only"}

    return {"result": "uncertain", "reason": "content present but no visible apply control found"}


# ---------------------------------------------------------------------------
# HTTP check (no browser)
# ---------------------------------------------------------------------------


def check_url_liveness(url: str, timeout: int = 10) -> dict:
    """
    Check a single URL for liveness using an HTTP GET request.

    Returns dict: {"url": str, "result": str, "reason": str}
    """
    # SSRF protection: block requests to private/internal IPs
    if is_private_ip(url):
        return {"url": url, "result": "uncertain", "reason": "blocked: private/internal IP address"}

    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }

    try:
        resp = requests.get(url, headers=headers, timeout=timeout, allow_redirects=True)
        status_code = resp.status_code
        final_url = resp.url
        body_text = resp.text

        # Extract rough apply-button signals from raw HTML
        # (without a real DOM we look for common button/link text)
        apply_controls: list[str] = []
        for pat in APPLY_PATTERNS:
            matches = pat.findall(body_text)
            apply_controls.extend(matches)

        result = classify_liveness(status_code, final_url, body_text, apply_controls)
        return {"url": url, **result}

    except requests.exceptions.Timeout:
        return {"url": url, "result": "uncertain", "reason": "request timed out"}
    except requests.exceptions.ConnectionError as exc:
        return {"url": url, "result": "uncertain", "reason": f"connection error: {exc}"}
    except requests.exceptions.RequestException as exc:
        return {"url": url, "result": "uncertain", "reason": f"request error: {exc}"}


# ---------------------------------------------------------------------------
# Batch check
# ---------------------------------------------------------------------------


def check_urls_batch(urls: list[str], max_workers: int = 5) -> list[dict]:
    """Check multiple URLs in parallel using a thread pool."""
    results: list[dict] = [None] * len(urls)  # type: ignore[list-item]

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        future_to_idx = {
            pool.submit(check_url_liveness, url): idx
            for idx, url in enumerate(urls)
        }
        for future in as_completed(future_to_idx):
            idx = future_to_idx[future]
            try:
                results[idx] = future.result()
            except Exception as exc:
                results[idx] = {
                    "url": urls[idx],
                    "result": "uncertain",
                    "reason": f"unexpected error: {exc}",
                }

    return results


# ---------------------------------------------------------------------------
# DB integration
# ---------------------------------------------------------------------------


def check_and_update_db(conn, limit: int = 50) -> dict:
    """
    Check liveness of job posts stored in the database and update is_live.

    Looks for rows that have an apply_url or post_url. Checks up to `limit`
    rows and sets is_live to 1 (active), 0 (expired), or -1 (uncertain).

    Returns summary dict: {"checked": N, "active": N, "expired": N, "uncertain": N}
    """
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT id, COALESCE(apply_url, post_url) AS url
        FROM posts
        WHERE COALESCE(apply_url, post_url) IS NOT NULL
        ORDER BY created_at DESC
        LIMIT ?
        """,
        (limit,),
    )

    rows = cursor.fetchall()
    if not rows:
        return {"checked": 0, "active": 0, "expired": 0, "uncertain": 0}

    urls = [row[1] for row in rows]
    ids = [row[0] for row in rows]

    results = check_urls_batch(urls)

    is_live_map = {"active": 1, "expired": 0, "uncertain": -1}
    summary = {"checked": len(results), "active": 0, "expired": 0, "uncertain": 0}

    for row_id, result in zip(ids, results):
        status = result["result"]
        summary[status] += 1
        cursor.execute(
            "UPDATE posts SET is_live = ? WHERE id = ?",
            (is_live_map[status], row_id),
        )

    conn.commit()
    return summary


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python liveness.py <url1> [url2] ...")
        sys.exit(1)

    urls = sys.argv[1:]
    print(f"Checking {len(urls)} URL(s)...\n")

    results = check_urls_batch(urls)
    active = expired = uncertain = 0

    for r in results:
        icon = {"active": "+", "expired": "X", "uncertain": "?"}[r["result"]]
        print(f"[{icon}] {r['result']:<10} {r['url']}")
        if r["result"] != "active":
            print(f"           {r['reason']}")
        if r["result"] == "active":
            active += 1
        elif r["result"] == "expired":
            expired += 1
        else:
            uncertain += 1

    print(f"\nResults: {active} active  {expired} expired  {uncertain} uncertain")
    if expired > 0 or uncertain > 0:
        sys.exit(1)
