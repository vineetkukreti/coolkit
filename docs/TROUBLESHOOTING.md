# coolkit -- Troubleshooting

> Common issues, debugging techniques, and recovery procedures.

## Quick Diagnostics

Run these checks to identify which component is failing:

| Component | Check Command | Expected |
|-----------|--------------|----------|
| Backend | `curl http://localhost:8000/api/db/stats` | JSON with post counts |
| Frontend | `curl http://localhost:5173` | HTML page |
| Browser | `curl http://localhost:8000/api/browser/status` | `{"running": true, "logged_in": true}` |
| Database | `ls -la data/linkedin_jobs.db` | File exists, non-zero size |
| Ollama | `curl http://localhost:11434/api/tags` | JSON with model list |
| Logs | `tail -f data/logs/backend.log` | Recent log entries |

---

## Installation Issues

### pip install fails

**Missing system dependencies:** Several packages require C libraries. On Debian/Ubuntu:

```bash
sudo apt install libxml2-dev libxslt-dev python3-dev build-essential
```

The `lxml` and `crawl4ai` packages are the most common offenders.

**Python version mismatch:** coolkit uses `str | None` union syntax which requires Python 3.11+. Check with `python3 --version`.

**Virtual environment not activated:** The `run.sh` script auto-activates `venv/`, but if running manually:

```bash
source venv/bin/activate
pip install -r requirements.txt
```

**google-genai package:** This is the official Google GenAI SDK, not the older `google-generativeai`. If you see import errors for `google.genai`, ensure you have the correct package.

### Playwright install fails

Playwright needs browser binaries downloaded separately:

```bash
playwright install --with-deps chromium
```

On Linux, `--with-deps` installs required system libraries (libgbm, libnss, etc.). If behind a proxy, set `HTTPS_PROXY` first.

### npm install fails

Requires Node.js 18+. Clear and retry: `rm -rf frontend-src/node_modules && cd frontend-src && npm install`.

---

## Startup Issues

### Backend fails to start

**Port 8000 already in use:** `run.sh` auto-kills processes on ports 8000 and 5173. If running manually:

```bash
lsof -ti:8000 | xargs kill -9
```

**Missing .env file:** The backend loads `config/.env` via `python-dotenv`. If the file is missing, email features are disabled and AI generation will fail. The server prints warnings at startup:

```
[WARN] Missing env vars: SMTP_USER, SMTP_PASSWORD -- email features disabled
[WARN] GEMINI_API_KEY not set -- AI email generation will fail
```

These are warnings, not fatal errors. The backend still starts.

**Import errors on startup:** All 11 route modules are imported at server init. A broken import in any route module prevents the entire backend from starting. Check `data/logs/backend.log` for the traceback.

### Backend starts but API returns 500

The `data/` directory must exist and be writable. Run `mkdir -p data`. The database auto-creates on first request.

### Frontend dev server won't start

Run `cd frontend-src && npm install && npx vite --port 5173 --host`. The `run.sh` script does this automatically.

---

## Browser / Playwright Issues

### Browser won't start

**Stale lock files:** If a previous session crashed, Chromium leaves `SingletonLock` files in the profile directory. The browser service cleans these automatically, but if it still fails:

```bash
rm -f data/browser_profiles/main/Singleton*
```

**Another Chromium instance using the profile:** Playwright persistent contexts lock the profile directory. Only one instance can use it at a time. Kill any existing Chromium processes:

```bash
pkill -f chromium
```

**Display server required:** The browser runs in headed mode (not headless) for anti-detection. On a headless server, you need Xvfb or a similar virtual display.

### LinkedIn login expired

Session cookies persist in `data/browser_profiles/main/` but expire every 1-2 weeks. The ConnectGate screen appears automatically. Click "Launch Browser", sign in, then "Verify Connection". Solve any CAPTCHA manually in the Chrome window.

### "Browser not running" errors in scraper

LinkedIn-based scrapers (search, feed, hashtags, enricher, deepfetch) require a running browser. Start it from Settings or via `POST /api/browser/start`. API-based scrapers (RemoteOK, Himalayas, HN, etc.) work independently.

### Browser stuck in "starting" state

The UI shows a timeout retry after 45 seconds. If persistent: kill zombie Chromium processes (`pkill -f chromium`), delete `data/browser_profiles/`, and verify Playwright is installed.

---

## Scraping Issues

### Scraper returns 0 results

**Source is down or changed:** Web scrapers depend on HTML structure. If a source redesigns their site, the scraper will silently return 0 results. Check the per-source status in the scraper UI for error events.

**LinkedIn requires login:** The `linkedin`, `feed`, and `hashtags` sources require an active browser session. Without it, they fail immediately with "Browser not running."

**All results are duplicates:** The DedupCache checks `post_url`, `content_hash`, and a normalized content prefix. If you are re-scraping the same sources, most results will be skipped. This is normal -- the "skipped" count in the event log shows how many duplicates were found.

**Query cap reached:** The smart query builder caps at 150 queries (MAX_QUERIES in config.py) to avoid rate-limiting.

### 403 / 429 errors from scrapers

Rate limiting. LinkedIn is most aggressive -- wait hours before retrying. Web scrapers use headed mode with anti-detection for sites that block headless Chromium (DuckDuckGo, Wellfound, YC). API sources rarely rate-limit.

### Scraper stuck in "running"

The coordinator waits for all source threads via `t.join()`. If a thread hangs, force-stop with `curl -X POST http://localhost:8000/api/scraper/stop` or restart the backend. Scraper state is in-memory only.

---

## LLM Issues

### Ollama not responding

The LLM client checks Ollama once and caches the result. If Ollama was started after the backend, restart the backend to re-detect. Required commands: `ollama serve` then `ollama pull qwen2.5:7b`. The system falls back to Gemini automatically; if both fail, extraction uses regex.

### Gemini API errors

**Missing API key:** Set `GEMINI_API_KEY` in `config/.env`. The server warns at startup if it is missing.

**Rate limit / quota exceeded:** The free tier of Gemini has per-minute and per-day limits. The email worker adds 1-2 second delays between generation calls, and the send worker adds 3-8 second delays. If you hit limits, check the [Google AI Studio dashboard](https://aistudio.google.com/).

**Model not available:** coolkit uses `gemini-2.5-flash-lite` for email generation and extraction. If the model name changes, update it in `backend/llm/client.py` (GEMINI_MODEL) and `backend/services/email_service.py`.

### Extraction returning empty fields

The extraction chain is: Ollama -> Gemini -> Regex. If all three fail for a post, fields like role, company, and location will be empty or "Not specified". This usually means the post content is too short or not in a recognizable job posting format.

---

## Email Issues

### SMTP authentication failure

Gmail requires an App Password (not your regular password). Enable 2FA on your Google account, then generate an App Password at Google Account -> Security -> App Passwords. Set `SMTP_PASSWORD` in `config/.env` to this 16-character password and `SMTP_USER` to your full Gmail address.

### Emails going to spam

The service sends both plain text and HTML. Anti-spam measures include: 3-8 second randomized delays between sends, automatic skipping of generic addresses (info@, careers@, hr@), MX record validation, and a domain blocklist in `email_service.py`.

### IMAP polling not detecting replies

IMAP reply detection polls every 5 minutes (auto-started at boot). Gmail IMAP must be enabled in Gmail Settings -> Forwarding and POP/IMAP. Uses `SMTP_USER`/`SMTP_PASSWORD` by default; override with `IMAP_USER`/`IMAP_PASSWORD`. Check status: `curl http://localhost:8000/api/email/imap-status`. Replies are classified as `interested`, `auto_reply`, `rejection`, or `info`.

### Attachment issues

The resume path comes from `PROFILE["resume_path"]` in `config.py`. The auto-apply system also uses `resume_selector.py` to pick the best resume variant for each job. Verify the file exists:

```bash
ls -la assets/resumes/default/
```

Only PDF format is supported for attachments.

---

## Auto-Apply Issues

### Daily quota reached

The default daily target is 500 applications (set in the `daily_quotas` table). Platform-specific budgets further limit each method:

| Platform | Daily Budget |
|----------|-------------|
| LinkedIn Easy Apply | 120 |
| Email Apply | 180 |
| Indeed | 30 |
| Naukri | 30 |
| Wellfound | 30 |
| Other | 110 |

Quota resets at midnight (based on server clock). Check current quota:

```bash
curl http://localhost:8000/api/auto-apply/quota
```

### Smart score gate

Jobs with a `smart_score` below 3.5 are automatically skipped. The three tiers are:

- **PREMIUM** (score >= 7.0): Full LLM-personalized email, LLM form answers, longer delays.
- **STANDARD** (score >= 5.0): Personalized email, template form answers.
- **BASIC** (score >= 3.5): Template email, template form answers.

If too many jobs are being skipped, check if the smart scoring is calibrated correctly.

### Form fields not filled correctly

Forms are filled using: PROFILE config values -> LLM answers (PREMIUM tier only) -> dropdown/radio keyword matching. If fields are missed, LinkedIn may have changed their form element structure. Check `_get_field_label` in `auto_apply.py`.

### Easy Apply flow changed

LinkedIn updates their UI periodically. Key selectors in `auto_apply.py`: `button[aria-label*="Easy Apply"]`, `button[aria-label*="Submit application"]`, `button[aria-label*="Next"]`. If these stop matching, applies fail with "No Easy Apply button found".

---

## Database Issues

### SQLite "database is locked"

WAL mode allows concurrent reads but only one writer. Causes: multiple backend processes, zombie processes holding the file. Fix: `fuser data/linkedin_jobs.db` to find holders, then `rm data/linkedin_jobs.db-wal data/linkedin_jobs.db-shm` if needed (data is preserved in the main .db file).

### Data not showing in UI

1. Check the API directly: `curl http://localhost:8000/api/db/stats`
2. If the database is empty, run a scraper first.
3. The frontend polls every 2-5 seconds. Hard refresh with Ctrl+Shift+R.
4. Check the browser console (F12) for failed API calls.

### WAL file growing large

During heavy scraping or bulk email operations, the WAL file can grow to hundreds of MB. This is normal. To reclaim space:

```bash
sqlite3 data/linkedin_jobs.db "PRAGMA wal_checkpoint(TRUNCATE)"
```

### Migration errors

The `run_migrations()` function in `db.py` runs `ALTER TABLE` statements wrapped in try/except. If a column already exists, the error is silently ignored. This is by design -- migrations are idempotent.

---

## Frontend Issues

### Blank page / white screen

Check browser console (F12) for errors. Verify the frontend is running (`curl http://localhost:5173`). In production mode, check `frontend/index.html` exists.

### API proxy not working

Vite proxies `/api` to `http://localhost:8000` (see `vite.config.js`). Verify the backend is running. In production mode (`--prod`), there is no proxy -- the backend serves the frontend directly.

### ConnectGate loop

Click "Verify Connection" after logging in. Verification navigates to `linkedin.com/feed/` and checks the URL. If LinkedIn redirects to a security challenge or terms page, verification will fail -- resolve the LinkedIn prompt first.

---

## Reset Procedures

### Reset browser profile

```bash
rm -rf data/browser_profiles/
```

Restart the backend and log in again. Session cookies will be lost.

### Reset database

```bash
rm data/linkedin_jobs.db data/linkedin_jobs.db-shm data/linkedin_jobs.db-wal
```

The backend recreates the database with the full schema on next startup.

### Reset scraper state

Scraper state is in-memory. Either:

```bash
curl -X POST http://localhost:8000/api/scraper/stop
```

Or restart the backend.

### Full reset

```bash
rm -rf data/ venv/ frontend-src/node_modules/ frontend/
```

Then follow the [Setup Guide](SETUP_GUIDE.md) from scratch.

---

## Log Locations

| Log | Location |
|-----|----------|
| Backend stdout | `data/logs/backend.log` (when using `run.sh`) |
| Frontend stdout | `data/logs/frontend.log` (when using `run.sh`) |
| Scraper events | In-memory, accessible via `GET /api/scraper/status` |
| Email worker | In-memory state + `worker_runs` table in database |
| IMAP polling | `imap_worker_state` via `GET /api/email/imap-status` |
| Application history | `applications` table in database |
| Auto-apply events | In-memory, accessible via `GET /api/auto-apply/status` |

---

## Getting Help

Open an issue on GitHub with:

- What you were doing.
- What you expected to happen.
- What actually happened.
- Backend logs (sanitize personal data and API keys).
- Browser console errors (if frontend issue).
- Output of the Quick Diagnostics commands above.

## See Also

- [Setup Guide](SETUP_GUIDE.md)
- [Configuration](CONFIGURATION.md)
- [Architecture](ARCHITECTURE.md)
- [API Reference](API_REFERENCE.md)
