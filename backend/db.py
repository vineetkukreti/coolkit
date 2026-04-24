"""
SQLite database layer for LinkedIn Job Parser.
Stores posts, extracted job info, and email outreach tracking.

Usage:
    from db import init_db, insert_posts, query_posts, export_to_excel

    conn = init_db()
    inserted, skipped = insert_posts(conn, posts_list)
    results = query_posts(conn, role="AI Engineer", domain="High", has_email=True)
    export_to_excel(conn, "output.xlsx")
    conn.close()

CLI:
    python db.py --stats
    python db.py --role "AI Engineer" --domain High --has-email
    python db.py --export output.xlsx
    python db.py --import-excel linkedin_posts_20260409_021403.xlsx
"""

import sqlite3
import hashlib
import argparse
import re
from pathlib import Path
from datetime import datetime

DB_PATH = Path("data/linkedin_jobs.db")

SCHEMA = """
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS posts (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    post_url        TEXT,
    content_hash    TEXT NOT NULL,
    author_name     TEXT,
    author_profile  TEXT,
    author_headline TEXT,
    content         TEXT NOT NULL,
    links           TEXT,
    email           TEXT,
    post_date       TEXT,
    keyword_matched TEXT,
    is_hiring       INTEGER DEFAULT 0,
    domain_relevance TEXT,
    created_at      TEXT DEFAULT (datetime('now')),
    updated_at      TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS jobs (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    post_id     INTEGER NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
    role        TEXT,
    company     TEXT,
    location    TEXT,
    experience  TEXT,
    created_at  TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS email_outreach (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    post_id         INTEGER REFERENCES posts(id) ON DELETE CASCADE,
    recipient_email TEXT NOT NULL,
    subject         TEXT,
    body            TEXT,
    status          TEXT DEFAULT 'pending',
    sent_at         TEXT,
    created_at      TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS pipeline_leads (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    post_id         INTEGER REFERENCES posts(id) ON DELETE CASCADE,
    outreach_id     INTEGER REFERENCES email_outreach(id),
    recipient_name  TEXT,
    recipient_email TEXT NOT NULL,
    role            TEXT,
    company         TEXT,
    location        TEXT,
    stage           TEXT DEFAULT 'applied',
    source          TEXT DEFAULT 'email',
    created_at      TEXT DEFAULT (datetime('now')),
    updated_at      TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS pipeline_events (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    lead_id         INTEGER NOT NULL REFERENCES pipeline_leads(id) ON DELETE CASCADE,
    event_type      TEXT NOT NULL,
    title           TEXT,
    content         TEXT,
    created_at      TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS pipeline_notes (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    lead_id         INTEGER NOT NULL REFERENCES pipeline_leads(id) ON DELETE CASCADE,
    content         TEXT NOT NULL,
    created_at      TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_pipeline_stage ON pipeline_leads(stage);
CREATE INDEX IF NOT EXISTS idx_pipeline_events_lead ON pipeline_events(lead_id);
CREATE INDEX IF NOT EXISTS idx_pipeline_notes_lead ON pipeline_notes(lead_id);

CREATE TABLE IF NOT EXISTS startup_leads (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    company_name    TEXT NOT NULL,
    website         TEXT,
    email           TEXT,
    description     TEXT,
    industry        TEXT,
    sector          TEXT,
    location        TEXT,
    city            TEXT,
    state           TEXT,
    country         TEXT DEFAULT 'India',
    funding_info    TEXT,
    employees       TEXT,
    funding_status  TEXT,
    linkedin_url    TEXT,
    facebook_url    TEXT,
    twitter_url     TEXT,
    youtube_url     TEXT,
    other_url       TEXT,
    dipp_recognition TEXT,
    entity_type     TEXT,
    source_file     TEXT,
    email_status    TEXT DEFAULT 'not_contacted',
    tags            TEXT,
    notes           TEXT,
    created_at      TEXT DEFAULT (datetime('now')),
    updated_at      TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_startup_leads_company ON startup_leads(company_name);
CREATE INDEX IF NOT EXISTS idx_startup_leads_industry ON startup_leads(industry);
CREATE INDEX IF NOT EXISTS idx_startup_leads_location ON startup_leads(location);
CREATE INDEX IF NOT EXISTS idx_startup_leads_email_status ON startup_leads(email_status);
CREATE INDEX IF NOT EXISTS idx_startup_leads_email ON startup_leads(email);

CREATE TABLE IF NOT EXISTS applications (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    post_id         INTEGER REFERENCES posts(id) ON DELETE SET NULL,
    platform        TEXT NOT NULL DEFAULT 'unknown',
    job_url         TEXT NOT NULL,
    job_title       TEXT,
    company         TEXT,
    location        TEXT,
    status          TEXT DEFAULT 'pending',
    apply_method    TEXT,
    error_message   TEXT,
    retry_count     INTEGER DEFAULT 0,
    applied_at      TEXT DEFAULT (datetime('now')),
    created_at      TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS daily_quotas (
    date            TEXT PRIMARY KEY,
    target          INTEGER DEFAULT 500,
    applied         INTEGER DEFAULT 0,
    failed          INTEGER DEFAULT 0,
    skipped         INTEGER DEFAULT 0
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_posts_url ON posts(post_url) WHERE post_url IS NOT NULL AND post_url != '';
CREATE INDEX IF NOT EXISTS idx_posts_content_hash ON posts(content_hash);
CREATE INDEX IF NOT EXISTS idx_posts_domain ON posts(domain_relevance);
CREATE INDEX IF NOT EXISTS idx_posts_is_hiring ON posts(is_hiring);
CREATE INDEX IF NOT EXISTS idx_jobs_role ON jobs(role);
CREATE INDEX IF NOT EXISTS idx_jobs_company ON jobs(company);
CREATE INDEX IF NOT EXISTS idx_outreach_status ON email_outreach(status);
CREATE UNIQUE INDEX IF NOT EXISTS idx_applications_url ON applications(job_url);
CREATE INDEX IF NOT EXISTS idx_applications_status ON applications(status);
CREATE INDEX IF NOT EXISTS idx_applications_date ON applications(applied_at);
"""


_URL_RE = re.compile(r'https?://[^\s<>")\]]+')


def extract_links(content: str) -> str:
    """Extract URLs from post content, return comma-separated."""
    if not content:
        return ""
    urls = _URL_RE.findall(content)
    # Deduplicate while preserving order
    seen = set()
    unique = []
    for u in urls:
        u = u.rstrip(".,;:")  # strip trailing punctuation
        if u not in seen:
            seen.add(u)
            unique.append(u)
    return ", ".join(unique)


def _normalize_content(content: str) -> str:
    """Normalize whitespace and strip common LinkedIn artifacts for dedup."""
    import re
    return re.sub(r'\s+', ' ', content).strip().lower()


def content_hash(content: str) -> str:
    return hashlib.sha256(content[:200].lower().encode()).hexdigest()


def content_hash_v2(content: str) -> str:
    """Stronger hash: normalized whitespace, more content."""
    return hashlib.sha256(_normalize_content(content)[:500].encode()).hexdigest()


_MIGRATIONS = [
    # Deep extraction columns
    "ALTER TABLE posts ADD COLUMN full_content TEXT",
    "ALTER TABLE posts ADD COLUMN apply_url TEXT",
    "ALTER TABLE posts ADD COLUMN deep_extracted INTEGER DEFAULT 0",
    "ALTER TABLE posts ADD COLUMN fit_score REAL",
    # Richer job data
    "ALTER TABLE jobs ADD COLUMN salary TEXT",
    "ALTER TABLE jobs ADD COLUMN tech_stack TEXT",
    "ALTER TABLE jobs ADD COLUMN fit_reasons TEXT",
]


def run_migrations(conn):
    """Add new columns safely — idempotent."""
    migrations = [
        *_MIGRATIONS,
        "ALTER TABLE posts ADD COLUMN source TEXT DEFAULT 'linkedin'",
        "ALTER TABLE posts ADD COLUMN is_live TEXT",
        "ALTER TABLE posts ADD COLUMN last_checked_at TEXT",
        "ALTER TABLE email_outreach ADD COLUMN followup_count INTEGER DEFAULT 0",
        "ALTER TABLE email_outreach ADD COLUMN last_followup_at TEXT",
        "ALTER TABLE posts ADD COLUMN smart_score REAL",
    ]
    for sql in migrations:
        try:
            conn.execute(sql)
        except Exception:
            pass  # column already exists
    conn.commit()


def init_db(db_path: str | Path | None = None) -> sqlite3.Connection:
    path = str(db_path or DB_PATH)
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    run_migrations(conn)
    return conn


def post_exists(conn: sqlite3.Connection, post_url: str, c_hash: str) -> bool:
    if post_url:
        row = conn.execute("SELECT 1 FROM posts WHERE post_url = ?", (post_url,)).fetchone()
        if row:
            return True
    row = conn.execute("SELECT 1 FROM posts WHERE content_hash = ?", (c_hash,)).fetchone()
    return row is not None


class DedupCache:
    """In-memory dedup cache. Load once before a scrape session,
    check thousands of posts in O(1) instead of O(n) SQL queries.

    Uses both post_url and content_hash for dedup. Also builds a set
    of normalized content prefixes to catch near-duplicates where only
    whitespace or trailing text differs."""

    def __init__(self, conn: sqlite3.Connection):
        self._urls = set()
        self._hashes = set()
        self._prefixes = set()  # normalized first-100-char prefixes
        rows = conn.execute("SELECT post_url, content_hash, content FROM posts").fetchall()
        for row in rows:
            if row["post_url"]:
                self._urls.add(row["post_url"])
            if row["content_hash"]:
                self._hashes.add(row["content_hash"])
            content = row["content"] if row["content"] else ""
            if content:
                prefix = _normalize_content(content)[:100]
                if len(prefix) >= 40:
                    self._prefixes.add(prefix)

    def exists(self, post_url: str, c_hash: str, content: str = "") -> bool:
        if post_url and post_url in self._urls:
            return True
        if c_hash in self._hashes:
            return True
        # Fuzzy fallback: normalized content prefix match
        if content:
            prefix = _normalize_content(content)[:100]
            if len(prefix) >= 40 and prefix in self._prefixes:
                return True
        return False

    def add(self, post_url: str, c_hash: str, content: str = ""):
        """Register a newly inserted post so it's deduped within the same session."""
        if post_url:
            self._urls.add(post_url)
        if c_hash:
            self._hashes.add(c_hash)
        if content:
            prefix = _normalize_content(content)[:100]
            if len(prefix) >= 40:
                self._prefixes.add(prefix)

    @property
    def size(self) -> int:
        return len(self._urls) + len(self._hashes)


def insert_post(conn: sqlite3.Connection, post: dict) -> int | None:
    """Insert a single post. Returns post id or None if duplicate."""
    c_hash = content_hash(post.get("content", ""))
    post_url = post.get("post_url", "")

    if post_exists(conn, post_url, c_hash):
        return None

    content = post.get("content", "")
    links = extract_links(content)

    cur = conn.execute(
        """INSERT INTO posts
           (post_url, content_hash, author_name, author_profile, author_headline,
            content, links, email, post_date, keyword_matched, is_hiring, domain_relevance,
            full_content, apply_url, deep_extracted, fit_score, source)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            post_url or None,
            c_hash,
            post.get("author_name", ""),
            post.get("author_profile", ""),
            post.get("author_headline", ""),
            content,
            links or None,
            post.get("email", ""),
            post.get("post_date", ""),
            post.get("keyword_matched", ""),
            1 if post.get("is_hiring") else 0,
            post.get("domain_relevance", "Low"),
            post.get("full_content") or None,
            post.get("apply_url") or None,
            1 if post.get("deep_extracted") else 0,
            post.get("fit_score"),
            post.get("source", "linkedin"),
        ),
    )
    post_id = cur.lastrowid

    # Split comma-separated roles into individual job rows
    roles_str = post.get("role_hiring_for", "Not specified")
    roles = [r.strip() for r in roles_str.split(",") if r.strip() and r.strip() != "Not specified"]
    if not roles:
        roles = [roles_str]

    for role in roles:
        conn.execute(
            """INSERT INTO jobs (post_id, role, company, location, experience, salary, tech_stack, fit_reasons)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                post_id,
                role,
                post.get("company", ""),
                post.get("location", ""),
                post.get("experience", ""),
                post.get("salary") or None,
                post.get("tech_stack") or None,
                post.get("fit_reasons") or None,
            ),
        )

    return post_id


def insert_posts(conn: sqlite3.Connection, posts: list[dict]) -> tuple[int, int]:
    """Batch insert posts. Returns (inserted_count, skipped_count)."""
    inserted = 0
    skipped = 0
    for post in posts:
        pid = insert_post(conn, post)
        if pid is not None:
            inserted += 1
        else:
            skipped += 1
    conn.commit()
    return inserted, skipped


def query_posts(
    conn: sqlite3.Connection,
    role: str | None = None,
    domain: str | None = None,
    has_email: bool | None = None,
    is_hiring: bool | None = None,
    company: str | None = None,
    limit: int = 100,
) -> list[dict]:
    """Query posts with optional filters. Returns list of dicts."""
    conditions = []
    params = []

    if role:
        conditions.append("j.role LIKE ?")
        params.append(f"%{role}%")
    if domain:
        conditions.append("p.domain_relevance = ?")
        params.append(domain)
    if has_email is True:
        conditions.append("p.email IS NOT NULL AND p.email != ''")
    if is_hiring is True:
        conditions.append("p.is_hiring = 1")
    if company:
        conditions.append("j.company LIKE ?")
        params.append(f"%{company}%")

    where = "WHERE " + " AND ".join(conditions) if conditions else ""
    params.append(limit)

    rows = conn.execute(
        f"""SELECT DISTINCT p.id, p.author_name, p.author_profile, p.author_headline,
                   p.post_url, p.content, p.links, p.email, p.post_date, p.keyword_matched,
                   p.is_hiring, p.domain_relevance, p.created_at,
                   (SELECT GROUP_CONCAT(j.role, ', ') FROM jobs j WHERE j.post_id = p.id) as role,
                   (SELECT j2.company FROM jobs j2 WHERE j2.post_id = p.id LIMIT 1) as company,
                   (SELECT j3.location FROM jobs j3 WHERE j3.post_id = p.id LIMIT 1) as location,
                   (SELECT j4.experience FROM jobs j4 WHERE j4.post_id = p.id LIMIT 1) as experience
            FROM posts p
            LEFT JOIN jobs j ON j.post_id = p.id
            {where}
            GROUP BY p.id
            ORDER BY p.created_at DESC
            LIMIT ?""",
        params,
    ).fetchall()

    return [dict(r) for r in rows]


def get_stats(conn: sqlite3.Connection) -> dict:
    """Return summary statistics from the database."""
    stats = {}
    stats["total_posts"] = conn.execute("SELECT COUNT(*) FROM posts").fetchone()[0]
    stats["with_email"] = conn.execute("SELECT COUNT(*) FROM posts WHERE email IS NOT NULL AND email != ''").fetchone()[0]
    stats["hiring"] = conn.execute("SELECT COUNT(*) FROM posts WHERE is_hiring = 1").fetchone()[0]

    stats["domain"] = {}
    for level in ("High", "Medium", "Low"):
        stats["domain"][level] = conn.execute(
            "SELECT COUNT(*) FROM posts WHERE domain_relevance = ?", (level,)
        ).fetchone()[0]

    stats["roles"] = {}
    for row in conn.execute("SELECT role, COUNT(*) as cnt FROM jobs GROUP BY role ORDER BY cnt DESC").fetchall():
        stats["roles"][row[0]] = row[1]

    stats["outreach"] = {}
    for row in conn.execute("SELECT status, COUNT(*) as cnt FROM email_outreach GROUP BY status").fetchall():
        stats["outreach"][row[0]] = row[1]

    return stats


# ─── Application Tracking ────────────────────────────────────────────────────

def application_exists(conn: sqlite3.Connection, job_url: str) -> bool:
    """Check if we've already applied to this job URL."""
    if not job_url:
        return False
    row = conn.execute("SELECT 1 FROM applications WHERE job_url = ?", (job_url,)).fetchone()
    return row is not None


def log_application(
    conn: sqlite3.Connection,
    platform: str,
    job_url: str,
    job_title: str = "",
    company: str = "",
    location: str = "",
    status: str = "applied",
    apply_method: str = "manual",
    post_id: int | None = None,
    error_message: str | None = None,
) -> int | None:
    """Log a job application. Returns application id or None if duplicate."""
    if application_exists(conn, job_url):
        return None
    cur = conn.execute(
        """INSERT INTO applications
           (post_id, platform, job_url, job_title, company, location, status, apply_method, error_message)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (post_id, platform, job_url, job_title, company, location, status, apply_method, error_message),
    )
    conn.commit()
    _increment_quota(conn, status)
    return cur.lastrowid


def get_applied_urls(conn: sqlite3.Connection) -> set:
    """Return set of all job URLs we've applied/attempted."""
    rows = conn.execute("SELECT job_url FROM applications").fetchall()
    return {r[0] for r in rows if r[0]}


def get_applications(conn: sqlite3.Connection, status: str | None = None, limit: int = 200) -> list[dict]:
    """Get application history with optional status filter."""
    if status:
        rows = conn.execute(
            "SELECT * FROM applications WHERE status = ? ORDER BY applied_at DESC LIMIT ?",
            (status, limit),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM applications ORDER BY applied_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [dict(r) for r in rows]


def get_application_stats(conn: sqlite3.Connection) -> dict:
    """Get application counts by status."""
    stats = {"applied": 0, "skipped": 0, "failed": 0, "pending": 0, "total": 0}
    for row in conn.execute("SELECT status, COUNT(*) as cnt FROM applications GROUP BY status").fetchall():
        stats[row[0]] = row[1]
    stats["total"] = sum(v for k, v in stats.items() if k != "total")
    return stats


# ─── Daily Quota Tracking ────────────────────────────────────────────────────

def _today() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def _ensure_quota(conn: sqlite3.Connection):
    """Create today's quota row if it doesn't exist."""
    conn.execute(
        "INSERT OR IGNORE INTO daily_quotas (date) VALUES (?)",
        (_today(),),
    )
    conn.commit()


def _increment_quota(conn: sqlite3.Connection, status: str):
    """Increment the appropriate counter in today's quota."""
    _ensure_quota(conn)
    col = {"applied": "applied", "failed": "failed", "skipped": "skipped"}.get(status)
    if col:
        conn.execute(
            f"UPDATE daily_quotas SET {col} = {col} + 1 WHERE date = ?",
            (_today(),),
        )
        conn.commit()


def get_today_quota(conn: sqlite3.Connection) -> dict:
    """Get today's quota status."""
    _ensure_quota(conn)
    row = conn.execute("SELECT * FROM daily_quotas WHERE date = ?", (_today(),)).fetchone()
    return dict(row) if row else {"date": _today(), "target": 500, "applied": 0, "failed": 0, "skipped": 0}


def quota_remaining(conn: sqlite3.Connection) -> int:
    """How many more applications can we send today?"""
    q = get_today_quota(conn)
    return max(0, q["target"] - q["applied"])


def get_unapplied_jobs(conn: sqlite3.Connection, limit: int = 600) -> list[dict]:
    """Get all jobs not yet applied to, ranked by fit score and relevance."""
    rows = conn.execute(
        """SELECT p.id, p.post_url, p.content, p.email, p.domain_relevance, p.fit_score,
                  p.source, p.apply_url,
                  (SELECT GROUP_CONCAT(j.role, ', ') FROM jobs j WHERE j.post_id = p.id) as role,
                  (SELECT j2.company FROM jobs j2 WHERE j2.post_id = p.id LIMIT 1) as company,
                  (SELECT j3.location FROM jobs j3 WHERE j3.post_id = p.id LIMIT 1) as location,
                  (SELECT j4.experience FROM jobs j4 WHERE j4.post_id = p.id LIMIT 1) as experience
           FROM posts p
           WHERE p.is_hiring = 1
             AND p.post_url NOT IN (SELECT job_url FROM applications)
           ORDER BY
             p.fit_score DESC NULLS LAST,
             CASE p.domain_relevance WHEN 'High' THEN 1 WHEN 'Medium' THEN 2 ELSE 3 END,
             CASE WHEN p.email IS NOT NULL AND p.email != '' THEN 0 ELSE 1 END,
             p.created_at DESC
           LIMIT ?""",
        (limit,),
    ).fetchall()
    return [dict(r) for r in rows]


def get_posts_for_outreach(conn: sqlite3.Connection) -> list[dict]:
    """Get posts with emails that haven't been contacted yet.
    Uses scalar subqueries for jobs to avoid duplicate rows when a post has multiple roles.
    Uses INSTR for multi-email matching (comma-separated email fields).
    """
    rows = conn.execute(
        """SELECT p.id, p.author_name, p.author_headline, p.author_profile, p.email, p.content,
                  p.links, p.domain_relevance, p.is_hiring,
                  (SELECT GROUP_CONCAT(j.role, ', ') FROM jobs j WHERE j.post_id = p.id) as role,
                  (SELECT j2.company FROM jobs j2 WHERE j2.post_id = p.id LIMIT 1) as company,
                  (SELECT j3.location FROM jobs j3 WHERE j3.post_id = p.id LIMIT 1) as location
           FROM posts p
           WHERE p.email IS NOT NULL AND p.email != ''
             AND p.is_hiring = 1
             AND LOWER(p.email) NOT LIKE '%southguild%'
             AND p.id NOT IN (SELECT post_id FROM email_outreach WHERE post_id IS NOT NULL AND status = 'sent')
             AND NOT EXISTS (
                 SELECT 1 FROM email_outreach eo
                 WHERE eo.status = 'sent'
                   AND INSTR(p.email, eo.recipient_email) > 0
             )
           ORDER BY
             CASE p.domain_relevance WHEN 'High' THEN 1 WHEN 'Medium' THEN 2 ELSE 3 END,
             p.created_at DESC""",
    ).fetchall()
    return [dict(r) for r in rows]


# ─── Excel Export (from DB) ──────────────────────────────────────────────────

def export_to_excel(conn: sqlite3.Connection, output_path: str, filters: dict | None = None):
    """Export DB posts to formatted Excel. Same styling as original."""
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.utils import get_column_letter

    filters = filters or {}
    posts = query_posts(conn, limit=10000, **filters)

    COLUMNS = [
        ("S.No",               8),
        ("Author Name",       22),
        ("Author Profile URL",30),
        ("Author Headline",   30),
        ("Post URL",          30),
        ("Post Content",      55),
        ("Role",              22),
        ("Company",           22),
        ("Email(s)",          30),
        ("Location",          18),
        ("Experience",        16),
        ("Domain Relevance",  16),
        ("Post Date",         15),
        ("Search Query",      25),
        ("Is Hiring?",        10),
    ]

    HEADER_FILL      = PatternFill("solid", fgColor="1B4F72")
    ALT_ROW_FILL     = PatternFill("solid", fgColor="EBF5FB")
    HIRING_FILL      = PatternFill("solid", fgColor="D5F5E3")
    DOMAIN_HIGH_FILL = PatternFill("solid", fgColor="ABEBC6")
    HEADER_FONT      = Font(bold=True, color="FFFFFF", size=11)
    LINK_FONT        = Font(color="2980B9", underline="single")
    THIN_BORDER      = Border(
        left=Side(style="thin", color="BFC9CA"),
        right=Side(style="thin", color="BFC9CA"),
        top=Side(style="thin", color="BFC9CA"),
        bottom=Side(style="thin", color="BFC9CA"),
    )

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "LinkedIn Hiring Posts"

    headers = [c[0] for c in COLUMNS]
    ws.append(headers)
    for col_idx, (_, width) in enumerate(COLUMNS, start=1):
        cell = ws.cell(row=1, column=col_idx)
        cell.font = HEADER_FONT
        cell.fill = HEADER_FILL
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = THIN_BORDER
        ws.column_dimensions[get_column_letter(col_idx)].width = width

    ws.row_dimensions[1].height = 30
    ws.freeze_panes = "A2"

    for i, post in enumerate(posts, start=2):
        domain_rel = post.get("domain_relevance", "Low")
        is_hiring = post.get("is_hiring", 0)
        row_fill = None
        if domain_rel == "High" and is_hiring:
            row_fill = DOMAIN_HIGH_FILL
        elif is_hiring:
            row_fill = HIRING_FILL
        elif i % 2 == 0:
            row_fill = ALT_ROW_FILL

        values = [
            i - 1,
            post.get("author_name", ""),
            post.get("author_profile", ""),
            post.get("author_headline", ""),
            post.get("post_url", ""),
            post.get("content", ""),
            post.get("role", ""),
            post.get("company", ""),
            post.get("email", ""),
            post.get("location", ""),
            post.get("experience", ""),
            domain_rel,
            post.get("post_date", ""),
            post.get("keyword_matched", ""),
            "Yes" if is_hiring else "No",
        ]

        ws.append(values)

        for col_idx, val in enumerate(values, start=1):
            cell = ws.cell(row=i, column=col_idx)
            if row_fill:
                cell.fill = row_fill
            cell.border = THIN_BORDER
            cell.alignment = Alignment(vertical="top", wrap_text=True)
            if col_idx in (3, 5) and isinstance(val, str) and val.startswith("http"):
                cell.font = LINK_FONT
                cell.hyperlink = val

        ws.row_dimensions[i].height = 80

    wb.save(output_path)
    return len(posts)


# ─── Import existing Excel into DB ──────────────────────────────────────────

def import_excel(conn: sqlite3.Connection, xlsx_path: str) -> tuple[int, int]:
    """Import posts from an existing Excel file into the database.
    Auto-detects column layout from the header row."""
    import openpyxl
    from post_parser import score_domain_relevance, is_hiring_post, normalize_experience

    wb = openpyxl.load_workbook(xlsx_path, read_only=True)
    ws = wb.active

    # Read header row to build column map
    header_row = next(ws.iter_rows(min_row=1, max_row=1, values_only=True))
    col_map = {}
    for idx, name in enumerate(header_row):
        if name:
            col_map[name.strip().lower()] = idx

    # Map header names to our field names (handles both old and new formats)
    def get(row, *possible_headers, default=""):
        for h in possible_headers:
            idx = col_map.get(h.lower())
            if idx is not None and idx < len(row) and row[idx] is not None:
                return str(row[idx])
        return default

    rows = list(ws.iter_rows(min_row=2, values_only=True))
    posts = []
    for row in rows:
        if not row or len(row) < 6:
            continue

        content = get(row, "Post Content", "Content")
        if not content:
            continue

        experience_raw = get(row, "Experience")
        experience = normalize_experience(experience_raw) if experience_raw else ""

        is_hiring_val = get(row, "Is Hiring?", "Is Hiring")
        is_hiring_bool = is_hiring_val.lower() == "yes" if is_hiring_val else is_hiring_post(content)

        domain = get(row, "Domain Relevance", "Domain")
        if not domain or domain in ("", "Low", "Medium", "High") == False:
            domain = score_domain_relevance(content)

        posts.append({
            "author_name":     get(row, "Author Name"),
            "author_profile":  get(row, "Author Profile URL", "Author Profile"),
            "author_headline": get(row, "Author Headline"),
            "post_url":        get(row, "Post URL"),
            "content":         content,
            "role_hiring_for": get(row, "Role", "Role Hiring For", default="Not specified"),
            "company":         get(row, "Company"),
            "email":           get(row, "Email(s)", "Email", "Emails"),
            "location":        get(row, "Location"),
            "experience":      experience,
            "domain_relevance": domain if domain in ("High", "Medium", "Low") else score_domain_relevance(content),
            "post_date":       get(row, "Post Date"),
            "keyword_matched": get(row, "Keyword Matched", "Search Query"),
            "is_hiring":       is_hiring_bool,
        })

    wb.close()
    return insert_posts(conn, posts)


# ─── CLI ─────────────────────────────────────────────────────────────────────

def cli():
    parser = argparse.ArgumentParser(description="LinkedIn Jobs DB — query, export, stats")
    parser.add_argument("--stats", action="store_true", help="Show database statistics")
    parser.add_argument("--role", type=str, help="Filter by role (e.g. 'AI Engineer')")
    parser.add_argument("--domain", type=str, choices=["High", "Medium", "Low"], help="Filter by domain relevance")
    parser.add_argument("--has-email", action="store_true", help="Only posts with email addresses")
    parser.add_argument("--hiring", action="store_true", help="Only confirmed hiring posts")
    parser.add_argument("--company", type=str, help="Filter by company name")
    parser.add_argument("--export", type=str, metavar="FILE.xlsx", help="Export results to Excel")
    parser.add_argument("--import-excel", type=str, metavar="FILE.xlsx", help="Import existing Excel file into DB")
    parser.add_argument("--outreach", action="store_true", help="Show posts ready for email outreach")
    parser.add_argument("--limit", type=int, default=50, help="Max results (default: 50)")

    args = parser.parse_args()
    conn = init_db()

    if args.import_excel:
        inserted, skipped = import_excel(conn, args.import_excel)
        print(f"Imported: {inserted} new, {skipped} duplicates skipped")
        conn.close()
        return

    if args.stats:
        s = get_stats(conn)
        print(f"\n  Total posts:      {s['total_posts']}")
        print(f"  With email:       {s['with_email']}")
        print(f"  Confirmed hiring: {s['hiring']}")
        print(f"\n  Domain Relevance:")
        for level, count in s["domain"].items():
            print(f"    {level:8s}  {count}")
        print(f"\n  Roles:")
        for role, count in s["roles"].items():
            print(f"    {role:25s}  {count}")
        if s["outreach"]:
            print(f"\n  Email Outreach:")
            for status, count in s["outreach"].items():
                print(f"    {status:10s}  {count}")
        print()
        conn.close()
        return

    if args.outreach:
        posts = get_posts_for_outreach(conn)
        print(f"\n  {len(posts)} posts ready for outreach:\n")
        for p in posts:
            print(f"  [{p['domain_relevance']:6s}] {p['author_name']:20s} | {p['role'] or '-':20s} | {p['email']}")
        print()
        conn.close()
        return

    filters = {}
    if args.role:
        filters["role"] = args.role
    if args.domain:
        filters["domain"] = args.domain
    if args.has_email:
        filters["has_email"] = True
    if args.hiring:
        filters["is_hiring"] = True
    if args.company:
        filters["company"] = args.company

    if args.export:
        count = export_to_excel(conn, args.export, filters)
        print(f"Exported {count} posts to {args.export}")
    else:
        posts = query_posts(conn, limit=args.limit, **filters)
        if not posts:
            print("No posts found matching filters.")
        else:
            print(f"\n  {len(posts)} results:\n")
            for p in posts:
                email_flag = "email" if p.get("email") else "     "
                hiring_flag = "HIRING" if p.get("is_hiring") else "      "
                print(
                    f"  [{p.get('domain_relevance', '-'):6s}] "
                    f"{hiring_flag} {email_flag}  "
                    f"{(p.get('author_name') or '-'):20s} | "
                    f"{(p.get('role') or '-'):20s} | "
                    f"{(p.get('experience') or '-'):12s} | "
                    f"{(p.get('company') or '-'):20s}"
                )
            print()

    conn.close()


if __name__ == "__main__":
    cli()
