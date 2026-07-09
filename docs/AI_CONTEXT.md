# coolkit -- AI Assistant Context

> Exhaustive reference for AI assistants working on this codebase. Covers architecture
> decisions, error handling, recovery patterns, every service file, and step-by-step
> guides for common modifications. For the quick cheat sheet, see `CLAUDE.md` in the
> project root.

---

## Project Overview

coolkit is a full-stack job hunting automation platform built for a single user
(an AI Engineer with 2 years of healthcare AI experience). The system:

1. **Scrapes** 120+ job sources (LinkedIn, RemoteOK, Greenhouse, Indeed, Naukri, 60+ HTML boards, etc.)
2. **Extracts** structured job data via LLM (Ollama local, Gemini API fallback, regex last resort)
3. **Scores** jobs on a 6-dimension fitness scale (role match, skill match, domain relevance, experience fit, quality signals, location fit)
4. **Auto-applies** to top-scoring jobs (LinkedIn Easy Apply, email application, redirect/manual)
5. **Sends cold emails** to hiring managers (Gemini-personalized, Gmail SMTP, A/B tested)
6. **Discovers emails** via 7 strategies (Hunter.io, website scraping, DuckDuckGo, Google, person patterns, generic patterns, domain inference)
7. **Tracks** the full pipeline (Applied -> Replied -> Interviewing -> Offer/Rejected)
8. **Analyzes** skills demand across scraped jobs to identify market gaps

---

## Tech Stack

| Layer | Technology | Version / Notes |
|-------|-----------|-----------------|
| Backend framework | FastAPI + Uvicorn | Port 8000 |
| Frontend framework | React + Vite | React 19, Vite 8, port 5173 |
| Styling | Tailwind CSS 4 | Dark theme, purple accent #A855F7 |
| Routing (frontend) | react-router-dom 7 | Hash-free SPA routing |
| Icons | lucide-react | Consistent icon set throughout |
| Database | SQLite3 | WAL mode, `data/linkedin_jobs.db` |
| Browser automation | Playwright | Chromium, headed mode, persistent profiles |
| LLM (primary) | Ollama | qwen2.5:7b, local, free |
| LLM (fallback) | Google Gemini | gemini-2.5-flash-lite via google-genai SDK |
| Email | Gmail SMTP | TLS port 587, resume PDF attachment |
| Email discovery | Hunter.io, BeautifulSoup, DuckDuckGo, SMTP verification | 7 strategies in `email_finder/strategies.py` |
| State management | React hooks + Context | No Redux; only Toast uses Context |

---

## Architecture Decisions

### Threading Model

Playwright requires all operations on the thread that created the browser context. The app
uses a dedicated browser thread (`_browser_worker` in `browser_service.py`) that consumes
commands from a `queue.Queue`. FastAPI route handlers dispatch work via `_run_on_browser_thread(fn, *args, timeout)`.

All other background work (scraping coordinator, email bulk worker, auto-apply engine,
IMAP polling, skills analysis) runs in daemon threads spawned from route handlers. Each
daemon thread creates its own SQLite connection via `init_db()` (with `check_same_thread=False`).

Mutable shared state (e.g., `scraper_state`, `auto_apply_state`, `email_worker_state`) is
protected by `threading.Lock()` instances.

### LLM Fallback Chain

```
Ollama (qwen2.5:7b, local, free)
  |-- success --> return result
  |-- fail/empty --> Gemini 2.5 Flash-Lite (API, ~$0.01/200 posts)
                       |-- success --> return result
                       |-- fail/empty --> Regex extraction (free, offline)
```

The singleton `LLMClient` in `backend/llm/client.py` manages this chain. It lazily checks
Ollama availability and caches the result. Gemini is initialized on first use from the
`GEMINI_API_KEY` environment variable. The app works fully offline if Ollama is running.

### Deduplication Strategy

Four layers prevent duplicate job storage:

1. **URL unique index** -- `posts.post_url` has a UNIQUE index (where not null/empty)
2. **Content hash v1** -- SHA256 of first 200 chars (lowercase), stored in `content_hash` column
3. **Normalized prefix match** -- `DedupCache` in `db.py` normalizes whitespace, takes first 100 chars, matches in O(1) via a set
4. **In-memory session cache** -- `DedupCache` loads all URLs + hashes + prefixes at scrape start, avoids per-post SQL queries

### Anti-Detection (Browser Scraping)

- Headed browser with persistent profile (`data/browser_profiles/`)
- Randomized user agent, viewport size, timezone, locale, geolocation (per region config)
- Human-like delays between actions (beta distribution timing)
- Per-character typing simulation for form fills
- Daily application caps: 120 LinkedIn Easy Apply, 180 email, 30 per other platform
- Rate limits: 45-120s between LinkedIn applications, 10-30s between emails

### Source Architecture

120+ sources in `backend/config_sources.py` split into 4 engine types:

| Engine | Count | Implementation | Browser? |
|--------|-------|---------------|----------|
| Custom scrapers | ~26 | Hand-written code in `scrapers/` | Mixed |
| Generic HTML | ~80 | BeautifulSoup + CSS selector configs | No |
| Generic API | ~3 | Template-based JSON consumers | No |
| ATS scrapers | ~3 (Greenhouse, Lever, Ashby) | Dedicated API consumers | No |

Sources are organized into 20 groups (linkedin, api, ats, remote, ai_ml, india, japan,
europe, uae, us, singapore, web3, academic, healthcare, startup, niche, regional,
freelance, browser, multi).

### Email Generation

Gemini system prompt includes full candidate profile, 5 key projects, and strict output
rules (120-180 words, no cliches, specific JD references, professional tone). Emails are
generated as drafts first, allowing human review. A/B testing alternates between hook styles
and tracks reply rates to auto-optimize.

### Email Discovery (7 Strategies)

Defined in `backend/email_finder/strategies.py`, executed in priority order:

1. **Hunter.io API** -- Domain search (free tier: 25/month)
2. **Website scraping** -- Crawl contact/about/careers pages for mailto links and text emails
3. **DuckDuckGo search** -- Search for company + email, extract from snippets and linked pages
4. **Google search fallback** -- Same approach via googlesearch-python
5. **Person-name patterns** -- Generate guesses: firstname@, first.last@, flast@, etc.
6. **Generic patterns** -- careers@, hr@, hiring@, info@, contact@, etc.
7. **Domain inference** -- Infer company domain from name, verify via MX records

Each found email gets a quality score (0-100) based on prefix type, domain type, source
trust, and SMTP verification status.

---

## Error Handling Strategy

### Route Level

All route handlers wrap logic in try/except. Errors return a `JSONResponse` with appropriate
HTTP status code and a JSON body of `{status: "error", message: "..."}`. Successful
responses typically include `{status: "ok", ...data}`.

### Service Level

Services return dicts with status/error keys, or raise exceptions that routes catch.
Background workers (scraper, email, auto-apply) catch exceptions per-item and continue
processing the batch, logging errors to their state dicts.

### Database Level

SQLite runs in WAL mode (`PRAGMA journal_mode=WAL`), which prevents most write locks and
allows concurrent reads. Connections use `check_same_thread=False`. Migrations in
`_run_migrations()` are idempotent (ALTER TABLE wrapped in try/except for "column already
exists"). Foreign keys are enforced (`PRAGMA foreign_keys=ON`).

### Frontend Level

- `useToast()` hook from `ToastProvider` context for user-facing notifications (success,
  error, warning, info) with auto-dismiss after 4 seconds
- Loading states on all async operations
- `ConnectGate` component blocks the app when the browser is disconnected (hard gate) or
  shows a soft banner when the LinkedIn session expires

### Common Failures and Handling

| Failure | Cause | Handling |
|---------|-------|----------|
| Browser not connected | Playwright not started | ConnectGate blocks UI; routes return error |
| Ollama timeout | Local LLM server down | Silent fallback to Gemini API |
| Gemini API failure | API key missing/expired | Silent fallback to regex extraction |
| SMTP auth failure | Wrong credentials in .env | Email features disabled at startup with warning |
| Scraper 403/429 | Rate limiting / blocking | Per-source error isolation, other sources continue |
| SQLite locked | Concurrent write contention | WAL mode prevents most cases; retry on lock |
| LinkedIn session expired | Cookie timeout | Soft banner with "Reconnect" button |

---

## Recovery Patterns

| Component | Recovery Mechanism |
|-----------|--------------------|
| Browser | Auto-restart on crash; session persists in `data/browser_profiles/`; ConnectGate UI |
| LLM | Automatic fallback chain (Ollama -> Gemini -> regex); lazy availability checking |
| SQLite | WAL mode resilience; thread-local connections avoid cross-thread issues |
| Scraper | Per-source error isolation; coordinator continues to next source on failure |
| Email worker | Blocklist for known-bad domains; bounce tracking; error classification |
| Auto-apply | Daily quota enforcement; per-platform rate limits; skip on error, continue batch |
| IMAP polling | Daemon thread with configurable interval; auto-start on server startup |

---

## Complete Services Inventory

All files in `backend/services/`:

| Service | File | Purpose |
|---------|------|---------|
| AI Tools | `ai_tools.py` | Gemini-powered job evaluation, outreach generation, company deep-dive, CV tailoring, interview prep |
| ATS Scanner | `ats_scanner.py` | Scans Greenhouse/Ashby/Lever APIs for tracked companies in portals.yml |
| Auto-Apply | `auto_apply.py` | Automated job application engine: LinkedIn Easy Apply, email apply, redirect. Daily quotas and rate limits |
| Browser Service | `browser_service.py` | Playwright lifecycle management, dedicated browser thread, command queue, login flow |
| Company Signals | `company_signals.py` | Gemini-based company health check (funding, layoffs, size). Used by smart_filter |
| Email A/B Test | `email_ab_test.py` | Generates 2 email variants per job, alternates sending, tracks reply rates |
| Email Service | `email_service.py` | Email generation (Gemini), SMTP sending with attachment, bulk worker, IMAP reply detection, blocklist |
| Follow-up Cadence | `followup_cadence.py` | Computes follow-up urgency, determines next follow-up dates, records follow-up events |
| Import Leads | `import_leads.py` | Imports CSV/XLSX lead files from `leads/` directory into startup_leads table |
| Liveness | `liveness.py` | Classifies job posting URLs as active/expired/uncertain via HTTP checks and regex |
| Logger | `logger.py` | Application tracking -- logs to SQLite worker_runs table, optional CSV/Excel export |
| Orchestrator | `orchestrator.py` | Daily automation cycle: scrape all sources, rank jobs, auto-apply until quota exhausted, generate report |
| Pattern Analysis | `pattern_analysis.py` | Outreach pattern analysis: which email styles, domains, roles get replies |
| Quality Dashboard | `quality_dashboard.py` | Conversion analytics: apply method vs response rate, smart score vs interview rate, domain vs reply rate |
| Referral Detector | `referral_detector.py` | Checks local data for LinkedIn connections at target company before cold applying |
| Resume Selector | `resume_selector.py` | Picks best resume variant based on job archetype (healthcare-ai, genai-platform, data-engineering) |
| Scraper Service | `scraper_service.py` | Scraper coordinator: manages per-source state, spawns source threads, aggregates results |
| Skills Intelligence | `skills_intel.py` | Extracts skills from saved jobs, computes market demand, identifies resume gaps, researches trends |
| Smart Filter | `smart_filter.py` | 6-dimension scoring (role, skill, domain, experience, quality, location). Threshold: >=5.0 auto-apply, 3.5-5.0 review, <3.5 skip |

---

## Complete Routes Inventory

All files in `backend/routes/`:

| Router | File | Prefix | Key Endpoints |
|--------|------|--------|---------------|
| Jobs | `jobs.py` | `/api` | GET /profile, GET /stats, POST /search, POST /apply, POST /skip, GET /applications |
| Browser | `browser.py` | `/api/browser` | POST /start, POST /stop, POST /login, POST /check-login, GET /status |
| Scraper | `scraper.py` | `/api/scraper` | POST /start, POST /stop, GET /status, GET /sources |
| Posts | `posts.py` | `/api/db` | GET /posts, GET /stats, GET /outreach-ready, POST /posts/{id}/find-email |
| Email | `email.py` | `/api/email` | POST /generate, POST /send, POST /bulk-generate, POST /bulk-send, GET /history, GET /stats, POST /check-replies |
| Pipeline | `pipeline.py` | `/api/pipeline` | GET /, GET /stats, GET /lead/{id}, POST /update-stage, POST /add-note, POST /sync |
| Leads | `leads.py` | `/api/leads` | GET /, GET /stats, GET /sources, GET /{id}, POST /{id}/update, POST /import |
| Settings | `settings.py` | `/api/settings` | GET /all, POST /profile, POST /smtp, POST /gemini, POST /test-email, POST /upload-resume, GET /resume-status |
| Tools | `tools.py` | `/api` | POST /tools/evaluate, POST /tools/outreach, POST /tools/deep-dive, POST /tools/tailor-cv, POST /tools/interview-prep, GET /ats/companies, POST /ats/scan, followup endpoints, analytics, smart-filter, company, resumes |
| Auto-Apply | `auto_apply.py` | `/api/auto-apply` | POST /start, POST /stop, GET /status, GET /quota |
| Skills Intel | `skills_intel.py` | `/api/skills` | GET /dashboard, POST /analyze, GET /analysis-status, GET /gaps, GET /trends, POST /trends/refresh, GET /news |

---

## Frontend Architecture

### Page Structure (19 pages)

Primary navigation pages (visible in Sidebar):
- `Dashboard.jsx` -- Overview stats, recent activity, quick actions
- `FindJobs.jsx` -- Tabbed: job search, scraper control, browse posts (tab via `?tab=`)
- `ApplyPage.jsx` -- Tabbed: auto-apply engine, application history
- `OutreachPage.jsx` -- Tabbed: email compose/bulk, startup leads
- `InsightsPage.jsx` -- Tabbed: email analytics, quality dashboard
- `Pipeline.jsx` -- Kanban-style lead pipeline tracker
- `LeadDetail.jsx` -- Individual lead view with timeline and notes
- `AITools.jsx` -- Tabbed: job evaluator, outreach generator, company deep-dive, CV tailor, interview prep
- `SkillsIntelligence.jsx` -- Skills demand analysis, gap identification, trends
- `Settings.jsx` -- Profile, SMTP, Gemini API key, resume upload

Legacy pages (still exist but redirected from old routes):
- `JobSearch.jsx`, `Scraper.jsx`, `Posts.jsx`, `EmailOutreach.jsx`, `EmailAnalytics.jsx`, `AutoApply.jsx`, `AppHistory.jsx`, `QualityDashboard.jsx`, `StartupLeads.jsx`

### Components (7)

| Component | Purpose |
|-----------|---------|
| `Sidebar.jsx` | Left nav with page links, active state, branding |
| `BrowserBar.jsx` | Top bar showing browser connection status |
| `ConnectGate.jsx` | Blocks app when browser disconnected; provides `useLinkedInStatus()` hook |
| `Toast.jsx` | Notification system; provides `ToastProvider` and `useToast()` hook |
| `FilterBar.jsx` | Reusable filter/search bar component |
| `PageTabs.jsx` | Reusable tab navigation, syncs with URL search params |
| `Onboarding.jsx` | First-run setup wizard |

### Frontend Patterns

**State management**: No Redux. React hooks + Context. Only `ToastContext` is global. All
page state is local via `useState`/`useEffect`.

**Polling**: Pages poll their status endpoints at 2-5 second intervals using `setInterval`
inside `useEffect`. Cleanup on unmount.

**Tab persistence**: Multi-tab pages use URL search params (`?tab=scraper`) via
`useSearchParams`. Tab state survives page refresh and browser back/forward.

**API client**: All endpoints in `frontend-src/src/lib/api.js` (75+ functions). Uses a
shared `request()` wrapper that handles JSON parsing and error extraction.

**Connection gating**: `ConnectGate` component with `useLinkedInStatus()` hook polls
`/api/browser/status` every 3 seconds. Hard gate (full block) when browser is stopped;
soft banner when browser is running but LinkedIn session expired.

---

## Database Overview

SQLite3 with WAL mode at `data/linkedin_jobs.db`. Schema defined in `backend/db.py`.

### Tables (13)

| Table | Purpose | Key Columns |
|-------|---------|-------------|
| `posts` | Scraped content | post_url (unique), content_hash, author_name, email, domain_relevance, fit_score, smart_score, source |
| `jobs` | Extracted job details | post_id (FK), role, company, location, experience, salary, tech_stack |
| `email_outreach` | Email drafts and sent | post_id (FK), recipient_email, subject, body, status, reply_detected_at, outreach_type |
| `pipeline_leads` | CRM lead tracker | post_id (FK), outreach_id (FK), stage, source |
| `pipeline_events` | Lead timeline events | lead_id (FK), event_type, title, content |
| `pipeline_notes` | Lead notes | lead_id (FK), content |
| `startup_leads` | Company database | company_name, website, email, industry, sector, location, funding_info |
| `applications` | Apply history | post_id (FK), platform, job_url (unique), status, apply_method |
| `daily_quotas` | Rate limits per day | date (PK), target, applied, failed, skipped |
| `worker_runs` | Background job tracking | worker_type, status, total, succeeded, failed |
| `skill_mentions` | Skills per job | job_id (FK), skill_name, category, required_level |
| `skill_demand_summary` | Aggregated skill stats | skill_name (unique), mention_count, percentage |
| `education_demands` | Education requirements | job_id (FK), degree_level, requirement, field |
| `skills_analysis_runs` | Analysis job tracking | status, total_jobs, processed |

### Migration Pattern

New columns are added via `_run_migrations()` in `db.py`. Each migration is an
`ALTER TABLE ADD COLUMN` wrapped in try/except (idempotent -- ignores "column already
exists" errors). Add new migrations to the `_MIGRATIONS` list or the inline list in
`run_migrations()`.

---

## Configuration Overview

### config/.env (secrets -- gitignored)

```
GEMINI_API_KEY=...        # Google AI API key for Gemini calls
SMTP_HOST=smtp.gmail.com  # Email server
SMTP_PORT=587
SMTP_USER=...             # Gmail address
SMTP_PASSWORD=...         # Gmail app password
FROM_EMAIL=...
FROM_NAME=...
HUNTER_API_KEY=...        # Optional: Hunter.io for email discovery
```

### backend/config.py (profile and search strategy)

- `PROFILE` dict -- Name, email, phone, resume path, experience, LinkedIn/GitHub URLs
- `RESUME_SKILLS` dict -- Skills with weight scores (1-5) for fitness matching
- `TARGET_ROLES` list -- Prioritized role titles
- `DOMAIN_KEYWORDS` list -- Healthcare/medical domain terms for relevance scoring
- `ROLE_KEYWORDS` dict -- Role title -> keyword variants mapping
- `REGIONS` dict -- 6 regions (India, Japan, Europe, UAE, US, Singapore) with locations, timezone, geolocation, locale
- `HASHTAG_FEEDS` list -- LinkedIn hashtags for scraping
- `JOB_SEARCH_QUERIES` list -- Pre-built search queries
- `build_smart_queries()` -- Generates 150 ranked, deduplicated queries per run (randomized)

### backend/config_sources.py (source registry)

Three source dictionaries:
- `CUSTOM_SOURCES` (~26) -- Sources with hand-written scraper functions
- `GENERIC_HTML_SOURCES` (~80) -- CSS selector-configured HTML scrapers
- `GENERIC_API_SOURCES` (~3) -- Template-based JSON API consumers

Each source has: label, group, type/engine. HTML sources additionally have: urls, selectors
(card, title, company, location, link), base_url.

`SOURCE_GROUPS` dict (20 groups) provides UI labels, icons, and display order.

---

## Important Constants

| Constant | Value | Location |
|----------|-------|----------|
| DB_PATH | `data/linkedin_jobs.db` | `db.py` |
| OLLAMA_MODEL | `qwen2.5:7b` | `llm/client.py` |
| GEMINI_MODEL | `gemini-2.5-flash-lite` | `llm/client.py` |
| APPLY_THRESHOLD | 5.0 (smart score) | `smart_filter.py` |
| CONSIDER_THRESHOLD | 3.5 | `smart_filter.py` |
| PLATFORM_BUDGETS.linkedin_easy_apply | 120/day | `auto_apply.py` |
| PLATFORM_BUDGETS.email_apply | 180/day | `auto_apply.py` |
| RATE_LIMITS.linkedin_easy_apply | 45-120s | `auto_apply.py` |
| RATE_LIMITS.email_apply | 10-30s | `auto_apply.py` |
| MAX_QUERIES | 150 | `config.py` |
| EMAIL_BLOCKLIST | [employer_domain from profile] | `email_service.py` |

---

## Common AI Tasks

### Adding a New Job Source

1. Choose engine type: custom (hand-written scraper) or generic HTML (selector config)
2. For generic HTML, add entry to `GENERIC_HTML_SOURCES` in `backend/config_sources.py` with keys: label, group (must match SOURCE_GROUPS), urls, selectors (card, title, company, location, link), base_url
3. For custom scrapers, add function in `backend/scrapers/api_scrapers.py` or `web_scrapers.py`, register in `CUSTOM_SOURCES`
4. Test with `python scripts/test_all_sources.py`

### Adding a New API Endpoint

1. Add route handler in `backend/routes/*.py` (try/except, return `{status: "ok", ...}`)
2. Add business logic in `backend/services/*.py`
3. Add API call in `frontend-src/src/lib/api.js`
4. Use in page component with standard polling or load pattern

### Adding a New Frontend Page

1. Create `frontend-src/src/pages/NewPage.jsx`
2. Add route in `App.jsx`, nav item in `Sidebar.jsx`
3. Follow existing patterns: dark theme, `bg-bg-primary`, card containers

### Modifying the Database Schema

1. Add column in `CREATE TABLE` in `backend/db.py`
2. Add idempotent migration in `run_migrations()`: `"ALTER TABLE x ADD COLUMN y TEXT"`
3. Update CRUD functions, routes, and frontend as needed

### Adding a New AI Tool

1. Add Gemini prompt + function in `backend/services/ai_tools.py`
2. Add route in `backend/routes/tools.py`
3. Add API call in `api.js`, add tab in `AITools.jsx`

---

## Design System

### Colors

| Token | Hex | Usage |
|-------|-----|-------|
| bg-primary | #0A0A0A | Page background |
| bg-secondary | #1A1A1A | Card background |
| bg-tertiary | #252525 | Nested elements, hover states |
| fg-primary | #FFFFFF | Primary text |
| fg-secondary | #A1A1AA | Secondary text |
| fg-muted | #71717A | Placeholder, disabled |
| accent | #A855F7 | Purple, primary actions |
| success | #22C55E | Positive states |
| warning | #F59E0B | Caution states |
| danger | #EF4444 | Error states |
| info | #3B82F6 | Informational |

### Typography

- Sans: Inter (system fallback: -apple-system, Segoe UI, sans-serif)
- Mono: Geist Mono (system fallback: Menlo, Consolas, monospace)

### Component Patterns

- Cards: `bg-bg-secondary border border-border rounded-2xl p-6`
- Buttons: `rounded-lg px-4 py-2 text-sm font-medium`
- Primary button: `bg-accent hover:bg-accent-dim text-fg-inverse`
- Inputs: `bg-bg-tertiary border border-border rounded-lg px-3 py-2 text-fg-primary`
- Toast: 4 types (success, error, warning, info), auto-dismiss 4s, max 3 visible

---

## Testing

```bash
# Test all 120+ job sources (connectivity + selector matching)
python scripts/test_all_sources.py

# Full scrape test (all sources, writes to data/full_scrape_report.json)
python scripts/full_scrape.py

# Live scrape test
python scripts/test_live_scrape.py

# Check backend health
curl http://localhost:8000/api/db/stats

# Database CLI
python backend/db.py --stats
python backend/db.py --role "AI Engineer" --domain High --has-email
python backend/db.py --export output.xlsx
```

### Manual Testing Checklist

- Start browser, verify LinkedIn login
- Run scraper on 2-3 sources, verify posts appear in DB
- Generate email for a post, verify draft quality
- Send test email via Settings page
- Run auto-apply on 1-2 jobs, verify application logged
- Check pipeline sync creates leads from sent emails

---

## Deployment

Single-machine only (requires display for headed Playwright). Runs on Linux (Manjaro).
Start with `./run.sh` (starts both backend on :8000 and frontend dev server on :5173).
Production mode: `./run.sh --prod` serves built frontend from `frontend/` directory.

Cron automation via orchestrator:
- Daily scrape + apply cycle (orchestrator.py)
- Email enrichment every 2 hours (email_finder/cron.py)
- IMAP reply polling every 5 minutes (auto-started on server boot)

---

## See Also

- `CLAUDE.md` -- Quick-reference cheat sheet (under 120 lines)
- `docs/ARCHITECTURE.md` -- System design and component interactions
- `docs/API_REFERENCE.md` -- Complete REST API documentation
- `docs/DATABASE_SCHEMA.md` -- Full table schemas and relationships
- `docs/SETUP_GUIDE.md` -- Installation and configuration guide
- `docs/SYSTEM_DIAGRAMS.md` -- Mermaid diagrams for all data flows
- `docs/SERVICES_REFERENCE.md` -- Detailed service function documentation
