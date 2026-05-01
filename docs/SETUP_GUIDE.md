# CareerKit -- Setup Guide

> Step-by-step installation, configuration, and first run.

## Prerequisites

- **Python 3.11+** -- `python3 --version`
- **Node.js 18+** and npm -- `node --version`
- **Ollama** (optional) -- local LLM for job extraction and scoring
- **Gmail account** with App Password -- required for email outreach features
- **Google AI Studio account** -- for Gemini API (free tier sufficient)

## Quick Start (5 minutes)

```bash
# 1. Clone
git clone https://github.com/vineetkukreti/careerkit.git
cd careerkit

# 2. Python environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
playwright install chromium

# 3. Environment file
mkdir -p config
cp config/env.example config/.env   # then edit with your keys

# 4. Frontend
cd frontend-src && npm install && cd ..

# 5. Launch
./run.sh
```

Open http://localhost:5173 -- the onboarding wizard walks you through the rest.

## Full Installation

### 1. Clone and Python Setup

```bash
git clone https://github.com/vineetkukreti/careerkit.git
cd careerkit

python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Python dependencies installed by `requirements.txt`:

| Package | Purpose |
|---------|---------|
| fastapi, uvicorn | Backend API server |
| playwright | Browser automation (LinkedIn, Indeed, etc.) |
| beautifulsoup4, lxml | HTML parsing for job boards |
| requests | HTTP client for API-based scrapers |
| google-genai | Gemini API client |
| crawl4ai | Web crawling framework |
| python-dotenv | Environment variable loading |
| pandas, openpyxl | Data export (Excel/CSV) |
| rich | CLI formatting |
| python-multipart | File upload support |
| dnspython | Email domain verification |
| duckduckgo-search | DuckDuckGo search scraper |
| googlesearch-python | Google search scraper |

After pip install, set up the browser:

```bash
playwright install chromium
```

This downloads a Chromium binary that Playwright uses for browser-based scraping and LinkedIn automation.

### 2. Environment Configuration

Create `config/.env` with your secrets:

```env
# --- LLM ---
GEMINI_API_KEY=your_gemini_api_key_here

# --- Email (Gmail SMTP) ---
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=you@gmail.com
SMTP_PASSWORD=your_16_char_app_password
FROM_EMAIL=you@gmail.com
FROM_NAME=Your Name

# --- Email Enrichment (optional) ---
HUNTER_API_KEY=your_hunter_api_key
```

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `GEMINI_API_KEY` | Yes | -- | Google AI Studio API key for LLM features |
| `SMTP_HOST` | No | `smtp.gmail.com` | SMTP server hostname |
| `SMTP_PORT` | No | `587` | SMTP server port (TLS) |
| `SMTP_USER` | Yes* | -- | Gmail address for sending emails |
| `SMTP_PASSWORD` | Yes* | -- | Gmail App Password (not regular password) |
| `FROM_EMAIL` | No | Same as SMTP_USER | Sender address shown in emails |
| `FROM_NAME` | No | -- | Sender display name |
| `HUNTER_API_KEY` | No | -- | Hunter.io API key for email finding |

*Required only if you want email outreach features. The server starts without them but prints a warning.

### Profile Configuration

Your profile is stored in `config/profile.json`. It gets created automatically when you complete the onboarding wizard or save settings in the UI. You can also copy the example:

```bash
cp config/profile.json.example config/profile.json
# Edit with your details
```

Key profile fields used for email personalization:

| Field | Used For | Example |
|-------|----------|---------|
| `name`, `first_name` | Email greetings & sign-off | "Jane Doe", "Jane" |
| `current_title` | Self-introduction in emails | "ML Engineer" |
| `employer` | Current company (also blocked from outreach) | "Acme Corp" |
| `employer_domain` | Blocked from receiving outreach emails | "acme.com" |
| `experience_years` | Email context | 3 |
| `skills_summary` | Core tech stack for email personalization | "Python, PyTorch, React, AWS" |
| `projects` | Matched to job posts in cold emails | List of `{name, description}` |
| `achievements` | Included in email prompts | List of strings |
| `education` | Background context | "M.S. Computer Science, MIT" |
| `linkedin`, `github` | Included in email signatures | URLs |

All these fields can be edited in **Settings > Profile** in the UI.

**Resume Setup**: Upload your resume in Settings > Profile. For role-specific variants, use Settings > Resume Variants. Resumes are stored in `assets/resumes/{variant}/resume.pdf`.

### 3. Frontend Setup

```bash
cd frontend-src
npm install
cd ..
```

Key frontend dependencies: React 19, Vite 8, Tailwind CSS 4, React Router 7, Lucide icons.

**Development mode** -- Vite dev server on port 5173, proxies `/api` requests to backend on port 8000.

**Production build** -- generates static files into `frontend/` directory, served directly by FastAPI:

```bash
cd frontend-src
npm run build
cd ..
./run.sh --prod
```

### 4. Ollama Setup (Optional)

Ollama provides a local LLM that CareerKit uses as its primary extraction engine. If unavailable, it falls back to the Gemini API automatically.

```bash
# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Pull the recommended model
ollama pull qwen2.5:7b

# Verify it is running
curl http://localhost:11434/api/tags
```

Ollama runs as a background service on port 11434. CareerKit detects it automatically on startup.

### 5. LinkedIn Browser Setup

CareerKit uses a persistent Playwright browser session for LinkedIn. First-time setup:

**Option A: Through the app (recommended)**

1. Start the application with `./run.sh`
2. Open the app -- the onboarding wizard appears on first visit
3. At the LinkedIn step, click "Launch Browser"
4. Log in to LinkedIn in the browser window that opens
5. The session is saved to `data/browser_profiles/`

**Option B: Via script**

```bash
python scripts/login.py
```

This opens a Chromium window to linkedin.com/login. Log in manually. The script waits up to 5 minutes for you to reach the LinkedIn feed, then saves the session and exits.

The browser session persists across restarts. Do not delete `data/browser_profiles/` unless you want to re-authenticate.

### 6. Gmail App Password

Gmail requires an App Password for SMTP access (regular passwords are blocked):

1. Go to https://myaccount.google.com/security
2. Enable **2-Step Verification** if not already on
3. Go to https://myaccount.google.com/apppasswords
4. Select app: "Mail", device: "Other" (enter "CareerKit")
5. Click **Generate**
6. Copy the 16-character password
7. Paste it as `SMTP_PASSWORD` in `config/.env`

### 7. Gemini API Key

1. Go to https://aistudio.google.com/apikey
2. Click **Create API key**
3. Copy the key and set it as `GEMINI_API_KEY` in `config/.env`

Free tier provides 15 requests per minute -- sufficient for normal use. CareerKit uses Gemini for email generation, job evaluation, resume tailoring, and interview prep.

## Running the Application

### Development Mode (default)

```bash
./run.sh
```

Starts backend on port 8000 and Vite dev server on port 5173 in parallel. Frontend hot-reloads on code changes. API calls from the frontend are proxied to the backend.

- Frontend: http://localhost:5173
- API: http://localhost:8000/api/db/stats

### Production Mode

```bash
./run.sh --prod
```

Starts backend only. Serves pre-built frontend from `frontend/` directory. Use this after running `npm run build` in `frontend-src/`.

- App: http://localhost:8000

### Backend Only

```bash
./run.sh --back
```

Backend API server only, no frontend. Useful when developing the frontend separately.

### Frontend Only

```bash
./run.sh --front
```

Vite dev server only. Requires the backend to already be running on port 8000.

### Alternative: scripts/start.sh

```bash
./scripts/start.sh
```

Simpler startup script -- backend only, auto-installs dependencies, opens browser automatically. Suitable for quick production use.

### Logs

All logs write to `data/logs/`:

```bash
tail -f data/logs/backend.log
tail -f data/logs/frontend.log
```

## Daily Automation

### Cron Setup

Use `scripts/daily_run.py` for scheduled job application cycles:

```bash
crontab -e
```

Add:

```cron
# Daily job cycle at 8 AM on weekdays
0 8 * * 1-5 cd /path/to/careerkit && ./venv/bin/python scripts/daily_run.py >> data/logs/daily.log 2>&1
```

### Manual Daily Run

```bash
# Full cycle: scrape all sources + apply to matching jobs
python scripts/daily_run.py --max 500

# Apply to existing jobs only (skip scraping)
python scripts/daily_run.py --max 100 --no-scrape
```

| Flag | Default | Description |
|------|---------|-------------|
| `--max N` | 500 | Maximum number of applications per run |
| `--no-scrape` | false | Skip the scraping phase, apply to already-collected jobs |

## Verifying Everything Works

After installation, check each component:

- [ ] **Backend**: `curl http://localhost:8000/api/db/stats` -- should return JSON with database statistics
- [ ] **Frontend**: open http://localhost:5173 -- should show the dashboard or onboarding wizard
- [ ] **Browser**: go to Settings page, click "Launch Browser" -- Chromium window should appear
- [ ] **Scraper**: run a small test scrape from the Scraper page (select 2-3 API sources, set max to 10)
- [ ] **Email**: go to Settings page, send a test email to yourself
- [ ] **Ollama**: `curl http://localhost:11434/api/tags` -- should list the qwen2.5:7b model
- [ ] **Gemini**: use any AI Tool (Evaluate, Outreach, etc.) from the AI Tools page

## Production Deployment

### Running Behind nginx

```nginx
server {
    listen 80;
    server_name careerkit.example.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_read_timeout 300s;
    }
}
```

Build the frontend first, then run in production mode:

```bash
cd frontend-src && npm run build && cd ..
./run.sh --prod
```

### systemd Service

Create `/etc/systemd/system/careerkit.service`:

```ini
[Unit]
Description=CareerKit Job Automation
After=network.target

[Service]
Type=simple
User=your_user
WorkingDirectory=/path/to/careerkit
ExecStart=/path/to/careerkit/venv/bin/uvicorn backend.server:app --host 0.0.0.0 --port 8000
Environment=PYTHONPATH=/path/to/careerkit/backend
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable careerkit
sudo systemctl start careerkit
```

### Log Rotation

Add to `/etc/logrotate.d/careerkit`:

```
/path/to/careerkit/data/logs/*.log {
    daily
    rotate 14
    compress
    missingok
    notifempty
    copytruncate
}
```

## Troubleshooting

### Browser will not connect
- Playwright runs in headed (visible) mode -- a display is required
- On headless Linux servers, use Xvfb: `xvfb-run ./run.sh`
- Check that port 8000 is free: `lsof -i :8000`

### LinkedIn blocks scraping
- Stay under 25 Easy Apply per day (safe zone: under 15)
- The browser profile persists login -- do not delete `data/browser_profiles/`
- If blocked, wait 24 hours, then re-login via Settings or `python scripts/login.py`

### Emails not sending
- Verify SMTP config on the Settings page with the Test Email button
- Gmail requires an App Password, not your regular account password
- Check `data/logs/backend.log` for SMTP error details

### Ollama not detected
- Confirm Ollama is running: `curl http://localhost:11434/api/tags`
- Pull the model if missing: `ollama pull qwen2.5:7b`
- CareerKit automatically falls back to Gemini if Ollama is unreachable

### Port conflicts
- `run.sh` auto-kills any process on ports 8000 and 5173 before starting
- Manual kill: `kill $(lsof -t -i:8000)`

## See Also

- [Configuration Reference](CONFIGURATION.md) -- all config options in detail
- [Architecture](ARCHITECTURE.md) -- system design and component interactions
- [API Reference](API_REFERENCE.md) -- all REST endpoints
- [Database Schema](DATABASE_SCHEMA.md) -- tables and relationships
