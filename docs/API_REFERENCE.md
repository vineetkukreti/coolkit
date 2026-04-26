# CareerKit -- API Reference

> Complete REST API documentation for all endpoints.

## Overview

- Base URL: `http://localhost:8000`
- Content-Type: `application/json` (unless noted otherwise)
- No authentication required (local-only deployment)
- All endpoints return JSON
- Frontend proxy: Vite dev server at `:5173` proxies `/api` to `:8000`

## Error Response Format

Standard error shape returned by FastAPI:

```json
{
  "detail": "Description of what went wrong"
}
```

HTTP status codes used: 200, 400, 404, 422, 500.

Validation errors (422) include field-level detail:

```json
{
  "detail": [
    {
      "loc": ["body", "field_name"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

---

## Browser Control

Prefix: `/api/browser`

Manages the Playwright browser instance used by LinkedIn scraping and auto-apply.

### POST `/api/browser/start`

Launch browser and navigate to LinkedIn login page.

**Request body:** None

**Example:**

```bash
curl -X POST http://localhost:8000/api/browser/start
```

**Success response:**

```json
{
  "status": "ready",
  "message": "Browser launched with LinkedIn login page."
}
```

**Error cases:**
- Already running: `{"status": "already_running"}`
- Launch failure: 500 with error detail

**Notes:** Browser runs on a dedicated thread. All browser commands are dispatched via a command queue.

---

### POST `/api/browser/login`

Navigate to LinkedIn login page in the running browser.

**Request body:** None

```bash
curl -X POST http://localhost:8000/api/browser/login
```

**Success response:**

```json
{
  "status": "ok",
  "message": "LinkedIn login page opened."
}
```

**Error cases:**
- Browser not running: 400 `"Browser not running. Start it first."`

---

### POST `/api/browser/check-login`

Check if the user is logged into LinkedIn.

**Request body:** None

```bash
curl -X POST http://localhost:8000/api/browser/check-login
```

**Success response:**

```json
{
  "logged_in": true
}
```

**Notes:** Returns `{"logged_in": false}` if browser is not running (no error thrown).

---

### POST `/api/browser/stop`

Close the browser and clean up state.

**Request body:** None

```bash
curl -X POST http://localhost:8000/api/browser/stop
```

**Success response:**

```json
{
  "status": "stopped"
}
```

**Notes:** Falls back to force-clean if graceful shutdown fails. Always returns 200.

---

### GET `/api/browser/status`

Get current browser state.

```bash
curl http://localhost:8000/api/browser/status
```

**Success response:**

```json
{
  "status": "ready",
  "running": true,
  "logged_in": true
}
```

**Browser states:** `stopped` -> `starting` -> `ready` -> `connected` (logged in to LinkedIn)

---

## Scraper

Prefix: `/api/scraper`

Multi-source job scraper supporting 100+ sources (LinkedIn, API boards, HTML scrapers).

### POST `/api/scraper/start`

Start scraping from selected sources in parallel background threads.

**Request body:**

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `max_posts` | int | 200 | Maximum posts to scrape per source |
| `sources` | string[] | `["linkedin"]` | Source keys to scrape |

```bash
curl -X POST http://localhost:8000/api/scraper/start \
  -H 'Content-Type: application/json' \
  -d '{"max_posts": 100, "sources": ["linkedin", "remoteok", "greenhouse"]}'
```

**Success response:**

```json
{
  "status": "started",
  "message": "Scraping Linkedin, Remoteok, Greenhouse in parallel for up to 100 posts..."
}
```

**Error cases:**
- Already running: 400 `"Scraper already running"`
- Browser needed but not running: 400 `"Browser not running. Start it from Settings first..."`

**Notes:** API-only sources (remoteok, himalayas, hn, remotive, greenhouse, lever, ashby, etc.) do not require the browser. LinkedIn and browser-based sources do.

---

### POST `/api/scraper/stop`

Stop all running scraper threads.

```bash
curl -X POST http://localhost:8000/api/scraper/stop
```

**Success response:**

```json
{
  "status": "stopped"
}
```

---

### GET `/api/scraper/status`

Get real-time scraper progress with per-source breakdown.

```bash
curl http://localhost:8000/api/scraper/status
```

**Success response:**

```json
{
  "running": true,
  "status": "running",
  "started_at": "2026-04-26T10:30:00",
  "sources": {
    "linkedin": {
      "status": "running",
      "log": ["Scraping page 1...", "Found 25 posts"],
      "log_count": 2,
      "progress": 25
    },
    "remoteok": {
      "status": "done",
      "log": ["Fetched 40 jobs"],
      "log_count": 1,
      "progress": 40
    }
  }
}
```

**Source statuses:** `waiting`, `running`, `done`, `error`, `stopped`

---

### GET `/api/scraper/sources`

Get all available scraper sources grouped by category.

```bash
curl http://localhost:8000/api/scraper/sources
```

**Success response:**

```json
{
  "total": 105,
  "groups": [
    {
      "key": "job_boards",
      "label": "Job Boards",
      "icon": "briefcase",
      "order": 1,
      "sources": [
        {"key": "linkedin", "label": "LinkedIn", "type": "custom"},
        {"key": "remoteok", "label": "RemoteOK", "type": "api"}
      ]
    }
  ]
}
```

---

## Posts & Database

Prefix: `/api/db`

Query scraped posts stored in SQLite, retrieve stats, and find emails for post authors.

### GET `/api/db/posts`

Query posts with filters and pagination.

**Query parameters:**

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `role` | string | null | Filter by job role |
| `domain` | string | null | Filter by domain |
| `has_email` | bool | null | Only posts with/without email |
| `is_hiring` | bool | null | Only hiring posts |
| `company` | string | null | Filter by company name |
| `location` | string | null | Filter by location |
| `source` | string | null | Filter by scrape source |
| `limit` | int | 200 | Results per page |
| `offset` | int | 0 | Pagination offset |

```bash
curl "http://localhost:8000/api/db/posts?is_hiring=true&has_email=true&limit=50"
```

**Success response:**

```json
{
  "posts": [
    {
      "id": 1,
      "author_name": "Jane Doe",
      "author_headline": "CTO at HealthTech Inc",
      "content": "We're hiring ML engineers...",
      "email": "jane@healthtech.com",
      "is_hiring": 1,
      "domain_relevance": "High",
      "post_url": "https://linkedin.com/feed/update/...",
      "links": "https://healthtech.com/careers"
    }
  ],
  "total": 42
}
```

---

### GET `/api/db/stats`

Aggregated database statistics.

```bash
curl http://localhost:8000/api/db/stats
```

**Success response:**

```json
{
  "total_posts": 1250,
  "hiring_posts": 480,
  "with_email": 210,
  "domains": {"High": 120, "Medium": 200, "Low": 160},
  "roles": {"ML Engineer": 85, "Data Scientist": 62}
}
```

---

### GET `/api/db/outreach-ready`

Get posts and startup leads that have emails and are ready for outreach. Includes draft status if an email has already been generated.

```bash
curl http://localhost:8000/api/db/outreach-ready
```

**Success response:**

```json
{
  "posts": [
    {
      "id": 15,
      "author_name": "John Smith",
      "email": "john@example.com",
      "is_hiring": 1,
      "domain_relevance": "High",
      "source_type": "post",
      "draft_id": 42,
      "draft_subject": "Healthcare AI Engineer...",
      "draft_body": "Hi John...",
      "email_status": "draft",
      "sent_at": null
    },
    {
      "id": 200,
      "author_name": "MedTech Corp",
      "email": "careers@medtech.com",
      "source_type": "startup_lead",
      "content": "AI-powered diagnostics startup"
    }
  ],
  "total": 85
}
```

**Notes:** Returns both posts (source_type: `"post"`) and startup leads (source_type: `"startup_lead"`) formatted uniformly. Excludes emails already sent.

---

### POST `/api/db/posts/{post_id}/find-email`

Find email addresses for a post's company using multiple strategies (web scraping, pattern guessing, Hunter API).

**Path parameters:**

| Param | Type | Description |
|-------|------|-------------|
| `post_id` | int | Post ID |

```bash
curl -X POST http://localhost:8000/api/db/posts/15/find-email
```

**Success response:**

```json
{
  "status": "ok",
  "post_id": 15,
  "company": "HealthTech Inc",
  "emails_found": 2,
  "emails": [
    {"email": "careers@healthtech.com", "source": "website_scrape", "score": 0.9},
    {"email": "hr@healthtech.com", "source": "pattern_guess", "score": 0.6}
  ],
  "saved": "careers@healthtech.com, hr@healthtech.com"
}
```

**Error cases:**
- Post not found: 404 `"Post not found"`
- Cannot determine company: `{"status": "error", "message": "Could not determine company name from post"}`

**Notes:** Also updates other posts from the same company that lack emails.

---

## Job Search

Prefix: `/api`

Direct job searching across LinkedIn, Naukri, and Wellfound.

### POST `/api/search`

Search for jobs across multiple platforms.

**Request body:**

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `keywords` | string | `"healthcare AI engineer"` | Search keywords |
| `location` | string | `"India"` | Location filter |
| `platforms` | string[] | `["linkedin", "naukri", "wellfound"]` | Platforms to search |
| `max_jobs` | int | 10 | Max results per platform |

```bash
curl -X POST http://localhost:8000/api/search \
  -H 'Content-Type: application/json' \
  -d '{"keywords": "ML engineer", "location": "Remote", "platforms": ["linkedin"], "max_jobs": 20}'
```

**Success response:**

```json
{
  "jobs": [
    {
      "title": "ML Engineer - Healthcare",
      "company": "MedAI Corp",
      "location": "Remote",
      "url": "https://www.linkedin.com/jobs/view/123456",
      "platform": "LinkedIn",
      "match_score": 8,
      "matched_skills": ["machine learning", "healthcare"],
      "posted": "2026-04-20"
    }
  ],
  "total": 15
}
```

**Notes:** Results are deduplicated and sorted by match_score descending. Naukri and Wellfound return search links rather than individual job cards.

---

### POST `/api/apply`

Log a job as manually applied.

**Request body:**

| Field | Type | Description |
|-------|------|-------------|
| `url` | string | Job posting URL |
| `title` | string | Job title |
| `company` | string | Company name |
| `location` | string | Job location |
| `platform` | string | Platform name |

```bash
curl -X POST http://localhost:8000/api/apply \
  -H 'Content-Type: application/json' \
  -d '{"url": "https://example.com/job/123", "title": "ML Engineer", "company": "Acme", "location": "Remote", "platform": "LinkedIn"}'
```

**Success response:**

```json
{
  "status": "ok",
  "message": "Logged application to Acme"
}
```

---

### POST `/api/skip`

Log a job as skipped.

**Request body:** Same as `/api/apply`.

```bash
curl -X POST http://localhost:8000/api/skip \
  -H 'Content-Type: application/json' \
  -d '{"url": "https://example.com/job/456", "title": "Data Analyst", "company": "Corp", "location": "NYC", "platform": "LinkedIn"}'
```

**Success response:**

```json
{
  "status": "ok"
}
```

---

### GET `/api/applications`

List application history.

**Query parameters:**

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `status` | string | null | Filter by status (`applied`, `skipped`) |

```bash
curl "http://localhost:8000/api/applications?status=applied"
```

**Success response:**

```json
{
  "applications": [
    {
      "url": "https://example.com/job/123",
      "title": "ML Engineer",
      "company": "Acme",
      "location": "Remote",
      "platform": "LinkedIn",
      "status": "applied",
      "apply_method": "manual",
      "applied_at": "2026-04-26 10:00:00"
    }
  ],
  "total": 45
}
```

---

### GET `/api/stats`

Get application statistics.

```bash
curl http://localhost:8000/api/stats
```

**Success response:**

```json
{
  "applied": 120,
  "skipped": 30,
  "failed": 5,
  "total": 155
}
```

---

### GET `/api/applications/quota`

Get today's application quota and progress.

```bash
curl http://localhost:8000/api/applications/quota
```

**Success response:**

```json
{
  "date": "2026-04-26",
  "target": 500,
  "applied": 42,
  "remaining": 458
}
```

---

## Email Outreach

Prefix: `/api/email`

Generate, send, and track cold outreach emails. Supports single and bulk operations.

### POST `/api/email/generate`

Generate a personalized cold email using Gemini AI.

**Request body:**

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `post_id` | int | 0 | Post ID to fetch data from DB |
| `author_name` | string | `""` | Recipient name |
| `author_headline` | string | `""` | Recipient headline/title |
| `role` | string | `""` | Job role |
| `company` | string | `""` | Company name |
| `location` | string | `""` | Location |
| `domain_relevance` | string | `""` | Domain relevance (High/Medium/Low) |
| `is_hiring` | bool | true | Whether the post is a hiring post |
| `content` | string | `""` | Post content for context |
| `to_email` | string | `""` | Recipient email |

```bash
curl -X POST http://localhost:8000/api/email/generate \
  -H 'Content-Type: application/json' \
  -d '{"post_id": 15}'
```

**Success response:**

```json
{
  "status": "ok",
  "post_id": 15,
  "subject": "Healthcare AI Engineer -- FHIR + ML Pipeline Experience",
  "body": "Hi John,\n\nI noticed your post about..."
}
```

**Error cases:**
- Gemini failure: 500 `"Email generation failed: ..."`

**Notes:** If `post_id` is provided, data is fetched from the database. Explicitly provided fields override DB values.

---

### POST `/api/email/send`

Send a single email via SMTP.

**Request body:**

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `post_id` | int | 0 | Associated post ID (optional) |
| `to_email` | string | required | Recipient email address |
| `subject` | string | required | Email subject |
| `body` | string | required | Email body text |
| `attach_resume` | bool | true | Attach resume PDF |

```bash
curl -X POST http://localhost:8000/api/email/send \
  -H 'Content-Type: application/json' \
  -d '{"to_email": "recruiter@example.com", "subject": "ML Engineer Application", "body": "Hi...", "attach_resume": true}'
```

**Success response:**

```json
{
  "status": "sent",
  "message": "Email sent to recruiter@example.com"
}
```

**Error cases:**
- Blocked email (employer domain): 400 `"Blocked: this email belongs to your current employer..."`
- Invalid email format: 400 with validation reason
- SMTP failure: 500 with error detail

**Notes:** Validates email format before sending. Blocked emails (current employer) are rejected. Failed sends are logged to the database with error type.

---

### POST `/api/email/save-draft`

Save or update a draft email for a post.

**Request body:**

| Field | Type | Description |
|-------|------|-------------|
| `post_id` | int | Associated post ID |
| `to_email` | string | Recipient email |
| `subject` | string | Email subject |
| `body` | string | Email body |

```bash
curl -X POST http://localhost:8000/api/email/save-draft \
  -H 'Content-Type: application/json' \
  -d '{"post_id": 15, "to_email": "hr@example.com", "subject": "Application", "body": "Hi..."}'
```

**Success response:**

```json
{
  "status": "ok",
  "message": "Draft saved"
}
```

**Notes:** Updates existing draft for the same post_id if one exists.

---

### POST `/api/email/bulk-generate`

Start bulk email generation in a background thread.

**Request body:**

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `post_ids` | int[] | `[]` | Post IDs to generate for. Empty = auto-select all outreach-ready posts without drafts. |

```bash
curl -X POST http://localhost:8000/api/email/bulk-generate \
  -H 'Content-Type: application/json' \
  -d '{"post_ids": [15, 22, 33]}'
```

**Success response:**

```json
{
  "status": "started",
  "message": "Generating emails for 3 posts in background...",
  "total": 3
}
```

**Error cases:**
- Worker already running: 400 `"Email worker already running (generate). Wait or stop it first."`
- No posts to process: `{"status": "ok", "message": "No posts to generate emails for."}`

---

### POST `/api/email/bulk-send`

Start bulk email sending in a background thread. Sends all pending drafts.

**Request body:**

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `attach_resume` | bool | true | Attach resume to all emails |

```bash
curl -X POST http://localhost:8000/api/email/bulk-send \
  -H 'Content-Type: application/json' \
  -d '{"attach_resume": true}'
```

**Success response:**

```json
{
  "status": "started",
  "message": "Sending 12 emails in background...",
  "total": 12
}
```

**Error cases:**
- Worker already running: 400
- No drafts to send: `{"status": "ok", "message": "No draft emails to send."}`

---

### GET `/api/email/worker-status`

Poll progress of bulk generate or bulk send operations.

```bash
curl http://localhost:8000/api/email/worker-status
```

**Success response:**

```json
{
  "running": true,
  "task": "generate",
  "current": 5,
  "total": 12,
  "current_label": "Generating email for HealthTech Inc...",
  "succeeded": 4,
  "failed": 1,
  "results": [
    {"post_id": 15, "status": "ok", "company": "HealthTech Inc"},
    {"post_id": 22, "status": "error", "error": "Rate limited"}
  ]
}
```

---

### POST `/api/email/worker-stop`

Stop the running bulk generate or send operation.

```bash
curl -X POST http://localhost:8000/api/email/worker-stop
```

**Success response:**

```json
{
  "status": "stopped"
}
```

---

### GET `/api/email/history`

Get the 200 most recent email outreach records with post context.

```bash
curl http://localhost:8000/api/email/history
```

**Success response:**

```json
{
  "history": [
    {
      "id": 1,
      "post_id": 15,
      "to_email": "hr@example.com",
      "subject": "Healthcare AI Engineer",
      "body": "Hi John...",
      "status": "sent",
      "sent_at": "2026-04-26 10:00:00",
      "created_at": "2026-04-26 09:55:00",
      "variant": "A",
      "variant_strategy": "direct",
      "outreach_type": "cold",
      "followup_count": 0,
      "to_name": "John Smith",
      "author_headline": "CTO at HealthTech",
      "role": "ML Engineer",
      "company": "HealthTech Inc",
      "location": "Remote"
    }
  ],
  "total": 150
}
```

---

### GET `/api/email/connections/{post_id}`

Find existing connections at the company associated with a post (referral detection).

**Path parameters:**

| Param | Type | Description |
|-------|------|-------------|
| `post_id` | int | Post ID |

```bash
curl http://localhost:8000/api/email/connections/15
```

**Success response:**

```json
{
  "has_connections": true,
  "company": "HealthTech Inc",
  "contacts": [
    {"name": "Jane Doe", "role": "Engineer", "email": "jane@healthtech.com"}
  ],
  "recommendation": "warm_referral"
}
```

---

### POST `/api/email/check-replies`

Run a single IMAP check for replies to sent emails.

```bash
curl -X POST http://localhost:8000/api/email/check-replies
```

**Success response:**

```json
{
  "checked": 50,
  "new_replies": 2,
  "bounces_detected": 1
}
```

---

### POST `/api/email/check-bounces`

Scan inbox for bounce notifications and mark affected emails. Uses the same IMAP check as reply detection.

```bash
curl -X POST http://localhost:8000/api/email/check-bounces
```

**Success response:** Same format as `/api/email/check-replies`.

---

### POST `/api/email/imap-start`

Start continuous IMAP polling for reply detection.

```bash
curl -X POST http://localhost:8000/api/email/imap-start
```

**Success response:**

```json
{
  "status": "started",
  "message": "IMAP polling started"
}
```

---

### POST `/api/email/imap-stop`

Stop IMAP polling.

```bash
curl -X POST http://localhost:8000/api/email/imap-stop
```

**Success response:**

```json
{
  "status": "stopped"
}
```

---

### GET `/api/email/imap-status`

Get IMAP worker status.

```bash
curl http://localhost:8000/api/email/imap-status
```

**Success response:**

```json
{
  "running": true,
  "last_check": "2026-04-26 10:30:00",
  "interval_minutes": 5
}
```

---

### GET `/api/email/stats`

Comprehensive email delivery statistics.

```bash
curl http://localhost:8000/api/email/stats
```

**Success response:**

```json
{
  "total": 200,
  "delivered": 180,
  "sent": 175,
  "failed": 15,
  "replied": 5,
  "draft": 5,
  "bounced": 3,
  "delivery_rate": "92.3%",
  "reply_rate": "2.8%",
  "errors": {
    "bounced": 3,
    "invalid_address": 8,
    "smtp_timeout": 4
  },
  "recent_failures": [
    {"email": "bad@example.com", "error_type": "bounced", "error_message": "Mailbox not found", "date": "2026-04-25"}
  ],
  "worker_history": [
    {"type": "bulk_send", "started_at": "2026-04-25 14:00", "finished_at": "2026-04-25 14:10", "status": "done", "total": 20, "succeeded": 18, "failed": 2}
  ]
}
```

---

### POST `/api/email/classify-failures`

One-time utility: classify existing failed emails that have no error_type by checking address format.

```bash
curl -X POST http://localhost:8000/api/email/classify-failures
```

**Success response:**

```json
{
  "classified": 12
}
```

---

### GET `/api/email/address-quality`

Report on email address quality issues (multi-address fields, generic addresses, bounced).

```bash
curl http://localhost:8000/api/email/address-quality
```

**Success response:**

```json
{
  "multi_address": [
    {"id": 5, "email": "hr@co.com, careers@co.com", "subject": "ML Engineer", "status": "sent"}
  ],
  "multi_count": 3,
  "generic": [
    {"id": 10, "email": "info@startup.com", "status": "draft"}
  ],
  "generic_count": 15,
  "bounced": [
    {"id": 20, "email": "old@defunct.com", "error": "Mailbox not found"}
  ],
  "bounced_count": 2
}
```

---

### GET `/api/email/send-time-stats`

Analyze reply rates by hour of day and day of week.

```bash
curl http://localhost:8000/api/email/send-time-stats
```

**Success response:**

```json
{
  "hourly": [
    {"hour": 9, "sent": 20, "replied": 3, "rate": 15.0},
    {"hour": 14, "sent": 15, "replied": 1, "rate": 6.7}
  ],
  "daily": [
    {"day": "Mon", "sent": 30, "replied": 4, "rate": 13.3},
    {"day": "Tue", "sent": 25, "replied": 2, "rate": 8.0}
  ],
  "recommendation": {
    "best_hour": 9,
    "best_day": "Mon",
    "best_hour_rate": 15.0,
    "best_day_rate": 13.3
  }
}
```

---

### POST `/api/email/update-status`

Manually update an email's status.

**Request body:**

| Field | Type | Description |
|-------|------|-------------|
| `outreach_id` | int | Email outreach record ID |
| `status` | string | New status: `sent`, `replied`, `failed`, `draft`, `bounced` |

```bash
curl -X POST http://localhost:8000/api/email/update-status \
  -H 'Content-Type: application/json' \
  -d '{"outreach_id": 42, "status": "replied"}'
```

**Success response:**

```json
{
  "status": "updated",
  "outreach_id": 42,
  "new_status": "replied"
}
```

---

### GET `/api/email/config-status`

Check whether SMTP is configured.

```bash
curl http://localhost:8000/api/email/config-status
```

**Success response:**

```json
{
  "configured": true,
  "smtp_host": "smtp.gmail.com",
  "from_email": "your_email@example.com",
  "from_name": "Your Name"
}
```

---

## Pipeline

Prefix: `/api/pipeline`

CRM-style pipeline to track leads through application stages.

### GET `/api/pipeline`

Get all pipeline leads with post context.

```bash
curl http://localhost:8000/api/pipeline
```

**Success response:**

```json
{
  "leads": [
    {
      "id": 1,
      "post_id": 15,
      "outreach_id": 42,
      "recipient_name": "John Smith",
      "recipient_email": "john@example.com",
      "role": "ML Engineer",
      "company": "HealthTech Inc",
      "location": "Remote",
      "stage": "applied",
      "source": "email",
      "created_at": "2026-04-20",
      "updated_at": "2026-04-25",
      "post_content": "We're hiring...",
      "author_headline": "CTO",
      "domain_relevance": "High"
    }
  ],
  "total": 30
}
```

---

### GET `/api/pipeline/stats`

Stage counts for the pipeline.

```bash
curl http://localhost:8000/api/pipeline/stats
```

**Success response:**

```json
{
  "applied": 25,
  "replied": 5,
  "interviewing": 3,
  "offer": 1,
  "rejected": 8,
  "total": 42
}
```

---

### GET `/api/pipeline/lead/{lead_id}`

Get full lead detail including timeline events, notes, and email history.

**Path parameters:**

| Param | Type | Description |
|-------|------|-------------|
| `lead_id` | int | Pipeline lead ID |

```bash
curl http://localhost:8000/api/pipeline/lead/1
```

**Success response:**

```json
{
  "id": 1,
  "post_id": 15,
  "recipient_name": "John Smith",
  "recipient_email": "john@example.com",
  "role": "ML Engineer",
  "company": "HealthTech Inc",
  "stage": "replied",
  "events": [
    {"id": 1, "event_type": "email_sent", "title": "Email Sent", "content": "Subject: ML Engineer...", "created_at": "2026-04-20"},
    {"id": 2, "event_type": "stage_change", "title": "Status -> Replied", "content": "Moved from applied to replied", "created_at": "2026-04-22"}
  ],
  "notes": [
    {"id": 1, "content": "Very responsive, follow up next week", "created_at": "2026-04-23"}
  ],
  "emails": [
    {"id": 42, "subject": "ML Engineer Application", "status": "sent", "sent_at": "2026-04-20"}
  ]
}
```

**Error cases:**
- Lead not found: 404

---

### POST `/api/pipeline/update-stage`

Move a lead to a different pipeline stage.

**Request body:**

| Field | Type | Description |
|-------|------|-------------|
| `lead_id` | int | Pipeline lead ID |
| `stage` | string | Target stage |

Valid stages: `applied`, `replied`, `interviewing`, `offer`, `rejected`

```bash
curl -X POST http://localhost:8000/api/pipeline/update-stage \
  -H 'Content-Type: application/json' \
  -d '{"lead_id": 1, "stage": "interviewing"}'
```

**Success response:**

```json
{
  "status": "ok",
  "message": "Lead moved to interviewing"
}
```

**Error cases:**
- Invalid stage: 400 `"Invalid stage. Must be one of: [...]"`
- Lead not found: 404

---

### POST `/api/pipeline/add-note`

Add a note to a pipeline lead.

**Request body:**

| Field | Type | Description |
|-------|------|-------------|
| `lead_id` | int | Pipeline lead ID |
| `content` | string | Note text |

```bash
curl -X POST http://localhost:8000/api/pipeline/add-note \
  -H 'Content-Type: application/json' \
  -d '{"lead_id": 1, "content": "Had a great first call. Technical round next week."}'
```

**Success response:**

```json
{
  "status": "ok"
}
```

---

### POST `/api/pipeline/sync`

Sync sent emails into pipeline_leads. Auto-creates leads for sent emails not yet tracked.

```bash
curl -X POST http://localhost:8000/api/pipeline/sync
```

**Success response:**

```json
{
  "status": "ok",
  "synced": 5,
  "message": "Synced 5 new leads into pipeline"
}
```

---

## Leads

Prefix: `/api/leads`

CRUD and enrichment for startup leads (imported from CSV/JSON data files).

### GET `/api/leads`

List startup leads with filters, search, sorting, and pagination.

**Query parameters:**

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `search` | string | `""` | Search company, description, email, tags |
| `industry` | string | `""` | Filter by industry |
| `country` | string | `""` | Filter by country (exact match) |
| `email_status` | string | `""` | Filter by email status |
| `has_email` | bool | null | Only leads with emails |
| `source` | string | `""` | Filter by source file |
| `sort_by` | string | `"company_name"` | Sort column |
| `sort_dir` | string | `"asc"` | Sort direction (`asc`/`desc`) |
| `limit` | int | 500 | Results per page |
| `offset` | int | 0 | Pagination offset |

Valid sort columns: `company_name`, `industry`, `location`, `country`, `email_status`, `created_at`, `funding_status`

```bash
curl "http://localhost:8000/api/leads?search=health&industry=Healthcare&has_email=true&limit=50"
```

**Success response:**

```json
{
  "leads": [
    {
      "id": 1,
      "company_name": "MedAI Corp",
      "email": "careers@medai.com",
      "description": "AI diagnostics platform",
      "industry": "Healthcare",
      "location": "Bangalore",
      "country": "India",
      "website": "https://medai.com",
      "linkedin_url": "https://linkedin.com/company/medai",
      "funding_info": "Series A",
      "tags": "healthtech, ai",
      "email_status": "not_contacted",
      "source_file": "healthcare_startups.csv"
    }
  ],
  "total": 120,
  "limit": 50,
  "offset": 0
}
```

---

### GET `/api/leads/stats`

Aggregate statistics for the leads dashboard.

```bash
curl http://localhost:8000/api/leads/stats
```

**Success response:**

```json
{
  "total": 500,
  "with_email": 320,
  "with_website": 450,
  "with_linkedin": 280,
  "by_country": {"India": 200, "US": 150, "UK": 50},
  "by_industry": {"Healthcare": 180, "AI/ML": 120},
  "by_source": {"healthcare_startups.csv": 300, "vc_portfolio.csv": 200},
  "by_email_status": {"not_contacted": 400, "contacted": 80, "replied": 20},
  "by_funding": {"Series A": 100, "Seed": 200, "Unknown": 200}
}
```

---

### GET `/api/leads/sources`

Get distinct source files for filter dropdown.

```bash
curl http://localhost:8000/api/leads/sources
```

**Success response:**

```json
{
  "sources": ["healthcare_startups.csv", "vc_portfolio.csv", "tracxn_export.csv"]
}
```

---

### GET `/api/leads/{lead_id}`

Get a single lead's full details.

```bash
curl http://localhost:8000/api/leads/42
```

**Success response:** Full lead object (all columns from startup_leads table).

**Error cases:**
- Lead not found: 404

---

### POST `/api/leads/{lead_id}/update`

Update a lead's fields.

**Request body:**

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `email_status` | string | `""` | New email status |
| `email` | string | `""` | New email address |
| `notes` | string | `""` | Notes |
| `tags` | string | `""` | Tags (comma-separated) |

```bash
curl -X POST http://localhost:8000/api/leads/42/update \
  -H 'Content-Type: application/json' \
  -d '{"email_status": "contacted", "notes": "Sent intro email"}'
```

**Success response:**

```json
{
  "status": "ok",
  "message": "Lead updated"
}
```

---

### POST `/api/leads/import`

Run lead import from data files.

```bash
curl -X POST http://localhost:8000/api/leads/import
```

**Success response:**

```json
{
  "status": "ok",
  "message": "Import complete. 500 total leads in database."
}
```

---

### POST `/api/leads/enrich/start`

Start bulk email finding in a background thread.

**Request body:**

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `max_leads` | int | 50 | Maximum leads to process |
| `target` | string | `"startup_leads"` | Target: `"startup_leads"` or `"posts"` |

```bash
curl -X POST http://localhost:8000/api/leads/enrich/start \
  -H 'Content-Type: application/json' \
  -d '{"max_leads": 100, "target": "startup_leads"}'
```

**Success response:**

```json
{
  "status": "started",
  "message": "Finding emails for 100 startup leads (out of 200 without emails)...",
  "missing": 200,
  "processing": 100
}
```

**Error cases:**
- Already running: 400 `"Email finder already running. Wait or stop it first."`
- All have emails: `{"status": "ok", "message": "All leads already have emails!"}`

---

### GET `/api/leads/enrich/status`

Poll enrichment progress.

```bash
curl http://localhost:8000/api/leads/enrich/status
```

**Success response:**

```json
{
  "running": true,
  "current": 25,
  "total": 100,
  "current_company": "MedAI Corp",
  "target": "startup_leads",
  "found": 18,
  "not_found": 5,
  "errors": 2,
  "summary": null,
  "results": [
    {"type": "found", "company": "MedAI Corp", "emails": ["hr@medai.com"], "current": 25, "total": 100}
  ]
}
```

---

### POST `/api/leads/enrich/stop`

Stop the running enrichment process.

```bash
curl -X POST http://localhost:8000/api/leads/enrich/stop
```

**Success response:**

```json
{
  "status": "stopped"
}
```

---

### POST `/api/leads/enrich/single/{lead_id}`

Find emails for a single lead synchronously.

**Path parameters:**

| Param | Type | Description |
|-------|------|-------------|
| `lead_id` | int | Startup lead ID |

```bash
curl -X POST http://localhost:8000/api/leads/enrich/single/42
```

**Success response:**

```json
{
  "status": "ok",
  "lead_id": 42,
  "company": "MedAI Corp",
  "emails_found": 2,
  "emails": [
    {"email": "careers@medai.com", "source": "website_scrape", "score": 0.9},
    {"email": "info@medai.com", "source": "pattern_guess", "score": 0.5}
  ],
  "saved": "careers@medai.com, info@medai.com"
}
```

**Error cases:**
- Lead not found: 404

---

## Settings

Prefix: `/api` and `/api/settings`

Profile, SMTP, Gemini API key, resume management.

### GET `/api/profile`

Get user profile.

```bash
curl http://localhost:8000/api/profile
```

**Success response:**

```json
{
  "name": "Your Name",
  "email": "your_email@example.com",
  "phone": "+91-XXXXXXXXXX",
  "linkedin": "https://linkedin.com/in/yourprofile",
  "github": "https://github.com/yourusername",
  "website": "https://yoursite.com",
  "location": "City, Country",
  "current_title": "AI Engineer",
  "experience_years": 2,
  "notice_period_days": 30,
  "resume_path": "assets/vineet_kukreti_resume.pdf"
}
```

---

### GET `/api/settings/all`

Get all configurable settings in one call.

```bash
curl http://localhost:8000/api/settings/all
```

**Success response:**

```json
{
  "profile": {"name": "Your Name", "email": "your_email@example.com"},
  "smtp": {
    "smtp_host": "smtp.gmail.com",
    "smtp_port": 587,
    "smtp_user": "your_email@example.com",
    "smtp_password_set": true,
    "from_email": "your_email@example.com",
    "from_name": "Your Name"
  },
  "gemini": {
    "api_key_set": true,
    "api_key_preview": "AIzaSyBx..."
  },
  "imap": {
    "imap_host": "imap.gmail.com",
    "imap_port": "993",
    "imap_configured": true
  }
}
```

**Notes:** Passwords are never returned in full. Only a boolean (`smtp_password_set`) or truncated preview (`api_key_preview`) is sent.

---

### POST `/api/settings/profile`

Save profile settings.

**Request body:**

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `name` | string | `""` | Full name |
| `email` | string | `""` | Email address |
| `phone` | string | `""` | Phone number |
| `linkedin` | string | `""` | LinkedIn URL |
| `github` | string | `""` | GitHub URL |
| `website` | string | `""` | Personal website |
| `location` | string | `""` | Location |
| `current_title` | string | `""` | Current job title |
| `experience_years` | int | 2 | Years of experience |
| `notice_period_days` | int | 30 | Notice period |
| `resume_path` | string | `""` | Path to resume file |

```bash
curl -X POST http://localhost:8000/api/settings/profile \
  -H 'Content-Type: application/json' \
  -d '{"name": "Your Name", "email": "your_email@example.com", "location": "City, Country"}'
```

**Success response:**

```json
{
  "status": "ok",
  "message": "Profile saved"
}
```

**Notes:** Writes to `backend/config.py` and updates in-memory PROFILE dict.

---

### POST `/api/settings/smtp`

Save SMTP settings.

**Request body:**

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `smtp_host` | string | `"smtp.gmail.com"` | SMTP server host |
| `smtp_port` | int | 587 | SMTP port |
| `smtp_user` | string | `""` | SMTP username |
| `smtp_password` | string | `""` | SMTP password (App Password for Gmail) |
| `from_email` | string | `""` | Sender email address |
| `from_name` | string | `""` | Sender display name |

```bash
curl -X POST http://localhost:8000/api/settings/smtp \
  -H 'Content-Type: application/json' \
  -d '{"smtp_host": "smtp.gmail.com", "smtp_port": 587, "smtp_user": "your_email@example.com", "smtp_password": "your_app_password", "from_email": "your_email@example.com", "from_name": "Your Name"}'
```

**Success response:**

```json
{
  "status": "ok",
  "message": "SMTP config saved"
}
```

**Notes:** Writes to `config/.env` and updates in-memory SMTP_CONFIG.

---

### POST `/api/settings/gemini`

Save Gemini API key.

**Request body:**

| Field | Type | Description |
|-------|------|-------------|
| `api_key` | string | Gemini API key |

```bash
curl -X POST http://localhost:8000/api/settings/gemini \
  -H 'Content-Type: application/json' \
  -d '{"api_key": "your_api_key"}'
```

**Success response:**

```json
{
  "status": "ok",
  "message": "Gemini API key saved"
}
```

---

### POST `/api/settings/test-email`

Send a test email to verify SMTP configuration.

```bash
curl -X POST http://localhost:8000/api/settings/test-email
```

**Success response:**

```json
{
  "status": "ok",
  "message": "Test email sent to your_email@example.com"
}
```

**Error cases:**
- SMTP not configured: 400 `"SMTP password not configured"`
- Send failure: 500

---

### POST `/api/settings/upload-resume`

Upload a resume PDF file.

**Content-Type:** `multipart/form-data`

| Field | Type | Description |
|-------|------|-------------|
| `file` | File | PDF file |

```bash
curl -X POST http://localhost:8000/api/settings/upload-resume \
  -F "file=@/path/to/resume.pdf"
```

**Success response:**

```json
{
  "status": "ok",
  "message": "Resume uploaded: resume.pdf (245 KB)",
  "filename": "resume.pdf",
  "path": "assets/resume.pdf"
}
```

**Error cases:**
- Non-PDF file: 400 `"Only PDF files are allowed."`

---

### GET `/api/settings/resume-status`

Check if resume file exists.

```bash
curl http://localhost:8000/api/settings/resume-status
```

**Success response:**

```json
{
  "exists": true,
  "filename": "resume.pdf",
  "path": "assets/resume.pdf",
  "size_kb": 245
}
```

---

## AI Tools

Prefix: `/api/tools`

Gemini-powered job evaluation, outreach generation, company research, CV tailoring, and interview prep.

### POST `/api/tools/evaluate`

Evaluate a job description with 7-block analysis against your profile.

**Request body:**

| Field | Type | Description |
|-------|------|-------------|
| `jd_text` | string | Full job description text |

```bash
curl -X POST http://localhost:8000/api/tools/evaluate \
  -H 'Content-Type: application/json' \
  -d '{"jd_text": "We are looking for an ML Engineer with 3+ years experience in healthcare AI..."}'
```

**Success response:**

```json
{
  "summary": "Strong match for healthcare AI role...",
  "cv_match": "85% alignment with key requirements",
  "gaps": ["Kubernetes experience", "5+ years preferred"],
  "score": 8.2,
  "verdict": "Strong Apply",
  "personalization": "Mention FHIR pipeline experience...",
  "interview_topics": ["ML model deployment", "Healthcare data standards"]
}
```

**Error cases:**
- Missing jd_text: 400 `"jd_text required"`
- AI failure: 500

---

### POST `/api/tools/outreach`

Generate personalized cold outreach messages.

**Request body:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `company` | string | yes | Company name |
| `role` | string | no | Role title |
| `recruiter_name` | string | no | Recruiter/hiring manager name |
| `context` | string | no | Additional context |

```bash
curl -X POST http://localhost:8000/api/tools/outreach \
  -H 'Content-Type: application/json' \
  -d '{"company": "MedAI Corp", "role": "ML Engineer", "recruiter_name": "Jane Doe"}'
```

**Success response:**

```json
{
  "email_text": "Hi Jane,\n\nI noticed MedAI Corp is building..."
}
```

---

### POST `/api/tools/deep-dive`

Deep research a company before outreach.

**Request body:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `company` | string | yes | Company name |
| `role` | string | no | Role for context |

```bash
curl -X POST http://localhost:8000/api/tools/deep-dive \
  -H 'Content-Type: application/json' \
  -d '{"company": "MedAI Corp", "role": "ML Engineer"}'
```

**Success response:**

```json
{
  "sections": [
    {"title": "Company Overview", "content": "MedAI Corp is a..."},
    {"title": "Tech Stack", "content": "Python, TensorFlow, FHIR..."},
    {"title": "Culture", "content": "Remote-first, fast-paced..."}
  ]
}
```

---

### POST `/api/tools/tailor-cv`

Generate an ATS-optimized CV tailored to a specific job description.

**Request body:**

| Field | Type | Description |
|-------|------|-------------|
| `jd_text` | string | Full job description text |

```bash
curl -X POST http://localhost:8000/api/tools/tailor-cv \
  -H 'Content-Type: application/json' \
  -d '{"jd_text": "Senior ML Engineer role at..."}'
```

**Success response:**

```json
{
  "cv_text": "VINEET KUKRETI\nML Engineer | Healthcare AI\n..."
}
```

---

### POST `/api/tools/interview-prep`

Generate interview preparation material for a company and role.

**Request body:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `company` | string | yes | Company name |
| `role` | string | no | Role title |

```bash
curl -X POST http://localhost:8000/api/tools/interview-prep \
  -H 'Content-Type: application/json' \
  -d '{"company": "MedAI Corp", "role": "ML Engineer"}'
```

**Success response:**

```json
{
  "questions": ["Tell me about your FHIR experience...", "How would you handle..."],
  "tips": ["Research their recent FDA clearance...", "Mention your pipeline work..."]
}
```

---

## ATS Scanner

Prefix: `/api/ats`

Scan company ATS portals (Greenhouse, Lever, Ashby) for healthcare AI jobs.

### GET `/api/ats/companies`

Get tracked companies from portals.yml.

```bash
curl http://localhost:8000/api/ats/companies
```

**Success response:**

```json
{
  "companies": [
    {"name": "Tempus", "enabled": true, "notes": "Healthcare AI"},
    {"name": "Flatiron Health", "enabled": true, "notes": "Oncology data"}
  ],
  "total": 15
}
```

**Notes:** Returns empty list with error field if `config/portals.yml` is not found.

---

### POST `/api/ats/scan`

Run ATS API scan for healthcare AI jobs across all tracked companies.

```bash
curl -X POST http://localhost:8000/api/ats/scan
```

**Success response:**

```json
{
  "status": "done",
  "total_found": 25,
  "inserted": 20,
  "skipped": 5,
  "jobs": [
    {"title": "ML Engineer", "company": "Tempus", "url": "https://..."}
  ]
}
```

---

## Auto-Apply

Prefix: `/api/auto-apply`

Automated job application engine using browser automation and email.

### POST `/api/auto-apply/start`

Start the auto-apply engine in a background thread.

**Request body:**

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `max_applications` | int | 500 | Maximum applications this run |

```bash
curl -X POST http://localhost:8000/api/auto-apply/start \
  -H 'Content-Type: application/json' \
  -d '{"max_applications": 100}'
```

**Success response:**

```json
{
  "status": "started",
  "message": "Auto-apply started for up to 100 applications"
}
```

**Error cases:**
- Returns `{"status": "error", "message": "..."}` if prerequisites are not met.

---

### POST `/api/auto-apply/stop`

Stop the auto-apply engine.

```bash
curl -X POST http://localhost:8000/api/auto-apply/stop
```

**Success response:**

```json
{
  "status": "stopped"
}
```

---

### GET `/api/auto-apply/status`

Get auto-apply progress and log.

```bash
curl http://localhost:8000/api/auto-apply/status
```

**Success response:**

```json
{
  "running": true,
  "progress": {
    "applied": 15,
    "failed": 2,
    "skipped": 3
  },
  "log": [
    "Applied to ML Engineer at HealthTech Inc",
    "Skipped: already applied to MedAI Corp"
  ]
}
```

---

### GET `/api/auto-apply/quota`

Get today's application quota and all-time stats.

```bash
curl http://localhost:8000/api/auto-apply/quota
```

**Success response:**

```json
{
  "quota": {
    "date": "2026-04-26",
    "target": 500,
    "applied": 42,
    "remaining": 458
  },
  "stats": {
    "applied": 1200,
    "skipped": 300,
    "failed": 50,
    "total": 1550
  }
}
```

---

## Skills Intelligence

Prefix: `/api/skills`

Analyze job market skill demands, identify resume gaps, and track trends.

### GET `/api/skills/dashboard`

Main skills intelligence dashboard data.

```bash
curl http://localhost:8000/api/skills/dashboard
```

**Success response:**

```json
{
  "top_skills": [
    {"skill": "Python", "count": 450, "percentage": 90.0},
    {"skill": "TensorFlow", "count": 200, "percentage": 40.0}
  ],
  "skill_categories": {"ml_frameworks": 350, "cloud": 200, "data_engineering": 180},
  "analysis_date": "2026-04-25"
}
```

---

### POST `/api/skills/analyze`

Trigger background skills analysis.

**Request body:**

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `use_llm` | bool | false | Use LLM for deeper extraction |
| `llm_sample_size` | int | 100 | Number of posts to analyze with LLM |

```bash
curl -X POST http://localhost:8000/api/skills/analyze \
  -H 'Content-Type: application/json' \
  -d '{"use_llm": true, "llm_sample_size": 50}'
```

**Success response:**

```json
{
  "status": "started",
  "message": "Analysis started..."
}
```

---

### GET `/api/skills/analysis-status`

Poll analysis progress.

```bash
curl http://localhost:8000/api/skills/analysis-status
```

**Success response:**

```json
{
  "running": true,
  "current": 30,
  "total": 100,
  "phase": "extracting"
}
```

---

### GET `/api/skills/gaps`

Resume gap analysis against market demands.

```bash
curl http://localhost:8000/api/skills/gaps
```

**Success response:**

```json
{
  "missing_skills": [
    {"skill": "Kubernetes", "demand_count": 180, "priority": "high"},
    {"skill": "Spark", "demand_count": 120, "priority": "medium"}
  ],
  "strong_skills": [
    {"skill": "Python", "demand_count": 450, "match": true},
    {"skill": "TensorFlow", "demand_count": 200, "match": true}
  ]
}
```

---

### GET `/api/skills/trends`

Get cached trending tools and technologies.

```bash
curl http://localhost:8000/api/skills/trends
```

**Success response:**

```json
{
  "trends": [
    {"name": "LLM Fine-tuning", "category": "AI/ML", "momentum": "rising"},
    {"name": "FHIR R4", "category": "Healthcare", "momentum": "stable"}
  ],
  "updated_at": "2026-04-25"
}
```

---

### POST `/api/skills/trends/refresh`

Re-fetch trends from Gemini AI.

```bash
curl -X POST http://localhost:8000/api/skills/trends/refresh
```

**Success response:** Same format as GET `/api/skills/trends` with fresh data.

---

### GET `/api/skills/news`

Get cached industry news.

```bash
curl http://localhost:8000/api/skills/news
```

**Success response:**

```json
{
  "articles": [
    {"title": "FDA approves AI diagnostic tool", "summary": "...", "relevance": "high"}
  ],
  "updated_at": "2026-04-25"
}
```

---

### POST `/api/skills/news/refresh`

Re-fetch news from Gemini AI.

```bash
curl -X POST http://localhost:8000/api/skills/news/refresh
```

**Success response:** Same format as GET `/api/skills/news` with fresh data.

---

## Smart Filter

Prefix: `/api/smart-filter`

Score job posts by fit using a weighted rubric (0-10 scale).

### POST `/api/smart-filter/score`

Score a single job post by ID or raw content.

**Request body:**

| Field | Type | Description |
|-------|------|-------------|
| `post_id` | int | Post ID to score from DB (optional) |
| `content` | string | Raw job content (if no post_id) |
| `role` | string | Role title |
| `company` | string | Company name |
| `location` | string | Location |
| `experience` | string | Experience requirements |
| `domain_relevance` | string | Domain relevance level |
| `fit_score` | float | Existing fit score to override |

```bash
curl -X POST http://localhost:8000/api/smart-filter/score \
  -H 'Content-Type: application/json' \
  -d '{"post_id": 15}'
```

**Success response:**

```json
{
  "score": 7.5,
  "factors": {
    "domain": 2.0,
    "skills": 1.5,
    "experience": 1.0,
    "location": 1.0,
    "recency": 1.0,
    "company_size": 1.0
  }
}
```

---

### POST `/api/smart-filter/score-all`

Score all unscored hiring posts in the database.

**Request body (optional):**

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `limit` | int | 500 | Maximum posts to score |

```bash
curl -X POST http://localhost:8000/api/smart-filter/score-all \
  -H 'Content-Type: application/json' \
  -d '{"limit": 200}'
```

**Success response:**

```json
{
  "scored": 150,
  "total": 150
}
```

---

### GET `/api/smart-filter/stats`

Get smart scoring statistics.

```bash
curl http://localhost:8000/api/smart-filter/stats
```

**Success response:**

```json
{
  "distribution": {"0-2": 50, "2-4": 80, "4-6": 120, "6-8": 100, "8-10": 30},
  "avg": 5.2,
  "median": 5.0
}
```

---

### GET `/api/smart-filter/top`

Get top-scoring unapplied jobs (threshold >= 3.5, limit 50).

```bash
curl http://localhost:8000/api/smart-filter/top
```

**Success response:**

```json
{
  "jobs": [
    {"post_id": 15, "score": 8.5, "role": "ML Engineer", "company": "HealthTech Inc"}
  ],
  "total": 30
}
```

---

## Follow-up

Prefix: `/api/followup`

Track and manage email follow-ups.

### GET `/api/followup/status`

Get follow-up urgency status for all sent emails.

```bash
curl http://localhost:8000/api/followup/status
```

**Success response:**

```json
{
  "overdue": [{"outreach_id": 1, "days_since": 14, "company": "Acme"}],
  "urgent": [{"outreach_id": 5, "days_since": 7, "company": "MedTech"}],
  "waiting": [{"outreach_id": 10, "days_since": 3, "company": "HealthAI"}],
  "cold": [{"outreach_id": 20, "days_since": 30, "company": "OldCorp"}]
}
```

---

### POST `/api/followup/record`

Record a follow-up sent for an outreach entry.

**Request body:**

| Field | Type | Description |
|-------|------|-------------|
| `outreach_id` | int | Email outreach record ID |

```bash
curl -X POST http://localhost:8000/api/followup/record \
  -H 'Content-Type: application/json' \
  -d '{"outreach_id": 5}'
```

**Success response:**

```json
{
  "status": "ok",
  "followup_count": 2
}
```

---

### POST `/api/followup/auto-send`

Start automatic follow-up sending for overdue emails.

```bash
curl -X POST http://localhost:8000/api/followup/auto-send
```

**Success response:**

```json
{
  "status": "started",
  "message": "Auto follow-up started"
}
```

---

### POST `/api/followup/preview/{outreach_id}`

Preview a follow-up email before sending.

```bash
curl -X POST http://localhost:8000/api/followup/preview/42
```

**Success response:**

```json
{
  "subject": "Re: ML Engineer Application",
  "body": "Hi John, I wanted to follow up on..."
}
```

---

### GET `/api/followup/worker-status`

Get follow-up worker status.

```bash
curl http://localhost:8000/api/followup/worker-status
```

**Success response:**

```json
{
  "running": false,
  "sent": 5,
  "failed": 1
}
```

---

### POST `/api/followup/worker-stop`

Stop the follow-up worker.

```bash
curl -X POST http://localhost:8000/api/followup/worker-stop
```

---

## Liveness

Prefix: `/api/liveness`

Check if job posting URLs are still active.

### POST `/api/liveness/check`

Check if a job URL (or batch of URLs) is still active.

**Request body:**

| Field | Type | Description |
|-------|------|-------------|
| `url` | string | Single URL to check (optional) |
| `urls` | string[] | Batch of URLs to check (optional) |

Provide either `url` or `urls`, not both.

```bash
curl -X POST http://localhost:8000/api/liveness/check \
  -H 'Content-Type: application/json' \
  -d '{"url": "https://example.com/jobs/123"}'
```

**Success response (single):**

```json
{
  "url": "https://example.com/jobs/123",
  "alive": true,
  "status_code": 200
}
```

**Success response (batch):**

```json
{
  "results": [
    {"url": "https://example.com/jobs/123", "alive": true, "status_code": 200},
    {"url": "https://example.com/jobs/456", "alive": false, "status_code": 404}
  ]
}
```

---

### POST `/api/liveness/scan`

Batch check liveness of all posts in the database.

```bash
curl -X POST http://localhost:8000/api/liveness/scan
```

**Success response:**

```json
{
  "checked": 100,
  "alive": 85,
  "dead": 15
}
```

---

## Analytics

Prefix: `/api/analytics`

Outreach pattern analysis and conversion tracking.

### GET `/api/analytics/patterns`

Get email outreach pattern analysis with recommendations.

```bash
curl http://localhost:8000/api/analytics/patterns
```

**Success response:**

```json
{
  "response_rate": 3.2,
  "best_times": {"hour": 9, "day": "Tuesday"},
  "recommendations": [
    "Send emails between 9-11 AM for best response rates",
    "Healthcare domain has 5x higher response rate"
  ]
}
```

---

### GET `/api/analytics/conversion`

Get conversion rates per role and domain.

```bash
curl http://localhost:8000/api/analytics/conversion
```

**Success response:**

```json
{
  "by_role": {"ML Engineer": {"sent": 50, "replied": 3, "rate": 6.0}},
  "by_domain": {"High": {"sent": 80, "replied": 5, "rate": 6.25}},
  "by_company": {"HealthTech Inc": {"sent": 2, "replied": 1, "rate": 50.0}}
}
```

---

## Company Intelligence

Prefix: `/api/company`

Company health signals and connection detection.

### POST `/api/company/scan`

Scan a company for health signals (funding, growth, layoffs, etc.).

**Request body:**

| Field | Type | Description |
|-------|------|-------------|
| `company` | string | Company name |

```bash
curl -X POST http://localhost:8000/api/company/scan \
  -H 'Content-Type: application/json' \
  -d '{"company": "MedAI Corp"}'
```

**Success response:**

```json
{
  "health_score": 8.0,
  "signals": [
    {"type": "funding", "detail": "Series B raised $50M", "sentiment": "positive"},
    {"type": "hiring", "detail": "15 open ML roles", "sentiment": "positive"}
  ]
}
```

---

### POST `/api/company/connections`

Find existing connections at a company.

**Request body:**

| Field | Type | Description |
|-------|------|-------------|
| `company` | string | Company name |

```bash
curl -X POST http://localhost:8000/api/company/connections \
  -H 'Content-Type: application/json' \
  -d '{"company": "MedAI Corp"}'
```

**Success response:**

```json
{
  "has_connections": true,
  "company": "MedAI Corp",
  "contacts": [
    {"name": "Jane Doe", "role": "Lead Engineer", "email": "jane@medai.com"}
  ],
  "recommendation": "warm_referral"
}
```

---

## Resume Management

Prefix: `/api/resumes`

Manage multiple resume variants and auto-selection.

### GET `/api/resumes/variants`

List all configured resume variants with details.

```bash
curl http://localhost:8000/api/resumes/variants
```

**Success response:**

```json
{
  "variants": [
    {
      "name": "healthcare-ai",
      "path": "assets/resumes/healthcare-ai/vineet_kukreti_resume.pdf",
      "description": "Emphasizes FHIR, medical imaging, clinical NLP",
      "keywords": ["healthcare", "fhir", "medical", "clinical"],
      "weight": 1.5,
      "exists": true,
      "size_kb": 245
    },
    {
      "name": "data-engineering",
      "path": "assets/resumes/data-engineering/vineet_kukreti_resume.pdf",
      "description": "Emphasizes pipelines, Spark, Airflow",
      "keywords": ["data engineer", "spark", "airflow", "etl"],
      "weight": 1.0,
      "exists": true,
      "size_kb": 230
    }
  ]
}
```

---

### POST `/api/resumes/variants/{variant_name}/upload`

Upload a PDF for a specific resume variant.

**Content-Type:** `multipart/form-data`

**Path parameters:**

| Param | Type | Description |
|-------|------|-------------|
| `variant_name` | string | Variant key (e.g., `healthcare-ai`) |

```bash
curl -X POST http://localhost:8000/api/resumes/variants/healthcare-ai/upload \
  -F "file=@/path/to/resume.pdf"
```

**Success response:**

```json
{
  "status": "ok",
  "variant": "healthcare-ai",
  "filename": "vineet_kukreti_resume.pdf",
  "size_kb": 245
}
```

**Error cases:**
- Unknown variant: 404
- Non-PDF file: 400

---

### POST `/api/resumes/test-selection`

Test which resume variant would be selected for given job info.

**Request body:**

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `role` | string | `""` | Job role |
| `content` | string | `""` | Job description content |
| `domain_relevance` | string | `""` | Domain relevance level |
| `company` | string | `""` | Company name |

```bash
curl -X POST http://localhost:8000/api/resumes/test-selection \
  -H 'Content-Type: application/json' \
  -d '{"role": "ML Engineer", "content": "Healthcare AI platform with FHIR...", "domain_relevance": "High"}'
```

**Success response:**

```json
{
  "selected": "healthcare-ai",
  "path": "assets/resumes/healthcare-ai/vineet_kukreti_resume.pdf",
  "scores": {
    "healthcare-ai": {"score": 12.5, "hits": 5},
    "data-engineering": {"score": 2.0, "hits": 2},
    "genai-platform": {"score": 1.0, "hits": 1}
  }
}
```

---

### POST `/api/resumes/select`

Select the best resume for a job (returns path only).

**Request body:**

| Field | Type | Description |
|-------|------|-------------|
| `role` | string | Job role |
| `content` | string | Job description |
| `domain_relevance` | string | Domain relevance |
| `company` | string | Company name |

```bash
curl -X POST http://localhost:8000/api/resumes/select \
  -H 'Content-Type: application/json' \
  -d '{"role": "ML Engineer", "content": "FHIR pipeline", "domain_relevance": "High"}'
```

**Success response:**

```json
{
  "selected": "assets/resumes/healthcare-ai/vineet_kukreti_resume.pdf"
}
```

---

## Quality Dashboard

Prefix: `/api/dashboard`

### GET `/api/dashboard/quality`

Get comprehensive application quality dashboard data.

```bash
curl http://localhost:8000/api/dashboard/quality
```

**Success response:**

```json
{
  "metrics": {
    "total_sent": 200,
    "reply_rate": 3.5,
    "avg_score": 6.2,
    "top_domains": ["Healthcare", "AI/ML"]
  }
}
```

---

## Email A/B Testing

Prefix: `/api/email`

### GET `/api/email/ab-stats`

Get A/B email variant performance statistics.

```bash
curl http://localhost:8000/api/email/ab-stats
```

**Success response:**

```json
{
  "variants": [
    {"variant": "A", "strategy": "direct", "sent": 50, "replied": 3, "rate": 6.0},
    {"variant": "B", "strategy": "referral", "sent": 45, "replied": 5, "rate": 11.1}
  ]
}
```

---

## Polling Patterns

Several operations run in background threads. Use these polling intervals for real-time UI updates:

| Endpoint | Recommended Interval | Description |
|----------|---------------------|-------------|
| `GET /api/browser/status` | 5s | Browser state changes |
| `GET /api/scraper/status` | 2s | Scraper progress per source |
| `GET /api/email/worker-status` | 3s | Bulk generate/send progress |
| `GET /api/auto-apply/status` | 2s | Auto-apply progress and log |
| `GET /api/skills/analysis-status` | 3s | Skills analysis progress |
| `GET /api/leads/enrich/status` | 3s | Email enrichment progress |
| `GET /api/followup/worker-status` | 3s | Follow-up sending progress |
| `GET /api/email/imap-status` | 30s | IMAP polling state |

All polling endpoints return a `running` boolean. Stop polling when `running` is `false`.

---

## See Also

- [Architecture](ARCHITECTURE.md) -- System design, threading, component interactions
- [Database Schema](DATABASE_SCHEMA.md) -- All tables, relationships, key queries
- [Services Reference](SERVICES_REFERENCE.md) -- Every service, function, and constant
- [Setup Guide](SETUP_GUIDE.md) -- Installation, configuration, usage
