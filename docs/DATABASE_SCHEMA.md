# CareerKit Database Schema

Database: SQLite3 with WAL mode
Location: `data/linkedin_jobs.db`

---

## Entity Relationship Diagram

```
┌──────────────┐     1:N     ┌──────────────┐
│    posts     │────────────>│     jobs      │
│  (post_url)  │             │  (id, FK)     │
└──────┬───────┘             └───────────────┘
       │
       │ 1:N
       v
┌──────────────┐     1:1     ┌──────────────────┐
│email_outreach│────────────>│  pipeline_leads   │
│  (id, FK)    │             │  (id, FK, FK)     │
└──────────────┘             └────────┬──────────┘
                                      │
                              ┌───────┴────────┐
                              │ 1:N        1:N │
                              v                v
                     ┌────────────────┐ ┌──────────────┐
                     │pipeline_events │ │pipeline_notes│
                     │  (id, FK)      │ │  (id, FK)    │
                     └────────────────┘ └──────────────┘

┌──────────────┐         ┌──────────────┐
│ startup_leads│         │ applications │
│  (id)        │         │  (id, FK)    │
└──────────────┘         └──────────────┘

                         ┌──────────────┐
                         │ daily_quotas │
                         │  (date PK)   │
                         └──────────────┘
```

---

## Tables

### `posts` — Scraped job posts

Primary source of all scraped content from LinkedIn and other portals.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `post_url` | TEXT | PRIMARY KEY | URL of the post |
| `content_hash` | TEXT | | SHA-256 of first 200 chars (dedup) |
| `content_hash_v2` | TEXT | | SHA-256 of first 500 chars normalized |
| `author_name` | TEXT | | Post author |
| `author_headline` | TEXT | | Author's headline/title |
| `content` | TEXT | | Full post text |
| `email` | TEXT | | Extracted email(s), comma-separated |
| `is_hiring` | TEXT | | "Yes" / "Maybe" / "No" |
| `domain_relevance` | TEXT | | "High" / "Medium" / "Low" |
| `deep_extracted` | INTEGER | DEFAULT 0 | Whether deep LLM extraction was done |
| `fit_score` | REAL | | Smart filter score (0-10) |
| `source` | TEXT | | Source identifier (linkedin, remoteok, etc.) |
| `is_live` | INTEGER | DEFAULT 1 | Whether the URL is still active |
| `created_at` | TEXT | DEFAULT CURRENT_TIMESTAMP | Insert timestamp |

**Indexes**: `post_url` (PK), `content_hash`, `content_hash_v2`

### `jobs` — Extracted job details (1:many per post)

Structured job information extracted via LLM or regex from posts.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT | |
| `post_id` | TEXT | FK → posts.post_url | Parent post |
| `role` | TEXT | | Job title (AI Engineer, ML Engineer, etc.) |
| `company` | TEXT | | Hiring company name |
| `location` | TEXT | | City/country/Remote |
| `experience` | TEXT | | Experience requirement ("2 years", "3-5 years") |
| `salary_min` | REAL | | Minimum salary (if available) |
| `salary_max` | REAL | | Maximum salary (if available) |
| `tech_stack` | TEXT | | Technologies mentioned (JSON array) |
| `fit_reasons` | TEXT | | Why this is a good fit (from LLM) |
| `created_at` | TEXT | DEFAULT CURRENT_TIMESTAMP | |

### `email_outreach` — Cold email tracking

Tracks every email generated and sent for outreach.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT | |
| `post_id` | TEXT | FK → posts.post_url | Related post |
| `recipient_email` | TEXT | | Target email address |
| `recipient_name` | TEXT | | Recipient name |
| `subject` | TEXT | | Email subject line |
| `body` | TEXT | | Email body content |
| `status` | TEXT | DEFAULT 'draft' | draft / sent / failed |
| `followup_count` | INTEGER | DEFAULT 0 | Number of follow-ups sent |
| `last_followup_at` | TEXT | | Timestamp of last follow-up |
| `created_at` | TEXT | DEFAULT CURRENT_TIMESTAMP | |
| `sent_at` | TEXT | | When email was sent |

### `pipeline_leads` — CRM lead tracking

Leads created from sent outreach emails, tracked through hiring stages.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT | |
| `post_id` | TEXT | FK → posts.post_url | Source post |
| `outreach_id` | INTEGER | FK → email_outreach.id | Source email |
| `recipient_email` | TEXT | | Contact email |
| `recipient_name` | TEXT | | Contact name |
| `role` | TEXT | | Job role |
| `company` | TEXT | | Company name |
| `stage` | TEXT | DEFAULT 'applied' | Current pipeline stage |
| `created_at` | TEXT | DEFAULT CURRENT_TIMESTAMP | |
| `updated_at` | TEXT | | Last stage change |

**Stages**: `applied` → `replied` → `interviewing` → `offer` / `rejected`

### `pipeline_events` — Timeline events per lead

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT | |
| `lead_id` | INTEGER | FK → pipeline_leads.id | Parent lead |
| `event_type` | TEXT | | email_sent / reply_received / stage_change / note / follow_up |
| `title` | TEXT | | Event title |
| `content` | TEXT | | Event details |
| `created_at` | TEXT | DEFAULT CURRENT_TIMESTAMP | |

### `pipeline_notes` — Recruiter notes per lead

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT | |
| `lead_id` | INTEGER | FK → pipeline_leads.id | Parent lead |
| `content` | TEXT | | Note text |
| `created_at` | TEXT | DEFAULT CURRENT_TIMESTAMP | |

### `startup_leads` — Target company database

Healthcare/startup companies for proactive outreach.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT | |
| `company_name` | TEXT | | Company name |
| `website` | TEXT | | Company website |
| `industry` | TEXT | | Industry sector |
| `country` | TEXT | | HQ country |
| `city` | TEXT | | HQ city |
| `employees` | TEXT | | Employee count range |
| `funding_info` | TEXT | | Funding stage/amount |
| `linkedin_url` | TEXT | | Company LinkedIn page |
| `email` | TEXT | | Found contact email(s) |
| `email_status` | TEXT | DEFAULT 'not_found' | not_found / found / verified / invalid |
| `source` | TEXT | | Import source file |
| `tags` | TEXT | | Tags (JSON array) |
| `notes` | TEXT | | Free-text notes |
| `created_at` | TEXT | DEFAULT CURRENT_TIMESTAMP | |

### `applications` — Auto-apply history

Every application attempt (manual or automated).

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT | |
| `post_id` | TEXT | FK → posts.post_url | Source post |
| `platform` | TEXT | | linkedin / email / redirect |
| `job_url` | TEXT | | Application URL |
| `job_title` | TEXT | | Job title |
| `company` | TEXT | | Company name |
| `location` | TEXT | | Job location |
| `status` | TEXT | | applied / partial / failed / skipped |
| `apply_method` | TEXT | | easy_apply / email / redirect |
| `message` | TEXT | | Status message or error |
| `applied_at` | TEXT | DEFAULT CURRENT_TIMESTAMP | |

### `daily_quotas` — Application rate limits

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `date` | TEXT | PRIMARY KEY | Date (YYYY-MM-DD) |
| `target` | INTEGER | DEFAULT 500 | Target applications |
| `applied` | INTEGER | DEFAULT 0 | Successful applications |
| `failed` | INTEGER | DEFAULT 0 | Failed attempts |
| `skipped` | INTEGER | DEFAULT 0 | Skipped jobs |

---

## Deduplication Strategy

CareerKit uses a multi-layer dedup approach to prevent duplicate posts:

```
Layer 1: URL dedup
    └── post_url is PRIMARY KEY → exact URL match

Layer 2: Content hash v1
    └── SHA-256 of first 200 characters
    └── Catches same content at different URLs

Layer 3: Content hash v2
    └── SHA-256 of first 500 characters (normalized: lowercase, stripped)
    └── Catches minor formatting differences

Layer 4: In-memory DedupCache
    └── Loaded on startup from DB
    └── O(1) lookups during scraping
    └── Stores: URLs, content hashes, content prefixes
```

---

## Key Queries

```sql
-- Posts ready for outreach (has email, is hiring, not yet contacted)
SELECT p.* FROM posts p
WHERE p.email IS NOT NULL AND p.email != ''
AND p.is_hiring IN ('Yes', 'Maybe')
AND p.post_url NOT IN (SELECT post_id FROM email_outreach)

-- Unapplied jobs ranked by fitness
SELECT j.*, p.fit_score, p.domain_relevance FROM jobs j
JOIN posts p ON j.post_id = p.post_url
WHERE j.post_id NOT IN (SELECT post_id FROM applications WHERE status = 'applied')
ORDER BY p.fit_score DESC, p.domain_relevance DESC

-- Pipeline funnel
SELECT stage, COUNT(*) as count FROM pipeline_leads GROUP BY stage

-- Daily quota
SELECT * FROM daily_quotas WHERE date = date('now')

-- Stats
SELECT
    COUNT(*) as total,
    SUM(CASE WHEN is_hiring = 'Yes' THEN 1 ELSE 0 END) as hiring,
    SUM(CASE WHEN email IS NOT NULL AND email != '' THEN 1 ELSE 0 END) as with_email
FROM posts
```
