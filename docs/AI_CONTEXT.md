# CareerKit — AI Context Document

> This document provides full context for AI assistants (Claude, GPT, Copilot, Cursor, etc.) working on this codebase. It covers architecture, conventions, key decisions, and common patterns.

## What Is This Project?

CareerKit is a full-stack job hunting automation platform built for a single user (Vineet Kukreti, AI Engineer with 2 years experience, focused on healthcare AI roles). It:

1. **Scrapes** 100+ job sources (LinkedIn, RemoteOK, Greenhouse, Indeed, etc.)
2. **Extracts** structured job data via LLM (Ollama local → Gemini API fallback → regex)
3. **Scores** jobs on a 6-dimension fitness scale (role, domain, experience, location, tech stack)
4. **Auto-applies** to top-scoring jobs (LinkedIn Easy Apply, email, redirect)
5. **Sends cold emails** to hiring managers (Gemini-personalized, Gmail SMTP)
6. **Tracks** the full pipeline (Applied → Replied → Interviewing → Offer/Rejected)

## Tech Stack

- **Backend**: Python 3.11+, FastAPI, Uvicorn, SQLite3 (WAL mode)
- **Frontend**: React 19, Vite 8, Tailwind CSS 4, react-router-dom 7, lucide-react
- **Browser automation**: Playwright (Chromium, headed mode, persistent profiles)
- **LLM**: Ollama (qwen2.5:7b local) primary, Gemini 2.5 Flash-Lite fallback
- **Email**: Gmail SMTP (TLS port 587) with resume PDF attachment
- **No global state library**: React hooks + Context API only

## Key Architecture Decisions

### Threading Model
Playwright requires single-threaded access. The app uses a dedicated browser thread that receives commands via a Queue. All other background work (scraping, email generation, auto-apply) runs in daemon threads. Each thread gets its own SQLite connection via `threading.local()`.

### LLM Fallback Chain
`Ollama (free, local) → Gemini API (cheap, ~$0.01/200 posts) → Regex (free, offline)`. The app checks Ollama availability on each call and silently falls back. This means the app works fully offline if Ollama is running.

### Deduplication
Four-layer dedup: URL primary key → content hash v1 (200 chars) → content hash v2 (500 chars normalized) → in-memory DedupCache for O(1) lookups during scraping sessions.

### Anti-Detection
Headed browser, persistent profiles, randomized UA/timezone/locale, human-like delays (beta distribution), per-character typing simulation, daily application caps (25 Easy Apply safe limit).

### Source Architecture
100+ sources split into 4 engine types:
- **Custom scrapers** — Hand-written Playwright/HTTP code (LinkedIn, Indeed, etc.)
- **API scrapers** — JSON endpoint consumers (RemoteOK, Greenhouse, Lever, Ashby)
- **Generic HTML** — BeautifulSoup with CSS selector configs (62+ sites)
- **Generic API** — Template-based JSON consumers

### Email Generation
Gemini system prompt includes candidate profile, 5 past projects, and strict rules (120-180 words, no cliches, specific references to JD). Emails are generated as drafts first, allowing human review before sending.

## File Structure Conventions

```
backend/
├── routes/     → FastAPI route handlers (thin, delegate to services)
├── services/   → Business logic (scraping, email, auto-apply, AI tools)
├── scrapers/   → Source-specific scraping implementations
├── extractors/ → Data extraction pipeline (LLM + regex + fitness)
├── llm/        → LLM client and extraction prompts
├── email_finder/ → Contact email discovery
├── utils/      → Anti-detection utilities
├── config.py   → User profile, skills, search strategy
├── config_sources.py → 100+ source definitions
├── db.py       → SQLite schema, CRUD, dedup
├── server.py   → FastAPI app entry point
└── post_parser.py → LinkedIn scraping via Playwright

frontend-src/src/
├── pages/      → One file per page (13 pages)
├── components/ → Shared UI (Sidebar, BrowserBar, Toast, etc.)
├── lib/api.js  → All API calls in one file
├── App.jsx     → Shell + routing + connection gating
└── index.css   → Dark theme + Tailwind config
```

## Coding Patterns

### Backend

**Route pattern** (thin routes, delegate to services):
```python
@router.post("/scraper/start")
async def start_scraper(req: ScraperStartRequest):
    # Validate
    # Spawn daemon thread → service function
    # Return status
```

**Thread-safe state pattern**:
```python
scraper_state = {"running": False, "sources": {}}
_scraper_lock = threading.Lock()

with _scraper_lock:
    scraper_state["running"] = True
```

**Browser thread command pattern**:
```python
def _run_on_browser_thread(fn, *args, timeout=60):
    result_q = queue.Queue()
    _browser_cmd_q.put((fn, args, result_q))
    status, result = result_q.get(timeout=timeout)
    return result
```

**DB access pattern** (thread-local connections):
```python
_local = threading.local()
def _get_db():
    if not hasattr(_local, 'conn'):
        _local.conn = init_db()
    return _local.conn
```

### Frontend

**API call pattern**:
```javascript
const api = {
    getPosts: (params) => fetch(`/api/db/posts?${new URLSearchParams(params)}`).then(r => r.json()),
    startScraper: (data) => fetch('/api/scraper/start', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(data) }).then(r => r.json()),
};
```

**Polling pattern** (for real-time updates):
```javascript
useEffect(() => {
    const interval = setInterval(async () => {
        const status = await api.getScraperStatus();
        setState(status);
    }, 2000);
    return () => clearInterval(interval);
}, []);
```

**Page data loading pattern**:
```javascript
useEffect(() => {
    const load = async () => {
        try {
            const [stats, posts] = await Promise.allSettled([
                api.getDbStats(),
                api.getPosts(filters),
            ]);
            // set state from results
        } catch (e) {
            toast.error("Failed to load");
        }
    };
    load();
}, []);
```

## Database

SQLite3 with WAL mode at `data/linkedin_jobs.db`. 9 tables:
- `posts` — Scraped content (PK: post_url)
- `jobs` — Extracted job details (FK → posts)
- `email_outreach` — Email drafts and sent (FK → posts)
- `pipeline_leads` — CRM leads (FK → posts, email_outreach)
- `pipeline_events` — Timeline events (FK → pipeline_leads)
- `pipeline_notes` — Notes (FK → pipeline_leads)
- `startup_leads` — Company database
- `applications` — Apply history (FK → posts)
- `daily_quotas` — Rate limits (PK: date)

See `docs/DATABASE_SCHEMA.md` for full schema.

## Configuration

| File | Purpose | Sensitive? |
|------|---------|-----------|
| `config/.env` | API keys, SMTP credentials | YES - gitignored |
| `backend/config.py` | User profile, skills, search strategy | Partially (email, phone) |
| `backend/config_sources.py` | 100+ source definitions | No |
| `config/portals.yml` | 37 tracked healthcare companies | No |

## Important Constants

| Constant | Value | Location |
|----------|-------|----------|
| DB_PATH | `data/linkedin_jobs.db` | db.py |
| SAFE_APPLY_LIMIT | 25/day | humanize.py |
| PLATFORM_BUDGETS.linkedin | 120/day | auto_apply.py |
| PLATFORM_BUDGETS.email | 180/day | auto_apply.py |
| RATE_LIMITS.linkedin | 45-120s | auto_apply.py |
| OLLAMA_MODEL | qwen2.5:7b | llm/client.py |
| GEMINI_MODEL | gemini-2.5-flash-lite | llm/client.py |
| EMAIL_BLOCKLIST | ["southguild"] | email_service.py |

## Common Tasks for AI Assistants

### Adding a new job source
1. Add source definition to `backend/config_sources.py` (in appropriate category)
2. If custom scraper needed, add to `backend/scrapers/` (api_scrapers.py or web_scrapers.py)
3. Register in `SOURCE_GROUPS` for UI grouping
4. Test with `python scripts/test_all_sources.py`

### Adding a new API endpoint
1. Add route handler in appropriate `backend/routes/*.py`
2. Add business logic in `backend/services/*.py`
3. Add API call in `frontend-src/src/lib/api.js`
4. Add UI in appropriate page component

### Adding a new page
1. Create `frontend-src/src/pages/NewPage.jsx`
2. Add route in `frontend-src/src/App.jsx`
3. Add nav item in `frontend-src/src/components/Sidebar.jsx`

### Modifying the database schema
1. Add column in `backend/db.py` table creation
2. Add migration in `_run_migrations()` (idempotent ALTER TABLE)
3. Update relevant CRUD functions
4. Update relevant API routes and frontend

### Adding a new AI tool
1. Add Gemini prompt + function in `backend/services/ai_tools.py`
2. Add route in `backend/routes/tools.py`
3. Add API call in `frontend-src/src/lib/api.js`
4. Add tab in `frontend-src/src/pages/AITools.jsx`

## Design System (Frontend)

Dark theme with purple accent:
- **BG**: Primary `#0A0A0A`, Secondary `#1A1A1A`, Tertiary `#252525`
- **Text**: White primary, `#A1A1AA` secondary, `#71717A` muted
- **Accent**: Purple `#A855F7`
- **Status**: Green `#22C55E`, Orange `#F59E0B`, Red `#EF4444`, Blue `#3B82F6`
- **Font**: Inter (sans), Geist Mono (monospace)
- **Cards**: `bg-bg-secondary border border-border rounded-2xl`
- **Buttons**: `rounded-lg px-4 py-2 text-sm font-medium`

## Testing

```bash
# Test all 100+ job sources
python scripts/test_all_sources.py

# Check backend health
curl http://localhost:8000/api/db/stats

# View logs
tail -f data/logs/backend.log
tail -f data/logs/daily.log
```

## Deployment

Currently single-machine only (requires display for headed Playwright). Runs on Linux (Manjaro). Start with `./run.sh`.

Cron automation:
- `0 8 * * 1-5` — Daily scrape + apply cycle
- `0 */2 * * *` — Email enrichment
