# coolkit -- Architecture

> System design, component interactions, threading model, and data flow.

## System Overview

coolkit is a full-stack job hunting automation platform. It scrapes 120+ job sources in parallel, extracts structured data via a local/cloud LLM chain, scores jobs on six weighted dimensions, automates applications across LinkedIn Easy Apply, email, and redirect channels, and manages cold email outreach with IMAP reply detection -- all from a single-page React dashboard.

The system is designed for local-only deployment on a single machine. There is no authentication layer; the assumption is the operator is the only user.

```
+-------------------------------------------------------------+
|                    React 19 SPA (Vite 8)                     |
|              Port 5173 (dev) / static (prod)                 |
+----------------------------+--------------------------------+
                             |
                        /api proxy
                             |
+----------------------------v--------------------------------+
|                   FastAPI + Uvicorn                          |
|                      Port 8000                               |
|                                                              |
|   routes/         services/         scrapers/                |
|   (11 modules)    (18 modules)      (5 modules)             |
+-----+--------+--------+--------+--------+------------------+
      |        |        |        |        |
      v        v        v        v        v
 +---------+ +-----+ +------+ +------+ +------+
 |Playwright| |Ollama| |SQLite| |Gmail | |IMAP  |
 |Chromium  | |local | | WAL  | |SMTP  | |Gmail |
 +---------+ +-----+ +------+ +------+ +------+
      |        |
      |    +---v----+
      |    | Gemini |
      |    | 2.5 FL |
      |    +--------+
      v
 120+ job boards
 (LinkedIn, Indeed, Wellfound, RemoteOK, Greenhouse, ...)
```

## Tech Stack

| Layer | Technology | Version | Purpose |
|-------|-----------|---------|---------|
| Frontend | React + Vite + Tailwind CSS | 19.2 / 8.0 / 4.2 | Single-page dashboard |
| Backend | FastAPI + Uvicorn | latest | REST API server |
| Database | SQLite3 (WAL mode) | stdlib | Persistent storage, all tables |
| Browser | Playwright (Chromium) | latest | LinkedIn scraping, auto-apply, web scrapers |
| LLM (primary) | Ollama (qwen2.5:7b) | local | Job extraction, free, ~1-3s latency |
| LLM (fallback) | Gemini 2.5 Flash-Lite | API | Cloud extraction + email generation, ~2-5s |
| Email (send) | Gmail SMTP (TLS, port 587) | -- | Cold outreach, follow-ups, application emails |
| Email (receive) | Gmail IMAP (SSL, port 993) | -- | Reply detection, bounce detection |
| Routing | react-router-dom | 7.14 | Client-side URL routing |
| Icons | lucide-react | 1.8 | UI iconography |
| DNS | dnspython | -- | MX record validation before sending |
| Search | duckduckgo-search | -- | DuckDuckGo job search scraper |

## Directory Structure

```
coolkit/
├── backend/
│   ├── server.py                 # FastAPI app creation, CORS, route registration, IMAP startup
│   ├── config.py                 # PROFILE dict, RESUME_SKILLS, search keywords, regions, query builder
│   ├── config_sources.py         # 120+ source definitions (CUSTOM, GENERIC_API, GENERIC_HTML)
│   ├── db.py                     # SQLite schema (13 tables), CRUD, DedupCache, migrations, CLI
│   ├── post_parser.py            # LinkedIn-specific scraping (search, feed, hashtags, deep fetch)
│   │
│   ├── routes/                   # Thin request handlers, delegate to services
│   │   ├── jobs.py               # Job search results, apply/skip actions
│   │   ├── scraper.py            # Start/stop/status for multi-source scraper
│   │   ├── browser.py            # Browser lifecycle (start, stop, login, check)
│   │   ├── posts.py              # Post listing, filtering, stats, outreach-ready
│   │   ├── email.py              # Email generation, sending, bulk ops, IMAP, follow-ups
│   │   ├── pipeline.py           # CRM pipeline (leads, events, notes, stages)
│   │   ├── leads.py              # Startup leads CRUD, import, email enrichment
│   │   ├── settings.py           # Profile editing, SMTP config, resume management
│   │   ├── tools.py              # AI tools, ATS scanner, smart filter, analytics
│   │   ├── auto_apply.py         # Auto-apply engine start/stop/status
│   │   └── skills_intel.py       # Skills demand analysis, education trends
│   │
│   ├── services/                 # Business logic, background workers, state management
│   │   ├── orchestrator.py       # Daily cycle: scrape -> score -> apply -> report
│   │   ├── scraper_service.py    # Scraper coordinator, thread pool, per-source state
│   │   ├── browser_service.py    # Playwright thread, command queue, anti-detection
│   │   ├── email_service.py      # Gemini email generation, SMTP, IMAP polling, follow-ups
│   │   ├── auto_apply.py         # AutoApplyEngine class, tier strategy, form filling
│   │   ├── smart_filter.py       # 6-dimension scoring (0-10), threshold gating
│   │   ├── ai_tools.py           # Gemini-powered career tools (evaluate, deep-dive, etc.)
│   │   ├── ats_scanner.py        # Greenhouse/Lever/Ashby API scanner
│   │   ├── import_leads.py       # CSV/Excel lead import
│   │   ├── liveness.py           # Job URL liveness checker (expired detection)
│   │   ├── pattern_analysis.py   # Outreach metrics + response rate analytics
│   │   ├── company_signals.py    # Company health/hiring signal detection
│   │   ├── followup_cadence.py   # Follow-up scheduling and analysis
│   │   ├── resume_selector.py    # Best resume variant for job archetype
│   │   ├── email_ab_test.py      # A/B test variant tracking for emails
│   │   ├── referral_detector.py  # Connection/referral detection at target companies
│   │   ├── quality_dashboard.py  # Data quality metrics
│   │   ├── skills_intel.py       # Skills extraction and demand summarization
│   │   └── logger.py             # Structured logging utility
│   │
│   ├── scrapers/                 # Source-specific scraping implementations
│   │   ├── api_scrapers.py       # RemoteOK, Himalayas, HN, Remotive, Greenhouse, Lever, etc.
│   │   ├── web_scrapers.py       # DuckDuckGo, Wellfound, YC, Indeed, Naukri, Arc.dev, etc.
│   │   └── generic_scrapers.py   # Config-driven HTML (BeautifulSoup) and API (JSON) scrapers
│   │
│   ├── extractors/               # Content processing pipeline
│   │   ├── pipeline.py           # Unified: dedup -> email -> LLM -> roles -> fitness -> domain
│   │   ├── text.py               # Regex extraction (emails, roles, locations, experience)
│   │   └── fitness.py            # Role relevance + experience fit check
│   │
│   ├── llm/                      # LLM abstraction layer
│   │   ├── client.py             # LLMClient singleton: Ollama -> Gemini fallback chain
│   │   └── extraction.py         # LLM prompts for structured job data extraction
│   │
│   └── email_finder/             # Contact discovery
│       ├── enrich.py             # Web scraping for contact emails
│       ├── cron.py               # Scheduled email enrichment
│       └── strategies.py         # Email finding strategies
│
├── frontend-src/                 # React source (Vite dev server)
│   ├── src/
│   │   ├── App.jsx               # Shell, routing, ConnectGate, session banner
│   │   ├── main.jsx              # React entry point
│   │   ├── index.css             # Dark theme variables, Tailwind base
│   │   ├── lib/api.js            # Centralized API client (all endpoints)
│   │   ├── pages/                # 19 page components
│   │   │   ├── Dashboard.jsx     # Stats overview, analytics cards
│   │   │   ├── FindJobs.jsx      # Tabbed: search + scraper + posts
│   │   │   ├── ApplyPage.jsx     # Tabbed: auto-apply engine + history
│   │   │   ├── OutreachPage.jsx  # Tabbed: email outreach + startup leads
│   │   │   ├── InsightsPage.jsx  # Tabbed: analytics + quality dashboard
│   │   │   ├── Pipeline.jsx      # Kanban/list CRM view
│   │   │   ├── LeadDetail.jsx    # Single lead timeline + notes
│   │   │   ├── AITools.jsx       # Evaluate, outreach, deep-dive, CV, interview tools
│   │   │   ├── SkillsIntelligence.jsx # Skills demand analysis charts
│   │   │   ├── Settings.jsx      # Profile, SMTP, API keys, resume upload
│   │   │   └── ... (+ legacy pages for backward compat redirects)
│   │   └── components/           # 7 shared components
│   │       ├── Sidebar.jsx       # Navigation with 3 sections
│   │       ├── BrowserBar.jsx    # Browser status indicator (top bar)
│   │       ├── ConnectGate.jsx   # Connection gating + onboarding flow
│   │       ├── Onboarding.jsx    # 4-step setup wizard
│   │       ├── FilterBar.jsx     # Reusable filter controls
│   │       ├── PageTabs.jsx      # Reusable tabbed navigation
│   │       └── Toast.jsx         # Notification context + provider
│   ├── package.json
│   └── vite.config.js            # Proxy /api -> :8000
│
├── frontend/                     # Vite production build output
├── config/
│   ├── .env                      # API keys, SMTP/IMAP credentials (gitignored)
│   └── portals.yml               # Tracked healthcare companies + ATS config
├── data/
│   ├── linkedin_jobs.db          # SQLite database (WAL mode)
│   ├── leads/                    # Imported lead CSV/Excel files
│   ├── logs/                     # Runtime logs (backend.log, frontend.log)
│   └── browser_profiles/         # Persistent Chromium session data (gitignored)
├── scripts/
│   ├── test_all_sources.py       # Source health checker
│   ├── full_scrape.py            # Full scrape across all sources
│   └── test_live_scrape.py       # Live scrape test
├── run.sh                        # Master launcher (4 modes: dev, prod, back, front)
└── requirements.txt              # Python dependencies
```

## Component Architecture

### Route Layer

Routes are thin HTTP handlers. They validate inputs, delegate to services, and return JSON responses. All routes are registered on the FastAPI app in `server.py`.

| Module | Prefix | Purpose |
|--------|--------|---------|
| `jobs.py` | `/api/jobs` | Job search results, apply/skip tracking |
| `scraper.py` | `/api/scraper` | Multi-source scraper start/stop/status |
| `browser.py` | `/api/browser` | Playwright browser lifecycle management |
| `posts.py` | `/api/db` | Post listing, filtering, stats, outreach-ready queries |
| `email.py` | `/api/email` | Email generation, bulk send, IMAP, follow-up ops |
| `pipeline.py` | `/api/pipeline` | CRM pipeline leads, events, notes, stage transitions |
| `leads.py` | `/api/leads` | Startup leads CRUD, CSV import, email enrichment |
| `settings.py` | `/api/settings` | Profile CRUD, SMTP config, resume upload |
| `tools.py` | `/api/tools` | AI tools, ATS scan, smart filter, analytics |
| `auto_apply.py` | `/api/auto-apply` | Auto-apply engine start/stop/status/quota |
| `skills_intel.py` | `/api/skills` | Skills demand analysis, run/status |

### Service Layer

Services own business logic, background threads, and in-memory state. Each service manages its own threading lock and state dict.

**Core orchestration:**
- `orchestrator.py` -- Daily cycle coordinator (scrape -> score -> apply -> report)
- `scraper_service.py` -- Scraper thread pool, per-source state tracking, coordinator
- `browser_service.py` -- Playwright command queue, dedicated browser thread

**Application engine:**
- `auto_apply.py` -- AutoApplyEngine class, tiered strategy, LinkedIn Easy Apply form filling
- `smart_filter.py` -- 6-dimension scoring engine (role, skill, domain, experience, quality, location)
- `resume_selector.py` -- Selects best resume variant per job archetype
- `liveness.py` -- Checks whether job URLs are still active

**Email pipeline:**
- `email_service.py` -- Gemini email generation, SMTP sending, IMAP polling, bounce detection
- `email_ab_test.py` -- A/B variant picking and performance tracking
- `followup_cadence.py` -- Follow-up scheduling based on time since last contact
- `referral_detector.py` -- Finds connections at target companies for warm outreach

**Intelligence:**
- `ai_tools.py` -- Gemini-powered career tools (evaluate fit, generate outreach, interview prep)
- `skills_intel.py` -- Regex + LLM skill extraction, demand summary aggregation
- `pattern_analysis.py` -- Outreach metrics, response rates, recommendations
- `company_signals.py` -- Company health/hiring signal detection
- `quality_dashboard.py` -- Data quality metrics across the pipeline

**Data management:**
- `import_leads.py` -- CSV/Excel lead import with deduplication
- `ats_scanner.py` -- Scans Greenhouse, Lever, Ashby APIs for open positions

### Scraper Engine

The scraper system supports four source types, each with different execution models:

**Custom scrapers** (26 sources) -- Hand-written scraper functions in `api_scrapers.py` and `web_scrapers.py`. These handle sites with complex pagination, authentication, or anti-bot measures.

**Generic API scrapers** (3 sources) -- Config-driven JSON endpoint scrapers defined in `config_sources.py` under `GENERIC_API_SOURCES`. Each entry specifies `url`, `jobs_path` (JSONPath to the array), and `fields` (dot-notation mappings). Executed by `generic_scrapers.scrape_generic_api()`.

**Generic HTML scrapers** (90+ sources) -- Config-driven HTML page scrapers defined in `GENERIC_HTML_SOURCES`. Each entry specifies `urls`, CSS `selectors` for card/title/company/location/link, and a `base_url`. Executed by `generic_scrapers.scrape_generic_html()` using requests + BeautifulSoup.

**Browser scrapers** (11 sources) -- Sites that require JavaScript rendering or have strong anti-bot protection. Each browser scraper gets its own Playwright instance in its own thread. Includes DuckDuckGo, Wellfound, YC, Indeed (JP), Naukri, and others.

**Parallel execution:**

The `_scraper_coordinator()` function in `scraper_service.py` orchestrates all sources:

1. LinkedIn-family sources (search, feed, hashtags, enricher, deep fetch) run **sequentially** on the dedicated browser thread because they share the logged-in LinkedIn session.
2. API scrapers run in **parallel** daemon threads -- lightweight HTTP calls with no browser.
3. Generic HTML/API scrapers run in **parallel** daemon threads -- each gets its own thread.
4. Browser scrapers run in **parallel** threads, each launching its own Playwright Chromium instance.

Per-source progress is tracked via `scraper_state["sources"][source_name]` with status, log entries, and progress counters. A threading lock (`_scraper_lock`) protects all state mutations.

### LLM Engine

The LLM layer uses a fallback chain to maximize availability while minimizing cost:

```
Ollama (qwen2.5:7b, local)     -- Try first. Free, ~1-3s latency.
         |
         v (if unavailable or empty response)
Gemini 2.5 Flash-Lite (API)    -- Cloud fallback. ~$0.01/200 posts, ~2-5s.
         |
         v (if API fails)
Regex fallback                  -- Pattern matching. Free, instant, lower accuracy.
```

The `LLMClient` singleton in `llm/client.py` handles this chain. It probes Ollama availability on first call and caches the result. Gemini uses the `google-genai` SDK with the API key from `config/.env`.

**Usage contexts:**
- **Job extraction** (`llm/extraction.py`): Extracts role, company, location, experience from raw post text.
- **Email generation** (`email_service.py`): Uses Gemini directly (bypasses Ollama) for long-form email drafting.
- **Form answers** (`auto_apply.py`): LLM-generated answers for custom application form questions (premium tier only).
- **AI tools** (`ai_tools.py`): Gemini for evaluate-fit, deep-dive, interview prep, etc.

### Extractor Pipeline

The unified pipeline in `extractors/pipeline.py` processes every scraped post through these stages:

```
Raw post dict (from any scraper)
     |
     v
1. Content validation -- Reject posts shorter than 20 characters
     |
     v
2. Deduplication -- Check URL + content_hash via DedupCache (in-memory O(1))
     |                Also fuzzy-matches normalized 100-char content prefixes
     v
3. Email extraction -- JS-extracted emails + regex scan + LLM deobfuscation
     |
     v
4. LLM extraction -- Ollama/Gemini extracts {role, company, location, experience}
     |                Falls back to regex extractors in text.py
     v
5. Domain scoring -- Counts healthcare/clinical keyword matches -> High/Medium/Low
     |
     v
6. Fitness check -- Validates role relevance + experience range for candidate
     |                Rejects mismatches (e.g., "10+ years senior" for a 2yr candidate)
     v
7. Storage -- db.insert_post() + db.insert_job() (one post -> multiple job rows)
```

### Email System

The email pipeline has four distinct phases:

**1. Generation** -- Gemini 2.5 Flash-Lite generates personalized cold emails using a detailed system prompt that includes the candidate profile, 3 key projects, and strict rules (120-180 words, no cliches, specific references to the post content). A/B testing picks between "proof-first" and "challenge-first" strategies. Referral connections are woven in when detected.

**2. Validation** -- Before sending, each email address is checked: format validation via regex, domain MX record lookup via `dnspython`, blocklist check (current employer, known-bouncing domains), generic prefix filtering (careers@, hr@, noreply@), and dedup against already-contacted recipients.

**3. Sending** -- `_bulk_send_worker()` sends drafts via Gmail SMTP with TLS. Each email includes plain text + HTML versions plus an optional resume PDF attachment. Anti-spam delay of 3-8 seconds between sends. Failed sends are tagged with `error_type` (bounced, auth_error, timeout, rejected).

**4. Reply detection** -- `_imap_poll_worker()` polls Gmail IMAP every 5 minutes (started on FastAPI startup). It searches the inbox for messages FROM any outreach recipient, matches replies by subject threading, and classifies them: `interested`, `auto_reply`, `rejection`, or `info`. Bounce detection searches for mailer-daemon messages and marks corresponding outreach entries as failed. Detected replies update `pipeline_leads` stage to "replied".

### Auto-Apply Engine

The `AutoApplyEngine` class orchestrates automated job applications with a tiered strategy based on smart scores:

**Tier system:**

| Tier | Score Range | Email Personalization | LLM Form Answers | Rate Limit |
|------|-------------|----------------------|-------------------|------------|
| PREMIUM | >= 7.0 | Gemini-personalized | Yes | 60-150s |
| STANDARD | >= 5.0 | Gemini-personalized | No (known answers only) | Method default |
| BASIC | >= 3.5 | Template email | No | Method default |
| SKIP | < 3.5 | -- | -- | -- |

**Apply methods (in priority order):**

1. **LinkedIn Easy Apply** -- Playwright navigates to the job URL, simulates human warm-up (scrolling, reading), clicks Easy Apply, fills multi-step forms using `PROFILE` config + LLM for custom questions, uploads the best resume variant, and submits. Budget: 120/day.

2. **Email Apply** -- Sends application email with resume attached via SMTP. Gemini generates personalized subject + body for premium/standard tiers; template for basic tier. Budget: 180/day.

3. **Redirect** -- Logs the job for manual follow-up when neither Easy Apply nor email is available.

**Pre-apply checks:** URL dedup, `applications` table dedup, daily quota check, smart_score threshold gate, and liveness check (HEAD request to verify the posting is still active).

## Threading Model

coolkit uses multiple threads because Playwright requires all operations on the same thread that created the browser context, while FastAPI serves requests from a thread pool.

```
Main Thread
  |-- FastAPI/Uvicorn (handles HTTP requests)
  |
  +-- Browser Thread (dedicated, long-lived, daemon)
  |     Created by: browser_service._browser_worker()
  |     Owns: Playwright instance, browser context, page objects
  |     Communication: _browser_cmd_q (Queue) for commands
  |                    Per-command result Queue for responses
  |     Runs: LinkedIn scraping, Easy Apply, login check
  |
  +-- Scraper Coordinator Thread (daemon, per-run)
  |     Created by: scraper_service._scraper_coordinator()
  |     Spawns child threads:
  |       +-- LinkedIn sources thread (sends commands to Browser Thread)
  |       +-- API scraper threads (1 per source, direct HTTP)
  |       +-- Generic scraper threads (1 per source, HTTP + BeautifulSoup)
  |       +-- Browser scraper threads (1 per source, own Playwright instance)
  |     Joins all child threads, then updates final state.
  |
  +-- Email Generate Worker (daemon, singleton)
  |     Created by: email_service._bulk_generate_worker()
  |     State: email_worker_state + _email_lock
  |
  +-- Email Send Worker (daemon, singleton)
  |     Created by: email_service._bulk_send_worker()
  |     Shares: email_worker_state + _email_lock
  |
  +-- IMAP Poll Worker (daemon, long-lived)
  |     Created by: email_service._imap_poll_worker()
  |     Started on: FastAPI startup event (server.py)
  |     Polls every 5 minutes, sleeps in 1-second increments for clean shutdown
  |     State: imap_worker_state + _imap_lock
  |
  +-- Auto-Apply Worker (daemon, singleton)
  |     Created by: auto_apply.start_auto_apply()
  |     State: auto_apply_state + _apply_lock
  |
  +-- Follow-up Worker (daemon, singleton)
  |     Created by: email_service._auto_followup_worker()
  |     State: followup_worker_state + _followup_lock
  |
  +-- Orchestrator Thread (daemon, per-run)
        Created by: orchestrator.start_daily_cycle()
        Coordinates: scraper phase -> scoring phase -> apply phase -> report
        State: orchestrator_state + _orch_lock
```

**Key constraints:**
- All Playwright operations on the main LinkedIn browser must go through `_browser_cmd_q`.
- Browser scraper threads (DuckDuckGo, Wellfound, etc.) launch their own isolated Playwright instances -- they do not share the main browser.
- Every background thread creates its own SQLite connection via `init_db()`. SQLite WAL mode allows concurrent reads.
- All state dicts are protected by their own `threading.Lock` instances.

## Data Flow

End-to-end pipeline from source discovery to UI display:

```
1. SOURCE DISCOVERY
   config_sources.py defines 120+ sources across 20 groups
   config.py builds randomized search queries (150 max, shuffled)
        |
        v
2. SCRAPING (parallel, per-source threads)
   LinkedIn: Playwright -> DOM extraction via injected JS
   API:      HTTP GET -> JSON parse
   HTML:     HTTP GET -> BeautifulSoup CSS selectors
   Browser:  Playwright -> page interaction -> CSS selectors
        |
        v
3. EXTRACTION (extractors/pipeline.py)
   Raw post -> dedup -> email extraction -> LLM extraction -> fitness check
        |
        v
4. SCORING (services/smart_filter.py)
   6 dimensions x weights = smart_score (0-10)
   Verdict: APPLY (>=5.0) | CONSIDER (3.5-5.0) | SKIP (<3.5)
        |
        v
5. STORAGE (db.py)
   posts table + jobs table (1:N) + indexes
   smart_score column for fast filtered queries
        |
        v
6. APPLICATION (services/auto_apply.py)
   Tier assignment -> method selection -> apply -> log -> quota update
        |
        v
7. OUTREACH (services/email_service.py)
   Generate (Gemini) -> validate (MX + blocklist) -> send (SMTP) -> poll (IMAP)
        |
        v
8. UI DISPLAY (React SPA)
   Polling (2-5s intervals) -> render tables, stats, pipeline kanban
```

## Error Handling Strategy

### Route layer

All route handlers use try/except blocks that return `JSONResponse` with a consistent shape:

```python
{"status": "error", "message": "Human-readable description"}
```

HTTP status codes: 200 for success, 400 for bad input, 404 for not found, 500 for internal errors.

### Service layer

Services return dicts with a `status` or `error` field. Background workers catch exceptions per-item and continue processing the rest of the batch, logging errors to the worker state's `results` array.

### Database layer

SQLite WAL mode (`PRAGMA journal_mode=WAL`) prevents most write locks by allowing concurrent readers. Each thread creates its own connection via `init_db()` with `check_same_thread=False`. Migrations are idempotent -- `ALTER TABLE ADD COLUMN` wrapped in try/except to handle "column already exists".

### Frontend

Toast notifications (via React Context) surface errors from API calls. Loading states are tracked per-component via `useState`. Polling continues on error -- the next poll may succeed.

### Common error scenarios

| Scenario | Handling |
|----------|----------|
| Ollama not running | LLMClient falls back to Gemini, then regex |
| Gemini API key missing | Warning on startup, email generation disabled |
| SMTP credentials missing | Warning on startup, email features disabled |
| Browser crash | Manual restart via UI; session persists in browser_profiles/ |
| Scraper source fails | Per-source isolation -- other sources continue |
| Email bounce | IMAP detects mailer-daemon, marks outreach as failed |
| Daily quota hit | Auto-apply loop stops, reports "quota exhausted" |
| LinkedIn rate limit | Human-like delays (45-120s), daily Easy Apply cap (120) |
| Duplicate post | DedupCache (in-memory) catches via URL + content_hash + prefix |

## Recovery and Resilience

**Browser crash recovery** -- The browser profile is stored in `data/browser_profiles/main/`. On restart, Playwright reloads the persistent context, preserving cookies and the LinkedIn login session. Stale Singleton lock files are cleaned up automatically before launch.

**LLM unavailability** -- The `LLMClient.call()` method implements automatic fallback: Ollama -> Gemini -> empty string. Callers handle empty responses by falling back to regex extractors. The Ollama availability check is cached after the first probe.

**SQLite resilience** -- WAL mode allows multiple readers and a single writer concurrently. Thread-local connections eliminate cross-thread access. The `DedupCache` pre-loads all URL/hash pairs into memory for O(1) lookups, avoiding repeated SQL queries during high-throughput scraping.

**Scraper fault isolation** -- The coordinator runs each source in its own thread. If one source throws an exception, it is caught, the source status is set to "error", and all other sources continue. The final scraper status is "done" unless every source failed.

**SMTP failure handling** -- Each send attempt returns structured error information including `error_type` (invalid_address, auth_error, connection, rejected, timeout, unknown) and `error_message`. Failed emails are marked in the database and can be retried.

**Daily quotas** -- The `daily_quotas` table enforces a hard cap (default 500 applications/day). The auto-apply loop checks `quota_remaining()` before each application. Platform-specific budgets (LinkedIn: 120, email: 180) provide additional per-channel limits.

**Graceful shutdown** -- All worker threads check a stop flag (`threading.Event`) between iterations. The IMAP poller sleeps in 1-second increments so it can stop within 1 second. `run.sh` traps SIGINT/SIGTERM and kills all child processes.

## Performance Characteristics

| Operation | Typical Latency | Notes |
|-----------|----------------|-------|
| API source scrape | 2-10s per source | HTTP calls, no browser overhead |
| HTML source scrape | 3-15s per source | requests + BeautifulSoup parsing |
| Browser source scrape | 10-30s per source | Playwright launch + page load + JS |
| LinkedIn search scrape | 30-120s per run | Multiple queries, human-like delays |
| LLM extraction (Ollama) | 1-3s per post | Local, qwen2.5:7b, ~80 tokens |
| LLM extraction (Gemini) | 2-5s per post | API round-trip, ~150 tokens |
| Smart scoring | <1ms per post | Pure Python, no I/O |
| Email generation (Gemini) | 3-8s per email | ~400 token output |
| SMTP send | 1-3s per email | TLS handshake + send |
| IMAP poll cycle | 5-30s | Depends on inbox size + match count |
| Easy Apply (one job) | 30-120s | Human-like delays, multi-step form |
| SQLite read | <1ms | WAL mode, indexed queries |
| SQLite write | 1-5ms | Single-writer, auto-commit |
| Frontend polling | 2-5s intervals | Per-page, via `setInterval` |

**Parallelism:** During a full scrape, 10-20 threads may run simultaneously (1 browser thread + 10 API threads + several generic scraper threads). Each thread uses its own SQLite connection. Memory usage is dominated by Playwright browser instances (~200-400MB each for browser scrapers).

## Security Model

**Credential storage** -- All secrets (API keys, SMTP password, IMAP password) live in `config/.env`, which is gitignored. They are loaded via `python-dotenv` on startup.

**Browser session** -- The persistent Chromium profile in `data/browser_profiles/` stores cookies and local storage, including the LinkedIn login session. This directory is gitignored.

**Anti-detection measures:**

| Measure | Implementation |
|---------|---------------|
| Persistent browser profile | Cookies survive restarts, avoids re-login |
| Headed mode (not headless) | Playwright runs a visible browser window |
| WebDriver flag removal | `navigator.webdriver` overridden to `undefined` |
| Fake plugin list | Chrome PDF Plugin, PDF Viewer, Native Client |
| Chrome runtime mock | `window.chrome = { runtime: {}, loadTimes, csi }` |
| Permissions API patch | Fixes Playwright fingerprint in notifications query |
| Randomized viewport | Width: 1280-1600, Height: 800-1024, per session |
| Randomized slow_mo | 600-1200ms between Playwright actions |
| Timezone/locale/geolocation | Matches `ACTIVE_REGIONS[0]` config |
| Human-like warm-up | Scrolling, pausing, reading before clicking Apply |
| Per-platform rate limits | LinkedIn: 45-120s, email: 10-30s between actions |
| Daily caps | Easy Apply: 120/day, email: 180/day, total: 500/day |
| Randomized search queries | Different keyword combos each run (150 max) |
| Anti-automation arg | `--disable-blink-features=AutomationControlled` |

**No API authentication** -- The FastAPI server has no auth middleware. It is intended for local-only access. CORS is fully open (`allow_origins=["*"]`).

## Frontend Architecture

**Stack:** React 19 + Vite 8 + Tailwind CSS 4. No Redux or state management library.

**State management:**
- Component-local state via `useState` / `useEffect` / `useRef` / `useCallback`
- Context API used only for Toast notifications (`ToastProvider`)
- `localStorage` for setup completion flag
- No WebSocket -- all real-time updates via HTTP polling at 2-5 second intervals

**Routing:** react-router-dom 7 with 10 primary routes and 9 redirect routes for backward compatibility with old URL structures. Tab state is persisted via URL search params (`?tab=scraper`).

**Pages (19 total):**
- `Dashboard.jsx` -- Stats cards, activity overview
- `FindJobs.jsx` -- Tabbed: job search + scraper control + posts browser
- `ApplyPage.jsx` -- Tabbed: auto-apply engine + application history
- `OutreachPage.jsx` -- Tabbed: email outreach + startup leads
- `InsightsPage.jsx` -- Tabbed: email analytics + quality dashboard
- `Pipeline.jsx` -- Kanban/list CRM view with stage columns
- `LeadDetail.jsx` -- Single lead with timeline, events, notes
- `AITools.jsx` -- Evaluate fit, generate outreach, deep-dive, CV, interview prep
- `SkillsIntelligence.jsx` -- Skills demand charts, education trends
- `Settings.jsx` -- Profile, SMTP config, API keys, resume management

**Components (7 shared):**
- `Sidebar.jsx` -- Navigation sidebar with 3 grouped sections
- `BrowserBar.jsx` -- Top bar showing browser connection status
- `ConnectGate.jsx` -- Hard gate when browser is stopped; soft banner for expired session
- `Onboarding.jsx` -- 4-step wizard (connect, configure, test, done)
- `FilterBar.jsx` -- Reusable filter controls
- `PageTabs.jsx` -- Reusable tabbed navigation with URL param sync
- `Toast.jsx` -- Notification system with context provider

**Theme:** Dark background with purple accent (`#A855F7`). All custom colors defined as CSS variables.

**API client:** `lib/api.js` exports a centralized `api` object with methods for every backend endpoint. All methods return parsed JSON. Errors surface via Toast.

## Configuration Hierarchy

```
config/.env                       # Secrets: GEMINI_API_KEY, SMTP_USER, SMTP_PASSWORD, etc.
    |
    v (loaded by python-dotenv on import)
backend/config.py                 # PROFILE dict, RESUME_SKILLS, TARGET_ROLES, DOMAIN_KEYWORDS,
    |                             # REGIONS, search query builder, random keyword engine
    v (imports)
backend/config_sources.py         # CUSTOM_SOURCES (26), GENERIC_API_SOURCES (3),
    |                             # GENERIC_HTML_SOURCES (90+), SOURCE_GROUPS (20)
    v (referenced by)
config/portals.yml                # 37 tracked healthcare companies + ATS endpoints
```

**Startup validation** (in `server.py`):
- Missing `SMTP_USER` or `SMTP_PASSWORD` -- prints warning, email features disabled
- Missing `GEMINI_API_KEY` -- prints warning, AI email generation will fail
- Ollama availability checked lazily on first LLM call

## See Also

- [API Reference](API_REFERENCE.md) -- All REST endpoints with request/response shapes
- [Database Schema](DATABASE_SCHEMA.md) -- All 13 tables, relationships, indexes, key queries
- [Services Reference](SERVICES_REFERENCE.md) -- Every service, function, and constant
- [System Diagrams](SYSTEM_DIAGRAMS.md) -- Mermaid diagrams for all data flows
