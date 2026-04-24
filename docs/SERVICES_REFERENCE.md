# CareerKit Services Reference

Complete reference for every service, its functions, and how they integrate.

---

## 1. Orchestrator (`services/orchestrator.py`)

**Purpose**: Coordinates the full daily automation cycle.

| Function | Signature | Description |
|----------|-----------|-------------|
| `run_daily_cycle` | `(max_applications=500, run_scrapers=True)` | Full cycle: scrape → filter → apply → outreach |

**Called by**: `scripts/daily_run.py` (cron)

---

## 2. Scraper Service (`services/scraper_service.py`)

**Purpose**: Multi-source scraper orchestration and state management.

| Function | Signature | Description |
|----------|-----------|-------------|
| `_scraper_coordinator` | `(max_posts, sources)` | Main thread: spawns parallel scraper threads |
| `_run_linkedin_scraper` | `(page, conn, max_posts, callback)` | LinkedIn via Playwright browser |
| `_run_api_scraper` | `(source_key, conn, max_posts, callback)` | HTTP API scrapers |
| `_run_web_scraper` | `(source_key, conn, max_posts, callback)` | Browser-based scrapers |
| `_init_source_state` | `(source_name)` | Initialize per-source tracking |
| `_make_source_callback` | `(source_name)` | Create progress callback for source |

**State**: `scraper_state` dict with `running`, `started_at`, `sources{}`
**Thread safety**: `_scraper_lock` (threading.Lock)

---

## 3. Browser Service (`services/browser_service.py`)

**Purpose**: Playwright browser lifecycle with anti-detection.

| Function | Signature | Description |
|----------|-----------|-------------|
| `_browser_worker` | `()` | Dedicated thread owning all Playwright objects |
| `_run_on_browser_thread` | `(fn, *args, timeout=60)` | Execute function on browser thread |
| `_start_browser` | `()` | Launch Chromium with persistent profile + anti-detection |
| `_do_open_login` | `()` | Navigate to LinkedIn login page |
| `_do_check_login` | `()` | Verify session via cookie check |
| `_do_stop_browser` | `()` | Clean shutdown |

**State**: `browser_state` dict with `pw`, `browser`, `page`, `running`, `logged_in`, `status`
**Thread safety**: `_browser_cmd_q` (Queue) for command dispatch

**Anti-detection measures**:
- Persistent profile (saves cookies)
- Headed mode (not headless)
- Randomized User-Agent (Chrome 120-124)
- Viewport: 1920x1080
- Timezone/locale per region
- Geolocation mocking
- `--disable-blink-features=AutomationControlled`

---

## 4. Email Service (`services/email_service.py`)

**Purpose**: Gemini-powered email generation + Gmail SMTP sending.

| Function | Signature | Description |
|----------|-----------|-------------|
| `_generate_email_with_gemini` | `(post_data)` | Generate personalized cold email |
| `_send_email_smtp` | `(to, subject, body, attach_resume=True)` | Send via Gmail TLS |
| `_is_blocked_email` | `(email, company)` | Check against blocklist |
| `_bulk_generate_worker` | `(post_ids)` | Thread: generate drafts in batch |
| `_bulk_send_worker` | `(attach_resume)` | Thread: send all drafts |

**State**: `email_worker_state` dict with `running`, `task`, `current`, `total`, `results`, `log`
**Config**: `SMTP_CONFIG` dict loaded from `.env`
**Blocklist**: `EMAIL_BLOCKLIST = ["southguild"]`

**Gemini prompt includes**:
- Candidate: name, title, healthcare experience
- 5 projects: RAG pipeline, healthcare data, fax automation, biomedical ETL, Excel automation
- Rules: 120-180 words, no cliches, specific JD references, no placeholders

---

## 5. Auto-Apply Service (`services/auto_apply.py`)

**Purpose**: Automated job application engine.

| Function | Signature | Description |
|----------|-----------|-------------|
| `_auto_apply_worker` | `(max_applications)` | Main loop: fetch, rank, apply |
| `_linkedin_warm_up` | `(page, job)` | Simulate human reading before apply |
| `_apply_linkedin_easy_apply` | `(page, job)` | Fill and submit LinkedIn form |
| `_apply_email` | `(job)` | Generate and send email application |
| `_apply_redirect` | `(page, job)` | Open external URL |

**State**: `auto_apply_state` dict with `running`, `progress{applied, failed, skipped}`
**Constants**:
- `PLATFORM_BUDGETS`: LinkedIn 120/day, Email 180/day
- `RATE_LIMITS`: LinkedIn 45-120s, Email 10-30s
- `DailyCap.SAFE_LIMIT`: 25 Easy Apply/day

---

## 6. Smart Filter (`services/smart_filter.py`)

**Purpose**: Multi-factor job scoring (0-10 scale).

| Function | Signature | Description |
|----------|-----------|-------------|
| `score_job` | `(content, role, company, location, experience, domain, fit_score)` | Calculate score |
| `score_and_update` | `(conn, post_id)` | Score + write to DB |
| `score_all_unscored` | `(conn, limit)` | Batch score hiring posts |
| `filter_unapplied` | `(conn, threshold=5.0, limit=20)` | Top-scoring unapplied |
| `get_filter_stats` | `(conn)` | Score distribution stats |

**Scoring Factors**:
| Factor | Weight | Logic |
|--------|--------|-------|
| Role match | 3.0 | In TARGET_ROLES? |
| Domain relevance | 2.5 | High=3, Medium=2, Low=1 |
| Experience fit | 2.0 | Within 0-3 year range |
| Location preference | 1.5 | In ACTIVE_REGIONS |
| Tech stack match | 1.0 | Overlap with RESUME_SKILLS |

---

## 7. AI Tools (`services/ai_tools.py`)

**Purpose**: Gemini-powered career tools.

| Function | Signature | Description |
|----------|-----------|-------------|
| `evaluate_job` | `(jd_text)` | 7-part JD analysis with score/verdict |
| `generate_outreach` | `(company, role, recruiter, context)` | Personalized cold email |
| `deep_dive_company` | `(company, role)` | Company research report |
| `tailor_cv` | `(jd_text)` | ATS-optimized resume |
| `interview_prep` | `(company, role)` | Question banks + tips |

All use `_call_gemini()` with temperature 0.4-0.7.

---

## 8. ATS Scanner (`services/ats_scanner.py`)

**Purpose**: Scan company career pages via ATS APIs.

Supports: Greenhouse API, Lever API, Ashby API, web search fallback.
Config: `config/portals.yml` (37 tracked healthcare companies)

---

## 9. Email Finder (`email_finder/enrich.py`)

**Purpose**: Find contact emails via web scraping + search.

| Function | Signature | Description |
|----------|-----------|-------------|
| `find_emails_for_company` | `(company, website, location)` | Multi-strategy email lookup |
| `enrich_leads` | `(conn, max_leads, target, on_progress)` | Batch enrichment |

**Strategy**:
1. Scrape company website (contact, careers, team, about pages)
2. Extract emails via regex
3. Score emails (hr@, careers@ get bonus)
4. Filter junk (noreply, example.com)
5. Fallback: DuckDuckGo search

---

## 10. Pattern Analysis (`services/pattern_analysis.py`)

**Purpose**: Email outreach metrics and optimization.

| Function | Signature | Description |
|----------|-----------|-------------|
| `analyze_patterns` | `(conn)` | Response rates, best send times, recommendations |
| `get_conversion_rates` | `(conn)` | Conversion by role/domain/company |

---

## 11. Follow-up Cadence (`services/followup_cadence.py`)

**Purpose**: Track and schedule email follow-ups.

| Function | Signature | Description |
|----------|-----------|-------------|
| `analyze_followups` | `(conn)` | Categorize: overdue/urgent/waiting/cold |
| `record_followup` | `(conn, outreach_id)` | Log follow-up sent |

---

## 12. Company Signals (`services/company_signals.py`)

**Purpose**: Assess company health and hiring signals.

| Function | Signature | Description |
|----------|-----------|-------------|
| `scan_company` | `(company, conn)` | Health score + signal list |

---

## 13. Liveness (`services/liveness.py`)

**Purpose**: Check if job URLs are still active.

| Function | Signature | Description |
|----------|-----------|-------------|
| `check_url_liveness` | `(url)` | HEAD request check |
| `check_urls_batch` | `(urls)` | Parallel batch check |
| `check_and_update_db` | `(conn)` | Update is_live column for all posts |

---

## 14. Resume Selector (`services/resume_selector.py`)

| Function | Signature | Description |
|----------|-----------|-------------|
| `list_variants` | `()` | Available resume versions |
| `select_resume` | `(role, content, domain, company)` | Best variant for job |

---

## 15. Import Leads (`services/import_leads.py`)

| Function | Signature | Description |
|----------|-----------|-------------|
| `import_all` | `()` | Load leads from CSV/Excel in data/leads/ |

---

## 16. Humanize (`utils/humanize.py`)

**Purpose**: Anti-detection delay utilities.

| Function | Signature | Description |
|----------|-----------|-------------|
| `random_sleep` | `(min, max)` | Beta-skewed distribution |
| `short_pause` | `()` | 0.6-1.0s |
| `medium_pause` | `()` | 1.8-3.0s |
| `read_pause` | `(text_length)` | 200 WPM simulation |
| `between_applications` | `()` | 60-180s cooldown |
| `page_load_pause` | `()` | 2.5-5.0s |
| `human_type` | `(page, selector, text)` | Per-char delay 60-180ms |
| `human_click` | `(page, selector)` | Wait + click |
| `human_scroll` | `(page, direction, steps)` | Random scroll increments |

**DailyCap class**: Hard limit of 25 Easy Apply/day (safe zone < 15)

---

## 17. Extractors

### `extractors/pipeline.py` — Post Processing Pipeline

| Function | Signature | Description |
|----------|-----------|-------------|
| `process_single_post` | `(raw, dedup, conn, query, on_event, skip_fitness)` | Full extraction flow |

Flow: Dedup → Email extraction → LLM extraction → Domain scoring → Hiring detection → Fitness check → Insert

### `extractors/text.py` — Regex Extraction

| Function | Returns | Description |
|----------|---------|-------------|
| `extract_emails(text)` | `list[str]` | Regex email extraction |
| `extract_roles(text)` | `list[str]` | Keyword role matching |
| `extract_location(text)` | `str` | Pattern matching (cities, countries, remote) |
| `extract_experience(text)` | `str` | Year pattern matching |
| `normalize_experience(raw)` | `str` | Clean format |
| `score_domain_relevance(text)` | `str` | High/Medium/Low healthcare keyword count |
| `is_hiring_post(content)` | `bool` | Hiring intent detection |

### `extractors/fitness.py` — Job Fitness Check

| Function | Returns | Description |
|----------|---------|-------------|
| `is_relevant_role(role)` | `bool` | 20+ whitelist, 45+ blacklist |
| `experience_to_years(exp)` | `(min, max)` | Parse experience string |
| `is_good_fit(role, experience)` | `bool` | Relevant role + not too senior |

---

## 18. LLM Module

### `llm/client.py` — LLM Client (Singleton)

| Method | Signature | Description |
|--------|-----------|-------------|
| `ollama_available` | `()` | Check localhost:11434 |
| `call_ollama` | `(prompt, max_tokens, temp)` | POST to Ollama API |
| `call_gemini` | `(prompt, max_tokens, temp)` | google.genai client |

### `llm/extraction.py` — LLM Extraction

| Function | Returns | Description |
|----------|---------|-------------|
| `llm_extract(content)` | `dict` | Role, company, location, experience |
| `llm_extract_emails(content)` | `list[str]` | Find obfuscated emails |
| `llm_deep_analyze(content)` | `dict` | Full analysis with fit_score |

---

## Integration Map

```
orchestrator.run_daily_cycle()
    ├── scraper_service._scraper_coordinator()
    │   ├── browser_service._run_on_browser_thread()
    │   ├── api_scrapers.scrape_*()
    │   └── web_scrapers.scrape_*()
    │       └── extractors.pipeline.process_single_post()
    │           ├── extractors.text.extract_*()
    │           ├── extractors.fitness.is_good_fit()
    │           ├── llm.extraction.llm_extract()
    │           │   └── llm.client.call_ollama/gemini()
    │           └── db.insert_post() + db.insert_job()
    │
    ├── smart_filter.score_all_unscored()
    │
    ├── auto_apply._auto_apply_worker()
    │   ├── db.get_unapplied_jobs()
    │   ├── humanize.between_applications()
    │   └── db.log_application()
    │
    └── email_service._bulk_generate_worker()
        ├── email_service._generate_email_with_gemini()
        └── email_service._send_email_smtp()
```
