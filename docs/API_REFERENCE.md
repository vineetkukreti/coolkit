# CareerKit API Reference

Base URL: `http://localhost:8000/api`

---

## Browser Control

| Method | Endpoint | Body | Response | Description |
|--------|----------|------|----------|-------------|
| POST | `/browser/start` | — | `{status, message}` | Launch Playwright browser, navigate to LinkedIn |
| POST | `/browser/login` | — | `{status}` | Open LinkedIn login page |
| POST | `/browser/check-login` | — | `{logged_in, status}` | Verify LinkedIn session |
| POST | `/browser/stop` | — | `{status}` | Close browser |
| GET | `/browser/status` | — | `{status, logged_in, running}` | Current browser state |

**Browser States**: `stopped` → `starting` → `ready` → `connected` (logged in)

---

## Scraper

| Method | Endpoint | Body | Response | Description |
|--------|----------|------|----------|-------------|
| POST | `/scraper/start` | `{max_posts, sources[]}` | `{status}` | Start multi-source scraping |
| POST | `/scraper/stop` | — | `{status}` | Stop running scraper |
| GET | `/scraper/status` | — | `{running, sources: {[name]: {status, log[], progress}}}` | Per-source progress |
| GET | `/scraper/sources` | — | `{groups: {[id]: {label, sources[]}}}` | All 100+ sources grouped |

**Source Types**:
- `linkedin` — Requires browser + login
- `api` — HTTP only (RemoteOK, Greenhouse, etc.)
- `browser` — Requires browser (Indeed, Wellfound)
- `html` — HTTP + BeautifulSoup

---

## Posts (LinkedIn DB)

| Method | Endpoint | Params/Body | Response | Description |
|--------|----------|-------------|----------|-------------|
| GET | `/db/posts` | `?role=&domain=&has_email=&is_hiring=&company=&limit=50` | `{posts[]}` | Query posts with filters |
| GET | `/db/stats` | — | `{total, hiring, with_email, domains{}, roles{}}` | Aggregated stats |
| GET | `/db/outreach-ready` | — | `{posts[]}` | Posts with emails ready for outreach |
| POST | `/db/posts/{post_id}/find-email` | — | `{emails[], status}` | Find emails for a post's company |

---

## Job Search

| Method | Endpoint | Body | Response | Description |
|--------|----------|------|----------|-------------|
| POST | `/search` | `{keywords, location, platforms[], max_jobs}` | `{jobs[]}` | Search jobs across platforms |
| POST | `/apply` | `{url, title, company, location, platform}` | `{status}` | Log job as applied |
| POST | `/skip` | `{url, title, company, platform}` | `{status}` | Log job as skipped |
| GET | `/applications` | `?status=` | `{applications[]}` | List applications |
| GET | `/stats` | — | `{applied, failed, skipped, total}` | Application counts |
| GET | `/applications/quota` | — | `{date, target, applied, remaining}` | Today's quota |

---

## Email Outreach

| Method | Endpoint | Body | Response | Description |
|--------|----------|------|----------|-------------|
| POST | `/email/generate` | `{post_id}` or `{author, role, company, content}` | `{subject, body}` | Generate email via Gemini |
| POST | `/email/send` | `{to_email, subject, body, attach_resume?}` | `{status, message_id}` | Send single email via SMTP |
| POST | `/email/save-draft` | `{post_id, to_email, subject, body}` | `{status}` | Save/update email draft |
| POST | `/email/bulk-generate` | `{post_ids[]}` | `{status}` | Background: generate drafts |
| POST | `/email/bulk-send` | `{attach_resume?}` | `{status}` | Background: send all drafts |
| GET | `/email/worker-status` | — | `{running, task, current, total, results{}}` | Poll bulk operation progress |
| POST | `/email/worker-stop` | — | `{status}` | Stop bulk operation |
| GET | `/email/history` | — | `{emails[]}` | 200 most recent sent emails |
| GET | `/email/config-status` | — | `{configured, smtp_host, from_email}` | SMTP config check |

**Email Generation**: Uses Gemini 2.5 Flash-Lite with a system prompt containing candidate profile, 5 past projects, and strict formatting rules (120-180 words, no cliches).

---

## Pipeline (CRM)

| Method | Endpoint | Body | Response | Description |
|--------|----------|------|----------|-------------|
| GET | `/pipeline` | — | `{leads[]}` | All leads with post context |
| GET | `/pipeline/stats` | — | `{applied, replied, interviewing, offer, rejected}` | Counts per stage |
| GET | `/pipeline/lead/{id}` | — | `{lead, events[], notes[], emails[]}` | Full lead detail |
| POST | `/pipeline/update-stage` | `{lead_id, stage}` | `{status}` | Move lead to stage |
| POST | `/pipeline/add-note` | `{lead_id, content}` | `{status}` | Add note to lead |
| POST | `/pipeline/sync` | — | `{created, existing}` | Auto-create leads from sent emails |

**Pipeline Stages**: `applied` → `replied` → `interviewing` → `offer` / `rejected`

---

## Startup Leads

| Method | Endpoint | Params/Body | Response | Description |
|--------|----------|-------------|----------|-------------|
| GET | `/leads` | `?search=&industry=&country=&email_status=&has_email=&sort=&page=&limit=` | `{leads[], total, pages}` | Filtered list with pagination |
| GET | `/leads/stats` | — | `{total, by_country{}, by_industry{}, by_source{}}` | Aggregations |
| GET | `/leads/sources` | — | `{sources[]}` | Distinct import sources |
| GET | `/leads/{id}` | — | `{lead}` | Single lead detail |
| POST | `/leads/{id}/update` | `{email_status?, email?, notes?, tags?}` | `{status}` | Update lead fields |
| POST | `/leads/import` | — | `{imported, skipped, errors}` | Import from data files |
| POST | `/leads/enrich/start` | `{max_leads?, target?}` | `{status}` | Background: find emails |
| GET | `/leads/enrich/status` | — | `{running, current, total, found, not_found, errors}` | Poll enrichment |
| POST | `/leads/enrich/stop` | — | `{status}` | Stop enrichment |
| POST | `/leads/enrich/single/{id}` | — | `{emails[], status}` | Find email for one lead |

---

## Auto-Apply

| Method | Endpoint | Body | Response | Description |
|--------|----------|------|----------|-------------|
| POST | `/auto-apply/start` | `{max_applications}` | `{status}` | Start auto-apply engine |
| POST | `/auto-apply/stop` | — | `{status}` | Stop auto-apply |
| GET | `/auto-apply/status` | — | `{running, progress{applied,failed,skipped}, log[]}` | Progress and log |
| GET | `/auto-apply/quota` | — | `{date, target, applied, all_time}` | Today's quota + totals |

**Platform Budgets**: LinkedIn Easy Apply: 120/day, Email: 180/day
**Rate Limits**: LinkedIn: 45-120s between apps, Email: 10-30s

---

## AI Tools

| Method | Endpoint | Body | Response | Description |
|--------|----------|------|----------|-------------|
| POST | `/tools/evaluate` | `{jd_text}` | `{summary, cv_match, gaps, score, verdict, personalization, interview_topics}` | Evaluate JD vs profile |
| POST | `/tools/outreach` | `{company, role, recruiter_name?, context?}` | `{email_text}` | Generate personalized outreach |
| POST | `/tools/deep-dive` | `{company, role}` | `{sections[]}` | Research company |
| POST | `/tools/tailor-cv` | `{jd_text}` | `{cv_text}` | ATS-optimized CV |
| POST | `/tools/interview-prep` | `{company, role}` | `{questions[], tips[]}` | Interview preparation |

---

## ATS Scanner

| Method | Endpoint | Body | Response | Description |
|--------|----------|------|----------|-------------|
| GET | `/ats/companies` | — | `{companies[]}` | Companies from portals.yml |
| POST | `/ats/scan` | — | `{results[]}` | Scan ATS APIs for jobs |

---

## Smart Filter

| Method | Endpoint | Body | Response | Description |
|--------|----------|------|----------|-------------|
| POST | `/smart-filter/score` | `{post_id}` | `{score, factors{}}` | Score single post (0-10) |
| POST | `/smart-filter/score-all` | — | `{scored, total}` | Score all unscored posts |
| GET | `/smart-filter/stats` | — | `{distribution{}, avg, median}` | Score statistics |
| GET | `/smart-filter/top` | `?limit=20` | `{jobs[]}` | Top-scoring unapplied |

---

## Analytics

| Method | Endpoint | Response | Description |
|--------|----------|----------|-------------|
| GET | `/analytics/patterns` | `{response_rate, best_times, recommendations[]}` | Email outreach patterns |
| GET | `/analytics/conversion` | `{by_role{}, by_domain{}, by_company{}}` | Conversion rates |
| GET | `/followup/status` | `{overdue[], urgent[], waiting[], cold[]}` | Follow-up urgency |
| POST | `/followup/record` | `{outreach_id}` | Record follow-up sent |
| GET | `/email/ab-stats` | `{variants[]}` | Email variant performance |
| GET | `/dashboard/quality` | `{metrics{}}` | Comprehensive quality dashboard |

---

## Liveness

| Method | Endpoint | Body | Response | Description |
|--------|----------|------|----------|-------------|
| POST | `/liveness/check` | `{url}` | `{alive, status_code}` | Check if job URL is active |
| POST | `/liveness/scan` | — | `{checked, alive, dead}` | Batch check all posts |

---

## Company Intelligence

| Method | Endpoint | Body | Response | Description |
|--------|----------|------|----------|-------------|
| POST | `/company/scan` | `{company}` | `{health_score, signals[]}` | Company health signals |
| POST | `/company/connections` | `{company}` | `{connections[]}` | Find existing connections |

---

## Resume

| Method | Endpoint | Body | Response | Description |
|--------|----------|------|----------|-------------|
| GET | `/resumes/variants` | — | `{variants[]}` | List resume variants |
| POST | `/resumes/select` | `{role, content, domain, company}` | `{variant, reason}` | Best resume for job |

---

## Settings

| Method | Endpoint | Body | Response | Description |
|--------|----------|------|----------|-------------|
| GET | `/profile` | — | `{name, email, phone, ...}` | Read user profile |
| GET | `/settings/all` | — | `{profile{}, smtp{}, gemini{}}` | All settings |
| POST | `/settings/profile` | `{name, email, phone, linkedin, ...}` | `{status}` | Update profile |
| POST | `/settings/smtp` | `{smtp_host, smtp_port, smtp_user, smtp_password, from_email}` | `{status}` | Update SMTP config |
| POST | `/settings/gemini` | `{api_key}` | `{status}` | Update Gemini API key |
| POST | `/settings/test-email` | — | `{status, message}` | Send test email |
| POST | `/settings/upload-resume` | `multipart/form-data` | `{status, path}` | Upload resume PDF |
| GET | `/settings/resume-status` | — | `{exists, filename}` | Check resume file |
