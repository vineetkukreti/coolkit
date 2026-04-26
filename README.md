# CareerKit

Full-stack job hunting automation -- scrapes 140+ sources, LLM-powered extraction, smart scoring, auto-apply, and cold email outreach with a React dashboard.

## What Is CareerKit?

- **Multi-source scraping** across 141 job boards, ATS platforms, and LinkedIn -- four engine types (API, HTML, Browser, LinkedIn) cover everything from RemoteOK to Greenhouse to regional boards in India, Japan, Europe, UAE, Singapore, and the US.
- **LLM extraction chain** (Ollama local -> Gemini API -> regex fallback) turns unstructured post text into structured job records: role, company, location, experience, domain relevance.
- **Auto-apply** handles LinkedIn Easy Apply end-to-end -- LLM-driven form filling, resume variant selection, daily quotas, and full application history.
- **Cold email outreach** with AI-personalized emails, IMAP reply detection, follow-up automation, A/B testing, and send-time optimization.
- **React dashboard** for pipeline tracking, analytics, skills intelligence, and AI tools (JD evaluation, company deep-dive, CV tailoring, interview prep).
- Works fully offline with Ollama for LLM tasks. Gemini API is an optional fallback. Designed for a solo job seeker but extensible.

## Features

| Category | What It Does |
|----------|-------------|
| **Job Discovery** | 141 sources across 4 engine types: API (RemoteOK, Himalayas, HN, Remotive, USAJobs), HTML (110+ boards via BeautifulSoup), Browser (Wellfound, YC, Indeed, Naukri via Playwright), LinkedIn (search, feed, hashtags, career links) |
| **AI Extraction** | Three-tier LLM chain: Ollama (local, free) -> Gemini API (fallback) -> Regex (last resort). Extracts role, company, location, experience from raw post text |
| **Smart Scoring** | 6-dimension fitness scoring: role match, skill overlap, experience fit, domain relevance, location, seniority. Configurable weights in profile |
| **Auto-Apply** | LinkedIn Easy Apply automation with Playwright. LLM fills form fields, selects resume variants per job, enforces daily quotas, logs every application |
| **Email Outreach** | AI-generated personalized cold emails via Gmail SMTP. IMAP reply detection, automated follow-ups, bulk send, A/B testing, send-time analytics |
| **Pipeline Tracking** | Kanban board with stage management (Applied -> Interview -> Offer). Notes, lead detail views, sync from scraper results |
| **Skills Intelligence** | Market demand analysis from scraped jobs, resume gap detection, skill trend tracking, industry news aggregation |
| **AI Tools** | JD evaluation against your profile, company deep-dive research, CV tailoring suggestions, interview prep generation, outreach message drafting |
| **Quality Dashboard** | Smart filter stats, address quality reports, email delivery analytics, conversion funnels, pattern analysis |

## Quick Start

```bash
git clone https://github.com/vineetkukreti/coolkit.git
cd coolkit
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
playwright install chromium
ollama pull qwen2.5:7b          # local LLM (4.7GB, optional but recommended)
cp config/.env.example config/.env   # add your GEMINI_API_KEY, SMTP creds
./run.sh                        # starts backend :8000 + frontend :5173
```

Other launch modes:

```bash
./run.sh --prod    # backend only, serves built frontend
./run.sh --back    # backend only
./run.sh --front   # frontend dev server only
```

See the full [Setup Guide](docs/SETUP_GUIDE.md) for detailed configuration.

## Architecture

```
React SPA (:5173) --> /api proxy --> FastAPI (:8000) --> Playwright (browser automation)
                                         |-----------> Ollama / Gemini (LLM extraction)
                                         |-----------> SQLite (data/linkedin_jobs.db)
                                         |-----------> Gmail SMTP/IMAP (email outreach)
```

- **Threading**: Dedicated browser thread (Playwright), daemon threads for scraping/email/auto-apply, thread-local SQLite connections.
- **LLM chain**: Ollama (local, free, offline) -> Gemini API (cloud fallback) -> Regex (last resort).
- **Frontend polling**: 2-5s intervals for real-time status updates. No WebSocket.

See the full [Architecture](docs/ARCHITECTURE.md) documentation.

## Project Structure

```
coolkit/
  backend/
    server.py                 # FastAPI entry point, route registration
    config.py                 # User profile, search keywords, scoring config
    config_sources.py         # 141 source definitions (API, HTML, browser, custom)
    db.py                     # SQLite schema, queries, thread-local connections
    routes/                   # Thin route handlers (jobs, scraper, browser, posts,
                              #   email, pipeline, leads, settings, tools, auto_apply,
                              #   skills_intel)
    services/                 # Business logic (scraper_service, email_service,
                              #   auto_apply, smart_filter, resume_selector,
                              #   quality_dashboard, referral_detector, skills_intel)
    scrapers/                 # Scraping engines (linkedin_jobs, linkedin_posts,
                              #   api_scrapers, web_scrapers, generic_scrapers)
    extractors/               # LLM extraction pipeline (text, fitness, pipeline)
    llm/                      # LLM client abstraction (Ollama + Gemini)
    email_finder/             # Email discovery (enrichment, strategies, cron)
  frontend-src/
    src/
      pages/                  # Dashboard, FindJobs, ApplyPage, OutreachPage,
                              #   InsightsPage, Pipeline, AITools, SkillsIntelligence,
                              #   Settings, LeadDetail, QualityDashboard
      components/             # Sidebar, BrowserBar, ConnectGate, FilterBar, PageTabs
      lib/api.js              # All API endpoint definitions
  frontend/                   # Built static assets (served in production)
  config/                     # .env file (secrets, API keys)
  scripts/                    # Utility scripts (test sources, scraping tools)
  data/                       # SQLite database, logs, scrape results
  docs/                       # Full documentation
  run.sh                      # Launch script (dev, prod, backend-only, frontend-only)
```

## Documentation

| Document | Description |
|----------|-------------|
| [Architecture](docs/ARCHITECTURE.md) | System design, component interactions, threading model |
| [API Reference](docs/API_REFERENCE.md) | All REST endpoints with request/response formats |
| [Database Schema](docs/DATABASE_SCHEMA.md) | All tables, relationships, key queries |
| [Services Reference](docs/SERVICES_REFERENCE.md) | Every service, function, and constant |
| [Setup Guide](docs/SETUP_GUIDE.md) | Installation, configuration, first run |
| [System Diagrams](docs/SYSTEM_DIAGRAMS.md) | Mermaid diagrams for all data flows |
| [AI Context](docs/AI_CONTEXT.md) | Comprehensive context for AI assistants |

## Tech Stack

| Layer | Technologies |
|-------|-------------|
| **Backend** | Python 3.11+, FastAPI, Uvicorn, Playwright, SQLite, Ollama, Google Gemini API, BeautifulSoup4, Pandas, Crawl4AI |
| **Frontend** | React 19, Vite 8, TailwindCSS 4, React Router 7, Lucide React |
| **Infrastructure** | Gmail SMTP/IMAP, DuckDuckGo Search, python-dotenv, Rich (CLI output) |

## Contributing

Contributions are welcome. Routes are thin wrappers -- business logic goes in `backend/services/`. Frontend uses React hooks and Context (Toast only), no Redux. Dark theme with purple accent (`#A855F7`).

## License

This project is licensed under [LICENSE] -- see the LICENSE file for details.
