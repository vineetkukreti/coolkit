# CareerKit Architecture

## System Overview

CareerKit is a full-stack job hunting automation platform that scrapes 100+ job sources, extracts structured data via LLM, scores candidates against job fitness, automates applications, and manages cold email outreach — all from a single dark-themed React dashboard.

```
                          +--------------------------+
                          |      React Frontend      |
                          |    (Vite + Tailwind)      |
                          |      Port 5173 (dev)      |
                          +------------+-------------+
                                       |
                                  /api proxy
                                       |
                          +------------v-------------+
                          |     FastAPI Backend       |
                          |       Port 8000           |
                          +--+-----+-----+-----+----+
                             |     |     |     |
              +--------------+  +--+--+  |  +--+----------+
              |                 |     |  |  |              |
     +--------v------+  +------v-+ +-v--v--v--+  +--------v-------+
     |   Playwright   |  |  LLM   | | SQLite  |  |  SMTP (Gmail)  |
     | Browser Engine |  | Engine | |   DB    |  |  Email Sender  |
     +-------+--------+  +---+----+ +----+----+  +----------------+
             |                |           |
     +-------v--------+  +---v----+  +---v---------+
     | LinkedIn, Indeed|  | Ollama |  | posts       |
     | Wellfound, YC   |  | (local)|  | jobs        |
     | 100+ portals    |  +---+----+  | outreach    |
     +-----------------+      |       | pipeline    |
                          +---v----+  | applications|
                          | Gemini |  | leads       |
                          | (API)  |  | quotas      |
                          +--------+  +-------------+
```

## Tech Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| Frontend | React 19 + Vite 8 + Tailwind CSS 4 | SPA dashboard |
| Backend | FastAPI + Uvicorn | REST API server |
| Database | SQLite3 (WAL mode) | Persistent storage |
| Browser | Playwright (Chromium) | Web scraping + auto-apply |
| LLM (primary) | Ollama (qwen2.5:7b) | Local extraction |
| LLM (fallback) | Gemini 2.5 Flash-Lite | Cloud extraction |
| Email | Gmail SMTP (TLS) | Cold outreach |
| Routing | react-router-dom 7 | Client-side routing |
| Icons | lucide-react | UI icons |

## Directory Structure

```
careerkit/
├── backend/
│   ├── server.py              # FastAPI app, route registration, static mount
│   ├── config.py              # User profile, skills, search keywords, regions
│   ├── config_sources.py      # 100+ job source definitions
│   ├── db.py                  # SQLite schema, CRUD, dedup, export/import
│   ├── post_parser.py         # LinkedIn post/job scraping via Playwright
│   ├── routes/
│   │   ├── jobs.py            # Job search, apply/skip tracking
│   │   ├── scraper.py         # Multi-source scraper orchestration
│   │   ├── browser.py         # Playwright browser lifecycle
│   │   ├── posts.py           # DB queries, post listing
│   │   ├── email.py           # Email generation, sending, bulk ops
│   │   ├── pipeline.py        # CRM lead tracking
│   │   ├── leads.py           # Startup leads CRUD + enrichment
│   │   ├── settings.py        # Profile, SMTP, Gemini config
│   │   ├── tools.py           # AI tools, ATS, analytics, smart filter
│   │   └── auto_apply.py      # Auto-apply engine control
│   ├── services/
│   │   ├── orchestrator.py    # Daily cycle coordination
│   │   ├── scraper_service.py # Scraper state + thread management
│   │   ├── browser_service.py # Playwright thread + anti-detection
│   │   ├── email_service.py   # Gemini email gen + SMTP send
│   │   ├── auto_apply.py      # Application automation engine
│   │   ├── smart_filter.py    # Multi-factor job scoring (0-10)
│   │   ├── ai_tools.py        # Gemini-powered career tools
│   │   ├── ats_scanner.py     # ATS API scanner (Greenhouse/Lever/Ashby)
│   │   ├── import_leads.py    # CSV/Excel lead import
│   │   ├── liveness.py        # Job URL liveness checker
│   │   ├── pattern_analysis.py# Outreach metrics + recommendations
│   │   ├── company_signals.py # Company health/hiring signals
│   │   ├── followup_cadence.py# Follow-up scheduling
│   │   ├── resume_selector.py # Best resume variant for job
│   │   ├── email_ab_test.py   # Email variant performance
│   │   └── logger.py          # Structured logging
│   ├── scrapers/
│   │   ├── linkedin_jobs.py   # LinkedIn job search scraper
│   │   ├── linkedin_posts.py  # LinkedIn post/feed scraper
│   │   ├── linkedin_feed.py   # LinkedIn feed reader
│   │   ├── linkedin_hashtags.py# Hashtag-based scraping
│   │   ├── linkedin_deep.py   # Deep profile/job extraction
│   │   ├── api_scrapers.py    # RemoteOK, Greenhouse, Lever, etc.
│   │   ├── web_scrapers.py    # Browser-based site scrapers
│   │   ├── generic_scrapers.py# Template HTML + API scrapers
│   │   ├── web.py             # HTTP utilities
│   │   ├── helpers.py         # Scraper helper functions
│   │   └── extract_posts.js   # JS injected into LinkedIn DOM
│   ├── extractors/
│   │   ├── pipeline.py        # Post processing pipeline
│   │   ├── text.py            # Regex extraction (email, role, location)
│   │   └── fitness.py         # Role relevance + experience fit check
│   ├── llm/
│   │   ├── client.py          # Ollama + Gemini client (singleton)
│   │   └── extraction.py      # LLM prompts for job extraction
│   ├── email_finder/
│   │   ├── enrich.py          # Web scraping for contact emails
│   │   └── cron.py            # Scheduled email enrichment
│   └── utils/
│       └── humanize.py        # Anti-detection delays + DailyCap
├── frontend-src/
│   ├── src/
│   │   ├── App.jsx            # Main shell, routing, connection gate
│   │   ├── main.jsx           # React entry point
│   │   ├── index.css          # Dark theme, Tailwind config
│   │   ├── lib/api.js         # API client (all endpoints)
│   │   ├── pages/
│   │   │   ├── Dashboard.jsx  # Stats, analytics, outreach insights
│   │   │   ├── JobSearch.jsx  # Keyword search + apply/skip
│   │   │   ├── Posts.jsx      # LinkedIn posts DB + scraper panel
│   │   │   ├── Scraper.jsx    # Multi-source scraper control
│   │   │   ├── AutoApply.jsx  # Auto-apply engine dashboard
│   │   │   ├── EmailOutreach.jsx # Email gen, drafts, sending
│   │   │   ├── Pipeline.jsx   # Kanban + list CRM view
│   │   │   ├── LeadDetail.jsx # Single lead timeline + notes
│   │   │   ├── StartupLeads.jsx # Company leads database
│   │   │   ├── EmailAnalytics.jsx # Follow-up tracking + metrics
│   │   │   ├── AppHistory.jsx # Application log + export CSV
│   │   │   ├── AITools.jsx    # Evaluate, outreach, deep-dive, CV, interview
│   │   │   └── Settings.jsx   # Profile, SMTP, API keys, resume upload
│   │   └── components/
│   │       ├── Sidebar.jsx    # Navigation (3 sections)
│   │       ├── BrowserBar.jsx # Browser status bar (top)
│   │       ├── ConnectGate.jsx# Connection gating + onboarding
│   │       ├── Onboarding.jsx # 4-step setup wizard
│   │       └── Toast.jsx      # Notification system
│   ├── package.json
│   └── vite.config.js         # Proxy /api → :8000
├── frontend/                  # Built production files
├── scripts/
│   ├── daily_run.py           # Cron: daily scrape + apply cycle
│   ├── login.py               # One-time LinkedIn login
│   ├── test_all_sources.py    # Source health check (100 sources)
│   ├── run_email_finder.sh    # Cron: email enrichment
│   ├── start.sh               # Simple backend launcher
│   ├── fix_sources.py         # Source configuration fixes
│   └── inspect_dom.py         # DOM structure inspector
├── config/
│   ├── .env                   # API keys, SMTP credentials
│   └── portals.yml            # 37 tracked healthcare companies + ATS config
├── data/
│   ├── linkedin_jobs.db       # SQLite database
│   ├── leads/                 # Imported lead files
│   ├── logs/                  # Runtime logs
│   └── browser_profiles/      # Persistent Chromium sessions
├── run.sh                     # Master launcher (backend + frontend)
├── requirements.txt           # Python dependencies
└── .gitignore
```

## Component Interactions

### 1. Scraping Pipeline

```
User clicks "Start Scraper" in UI
         │
         v
POST /api/scraper/start {max_posts, sources[]}
         │
         v
scraper_service._scraper_coordinator()
         │
         ├── Thread 1: LinkedIn (browser required)
         │   └── post_parser.scrape_posts(page, conn)
         │       ├── extract_posts.js (injected into DOM)
         │       └── extractors/pipeline.process_single_post()
         │           ├── Dedup check (URL + content hash)
         │           ├── text.extract_emails() + extract_roles()
         │           ├── llm_extract() (Ollama → Gemini → regex)
         │           ├── text.score_domain_relevance()
         │           ├── fitness.is_good_fit()
         │           └── db.insert_post() + db.insert_job()
         │
         ├── Thread 2: API sources (no browser)
         │   └── api_scrapers.scrape_remoteok/greenhouse/lever()
         │       └── HTTP GET → JSON parse → insert_post()
         │
         └── Thread 3-N: Browser sources (own threads)
             └── web_scrapers.scrape_indeed/wellfound/naukri()
                 └── Playwright page → CSS selectors → insert_post()
```

### 2. Email Outreach Pipeline

```
GET /api/db/outreach-ready
    → Posts with emails + not yet contacted
         │
         v
POST /api/email/bulk-generate {post_ids[]}
         │
         v
email_service._bulk_generate_worker()
    │
    ├── For each post:
    │   ├── Build context (author, role, company, content)
    │   ├── _generate_email_with_gemini()
    │   │   └── System prompt: candidate profile + 5 projects
    │   │       + rules (120-180 words, no cliches, specific refs)
    │   └── Save draft → email_outreach (status=draft)
    │
    v
POST /api/email/bulk-send {attach_resume}
         │
         v
email_service._bulk_send_worker()
    │
    ├── For each draft:
    │   ├── Check EMAIL_BLOCKLIST
    │   ├── _send_email_smtp() (Gmail TLS on 587)
    │   │   └── Optional resume PDF attachment
    │   └── Update status → sent
    │
    v
POST /api/pipeline/sync
    └── Auto-create pipeline_leads from sent emails
```

### 3. Auto-Apply Pipeline

```
POST /api/auto-apply/start {max_applications}
         │
         v
auto_apply._auto_apply_worker()
    │
    ├── db.get_unapplied_jobs(limit=600)
    ├── Sort by: fit_score DESC, domain_relevance DESC
    │
    └── For each job:
        ├── Check PLATFORM_BUDGETS (LinkedIn: 120/day, Email: 180/day)
        ├── Check RATE_LIMITS (LinkedIn: 45-120s, Email: 10-30s)
        ├── Route by apply method:
        │   ├── LinkedIn Easy Apply → Playwright form fill
        │   │   └── humanize._linkedin_warm_up() (scroll, wait)
        │   ├── Email Apply → draft + send via SMTP
        │   └── Redirect → open URL in browser
        ├── Log to applications table
        └── Update daily_quotas
```

### 4. LLM Extraction Chain

```
Raw post text
    │
    ├── Try 1: Ollama (qwen2.5:7b, local, free)
    │   └── POST http://localhost:11434/api/generate
    │       └── JSON: {role, company, location, experience}
    │
    ├── Try 2: Gemini 2.5 Flash-Lite (API, ~$0.01/200 posts)
    │   └── google.genai.Client.generate()
    │       └── JSON: {role, company, location, experience}
    │
    └── Try 3: Regex fallback (free, offline)
        ├── text.extract_roles() → keyword matching
        ├── text.extract_location() → pattern matching
        └── text.extract_experience() → year pattern matching
```

## Threading Model

CareerKit uses a carefully designed multi-thread architecture because Playwright requires single-threaded access:

```
Main Thread (FastAPI/Uvicorn)
    │
    ├── Browser Thread (dedicated, long-lived)
    │   └── Owns: Playwright, browser, page objects
    │   └── Receives commands via: _browser_cmd_q (Queue)
    │   └── Returns results via: per-command result queues
    │
    ├── Scraper Threads (daemon, per-source)
    │   ├── LinkedIn scraper → sends commands to Browser Thread
    │   ├── API scrapers → direct HTTP (no browser)
    │   └── Web scrapers → own Playwright contexts
    │
    ├── Email Worker Thread (daemon, singleton)
    │   └── Bulk generate or bulk send
    │   └── State: email_worker_state dict + _email_lock
    │
    ├── Auto-Apply Thread (daemon, singleton)
    │   └── State: auto_apply_state dict + _apply_lock
    │
    └── Thread-Local DB Connections
        └── Each thread gets own SQLite connection via _local
```

## Anti-Detection Measures

| Measure | Implementation |
|---------|---------------|
| Persistent browser profile | Stores cookies, avoids re-login |
| Headed mode | Playwright runs visible (not headless) |
| Randomized User-Agent | Chrome 120-124 on Linux/Mac/Windows |
| Viewport spoofing | 1920x1080, device scale 1 |
| Timezone/locale rotation | Matches ACTIVE_REGIONS config |
| Geolocation mocking | GPS coordinates per region |
| Human-like delays | Beta-distributed random waits (humanize.py) |
| Typing simulation | Per-character delays (60-180ms) |
| Scroll simulation | Random increments, pauses |
| Daily caps | Hard limit: 25 Easy Apply/day (safe < 15) |
| Rate limiting | 45-120s between LinkedIn applications |
| Randomized search queries | Different keywords each run |

## State Management

### Backend State (in-memory dicts)

| State | Location | Purpose |
|-------|----------|---------|
| `browser_state` | browser_service.py | Browser lifecycle (running, logged_in, page) |
| `scraper_state` | scraper_service.py | Scraper progress per source |
| `email_worker_state` | email_service.py | Bulk email progress |
| `auto_apply_state` | auto_apply.py | Auto-apply progress |

### Frontend State

- No global state library (no Redux/Zustand)
- React hooks: useState, useEffect, useRef, useCallback
- Context API: Toast notifications only
- localStorage: Setup completion flag
- Polling: 2-5 second intervals for real-time updates

## Configuration Hierarchy

```
config/.env                    # Secrets (API keys, SMTP)
    ↓ loaded by
backend/config.py              # User profile, skills, search strategy
    ↓ imports
backend/config_sources.py      # 100+ source definitions
    ↓ referenced by
config/portals.yml             # 37 tracked healthcare companies
```
