# CareerKit -- Configuration Reference

> All configuration options, environment variables, and customization points.

## Configuration Locations

| File | Purpose | Committed to Git? |
|------|---------|-------------------|
| `config/.env` | Secrets and API keys | No (gitignored) |
| `backend/config.py` | User profile, search strategy, scoring weights | Yes (contains personal data -- replace with yours) |
| `backend/config_sources.py` | Job source definitions and groups | Yes |
| `frontend-src/vite.config.js` | Frontend build and proxy config | Yes |
| `run.sh` | Startup modes and port config | Yes |

## Environment Variables (config/.env)

Loaded by `python-dotenv` at server startup in `backend/server.py`.

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `GEMINI_API_KEY` | Yes | -- | Google AI Studio API key. Used for email generation, job evaluation, resume tailoring, interview prep. Free tier: 15 RPM. |
| `SMTP_USER` | Yes* | -- | Gmail address for outbound email. Also used for IMAP reply detection. |
| `SMTP_PASSWORD` | Yes* | -- | Gmail App Password (16 characters). Regular passwords will not work. |
| `SMTP_HOST` | No | `smtp.gmail.com` | SMTP server hostname. |
| `SMTP_PORT` | No | `587` | SMTP server port (STARTTLS). |
| `FROM_EMAIL` | No | Same as `SMTP_USER` | Sender address displayed in outgoing emails. |
| `FROM_NAME` | No | -- | Display name shown in the From header. |
| `HUNTER_API_KEY` | No | -- | Hunter.io API key for email enrichment. Optional -- the app has built-in email finding without it. |

*The server starts without SMTP credentials but prints a warning and disables all email features (sending, IMAP polling, enrichment).

If `GEMINI_API_KEY` is missing, the server warns at startup and AI-powered features (email generation, job evaluation, tools) will fail.

## User Profile (backend/config.py)

This file defines your identity, skills, and search strategy. All values are used by the scoring engine, AI prompts, and auto-apply form filling.

### PROFILE dict

Your personal details, used to fill application forms and generate outreach emails.

| Field | Type | Description |
|-------|------|-------------|
| `name` | str | Full name |
| `first_name` | str | First name (for form fields) |
| `last_name` | str | Last name (for form fields) |
| `email` | str | Contact email |
| `phone` | str | Phone number with country code |
| `resume_path` | str | Path to default PDF resume (relative to project root) |
| `location` | str | Current location |
| `experience_years` | int | Total years of experience |
| `current_title` | str | Current job title |
| `linkedin` | str | LinkedIn profile URL |
| `github` | str | GitHub profile URL |
| `website` | str | Personal website URL |
| `notice_period_days` | int | Notice period in days |
| `desired_salary` | int | Target annual salary |
| `current_salary` | int | Current annual salary |
| `require_visa` | str | Visa sponsorship requirement |
| `us_citizenship` | str | US citizenship status |
| `willing_to_relocate` | str | Relocation willingness |
| `previously_worked_here` | str | Default answer for "worked here before" |
| `education_level` | str | Highest education level |
| `certifications` | str | Certifications or "None" |
| `gender` | str | Gender (for EEO forms) |
| `ethnicity` | str | Ethnicity (for EEO forms) |
| `disability_status` | str | Disability status (for EEO forms) |
| `veteran_status` | str | Veteran status (for EEO forms) |

### RESUME_SKILLS dict

Maps skill names to integer weights (1-5). Higher weights increase the fitness score when a job description mentions that skill. The scoring engine sums matched skill weights to rank jobs.

```python
RESUME_SKILLS = {
    "python": 3,
    "neo4j": 4,
    "knowledge graph": 4,
    "healthcare": 4,
    "llm": 4,
    # ... add your skills here
}
```

Weight guidelines: 1 = familiar, 2 = used in projects, 3 = proficient, 4 = core expertise, 5 = domain-defining.

### TARGET_ROLES list

Ordered list of role titles you are targeting. Used by the scoring engine to boost jobs matching these titles. First entry has highest priority.

```python
TARGET_ROLES = [
    "AI Engineer",
    "ML Engineer",
    "GenAI Engineer",
    "LLM Engineer",
    "Agentic AI Engineer",
]
```

### DOMAIN_KEYWORDS list

Keywords that indicate domain relevance. Jobs containing these terms score higher on the domain relevance axis. The default list targets healthcare/medical/biotech.

Contains 28 terms across categories: healthcare terminology (`healthcare`, `medical`, `clinical`), regulatory (`fda`, `hipaa`, `hl7`, `fhir`), specializations (`radiology`, `pathology`, `oncology`, `genomics`), and industry (`pharma`, `biotech`, `life sciences`).

### DEFAULTS dict

| Key | Default | Description |
|-----|---------|-------------|
| `keywords` | (randomized) | Search keywords -- regenerated each run via `random_search_keywords()` |
| `location` | `"India"` | Default search location |
| `max_jobs` | `25` | Max jobs to scrape per source per run |
| `mode` | `"semi"` | `"semi"` = approve each application, `"auto"` = apply to all matches |

### REGIONS dict

Six geographic regions used for multi-region job targeting. Each region defines:

| Region | Locations | Timezone |
|--------|-----------|----------|
| `india` | India, Bangalore, Mumbai, Hyderabad, Delhi, Pune, Chennai, Noida, Gurgaon | Asia/Kolkata |
| `japan` | Japan, Tokyo, Osaka, Kyoto, Yokohama | Asia/Tokyo |
| `europe` | Germany, UK, Netherlands, France, Berlin, London, Amsterdam, Paris, Dublin, Zurich, Stockholm, Barcelona, Munich, Hamburg, Copenhagen | Europe/Berlin |
| `uae` | Dubai, UAE, Abu Dhabi, Middle East, MENA | Asia/Dubai |
| `us` | United States, New York, San Francisco, Austin, Seattle, Boston, Los Angeles, Chicago, Denver, Washington DC, Atlanta, Miami | America/New_York |
| `singapore` | Singapore, Southeast Asia | Asia/Singapore |

Each region also includes `geolocation` (lat/lon) and `locale` fields used by browser-based scrapers.

`ACTIVE_REGIONS` controls which regions are included in query generation. Remove a region from this list to exclude its locations from searches.

### HASHTAG_FEEDS list

LinkedIn hashtags scraped for hiring posts: `hiring`, `wearehiring`, `nowhiring`, `jobopening`, `jobalert`, `AIjobs`, `AIhiring`, `healthcareAI`, `healthtech`, `machinelearning`, `artificialintelligence`, `genai`, `remotejobs`, `techhiring`, `startupjobs`.

### JOB_SEARCH_QUERIES list

23 pre-built LinkedIn job search queries. Domain-specific queries (`"AI Engineer healthcare"`, `"ML Engineer healthcare"`) are listed first, followed by general role queries (`"AI Engineer"`, `"LLM Engineer"`).

`JOB_EXP_LEVELS` is set to `"2%2C3"` (Entry + Associate level). `JOB_TYPE` is `"F"` (Full-time).

### Functions

**`random_search_keywords()`** -- Returns a randomized keyword string combining a role (from 12 role keywords), a domain (60% healthcare tier, 40% general tier), and optionally an experience tag. Called once per run to vary LinkedIn searches.

**`build_smart_queries()`** -- Generates up to `MAX_QUERIES` (150) ranked, deduplicated search queries across four tiers: healthcare-domain, general-domain, action-verb, and location-based. Shuffled each run to avoid pattern detection.

**`get_profile_context()`** -- Returns a formatted text block of your profile for use in AI prompts (email generation, job evaluation, etc.).

## Source Configuration (backend/config_sources.py)

Defines all job sources the scraper can use. Currently contains 100+ sources across three categories.

### Source Types

**CUSTOM_SOURCES** (26 sources) -- Have dedicated scraper functions in `backend/scrapers/`. Includes LinkedIn (6 sources), API scrapers (10 sources: RemoteOK, Himalayas, HN, Remotive, WWR, Working Nomads, Greenhouse, Lever, Ashby, JobSpy), and browser scrapers (10 sources: DuckDuckGo, Wellfound, YC, Indeed, Naukri, Arc.dev, WeWorkRemotely, JapanDev, EU Remote, Bayt, RemoteAI).

**GENERIC_API_SOURCES** (3 sources) -- JSON API endpoints scraped with a generic handler. Configured with URL templates, JSON path to jobs array, and field mappings. Sources: USAJobs, SmartRecruiters, Euraxess.

**GENERIC_HTML_SOURCES** (70+ sources) -- Static HTML pages scraped with requests + BeautifulSoup. Configured with URLs, CSS selectors for card/title/company/location/link, and a base URL for resolving relative links.

### Source Groups (20 categories)

| Group | Label | Source Count (approx.) |
|-------|-------|----------------------|
| `linkedin` | LinkedIn | 6 |
| `api` | API Scrapers (No Browser) | 6 |
| `ats` | Company ATS Boards | 4 |
| `multi` | Multi-Platform | 1 |
| `browser` | Browser Scrapers | 5 |
| `remote` | Remote Job Boards | 15+ |
| `ai_ml` | AI/ML Specific | 10+ |
| `startup` | Startup Focused | 2 |
| `india` | India | 6 |
| `japan` | Japan | 5 |
| `europe` | Europe | 15+ |
| `uae` | UAE / Middle East | 7 |
| `us` | United States | 8 |
| `singapore` | Singapore | 5 |
| `web3` | Web3 / Crypto | 4 |
| `academic` | Academic / Research | 3 |
| `healthcare` | Healthcare | 4 |
| `niche` | Niche / Community | 3 |
| `regional` | Regional and Other | 3 |
| `freelance` | Freelance / Contract | 1 |

### Adding a New HTML Source

1. Open `backend/config_sources.py`
2. Add an entry to `GENERIC_HTML_SOURCES`:

```python
"my_source": {
    "label": "My Job Board",
    "group": "remote",          # Must match a key in SOURCE_GROUPS
    "urls": ["https://example.com/jobs?q=AI+engineer"],
    "selectors": {
        "card": "[class*='job']",          # CSS selector for each job card
        "title": "h2 a",                   # Title element within the card
        "company": "[class*='company']",   # Company name element
        "location": "[class*='location']", # Location element
        "link": "a[href]",                 # Link element (href extracted)
    },
    "base_url": "https://example.com",     # For resolving relative URLs
},
```

3. Restart the backend. The new source appears in the Scraper page under its group.

### Adding a New API Source

Add to `GENERIC_API_SOURCES` with these fields:

| Field | Description |
|-------|-------------|
| `url` | API endpoint URL with `{query}` placeholder |
| `headers` | Optional HTTP headers (auth, user-agent) |
| `jobs_path` | Dot-notation path to the jobs array in JSON response |
| `fields` | Dot-notation mapping: `title`, `company`, `location`, `url`, `date` |
| `search_terms` | List of search queries to send |
| `companies` | (SmartRecruiters-style) List of company slugs with `url_template` |

### Source Configuration Fields

For HTML sources, the `enabled` field can be set to `False` to disable a source without removing it.

## Frontend Configuration

Defined in `frontend-src/vite.config.js`:

| Setting | Value | Description |
|---------|-------|-------------|
| Dev server port | `5173` | Vite development server |
| API proxy | `/api` -> `http://localhost:8000` | All `/api` requests forwarded to backend |
| Build output | `../frontend` | Production build directory (served by FastAPI) |
| `emptyOutDir` | `true` | Clears output directory before each build |
| Plugins | react, tailwindcss | React JSX support + Tailwind CSS 4 |

## Runtime Flags

### run.sh

| Flag | Mode | Description |
|------|------|-------------|
| (none) | Development | Backend + Vite dev server in parallel |
| `--prod` | Production | Backend only, serves built frontend from `frontend/` |
| `--back` | Backend only | API server only, no frontend |
| `--front` | Frontend only | Vite dev server only (backend must be running) |

Ports are hardcoded: backend on 8000, frontend on 5173. The script auto-kills any existing process on these ports before starting.

### scripts/daily_run.py

| Flag | Default | Description |
|------|---------|-------------|
| `--max N` | 500 | Maximum applications to submit |
| `--no-scrape` | false | Skip scraping, apply only to existing jobs in database |

### build_smart_queries() Tuning

| Constant | Default | Description |
|----------|---------|-------------|
| `MAX_QUERIES` | 150 | Cap on total generated search queries per run |

## See Also

- [Setup Guide](SETUP_GUIDE.md) -- installation and first run
- [Services Reference](SERVICES_REFERENCE.md) -- all backend services and functions
- [Architecture](ARCHITECTURE.md) -- system design and data flow
