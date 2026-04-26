# CareerKit -- Security

> Credential management, sensitive data handling, and security considerations for contributors and users.

## Reporting Security Issues

**Do not open a public issue for security vulnerabilities.** Instead, contact the maintainer directly via email. Include:

- A description of the vulnerability.
- Steps to reproduce the issue.
- The potential impact (what data could be exposed, what actions an attacker could take).
- Any suggested fix, if you have one.

The maintainer will acknowledge receipt within 48 hours and provide a timeline for a fix.

## Credential Storage

All secrets are stored in `config/.env`, which is gitignored. No credentials are hardcoded in source files. The following secrets are used:

| Variable | Purpose |
|----------|---------|
| `SMTP_USER` | Gmail address for sending outreach emails |
| `SMTP_PASSWORD` | Gmail App Password (not the main account password) |
| `GEMINI_API_KEY` | Google Gemini API key for LLM extraction and email generation |
| `HUNTER_API_KEY` | Hunter.io API key for email discovery (optional) |

The server validates these at startup and logs warnings if any are missing (see `backend/server.py`). Features that depend on missing credentials are disabled gracefully rather than crashing.

**Best practices for credential management:**

- Use a Gmail App Password, never your main Gmail password. Generate one at https://myaccount.google.com/apppasswords.
- Use the Gemini free tier for development. The free tier has generous limits for personal use.
- Rotate credentials periodically. If you suspect a leak, regenerate the affected key immediately.
- Never store credentials in shell history. Use `config/.env` exclusively.

## Sensitive Data Inventory

| Data | Location | Risk | Mitigation |
|------|----------|------|------------|
| Gmail SMTP password | `config/.env` | Email account access | Gitignored; uses App Password, not main password |
| Gemini API key | `config/.env` | API billing | Gitignored; free tier has usage limits |
| Hunter.io API key | `config/.env` | API billing | Gitignored; optional, free tier available |
| LinkedIn session cookies | `data/browser_profiles/` | LinkedIn account access | Gitignored; local filesystem only |
| Personal profile data | `backend/config.py` PROFILE dict | Identity exposure | Contributors must replace with placeholders in commits |
| Job application database | `data/linkedin_jobs.db` | Privacy (job history, emails, contacts) | Gitignored; never committed |
| Email outreach history | `data/linkedin_jobs.db` | Privacy (recipient emails, sent content) | Gitignored; never committed |
| Resume files | `assets/resumes/` | Personal information | PDF/TEX/BAK files are gitignored |

## Browser Profile Security

CareerKit uses a persistent Playwright browser profile stored in `data/browser_profiles/`. This directory contains LinkedIn session cookies. If this directory is leaked or shared:

- An attacker gains full access to the associated LinkedIn account.
- They can read messages, connections, and profile data.

Mitigations:

- The `data/` directory is gitignored in its entirety.
- To invalidate a leaked session, delete `data/browser_profiles/` and log in again through the Settings page.
- The browser runs in headed (visible) mode, not headless, so session activity is always visible on screen.
- Do not copy `data/browser_profiles/` to other machines. Each machine should maintain its own session.

## Database Security

The SQLite database at `data/linkedin_jobs.db` contains:

- Job posting content and URLs.
- Contact emails extracted from posts.
- Full email outreach history (subjects, bodies, recipient addresses).
- Application tracking data (which jobs you applied to, when, status).
- Pipeline lead information (names, emails, companies, stages).

This data is privacy-sensitive. The database file is gitignored and should never be shared, committed, or backed up to cloud storage without encryption. If you need to share a database for debugging, export only the relevant rows with personal data redacted.

## Anti-Detection and Ethics

CareerKit is designed for personal use by a single job seeker, not for mass scraping or spamming. The following measures enforce responsible usage:

- **Headed browser**: All Playwright automation runs in a visible browser window. No headless mode.
- **Human-like delays**: Random delays between actions (typically 2-5 seconds, configurable per platform in `services/auto_apply.py`).
- **Viewport randomization**: Browser window dimensions vary slightly between sessions.
- **Daily application caps**: The `daily_quotas` table in the database enforces a configurable daily limit (default 500 total applications).
- **Platform-specific budgets**: `PLATFORM_BUDGETS` in `services/auto_apply.py` limits applications per source per day:
  - LinkedIn Easy Apply: 120/day
  - Email applications: 180/day
  - Indeed, Naukri, Wellfound: 30/day each
  - Other platforms: 110/day combined
- **Rate limiting per platform**: `RATE_LIMITS` in `services/auto_apply.py` enforces minimum delays between applications (e.g., 45-120 seconds between LinkedIn Easy Apply submissions).
- **Email sending delays**: Configurable pauses between outreach emails to avoid triggering spam filters.
- **Deduplication**: The `DedupCache` in `db.py` prevents applying to or emailing the same target twice, using URL matching, content hashing, and normalized prefix comparison.
- **Scraper respects site structure**: Generic scrapers use `requests` with standard User-Agent headers. Browser scrapers navigate pages as a normal user would.

These limits are configurable but should not be removed or set to zero. Aggressive automation can result in account bans and harms the platforms that job seekers depend on.

## Rate Limiting Details

| Mechanism | Location | Default |
|-----------|----------|---------|
| Daily application quota | `db.py` `daily_quotas` table | 500/day |
| LinkedIn Easy Apply rate | `services/auto_apply.py` RATE_LIMITS | 45-120s between apps |
| Email apply rate | `services/auto_apply.py` RATE_LIMITS | 10-30s between apps |
| General platform rate | `services/auto_apply.py` RATE_LIMITS | 15-45s between apps |
| Platform daily budgets | `services/auto_apply.py` PLATFORM_BUDGETS | See table above |
| Scraper log retention | `services/scraper_service.py` | Last 300 events per source |
| Auto-apply log retention | `services/auto_apply.py` | Last 500 events |

## For Contributors

Follow these rules to prevent accidental exposure of sensitive data:

- **Never log credentials or API keys.** If you need to log authentication state, log only whether a credential is present (truthy), not its value.
- **Never commit `config/.env` or anything in `data/`.** The `.gitignore` already excludes these, but verify before committing.
- **Sanitize personal data in screenshots and PR descriptions.** Blur or redact names, emails, and company details.
- **Use placeholder values in code examples.** Do not paste real credentials, even in comments.
- **The `PROFILE` dict in `backend/config.py` contains real personal data** (name, email, phone, LinkedIn URL). When modifying this file, replace all personal values with generic placeholders before committing.
- **Review `.gitignore` before committing** to ensure no sensitive files are staged.
- **SQL injection**: Always use parameterized queries (`?` placeholders). Never use f-strings or string concatenation to build SQL. The existing codebase follows this pattern consistently.
- **Error messages**: Do not expose stack traces or internal paths in API responses. Catch exceptions and return sanitized error messages.

## Network Exposure

By default, the backend binds to `0.0.0.0:8000`, making it accessible to other devices on the local network. This is intentional for development (e.g., testing from a phone) but means:

- Anyone on your network can access the API and trigger scraping, emailing, or application actions.
- There is no authentication on API endpoints.

For production or shared-network environments, bind to `127.0.0.1` only or add authentication middleware. This is a known limitation for a personal-use tool.

## .gitignore Coverage

The following categories are excluded from version control:

| Pattern | Reason |
|---------|--------|
| `config/.env` | API keys, SMTP credentials |
| `data/` | Database, browser profiles, logs, scrape results -- all runtime/sensitive |
| `venv/`, `node_modules/` | Dependency directories |
| `*.pdf`, `*.tex`, `*.bak` | Resume files containing personal information |
| `*.csv`, `*.xlsx` | Exported data files |
| `*.db` | SQLite database files |
| `*.log`, `logs/` | Application logs (may contain PII) |
| `browser_session/`, `.browser_profile/` | Legacy browser session directories |
| `debug_*.html`, `debug_*.png` | Debug artifacts from scraping |
| `__pycache__/`, `*.pyc` | Python bytecode |
| `.claude/`, `.vscode/`, `.idea/` | IDE and tool configuration |
| `memory/` | Personal notes |

## See Also

- [Contributing](CONTRIBUTING.md)
- [Setup Guide](SETUP_GUIDE.md)
- [Architecture](ARCHITECTURE.md)
