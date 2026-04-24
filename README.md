# LinkedIn Job Parser

Automated LinkedIn scraper that finds AI/ML hiring posts, extracts structured job info using a local LLM, and stores everything in a SQLite database. Built for targeting **healthcare/medical/clinical AI** roles.

## Screenshots

### Scraper Running
![Scraper Running](screenshots/01_scraper_running.svg)

### Results Table
![Results Table](screenshots/02_results_table.svg)

### Session Summary
![Session Summary](screenshots/03_session_summary.svg)

### Database Stats (`python db.py --stats`)
![DB Stats](screenshots/04_db_stats.svg)

### Outreach Query (`python db.py --outreach`)
![Outreach](screenshots/05_outreach_query.svg)

### LLM Extraction (Local Ollama)
![LLM Extraction](screenshots/06_llm_extraction.svg)

## How It Works

```
LinkedIn (Playwright) --> Scroll & Extract Posts --> Local LLM (Ollama) --> SQLite DB
        |                        |                        |                    |
   73 search queries      JS DOM extraction       qwen2.5:7b extracts    Deduped,
   sorted by date         author, content,        role, company,         filtered,
   healthcare-first       emails, URLs            location, experience   scored
```

**Step by step:**

1. Opens LinkedIn in Chromium using a persistent logged-in session
2. Searches 73 keyword queries (healthcare AI first, then broader AI/ML)
3. Scrolls through results, expands truncated posts, extracts data via JavaScript
4. Sends each post to **Ollama (qwen2.5:7b)** running locally on GPU to extract:
   - Role (mapped to: AI Engineer, ML Engineer, GenAI Engineer, Data Engineer, Data Scientist, Analyst)
   - Company, Location, Experience (clean format: "2 years", "3-5 years")
5. Scores **healthcare/medical/clinical domain relevance** (High / Medium / Low)
6. Filters out irrelevant roles (Java, DevOps, QA, etc.) and bad experience fits (fresher-only, 6yr+ senior)
7. Saves to SQLite with dedup -- re-runs only add new posts

## Project Structure

```
linkedin-job-parser/
  post_parser.py      # Main scraper -- searches LinkedIn, extracts, saves to DB
  db.py               # SQLite layer -- insert, query, export, CLI tool
  config.py           # User profile (name, email, resume skills)
  login.py            # Manual LinkedIn login helper
  extract_posts.js    # JavaScript injected into LinkedIn pages to grab post data
  .env                # API keys (GEMINI_API_KEY for LLM fallback)
  linkedin_jobs.db    # SQLite database (auto-created)
  browser_session/    # Persistent Chromium profile (stays logged in)
  venv/               # Python virtual environment
```

## Setup

### Prerequisites

- Python 3.11+
- [Ollama](https://ollama.com/) installed and running
- A LinkedIn account

### Installation

```bash
# Clone and enter project
cd linkedin-job-parser

# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install playwright rich openpyxl python-dotenv google-genai
playwright install chromium

# Pull the local LLM model (4.7GB, runs on GPU)
ollama pull qwen2.5:7b
```

### First-time LinkedIn Login

```bash
python login.py
```

This opens a browser window. Log in to LinkedIn manually. The session is saved in `browser_session/` and reused for all future runs.

### Configure (optional)

Create `.env` for Gemini API fallback (only used if Ollama is not running):

```
GEMINI_API_KEY=your_key_here
```

Edit `config.py` with your profile details.

## Usage

### Scrape LinkedIn Posts

```bash
# Default: scrape hiring posts (target: 1000, gets ~150-180 per session)
python post_parser.py

# Scrape LinkedIn job listings
python post_parser.py --jobs

# Both posts + jobs
python post_parser.py --both

# Custom target
python post_parser.py --posts --max 500
```

### Query the Database

```bash
# Full statistics
python db.py --stats

# Filter by role
python db.py --role "AI Engineer"

# Healthcare posts with email addresses
python db.py --domain High --has-email

# Only confirmed hiring posts
python db.py --hiring

# Posts ready for email outreach (have email, not yet contacted)
python db.py --outreach

# Export to Excel
python db.py --export jobs.xlsx

# Export filtered subset
python db.py --export healthcare_ai.xlsx --domain High --role "AI Engineer"

# Import from old Excel file
python db.py --import-excel linkedin_posts_20260409.xlsx
```

## Database Schema

Three tables in `linkedin_jobs.db`:

**`posts`** -- Scraped LinkedIn posts (deduped by URL + content hash)
| Column | Description |
|--------|-------------|
| post_url | LinkedIn post URL (unique) |
| content_hash | SHA-256 of first 200 chars (dedup fallback) |
| author_name | Post author |
| content | Full post text |
| email | Extracted email addresses |
| is_hiring | Boolean: hiring signals detected |
| domain_relevance | High / Medium / Low (healthcare keyword score) |

**`jobs`** -- Extracted job details (1:many per post)
| Column | Description |
|--------|-------------|
| role | AI Engineer, ML Engineer, GenAI Engineer, Data Engineer, Data Scientist, Analyst |
| company | Hiring company |
| location | City/country/Remote |
| experience | Clean format: "2 years", "3-5 years", "0 years (Fresher)" |

**`email_outreach`** -- Cold email tracking (for future email sender)
| Column | Description |
|--------|-------------|
| recipient_email | Contact email |
| status | pending / sent / replied / bounced |
| sent_at | Timestamp |

## LLM Extraction

**Primary: Ollama (local, free, offline)**
- Model: `qwen2.5:7b` (4.7GB, runs on GPU)
- Extracts role, company, location, experience from unstructured post text
- ~1-2 seconds per post on RTX 4050

**Fallback: Gemini 2.5 Flash-Lite (API)**
- Only used when Ollama is not running
- Cost: ~$0.01 per 200 posts
- Requires `GEMINI_API_KEY` in `.env`

**Last resort: Regex**
- Keyword matching for roles, location patterns, experience patterns
- No LLM needed, but lower accuracy

## Fitness Filtering

Posts are automatically filtered based on profile fit:

| Filter | Action |
|--------|--------|
| Relevant roles (AI/ML/Data/NLP/GenAI) | Keep |
| Irrelevant roles (Java, DevOps, QA, nurses, etc.) | Skip |
| Fresher-only (0 years) | Skip |
| Too senior (6+ years minimum) | Skip |
| Everything else | Keep |

## Run Daily for Best Results

LinkedIn content search returns ~150-180 unique posts per session. To accumulate more, run daily -- the database dedup ensures re-runs only save new posts:

```bash
# Each run adds only new posts
python post_parser.py
python post_parser.py   # next day -- skips duplicates, saves new ones
```

## Tech Stack

- **Playwright** -- Browser automation (persistent Chromium session)
- **Ollama + qwen2.5:7b** -- Local LLM for structured extraction
- **SQLite** -- Zero-config database storage
- **Rich** -- Terminal UI (tables, colors, progress)
- **openpyxl** -- Excel export
- **python-dotenv** -- Environment variable management
