# CareerKit -- Services Reference

> Complete reference for all backend services, their functions, dependencies, and behavior.

## Overview

- Services live in `backend/services/`
- Routes are thin -- services hold all business logic and state
- Services manage their own thread safety via locks and state dicts
- Services communicate via direct imports (no message bus)
- Background workers are daemon threads that update shared state dicts
- LLM calls use a dual-provider chain: Ollama (local, free) then Gemini (API fallback)

## Service Index

| Service | File | Purpose | Thread-safe? | Background Worker? |
|---------|------|---------|:------------:|:------------------:|
| Orchestrator | `orchestrator.py` | Full daily scrape-score-apply cycle | Yes | Yes |
| Scraper Service | `scraper_service.py` | Multi-source scraper coordinator | Yes | Yes |
| Browser Service | `browser_service.py` | Playwright browser lifecycle | Yes (queue) | Yes |
| Email Service | `email_service.py` | Email generation, SMTP sending, IMAP polling | Yes | Yes |
| Auto-Apply | `auto_apply.py` | Automated job application engine | Yes | Yes |
| Smart Filter | `smart_filter.py` | 6-dimension job scoring | No (stateless) | No |
| AI Tools | `ai_tools.py` | Gemini-powered evaluate/outreach/prep | No (stateless) | No |
| Skills Intelligence | `skills_intel.py` | Skill extraction, gap analysis, trends | Yes | Yes |
| Quality Dashboard | `quality_dashboard.py` | Application conversion analytics | No (stateless) | No |
| Email A/B Testing | `email_ab_test.py` | Variant tracking and winner detection | No (counter only) | No |
| Resume Selector | `resume_selector.py` | Job-archetype resume matching | No (stateless) | No |
| Referral Detector | `referral_detector.py` | Connection lookup before cold apply | No (stateless) | No |
| Pattern Analysis | `pattern_analysis.py` | Outreach funnel and conversion stats | No (stateless) | No |
| Company Signals | `company_signals.py` | Company health scanning via Gemini | No (cache only) | No |
| ATS Scanner | `ats_scanner.py` | Greenhouse/Ashby/Lever API scanner | No (thread pool) | No |
| Liveness | `liveness.py` | Job posting expiry detection | No (thread pool) | No |
| Import Leads | `import_leads.py` | CSV/XLSX lead import to DB | No | No |
| Followup Cadence | `followup_cadence.py` | Follow-up urgency computation | No (stateless) | No |
| Logger | `logger.py` | CSV/Excel application tracking backup | No | No |

---

## Services

### Orchestrator (`orchestrator.py`)

**Purpose**: Runs the full daily job application cycle: scrape all sources, smart-score unscored jobs, auto-apply until quota exhausted, and generate a daily report.

**State dict**:
```python
orchestrator_state = {
    "running": False,
    "status": "idle",       # idle | scraping | scoring | applying | reporting | done | error
    "started_at": None,
    "phase": None,
    "log": [],              # capped at 300 entries
}
```

**Thread safety**: `_orch_lock` (threading.Lock), `_orch_stop` (threading.Event).

**Public functions**:

| Function | Signature | Description |
|----------|-----------|-------------|
| `start_daily_cycle` | `(max_applications: int = 500, run_scrapers: bool = True) -> dict` | Start the daily cycle in a background daemon thread |
| `stop_daily_cycle` | `() -> dict` | Signal stop via Event, also stops auto-apply |
| `get_orchestrator_status` | `() -> dict` | Return current state (last 100 log entries) |

**Internal functions**:

| Function | Description |
|----------|-------------|
| `run_daily_cycle` | Full pipeline: scrape phase, smart scoring, auto-apply, report |
| `_run_scraper_phase` | Runs API scrapers first, then browser scrapers if browser is available |
| `_orch_emit` | Append timestamped event to orchestrator log |

**Dependencies**: `scraper_service._scraper_coordinator`, `smart_filter.score_all_unscored`, `smart_filter.filter_unapplied`, `auto_apply.AutoApplyEngine`, `browser_service.browser_state`, `db.init_db`, `db.quota_remaining`, `db.get_today_quota`, `db.get_application_stats`.

**Called by**: `routes/auto_apply.py` (POST `/api/orchestrator/start`, `/api/orchestrator/stop`, GET `/api/orchestrator/status`).

**Error behavior**: Catches all exceptions, logs them, sets status to `"error"`. Always resets `running` to `False` in finally block.

---

### Scraper Service (`scraper_service.py`)

**Purpose**: Coordinates all scraper sources in parallel. LinkedIn-based sources run sequentially on the browser thread; API scrapers and web scrapers each get their own thread.

**State dict**:
```python
scraper_state = {
    "running": False,
    "status": "idle",       # idle | running | done | error
    "started_at": None,
    "sources": {},          # per-source: { "linkedin": { status, log, progress }, ... }
}
```

**Thread safety**: `_scraper_lock` (threading.Lock). All reads/writes to `scraper_state` are lock-protected.

**Public/internal functions**:

| Function | Signature | Description |
|----------|-----------|-------------|
| `_scraper_coordinator` | `(max_posts: int, sources: list[str])` | Main coordinator -- launches all source scrapers in parallel where possible |
| `_init_source_state` | `() -> dict` | Fresh per-source state with status, log, progress |
| `_make_source_callback` | `(source_name) -> Callable` | Creates a per-source event callback that stores events to the source log |
| `_run_linkedin_scraper` | `(max_posts, on_event)` | LinkedIn search scraper on browser thread |
| `_run_linkedin_feed_scraper` | `(max_posts, on_event)` | LinkedIn feed scraper on browser thread |
| `_run_linkedin_hashtag_scraper` | `(max_posts, on_event)` | LinkedIn hashtag scraper on browser thread |
| `_run_enricher` | `(max_visits, on_event)` | Profile email enricher on browser thread |
| `_run_deep_fetcher` | `(max_visits, on_event)` | Deep content fetcher on browser thread |
| `_run_api_scraper` | `(source_name, scraper_fn, max_posts, on_event)` | Runs any API-based scraper (no browser) |
| `_run_web_scraper` | `(source_name, scraper_fn, max_posts, on_event)` | Runs a web scraper in its own Playwright browser instance |
| `_run_career_link_scraper` | `(source_name, max_visits, on_event)` | Career link follower in its own browser |

**Execution model**:
- LinkedIn sources (search, feed, hashtags, enricher, deepfetch): sequential on browser thread via `_run_on_browser_thread`
- API scrapers (remoteok, himalayas, hn, remotive, wwr_rss, workingnomads, greenhouse, lever, ashby, jobspy): parallel threads, HTTP only
- Generic scrapers (config-driven HTML/API from `config_sources.py`): parallel threads
- Web scrapers (google, wellfound, yc, indeed, naukri, arcdev, weworkremotely, japandev, euremotejobs, bayt, remoteai): parallel threads, each with its own headed Playwright browser with anti-detection

**Dependencies**: `browser_service.browser_state`, `browser_service._run_on_browser_thread`, `post_parser.scrape_posts/scrape_feed/scrape_hashtags`, `scrapers.api_scrapers.*`, `scrapers.web_scrapers.*`, `scrapers.generic_scrapers.*`, `config_sources.GENERIC_HTML_SOURCES/GENERIC_API_SOURCES`, `db.init_db`, `db.insert_posts`.

**Called by**: `routes/scraper.py`, `orchestrator._run_scraper_phase`.

---

### Browser Service (`browser_service.py`)

**Purpose**: Manages a single Playwright browser instance with persistent LinkedIn login and anti-detection. All Playwright operations must run on a dedicated browser thread.

**State dict**:
```python
browser_state = {
    "pw": None,
    "browser": None,
    "page": None,
    "running": False,
    "logged_in": False,
    "status": "stopped",    # stopped | starting | ready | error
}
```

**Thread model**: Playwright requires all operations on the same thread that created the context. A dedicated daemon thread runs `_browser_worker`, processing commands from `_browser_cmd_q` (Queue of `(command, args, result_queue)` tuples).

**Public functions**:

| Function | Signature | Description |
|----------|-----------|-------------|
| `_run_on_browser_thread` | `(fn, *args, timeout=60)` | Execute any function on the browser thread and return result |

**Browser thread commands**:

| Function | Description |
|----------|-------------|
| `_do_start_browser` | Launch Playwright with persistent profile, navigate to LinkedIn login |
| `_do_open_login` | Navigate to LinkedIn login page |
| `_do_check_login` | Navigate to feed, check if logged in |
| `_do_stop_browser` | Close browser context and Playwright instance |

**Anti-detection measures**: Persistent profile at `data/browser_profiles/main`, randomized viewport, randomized `slow_mo` (600-1200ms), spoofed `navigator.webdriver`, fake plugins, fake `window.chrome`, permissions API override, realistic screen properties.

**Configuration dependencies**: `config.REGIONS`, `config.ACTIVE_REGIONS` (locale, timezone, geolocation).

**Called by**: `routes/browser.py`, `scraper_service` (LinkedIn sources), `auto_apply.AutoApplyEngine`.

---

### Email Service (`email_service.py`)

**Purpose**: Handles all email operations: LLM-powered email generation, SMTP sending with resume attachments, bulk generate/send workers, auto follow-up, IMAP reply detection with classification, and bounce detection.

**State dicts**:
```python
email_worker_state = {
    "running": False,
    "task": None,           # "generating" | "sending"
    "current": 0, "total": 0,
    "current_label": "",
    "results": [],
    "error": None,
}

followup_worker_state = {
    "running": False,
    "current": 0, "total": 0,
    "succeeded": 0, "failed": 0,
    "results": [], "error": None,
}

imap_worker_state = {
    "running": False,
    "last_checked": None,
    "replies_found": 0,
    "total_checked": 0,
    "error": None,
}
```

**Thread safety**: `_email_lock`, `_followup_lock`, `_imap_lock` (all threading.Lock).

**Public functions**:

| Function | Signature | Description |
|----------|-----------|-------------|
| `validate_email_before_send` | `(email: str) -> dict` | Format check + MX record validation |
| `send_email_with_resume` | `(to_email, subject, body, resume_path="") -> dict` | Send email with resume PDF attached |
| `start_auto_followup` | `() -> dict` | Start background follow-up worker for overdue entries |
| `get_followup_worker_status` | `() -> dict` | Return followup_worker_state |
| `stop_followup_worker` | `() -> dict` | Stop follow-up worker |
| `preview_followup` | `(outreach_id) -> dict` | Generate follow-up preview without sending |
| `start_imap_polling` | `(interval_minutes=5) -> dict` | Start IMAP polling daemon thread |
| `stop_imap_polling` | `() -> dict` | Stop IMAP polling |
| `check_replies_once` | `() -> dict` | Run single IMAP scan |
| `get_imap_status` | `() -> dict` | Return imap_worker_state |

**Internal functions**:

| Function | Description |
|----------|-------------|
| `_generate_email_with_gemini` | Generate personalized cold email via Gemini 2.5 Flash Lite |
| `_generate_email_with_ollama` | Generate email via local Ollama, falls back to Gemini |
| `_parse_generated_email` | Parse AI output into subject + body, strip placeholders |
| `_build_email_input` | Build structured input block for email agent prompt |
| `_send_email_smtp` | Low-level SMTP send with HTML + plain text + optional attachment |
| `_is_blocked_email` | Check against EMAIL_BLOCKLIST (current employer, bouncing domains) |
| `_bulk_generate_worker` | Background thread: generate drafts for list of post IDs |
| `_bulk_send_worker` | Background thread: send all draft emails with anti-spam delays (3-8s) |
| `_auto_followup_worker` | Background thread: generate + send follow-ups for overdue entries |
| `_generate_followup_email` | Generate follow-up email via Gemini with fallback template |
| `_classify_reply` | Classify reply as: interested, auto_reply, rejection, or info |
| `_imap_check_replies` | IMAP scan: match replies to outreach, detect bounces |
| `_imap_poll_worker` | Background loop: check replies every N minutes |

**Configuration dependencies**: `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `FROM_EMAIL`, `FROM_NAME`, `IMAP_HOST`, `IMAP_PORT`, `IMAP_USER`, `IMAP_PASSWORD`, `GEMINI_API_KEY`.

**Called by**: `routes/email.py`, `auto_apply._email_apply`. IMAP polling auto-starts on server startup (`server.py`).

---

### Auto-Apply Service (`auto_apply.py`)

**Purpose**: Automated job application engine supporting LinkedIn Easy Apply (Playwright), email application (SMTP + resume), and redirect/manual logging. Uses score-gated tiers to invest more effort in better matches.

**State dict**:
```python
auto_apply_state = {
    "running": False,
    "status": "idle",       # idle | running | done | stopped | error
    "started_at": None,
    "progress": { "total_attempted": 0, "applied": 0, "failed": 0, "skipped": 0, "current_job": None },
    "log": [],              # capped at 500 entries
}
```

**Thread safety**: `_apply_lock` (threading.Lock), `_stop_flag` (threading.Event).

**Constants**:

| Constant | Purpose |
|----------|---------|
| `PLATFORM_BUDGETS` | Daily cap per platform: linkedin=120, email=180, indeed=30, etc. |
| `RATE_LIMITS` | Seconds between applications per platform (tuple of min, max) |
| `APPLY_TIERS` | Score-gated tiers: PREMIUM (>=7.0), STANDARD (>=5.0), BASIC (>=3.5) |

**Public functions**:

| Function | Signature | Description |
|----------|-----------|-------------|
| `start_auto_apply` | `(max_applications: int = 500) -> dict` | Start auto-apply in background thread |
| `stop_auto_apply` | `() -> dict` | Signal stop via Event |
| `get_auto_apply_status` | `() -> dict` | Return current state with last 100 log entries |

**Class: `AutoApplyEngine`**:

| Method | Signature | Description |
|--------|-----------|-------------|
| `__init__` | `(conn, page=None)` | Initialize with DB connection and optional Playwright page |
| `should_apply` | `(job: dict) -> tuple[bool, str]` | Pre-check: dedup, quota, score gate (>=3.5), liveness check |
| `apply_one` | `(job: dict) -> dict` | Apply to a single job with tier-appropriate effort |
| `run` | `(max_applications=500, on_complete=None)` | Main loop: process jobs until quota or max reached |

**Internal functions**:

| Function | Description |
|----------|-------------|
| `_linkedin_easy_apply` | Playwright automation: navigate, warm-up, click Easy Apply, fill multi-step form |
| `_linkedin_warm_up` | Simulate human browsing before applying (scroll, read, company page visit for premium) |
| `_fill_form_fields` | Fill phone, city, resume upload, text questions, dropdowns, radio buttons, numeric inputs |
| `_handle_text_questions` | Fill textareas using known answers + LLM (Gemini, premium tier only) |
| `_handle_dropdowns` | Select experience/education options |
| `_handle_radio_buttons` | Handle yes/no for authorization, sponsorship, relocation |
| `_handle_numeric_inputs` | Fill salary, notice period, experience years, GPA |
| `_get_known_answer` | Return hardcoded answers for common questions (no API call) |
| `_llm_answer_question` | Use Gemini to answer custom form questions |
| `_email_apply` | Send application email with Gemini-personalized content + resume |
| `_redirect_apply` | Log for manual follow-up |
| `_register_for_followup` | Create pipeline_lead entry for followup_cadence tracking |
| `_get_apply_tier` | Map smart_score to PREMIUM/STANDARD/BASIC/skip |

**Dependencies**: `browser_service.browser_state`, `email_service.send_email_with_resume`, `email_service.validate_email_before_send`, `resume_selector.get_resume_for_job`, `liveness.check_url_liveness`, `ai_tools._call_gemini`, `config.PROFILE`.

**Called by**: `routes/auto_apply.py`, `orchestrator.run_daily_cycle`.

---

### Smart Filter (`smart_filter.py`)

**Purpose**: Scores scraped jobs on 6 weighted dimensions before they reach the auto-apply engine. Only jobs above the threshold get applied to.

**Scoring dimensions**:

| Dimension | Weight | Range | Scorer |
|-----------|--------|-------|--------|
| `role_match` | 0.25 | 0-10 | Target role matching (exact=10, AI/ML=8, adjacent=4-6) |
| `skill_match` | 0.25 | 0-10 | Weighted RESUME_SKILLS keyword matching |
| `domain_relevance` | 0.20 | 0-10 | Healthcare/clinical domain keyword counting |
| `experience_fit` | 0.15 | 0-10 | Experience range vs candidate's 2 years |
| `quality_signals` | 0.10 | 0-10 | JD depth, equity mentions, funded company, spam detection |
| `location_fit` | 0.05 | 0-10 | Remote=10, India=9, Asia=7, Europe=5, US-only=2 |

**Thresholds**: APPLY >= 5.0, CONSIDER >= 3.5, SKIP < 3.5.

**LLM blending**: If `fit_score` exists from extraction, final = 70% rule-based + 30% LLM.

**Public functions**:

| Function | Signature | Description |
|----------|-----------|-------------|
| `score_job` | `(content, role="", company="", location="", experience="", domain_relevance="", fit_score=None) -> dict` | Score a job, returns smart_score + verdict + breakdown |
| `score_and_update` | `(conn, post_id: int) -> dict` | Score a post and write smart_score to DB |
| `score_all_unscored` | `(conn, limit=500) -> dict` | Batch score all unscored hiring posts |
| `filter_unapplied` | `(conn, threshold=5.0, limit=100) -> list[dict]` | Get unapplied jobs above threshold, ordered by score |
| `get_filter_stats` | `(conn) -> dict` | Statistics: total, scored, avg, APPLY/CONSIDER/SKIP counts |

**Configuration dependencies**: `config.RESUME_SKILLS`, `config.DOMAIN_KEYWORDS`, `config.TARGET_ROLES`, `config.PROFILE`.

**Called by**: `routes/tools.py`, `orchestrator.run_daily_cycle`, `auto_apply.AutoApplyEngine.should_apply` (indirectly via score thresholds).

---

### AI Tools (`ai_tools.py`)

**Purpose**: Five Gemini-powered tools for job search assistance. All functions call `_call_gemini` and return parsed JSON.

**Public functions**:

| Function | Signature | Description |
|----------|-----------|-------------|
| `evaluate_job` | `(jd_text: str) -> dict` | Structured JD evaluation: archetype, CV match %, gaps, score 1-5, verdict, interview topics |
| `generate_outreach` | `(company, role, recruiter_name="", context="") -> dict` | Generate cold email + LinkedIn message + follow-up |
| `deep_dive_company` | `(company, role="") -> dict` | Company research: AI strategy, challenges, outreach hook |
| `tailor_cv` | `(jd_text: str) -> dict` | ATS-optimized resume sections: summary, competencies, bullets, keyword coverage |
| `interview_prep` | `(company, role) -> dict` | Interview material: process overview, rounds, STAR stories, tech checklist |

**Helper functions**:

| Function | Description |
|----------|-------------|
| `_call_gemini` | Call Gemini 2.5 Flash Lite API with configurable temperature/tokens |
| `_parse_json_response` | Extract JSON from response with markdown code block handling |

**Configuration dependencies**: `GEMINI_API_KEY`, `config.RESUME_SKILLS`, `config.get_profile_context()`.

**Called by**: `routes/tools.py`, `auto_apply._llm_answer_question`.

---

### Skills Intelligence (`skills_intel.py`)

**Purpose**: Extracts skills from all saved job postings via regex + optional LLM, computes market demand stats, identifies resume gaps, and provides trend/news data.

**State dict**:
```python
analysis_state = {
    "running": False,
    "run_id": None,
    "status": "idle",       # idle | running | completed | failed
    "total": 0,
    "processed": 0,
    "phase": "",            # starting | regex_scan | llm_enrichment | aggregation | done
    "log": [],
}
```

**Thread safety**: `_analysis_lock` (threading.Lock).

**Tech taxonomy**: 90+ skills across 7 categories (Languages, AI_ML, Frameworks, Cloud, Databases, DevOps, Domain) with pre-compiled regex patterns. Requirement level inferred from context window (required/preferred/mentioned).

**Public functions**:

| Function | Signature | Description |
|----------|-----------|-------------|
| `start_analysis` | `(use_llm=False, llm_sample=100) -> dict` | Start background analysis: regex scan all jobs, optional LLM enrichment, aggregate |
| `get_analysis_status` | `() -> dict` | Return analysis_state snapshot |
| `get_dashboard_data` | `(conn) -> dict` | Top 50 skills, by category, education stats, experience distribution |
| `compute_gap_analysis` | `(conn) -> dict` | Compare RESUME_SKILLS vs market: strengths, gaps (priority 1-3), underutilized, readiness score |
| `refresh_trends` | `() -> dict` | Fetch AI/ML tool trends from Gemini (24h cache) |
| `get_trend_data` | `() -> dict` | Return cached trend data |
| `refresh_news` | `() -> dict` | Fetch healthcare AI / ML engineering news from Gemini (24h cache) |
| `get_news_data` | `() -> dict` | Return cached news data |
| `regex_extract_skills` | `(text: str) -> list[dict]` | Fast regex skill extraction against taxonomy |
| `regex_extract_education` | `(text: str) -> list[dict]` | Extract education requirements (PhD/Masters/Bachelors) |
| `llm_extract_skills` | `(content: str) -> dict or None` | Gemini-based structured skill extraction |

**In-memory caches**: `_trend_cache`, `_news_cache` (24-hour TTL).

**Configuration dependencies**: `GEMINI_API_KEY`, `config.RESUME_SKILLS`.

**DB tables used**: `skill_mentions`, `education_demands`, `skill_demand_summary`, `skills_analysis_runs`.

**Called by**: `routes/skills_intel.py`.

---

### Quality Dashboard (`quality_dashboard.py`)

**Purpose**: Computes application conversion analytics across multiple dimensions.

**Public function**:

| Function | Signature | Description |
|----------|-----------|-------------|
| `get_dashboard_data` | `(conn) -> dict` | Full analytics: overview, by method, by domain, by platform, by score bucket, by hour, email performance, top companies, daily trend |

**Analytics dimensions**:
- **Overview**: Total applications, success rate, email reply rate
- **By method**: easy_apply, email, redirect success rates
- **By domain**: High/Medium/Low relevance conversion
- **By platform**: LinkedIn, RemoteOK, etc. conversion
- **By score bucket**: PREMIUM (7+), STANDARD (5-7), BASIC (3.5-5), SKIP (<3.5)
- **By hour**: Time-of-day application success
- **Email performance**: Reply rate by domain relevance
- **Top companies**: Volume by company
- **Daily trend**: Last 30 days from daily_quotas table

**Called by**: `routes/tools.py`.

---

### Email A/B Testing (`email_ab_test.py`)

**Purpose**: Tracks two email strategy variants (proof-first vs challenge-first), alternates between them, and tracks reply rates to find a winner.

**Variant strategies**:
- **A (proof-first)**: Lead with strongest quantified achievement
- **B (challenge-first)**: Lead with their specific challenge, show you solved it

**Public functions**:

| Function | Signature | Description |
|----------|-----------|-------------|
| `pick_variant` | `() -> str` | Alternate A/B using simple counter |
| `generate_ab_variants` | `(job: dict) -> dict` | Generate both variants via Gemini |
| `record_variant` | `(conn, outreach_id, variant, strategy="")` | Record which variant was sent |
| `get_ab_stats` | `(conn) -> dict` | Stats per variant: sent, replies, bounce, reply_rate, winner detection (requires 10+ samples, 20% lift) |

**DB migrations**: Adds `variant` and `variant_strategy` columns to `email_outreach` if missing.

**Configuration dependencies**: `GEMINI_API_KEY`, `config.PROFILE`, `config.RESUME_SKILLS`.

**Called by**: `email_service._bulk_generate_worker`, `routes/email.py`.

---

### Resume Selector (`resume_selector.py`)

**Purpose**: Picks the best resume PDF variant based on job content keyword matching.

**Configured variants**:

| Variant | Keywords (sample) | Weight |
|---------|-------------------|--------|
| `healthcare-ai` | healthcare, clinical, oncology, HIPAA, pharma | 1.5 |
| `genai-platform` | LLM, RAG, agents, langchain, transformer | 1.3 |
| `data-engineering` | data pipeline, ETL, MLOps, airflow, Kubernetes | 1.0 |
| `default` | (fallback) | 0.5 |

**Public functions**:

| Function | Signature | Description |
|----------|-----------|-------------|
| `select_resume` | `(role="", content="", domain_relevance="", company="") -> str` | Return path to best-matching resume (min 2.0 score, else default) |
| `get_resume_for_job` | `(job: dict) -> str` | Convenience wrapper accepting a job dict |
| `list_variants` | `() -> list[dict]` | List all variants with existence status |

**Called by**: `auto_apply._fill_form_fields`, `auto_apply._email_apply`, `routes/settings.py`.

---

### Referral Detector (`referral_detector.py`)

**Purpose**: Before cold applying, checks local DB for existing connections at the target company. Searches scraped post authors, pipeline leads, email outreach history, and startup leads.

**Public functions**:

| Function | Signature | Description |
|----------|-----------|-------------|
| `find_connections` | `(conn, company: str) -> dict` | Find contacts at company. Returns `{has_connections, contacts[], recommendation}` |
| `has_connections` | `(conn, company: str) -> bool` | Quick boolean check |

**Recommendation values**: `warm_followup` (prior reply), `warm_intro` (pipeline lead exists), `referral_outreach` (contacts found), `cold_apply` (no connections).

**Data sources searched**: `posts` (author headline/content), `pipeline_leads`, `email_outreach` + `jobs`, `startup_leads`.

**Called by**: `email_service._bulk_generate_worker`.

---

### Pattern Analysis (`pattern_analysis.py`)

**Purpose**: Analyzes outreach patterns across the entire email pipeline. Port of `career-ops/analyze-patterns.mjs`.

**Public functions**:

| Function | Signature | Description |
|----------|-----------|-------------|
| `analyze_patterns` | `(conn) -> dict` | Full analysis: metadata, funnel, by domain, by role, by company, response time, recommendations |
| `get_conversion_rates` | `(conn) -> dict` | Per-role and per-domain conversion rates |

**Recommendation engine**: Generates actionable recommendations based on:
- Domain relevance performance (focus on high, stop low)
- Best-performing role type
- Zero-reply detection (change template after 10 sends)
- Unresponsive companies (deprioritize after 2+ unanswered)
- Funnel drop-off (reply-to-interview conversion)

**Also provides CLI**: `python pattern_analysis.py --summary` for human-readable output.

**Called by**: `routes/tools.py`.

---

### Company Signals (`company_signals.py`)

**Purpose**: Quick company health assessment using Gemini. Returns green/yellow/red signal with score modifier.

**Caching**: Dual-layer cache -- in-memory dict (`_signal_cache`) + SQLite `company_signals` table. Entries expire after 7 days.

**Public functions**:

| Function | Signature | Description |
|----------|-----------|-------------|
| `scan_company` | `(company, conn=None) -> dict` | Scan company via Gemini. Returns `{signal, score_modifier, reasons}` |
| `scan_and_cache` | `(conn, company) -> dict` | Convenience wrapper with DB caching |
| `get_company_modifier` | `(conn, company) -> float` | Get just the score modifier (0 if not cached) |

**Signal values**: `green` (+0.5 modifier), `yellow` (0), `red` (-1.5).

**Configuration dependencies**: `GEMINI_API_KEY`.

**Called by**: `routes/tools.py`.

---

### ATS Scanner (`ats_scanner.py`)

**Purpose**: Fetches jobs from Greenhouse, Ashby, and Lever ATS APIs. Configured via `config/portals.yml`. Port of `career-ops/scan.mjs`.

**Public functions**:

| Function | Signature | Description |
|----------|-----------|-------------|
| `scan_all` | `(portals_path="config/portals.yml", conn=None, on_event=None) -> list[dict]` | Scan all enabled companies, filter by title keywords, dedup against DB |
| `scan_company` | `(company, title_filter, seen_urls, on_event=None) -> list[dict]` | Scan a single company's ATS API |
| `detect_api` | `(company: dict) -> dict or None` | Detect ATS type (greenhouse/ashby/lever) from URL patterns |
| `build_title_filter` | `(title_filter: dict) -> Callable` | Build positive/negative keyword filter |

**Concurrency**: `ThreadPoolExecutor` with up to 10 workers for parallel API fetching.

**Output**: Normalized job dicts matching the `posts` table schema (author_name, post_url, content, role, company, etc.).

**Configuration**: `config/portals.yml` with `tracked_companies[]` and `title_filter` (positive/negative keywords).

**Called by**: `routes/tools.py`.

---

### Liveness (`liveness.py`)

**Purpose**: Classifies job posting URLs as active, expired, or uncertain using HTTP checks and regex pattern matching. Port of `career-ops/liveness-core.mjs`.

**Public functions**:

| Function | Signature | Description |
|----------|-----------|-------------|
| `check_url_liveness` | `(url, timeout=10) -> dict` | Check a single URL. Returns `{url, result, reason}` |
| `check_urls_batch` | `(urls, max_workers=5) -> list[dict]` | Parallel batch check via ThreadPoolExecutor |
| `classify_liveness` | `(status_code, final_url, body_text, apply_controls=None) -> dict` | Classification logic |
| `check_and_update_db` | `(conn, limit=50) -> dict` | Check posts in DB and update `is_live` column |

**Classification logic**: HTTP 404/410 = expired; URL error patterns = expired; body expiration patterns (multilingual) = expired; apply button detected = active; listing redirect = expired; insufficient content (<300 chars) = expired; otherwise = uncertain.

**Called by**: `auto_apply.AutoApplyEngine.should_apply`, `routes/tools.py`.

---

### Import Leads (`import_leads.py`)

**Purpose**: Imports startup lead CSV/XLSX files into the `startup_leads` table.

**Public functions**:

| Function | Signature | Description |
|----------|-----------|-------------|
| `import_healthcare_biotech_192` | `(conn) -> int` | Import US healthcare/biotech startups CSV |
| `import_healthcare_startups_india` | `(conn) -> int` | Import Indian healthcare startups CSV |
| `import_sisfs` | `(conn) -> int` | Import DIPP-recognized startups CSV |
| `import_recruiter_xlsx` | `(conn, filename) -> int` | Import recruiter leads XLSX |
| `import_all` | `()` | Import all files, print stats |

**Data directory**: `data/leads/`.

**Called by**: `routes/leads.py`, CLI `python import_leads.py`.

---

### Followup Cadence (`followup_cadence.py`)

**Purpose**: Computes follow-up urgency for sent outreach emails based on configurable cadence rules. Port of `career-ops/followup-cadence.mjs`.

**Cadence configuration**:

| Parameter | Default | Description |
|-----------|---------|-------------|
| `applied_first` | 7 days | Days before first follow-up |
| `applied_subsequent` | 7 days | Days between follow-ups |
| `applied_max_followups` | 2 | Max follow-ups before marking cold |
| `responded_initial` | 1 day | Days after response to follow up |
| `responded_subsequent` | 3 days | Days between response follow-ups |
| `interview_thankyou` | 1 day | Days to send thank-you after interview |

**Public functions**:

| Function | Signature | Description |
|----------|-----------|-------------|
| `analyze_followups` | `(conn) -> dict` | Compute urgency for all sent emails. Returns `{metadata, entries[], cadence_config}` |
| `record_followup` | `(conn, outreach_id) -> dict` | Increment followup_count, set last_followup_at |
| `compute_urgency` | `(stage, days_since_sent, days_since_last_followup, followup_count) -> str` | Returns urgent/overdue/waiting/cold |
| `compute_next_followup_date` | `(stage, sent_date, last_followup_date, followup_count) -> str or None` | Next follow-up ISO date |

**DB migrations**: Adds `followup_count` and `last_followup_at` columns to `email_outreach` if missing.

**Called by**: `email_service._auto_followup_worker`, `email_service.start_auto_followup`, `routes/email.py`.

---

### Logger (`logger.py`)

**Purpose**: Application tracking with SQLite as primary store and CSV/Excel backup.

**Public functions**:

| Function | Signature | Description |
|----------|-----------|-------------|
| `log_application` | `(platform, title, company, location, url, status, notes="", keywords="")` | Log to SQLite + CSV, refresh Excel |
| `get_applied_urls` | `() -> set` | Return set of already-applied URLs |

**Files**: CSV at `data/applications_log.csv`, Excel at `data/applications_tracker.xlsx`.

**Called by**: `routes/jobs.py`.

---

## Email Finder Module

The `backend/email_finder/` package is a service-like module for discovering and verifying contact emails.

### Strategies (`email_finder/strategies.py`)

**Purpose**: All email discovery strategies, constants, scoring, and verification. Shared by both `enrich.py` and `cron.py`.

**7 discovery strategies** (in priority order):

| # | Strategy | Function | Source |
|---|----------|----------|--------|
| 1 | Hunter.io API | `strategy_hunter_io(domain)` | API (25 free/month) |
| 2 | Website scraping | `strategy_website(website)` | HTTP crawl of /contact, /about, /careers, etc. |
| 3 | DuckDuckGo search | `strategy_duckduckgo(company, extra)` | duckduckgo-search package |
| 4 | Google search | `strategy_google_search(company, extra)` | googlesearch-python package |
| 5 | Person-name patterns | `strategy_person_patterns(author_name, domain)` | Generate firstname@, first.last@, etc. |
| 6 | Generic patterns | `strategy_generic_patterns(domain)` | Generate careers@, hr@, info@, etc. |
| 7 | Domain inference | `infer_domain(company)` | Try common TLDs + search for company website |

**Verification functions**:

| Function | Description |
|----------|-------------|
| `verify_mx(domain)` | Check for MX records via dns.resolver |
| `verify_smtp(email, mx_host, timeout=8)` | SMTP RCPT TO probe -- returns accepted/rejected/unknown |
| `verify_email_full(email)` | Full verification: MX + SMTP |
| `verify_batch(emails, timeout=5)` | Batch verify, grouped by domain for MX efficiency |

**Scoring**: `score_email(email, verified, source)` returns 0-60+ score based on email type (HR=+25, person=+20, contact=+15), company domain vs generic (+10), verification (+15), source trust (hunter=+10).

**Configuration dependencies**: `HUNTER_API_KEY`.

### Enrichment (`email_finder/enrich.py`)

**Purpose**: Bulk email enrichment using all strategies from `strategies.py`.

**Public functions**:

| Function | Signature | Description |
|----------|-----------|-------------|
| `find_emails_for_company` | `(company_name, website="", location="", author_name="") -> list[dict]` | Find emails using all strategies, verify pattern guesses, return sorted by score |
| `enrich_leads` | `(conn, max_leads=50, target="startup_leads", on_progress=None) -> dict` | Bulk enrich leads/posts without emails. Returns {enriched, skipped, failed, total_emails_found} |

**Called by**: `routes/leads.py`, `routes/email.py`.

### Cron (`email_finder/cron.py`)

**Purpose**: Scheduled email finding with full SMTP verification. Processes posts and startup leads without emails.

**Public functions**:

| Function | Signature | Description |
|----------|-----------|-------------|
| `run_cron` | `(max_items=20, target="both") -> dict` | Main cron: find + verify emails for posts and/or leads |
| `find_verified_emails` | `(company, website, location, linkedin_url, author_name) -> list[dict]` | Find and SMTP-verify emails (8 strategies including LinkedIn page follow) |
| `verify_existing` | `(max_items=50)` | Re-verify existing emails in DB, remove invalid ones |

**Logging**: File log at `data/logs/email_finder.log`.

**Called by**: `routes/email.py`, CLI `python -m email_finder.cron`.

---

## LLM Module

### Client (`llm/client.py`)

**Purpose**: Centralized LLM client with Ollama primary and Gemini fallback.

**Class: `LLMClient`** (module-level singleton `llm`):

| Method | Signature | Description |
|--------|-----------|-------------|
| `call` | `(prompt, max_tokens=150, temperature=0) -> str` | Try Ollama first, fall back to Gemini |
| `call_ollama` | `(prompt, max_tokens=80, temperature=0) -> str` | Call local Ollama (qwen2.5:7b) |
| `call_gemini` | `(prompt, max_tokens=150, temperature=0) -> str` | Call Gemini 2.5 Flash Lite via google-genai SDK |
| `ollama_available` | `() -> bool` | Check Ollama /api/tags endpoint (cached) |

**Configuration**: `OLLAMA_URL` (localhost:11434), `OLLAMA_MODEL` (qwen2.5:7b), `GEMINI_API_KEY`, `GEMINI_MODEL` (gemini-2.5-flash-lite).

**Called by**: `llm/extraction.py`, `extractors/pipeline.py`.

### Extraction (`llm/extraction.py`)

**Purpose**: LLM-powered extraction of structured job data from post content.

**Public functions**:

| Function | Signature | Description |
|----------|-----------|-------------|
| `llm_extract` | `(content: str) -> dict` | Extract role/company/location/experience using Ollama then Gemini |
| `ollama_extract` | `(content: str) -> dict` | Extract via Ollama only |
| `gemini_extract` | `(content: str) -> dict` | Extract via Gemini only |
| `llm_extract_emails` | `(content: str) -> list[str]` | Find obfuscated emails (hr at company dot com) via Gemini |
| `llm_deep_analyze` | `(content: str) -> dict` | Deep analysis: role, company, tech_stack, emails, fit_score, talking_points |
| `ollama_available` | `() -> bool` | Delegate to LLMClient singleton |

**Called by**: `extractors/pipeline.py`, `post_parser.py`.

---

## Service Dependency Map

```
orchestrator
  |-- scraper_service._scraper_coordinator
  |     |-- browser_service._run_on_browser_thread
  |     |-- post_parser.scrape_posts / scrape_feed / scrape_hashtags
  |     |-- scrapers.api_scrapers.*
  |     |-- scrapers.web_scrapers.*
  |     `-- scrapers.generic_scrapers.*
  |-- smart_filter.score_all_unscored / filter_unapplied
  `-- auto_apply.AutoApplyEngine
        |-- browser_service.browser_state (page)
        |-- liveness.check_url_liveness
        |-- resume_selector.get_resume_for_job
        |-- email_service.send_email_with_resume
        |     |-- email_ab_test.pick_variant / record_variant
        |     |-- referral_detector.find_connections
        |     `-- followup_cadence.analyze_followups / record_followup
        `-- ai_tools._call_gemini (form question answering)

email_service (bulk workers)
  |-- email_ab_test.pick_variant / record_variant
  |-- referral_detector.find_connections
  `-- followup_cadence.analyze_followups / record_followup

skills_intel (background analysis)
  `-- llm_extract_skills (Gemini, optional)

email_finder
  |-- strategies.py (all 7 strategies + verification)
  |-- enrich.py (bulk enrichment)
  `-- cron.py (scheduled runs)

llm module
  |-- client.py (Ollama + Gemini singleton)
  `-- extraction.py (job info + email deobfuscation)
```

---

## Adding a New Service

1. **Create file** in `backend/services/your_service.py`
2. **Define state dict** if the service has a background worker:
   ```python
   your_state = {"running": False, "status": "idle", ...}
   _your_lock = threading.Lock()
   ```
3. **Implement public functions** -- keep them stateless where possible
4. **Add route endpoints** in `backend/routes/your_route.py`:
   ```python
   from fastapi import APIRouter
   router = APIRouter(prefix="/api/your-feature", tags=["your-feature"])
   ```
5. **Register the router** in `backend/server.py`:
   ```python
   from routes.your_route import router as your_router
   app.include_router(your_router)
   ```
6. **Thread safety**: If the service has background workers, use a threading.Lock for state mutations and threading.Event for stop signals
7. **Error handling**: Catch exceptions, log them, set status to `"error"`, always reset `running` to `False` in finally blocks

---

## See Also

- [Architecture](ARCHITECTURE.md) -- System design, component interactions, threading model
- [API Reference](API_REFERENCE.md) -- All REST endpoints with request/response formats
- [Database Schema](DATABASE_SCHEMA.md) -- All tables, relationships, key queries
- [Setup Guide](SETUP_GUIDE.md) -- Installation, configuration, usage
