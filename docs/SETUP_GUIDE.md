# CareerKit Setup Guide

## Prerequisites

- Python 3.11+
- Node.js 18+ (for frontend dev)
- Ollama (optional, for local LLM)
- Gmail account with app password (for email outreach)
- Gemini API key (free tier works)

## Quick Start

### 1. Clone and setup

```bash
git clone https://github.com/vineetkukreti/careerkit.git
cd careerkit
```

### 2. Configure secrets

Create `config/.env`:
```env
GEMINI_API_KEY=your_gemini_api_key
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your_email@gmail.com
SMTP_PASSWORD=your_app_password
FROM_EMAIL=your_email@gmail.com
FROM_NAME=Your Name
```

**Getting a Gmail App Password:**
1. Go to https://myaccount.google.com/security
2. Enable 2-Step Verification
3. Go to App passwords → Generate one for "Mail"
4. Use the 16-char password as `SMTP_PASSWORD`

**Getting a Gemini API Key:**
1. Go to https://aistudio.google.com/apikey
2. Create a new API key
3. Free tier: 15 RPM, sufficient for this tool

### 3. Update your profile

Edit `backend/config.py`:
```python
PROFILE = {
    "name": "Your Name",
    "experience_years": 2,
    "current_title": "Your Title",
    "email": "your_email@gmail.com",
    "location": "Your Location",
    ...
}

RESUME_SKILLS = {
    "python": 3,
    "your_skill": 4,
    ...
}

TARGET_ROLES = ["Your Target Role 1", "Target Role 2"]
```

### 4. Launch

```bash
./run.sh           # Backend (8000) + Frontend (5173)
./run.sh --prod    # Backend only, serves built frontend
./run.sh --back    # Backend only
./run.sh --front   # Frontend dev only
```

Open http://localhost:5173 (dev) or http://localhost:8000 (prod)

### 5. First-time setup

The app shows an onboarding wizard on first visit:
1. **Welcome** — Accept disclaimer, review features
2. **Profile** — Enter your details (saved to backend)
3. **LinkedIn** — Launch browser → Log in to LinkedIn → Verify
4. **Done** — Ready to use

### 6. (Optional) Local LLM with Ollama

```bash
# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Pull the model
ollama pull qwen2.5:7b

# Ollama runs on http://localhost:11434 automatically
# CareerKit detects it and uses it as primary LLM
```

If Ollama is not running, CareerKit falls back to Gemini API automatically.

---

## Daily Automation (Optional)

### Cron setup for daily job applications

```bash
# Edit crontab
crontab -e

# Add these lines:

# Daily job cycle at 8 AM on weekdays
0 8 * * 1-5 cd /path/to/careerkit && ./venv/bin/python scripts/daily_run.py >> data/logs/daily.log 2>&1

# Email enrichment every 2 hours
0 */2 * * * cd /path/to/careerkit && ./venv/bin/bash scripts/run_email_finder.sh >> data/logs/email_finder.log 2>&1
```

### Manual daily run

```bash
python scripts/daily_run.py --max 500          # Full cycle: scrape + apply
python scripts/daily_run.py --max 100 --no-scrape  # Apply to existing jobs only
```

---

## Usage Guide

### Scraping Jobs

1. Go to **Scraper** page
2. Ensure browser is connected (green status bar)
3. Select sources (LinkedIn, RemoteOK, Greenhouse, etc.)
4. Set max posts (default: 1000)
5. Click **Start** — watch per-source progress in real-time

**Source types:**
- **LinkedIn** — Requires browser login. Scrapes posts and jobs.
- **API sources** — No browser needed. RemoteOK, Greenhouse, Lever, Ashby, etc.
- **Browser sources** — Need browser. Indeed, Wellfound, Naukri, YC.
- **HTML sources** — No browser. 60+ static job boards.

### Reviewing Posts

Go to **Posts** page to see all scraped content:
- Filter by domain relevance (High/Medium/Low)
- Filter by hiring status (Yes/Maybe/No)
- Toggle "Has Email" to see outreach-ready posts
- Click "Find Email" to enrich posts without emails
- Use bulk email finder for batch enrichment

### Email Outreach

1. Go to **Email Outreach** page
2. See stats: Ready / Not Generated / Drafts / Sent
3. Click **Generate All** — Gemini creates personalized emails
4. Review and edit drafts in the queue
5. Click **Send All Drafts** or send individually
6. Toggle "Attach Resume" before sending

### Auto-Apply

1. Go to **Auto-Apply** page
2. Set target number of applications
3. Click **Start** — engine applies to top-scoring jobs
4. Watch progress: Applied / Failed / Skipped
5. Daily quota prevents over-application

### Pipeline (CRM)

- **Kanban view** — Drag leads through stages
- **List view** — Sortable table of all leads
- Stages: Applied → Replied → Interviewing → Offer / Rejected
- Click a lead for full timeline, notes, and email history
- Use **Sync** to auto-create leads from sent emails

### AI Tools

5 tools powered by Gemini:
- **Evaluate** — Paste a JD, get 7-part analysis with score
- **Outreach** — Generate personalized cold email
- **Deep Dive** — Research a company before applying
- **Tailor CV** — ATS-optimized resume for specific JD
- **Interview Prep** — Question banks and preparation guide

### Analytics

- **Follow-ups** — Which emails need follow-up (overdue/urgent/waiting)
- **Patterns** — Response rates, best send times
- **Conversion** — Rates by role, domain, company
- **App History** — Full application log with CSV export

---

## CLI Commands (Legacy)

These still work for power users:

```bash
# Scrape posts
python backend/post_parser.py                    # Target 1000 posts
python backend/post_parser.py --jobs             # LinkedIn job listings
python backend/post_parser.py --both             # Posts + jobs

# Query database
python backend/db.py --stats                     # Database statistics
python backend/db.py --role "AI Engineer"        # Filter by role
python backend/db.py --domain High --has-email   # Healthcare with emails
python backend/db.py --outreach                  # Ready for outreach

# Export/Import
python backend/db.py --export jobs.xlsx          # Export to Excel
python backend/db.py --import-excel file.xlsx    # Import legacy data
```

---

## Troubleshooting

### Browser won't connect
- CareerKit uses headed (visible) Playwright — a display is required
- On Linux servers, use Xvfb: `xvfb-run ./run.sh`
- Check port 8000 is free: `lsof -i :8000`

### LinkedIn blocks scraping
- Don't exceed 25 Easy Apply/day (safe zone: < 15)
- Browser profile persists login — don't clear `data/browser_profiles/`
- If blocked, wait 24 hours, then re-login via `scripts/login.py`

### Emails not sending
- Verify SMTP config: Settings page → Test Email
- Gmail requires app password (not regular password)
- Check `data/logs/` for error details

### Ollama not detected
- Ensure Ollama is running: `curl http://localhost:11434/api/tags`
- Pull the model: `ollama pull qwen2.5:7b`
- CareerKit auto-falls back to Gemini if Ollama is unavailable

### Port conflicts
- `run.sh` auto-kills processes on ports 8000/5173
- Or manually: `kill $(lsof -t -i:8000)`
