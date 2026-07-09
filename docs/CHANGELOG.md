# coolkit -- Changelog

> All notable changes to this project will be documented in this file.
> Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [Unreleased]

### Added
- (Template for upcoming changes)

### Changed
- (Template)

### Fixed
- (Template)

---

## [1.0.0] - 2026-04-26

### Added
- Full-stack React + FastAPI web application replacing CLI workflow
- Dashboard with real-time stats, outreach analytics, and pipeline overview
- Multi-source job scraping across 100+ sources in 20 categories
  - LinkedIn: search, posts, feed, hashtags, deep extraction, profile enrichment
  - API sources: RemoteOK, Himalayas, Hacker News, Remotive, WWR, WorkingNomads
  - ATS boards: Greenhouse, Lever, Ashby
  - Web scrapers: Google, Indeed, Naukri, Wellfound, YC, ArcDev, JapanDev, Bayt, WeWorkRemotely, EU Remote Jobs, RemoteAI
  - Generic HTML/API scraper engine for 65+ additional job boards
  - Multi-region targeting: India, Japan, Europe, UAE, US, Singapore
  - Career link follower for extracting emails from external job pages
- LLM-powered extraction chain (Ollama -> Gemini -> regex fallback) for role, company, location, experience, salary, and tech stack
- Smart fitness scoring with six dimensions: role fit, skill match, domain relevance, experience alignment, posting quality, and location compatibility
- LinkedIn Easy Apply automation with multi-step form filling, LLM-powered custom question answers, and human-like warm-up behavior
- Score-gated apply tiers (Premium, Standard, Basic) to invest more effort in better-matching jobs
- AI-personalized cold email outreach via Gemini 2.5 Flash Lite with A/B variant testing
- IMAP-based reply detection with classification (interested, auto-reply, rejection, info)
- Automated follow-up scheduling with cadence analysis
- Email validation (format + MX record check) and domain blocklist
- Bounce detection via mailer-daemon message scanning
- Application pipeline with Kanban board and stage tracking (applied, replied, interviewing, offered, rejected)
- Skills Intelligence: market demand analysis from job descriptions, resume gap detection, trending tools tracking
- AI Tools: JD evaluation, company deep-dive, CV tailoring, interview preparation
- Startup leads management with email enrichment (Hunter API, web scraping, DuckDuckGo search)
- Email A/B testing framework and quality dashboard
- Multi-resume variant support with smart selection based on job archetype
- Referral detector for warm outreach when connections exist at target companies
- Settings UI for profile, SMTP credentials, Gemini API key, and browser management
- Daily automation via cron script (scripts/daily_run.py)
- Comprehensive documentation (12 docs covering architecture, API, database schema, setup, services, security, and troubleshooting)

### Technical
- FastAPI backend with 11 route modules and 60+ endpoints
- SQLite database with WAL mode, 16 tables, and idempotent migrations
- Thread-safe architecture: dedicated browser thread with command queue, scraper coordinator with parallel source threads, daemon threads for email/IMAP/auto-apply workers
- In-memory dedup cache (DedupCache) using URL, content hash, and normalized prefix matching for O(1) duplicate detection during scrapes
- Anti-detection measures: persistent browser profile, randomized viewport/delays, navigator property spoofing, headed mode for bot-blocked sites
- React 19 frontend with 19 pages and 7 reusable components
- TailwindCSS dark theme with purple accent (#A855F7)
- Vite dev server with API proxy to backend
- Centralized API client (frontend-src/src/lib/api.js) with 75+ functions
- Smart query builder generating up to 150 ranked, deduplicated search queries per run

---

## Template for Future Releases

```
## [X.Y.Z] - YYYY-MM-DD

### Added
- New features

### Changed
- Changes in existing functionality

### Deprecated
- Soon-to-be removed features

### Removed
- Removed features

### Fixed
- Bug fixes

### Security
- Vulnerability fixes
```
