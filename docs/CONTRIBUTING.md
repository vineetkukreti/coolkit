# CareerKit -- Contributing Guide

> How to set up your development environment, follow project conventions, and submit contributions.

## Welcome

CareerKit is a full-stack job hunting automation platform: it scrapes 100+ job sources, extracts structured data via LLM, scores relevance, and automates applications and cold email outreach. Contributions are welcome in the following areas:

- **New job sources** -- the most common contribution (see below)
- **Bug fixes** -- scraper breakage, UI glitches, extraction accuracy
- **New features** -- pages, services, API endpoints
- **Documentation** -- improving or expanding the docs in `docs/`

## Development Setup

### Prerequisites

- Python 3.11+
- Node.js 18+ and npm
- Playwright browsers (`playwright install`)
- SQLite (included with Python)
- Ollama (optional, for local LLM) or a Gemini API key

### Steps

1. **Fork and clone** the repository.

2. **Create a Python virtual environment and install dependencies:**

   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   playwright install
   ```

3. **Install frontend dependencies:**

   ```bash
   cd frontend-src
   npm install
   cd ..
   ```

4. **Set up configuration:**

   Copy the example environment file and fill in your credentials:

   ```bash
   cp config/.env.example config/.env
   ```

   Required variables: `SMTP_USER`, `SMTP_PASSWORD`, `GEMINI_API_KEY`.
   Optional: `HUNTER_API_KEY`.

5. **Run the application:**

   ```bash
   ./run.sh           # backend + frontend dev (parallel)
   ./run.sh --prod    # backend only (serves built frontend)
   ./run.sh --back    # backend only
   ./run.sh --front   # frontend dev only
   ```

6. **Verify:**
   - Backend API: `http://localhost:8000/api/db/stats`
   - Frontend dev: `http://localhost:5173`

## Project Structure Overview

```
backend/
  server.py              # FastAPI entry point, router registration
  config.py              # User profile, search keywords
  config_sources.py      # 100+ job source definitions
  db.py                  # SQLite schema, migrations, queries
  routes/                # Thin API route handlers
  services/              # Business logic, state management, threads
  scrapers/              # API, browser, and generic scrapers
  extractors/            # LLM extraction, fitness scoring
  llm/                   # LLM client abstraction
frontend-src/
  src/App.jsx            # React Router setup
  src/pages/             # Page components
  src/components/        # Shared UI components
  src/lib/api.js         # Centralized API client
config/
  .env                   # Secrets (gitignored)
data/                    # SQLite DB, browser profiles, logs (gitignored)
scripts/                 # Utility and test scripts
docs/                    # Project documentation
```

For a deeper dive, see [Architecture](ARCHITECTURE.md).

## Code Style and Conventions

### Python (Backend)

- No enforced formatter. Match the style of existing code in each file.
- Prefer f-strings for string formatting.
- Use type hints where they already exist in the surrounding code.
- **Routes are thin handlers.** They validate input, call a service, and return the result. Do not put business logic in route files. Example pattern from `routes/scraper.py`:

  ```python
  @router.post("/api/scraper/start")
  def api_start_scraper(req: ScraperStartRequest):
      # Validate state
      # Delegate to service function
      # Return result
  ```

- **Services manage their own state and thread safety.** Use `threading.Lock` for shared state dicts. See `services/scraper_service.py` for the pattern.
- **Thread-local database connections.** Each thread calls `init_db()` to get its own SQLite connection. Never share connections across threads.
- Use **parameterized SQL queries** (e.g., `conn.execute("SELECT * FROM posts WHERE id = ?", (post_id,))`). Never use string interpolation or f-strings in SQL.
- Database schema uses `CREATE TABLE IF NOT EXISTS`. New columns on existing tables use `ALTER TABLE` wrapped in try/except (see `_MIGRATIONS` in `db.py`).

### JavaScript / React (Frontend)

- **Functional components only**, using hooks (`useState`, `useEffect`, `useMemo`, `useCallback`).
- **TailwindCSS utility classes** for all styling. No separate CSS files.
- **No Redux.** State is managed with React hooks. The only shared context is `ToastProvider` (see `components/Toast.jsx`).
- **Polling for real-time updates** (2-5 second intervals via `setInterval` in `useEffect`). No WebSocket.
- **All API calls go through `lib/api.js`**, which wraps `fetch` with error handling and JSON parsing. Add new endpoints there, not inline.
- **Dark theme with purple accent** (`#A855F7`). Use the existing Tailwind color tokens (`bg-bg-primary`, `text-fg-primary`, `bg-accent`, etc.).
- Icons come from `lucide-react`.

## Common Contribution Types

### Adding a New Job Source (Most Common)

This is the simplest way to contribute. There are three tiers of complexity:

**Tier 1: Generic HTML source (no code changes needed beyond config)**

1. Add an entry to `GENERIC_HTML_SOURCES` in `backend/config_sources.py`:

   ```python
   "mysite": {
       "label": "My Job Site",
       "group": "remote",         # Must match a key in SOURCE_GROUPS
       "urls": ["https://example.com/jobs?q=AI+engineer"],
       "selectors": {
           "card": ".job-listing",
           "title": "h2 a",
           "company": ".company-name",
           "location": ".location",
           "link": "h2 a",
       },
       "base_url": "https://example.com",
   },
   ```

2. The generic engine in `scrapers/generic_scrapers.py` handles the rest.

**Tier 2: Generic API source (JSON endpoint)**

1. Add an entry to `GENERIC_API_SOURCES` in `backend/config_sources.py`:

   ```python
   "myapi": {
       "label": "My API",
       "group": "api",
       "url": "https://api.example.com/jobs?q={query}&limit=50",
       "jobs_path": "results",
       "fields": {
           "title": "position_title",
           "company": "company_name",
           "location": "location",
           "url": "apply_url",
           "date": "posted_at",
       },
       "search_terms": ["AI Engineer", "Machine Learning"],
   },
   ```

**Tier 3: Custom scraper (needs a dedicated function)**

1. Add the source key to `CUSTOM_SOURCES` in `config_sources.py`.
2. Create a scraper function in `scrapers/api_scrapers.py` (for API-based) or the appropriate scraper file. Follow the standard interface:

   ```python
   def scrape_mysite(page, conn, max_posts=50, on_event=None) -> list[dict]:
       # page: Playwright page (None for API scrapers)
       # conn: SQLite connection
       # on_event: callback for progress events
       # Returns: list of post dicts
   ```

3. Register the scraper function in `services/scraper_service.py`.

**Testing your source:**

```bash
python scripts/test_all_sources.py
```

### Adding a New API Endpoint

1. Add the route in `backend/routes/` (new file or add to an existing one). Use `APIRouter`:

   ```python
   from fastapi import APIRouter
   router = APIRouter()

   @router.get("/api/my-feature/data")
   def get_data():
       conn = _get_db()
       # ...
   ```

2. Create a Pydantic model for request bodies if needed.
3. Implement the business logic in `backend/services/` (not in the route handler).
4. If you created a new route file, register it in `backend/server.py`:

   ```python
   from routes.my_feature import router as my_feature_router
   app.include_router(my_feature_router)
   ```

5. Add the frontend API function in `frontend-src/src/lib/api.js`:

   ```javascript
   getMyData: () => request('/my-feature/data'),
   ```

### Adding a New Frontend Page

1. Create the page component in `frontend-src/src/pages/MyPage.jsx`. Follow existing patterns: loading state, error handling, Toast notifications.
2. Add the route in `App.jsx`:

   ```jsx
   <Route path="/my-page" element={<MyPage />} />
   ```

3. Add a sidebar entry in `components/Sidebar.jsx`.
4. Use `useToast()` from `components/Toast.jsx` for success/error notifications.

### Modifying the Database Schema

1. For **new tables**: add `CREATE TABLE IF NOT EXISTS` in the `SCHEMA` string in `backend/db.py`.
2. For **new columns on existing tables**: add an `ALTER TABLE` statement to the `_MIGRATIONS` list or `run_migrations()`. Wrap in try/except so it is idempotent:

   ```python
   _MIGRATIONS = [
       # ... existing migrations ...
       "ALTER TABLE posts ADD COLUMN my_new_column TEXT",
   ]
   ```

3. Update any affected queries in `db.py` or services.
4. Update `docs/DATABASE_SCHEMA.md`.

## Development Workflow

1. Create a feature branch from `main`:
   - `feature/add-glassdoor-source`
   - `fix/email-send-timeout`
2. Make your changes.
3. Test manually. There is no automated test suite yet. Verify:
   - The backend starts without errors.
   - Your feature works in the UI (if applicable).
   - Existing functionality is not broken.
4. Commit with a descriptive message.
5. Push and create a pull request.

## PR Guidelines

- Keep PRs focused: one feature or one fix per PR.
- Include before/after screenshots for UI changes.
- Document any new environment variables needed.
- Update relevant docs in `docs/` if behavior changes.
- Never commit `config/.env`, anything in `data/`, or files containing personal data.
- Describe what changed and how to test it in the PR body.

## Reporting Issues

- **Bug reports:** Include steps to reproduce, expected behavior, and actual behavior. If a scraper broke, note which source and any error messages from the log.
- **Feature requests:** Describe the use case, not just the desired solution.
- **Security issues:** Do not open a public issue. See [Security](SECURITY.md) for private disclosure instructions.

## See Also

- [Setup Guide](SETUP_GUIDE.md)
- [Architecture](ARCHITECTURE.md)
- [API Reference](API_REFERENCE.md)
- [Database Schema](DATABASE_SCHEMA.md)
- [Security](SECURITY.md)
