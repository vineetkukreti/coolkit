# CareerKit — System Diagrams

> Visual reference for all major system flows, state machines, and architecture.
> All diagrams use Mermaid syntax.

---

## 1. High-Level System Architecture

```mermaid
graph TD
    USER[User Browser] -->|HTTP :5173| REACT[React SPA<br/>Vite Dev Server]
    REACT -->|/api proxy| FASTAPI[FastAPI :8000]

    FASTAPI --> ROUTES[11 Route Modules]
    ROUTES --> SERVICES[Service Layer]

    SERVICES --> SQLITE[(SQLite<br/>WAL mode, thread-local)]
    SERVICES -->|Command Queue| PLAYWRIGHT[Playwright<br/>Chromium]
    SERVICES -->|HTTP :11434| OLLAMA[Ollama<br/>qwen2.5:7b]
    SERVICES -->|HTTPS| GEMINI[Gemini 2.5<br/>Flash Lite]
    SERVICES -->|SMTP :587| GMAIL[Gmail SMTP]
    SERVICES -->|IMAP :993| IMAP[Gmail IMAP]

    PLAYWRIGHT --> LINKEDIN[LinkedIn]
    PLAYWRIGHT --> JOBBOARDS[Job Board Sites]

    FASTAPI -->|Static mount /| FRONTEND_DIST[frontend/ dist]

    style SQLITE fill:#1e293b,stroke:#7c3aed
    style FASTAPI fill:#1e293b,stroke:#7c3aed
    style REACT fill:#1e293b,stroke:#7c3aed
```

---

## 2. Scraping Pipeline

```mermaid
flowchart TD
    START([Start Scraper]) --> COORD[_scraper_coordinator]
    COORD --> INIT[Initialize per-source state<br/>status: waiting]

    COORD --> LI_GROUP[LinkedIn Sources<br/>Sequential on browser thread]
    COORD --> API_GROUP[API Sources<br/>Parallel threads, no browser]
    COORD --> HTML_GROUP[Generic HTML Sources<br/>Parallel threads, requests+BS4]
    COORD --> WEB_GROUP[Web Sources<br/>Parallel threads, own Playwright]

    LI_GROUP --> |browser thread queue| LI_SEARCH[LinkedIn Search]
    LI_GROUP --> LI_FEED[LinkedIn Feed]
    LI_GROUP --> LI_HASH[Hashtag Feeds]
    LI_GROUP --> ENRICHER[Email Enricher]
    LI_GROUP --> DEEP[Deep Fetch]

    API_GROUP --> REMOTEOK[RemoteOK]
    API_GROUP --> HIMALAYAS[Himalayas]
    API_GROUP --> HN[HN Hiring]
    API_GROUP --> REMOTIVE[Remotive]
    API_GROUP --> ATS[Greenhouse / Lever / Ashby]
    API_GROUP --> MORE_API[+ 4 more API sources]

    HTML_GROUP --> GEN_HTML[Generic HTML Scraper<br/>config_sources.py definitions]

    WEB_GROUP --> GOOGLE[DuckDuckGo]
    WEB_GROUP --> WELLFOUND[Wellfound]
    WEB_GROUP --> YC[YC Jobs]
    WEB_GROUP --> MORE_WEB[+ 8 more browser sources]

    LI_SEARCH --> RAW[Raw Posts]
    API_GROUP --> RAW
    HTML_GROUP --> RAW
    WEB_GROUP --> RAW

    RAW --> DEDUP{Dedup Check<br/>post_url hash}
    DEDUP -->|duplicate| SKIP[Skip + emit callback]
    DEDUP -->|new| EXTRACT[Email Extraction<br/>extractors/text.py]
    EXTRACT --> LLM[LLM Extraction<br/>role, company, location]
    LLM --> DOMAIN[Domain Relevance Scoring]
    DOMAIN --> HIRING{Hiring Intent?}
    HIRING -->|no| SKIP
    HIRING -->|yes| INSERT[insert_posts to SQLite]
    INSERT --> CALLBACK[Emit progress event<br/>per-source callback]

    CALLBACK -->|2-5s poll| UI[Frontend UI Update]
```

---

## 3. LLM Extraction Chain

```mermaid
flowchart TD
    INPUT[Raw Post Text] --> CHECK_OLLAMA{Ollama running?<br/>localhost:11434}

    CHECK_OLLAMA -->|yes| OLLAMA[Ollama qwen2.5:7b<br/>temperature=0, max_tokens=80]
    CHECK_OLLAMA -->|no / timeout| GEMINI_CHECK

    OLLAMA --> PARSE_O{Valid JSON<br/>response?}
    PARSE_O -->|yes| RESULT[Structured Data]
    PARSE_O -->|empty / malformed| GEMINI_CHECK

    GEMINI_CHECK{Gemini API key<br/>configured?} -->|yes| GEMINI[Gemini 2.5 Flash Lite<br/>google.genai SDK]
    GEMINI_CHECK -->|no| REGEX

    GEMINI --> PARSE_G{Valid JSON<br/>response?}
    PARSE_G -->|yes| RESULT
    PARSE_G -->|error / empty| REGEX

    REGEX[Regex Fallback<br/>extractors/text.py] --> ROLES[extract_roles<br/>keyword match]
    REGEX --> LOCS[extract_location<br/>pattern match]
    REGEX --> EXPS[extract_experience<br/>year range patterns]
    REGEX --> EMAILS[extract_emails<br/>email regex]
    ROLES --> RESULT
    LOCS --> RESULT
    EXPS --> RESULT
    EMAILS --> RESULT

    RESULT --> OUTPUT["{ role, company, location,<br/>experience, tech_stack,<br/>fit_reasons, emails }"]
```

---

## 4. Email Outreach Pipeline

```mermaid
flowchart TD
    SELECT[Select Posts<br/>with emails + is_hiring] --> VALIDATE[Validate Emails<br/>format + MX lookup]
    VALIDATE -->|invalid domain| SKIP_INVALID[Skip]
    VALIDATE -->|valid| BLOCKLIST{Blocklist Check<br/>current employer, known bouncers}
    BLOCKLIST -->|blocked| SKIP_BLOCK[Skip]
    BLOCKLIST -->|ok| DEDUP{Already emailed<br/>this recipient?}
    DEDUP -->|yes| SKIP_DUP[Skip]
    DEDUP -->|no| GENERIC{Generic address?<br/>info@ hr@ careers@}
    GENERIC -->|yes| SKIP_GEN[Skip]
    GENERIC -->|no| VARIANT[Pick A/B Variant<br/>proof-first vs challenge-first]

    VARIANT --> REFERRAL{Referral connections<br/>at company?}
    REFERRAL -->|yes| ADD_CONTEXT[Add referral context<br/>to prompt]
    REFERRAL -->|no| GENERATE

    ADD_CONTEXT --> GENERATE[Generate Email<br/>Gemini 2.5 Flash Lite]
    GENERATE --> PARSE[Parse subject + body<br/>strip placeholders]
    PARSE --> DRAFT[Save as draft<br/>email_outreach table]
    DRAFT --> RECORD[Record A/B variant]

    DRAFT --> REVIEW{Human Review<br/>Edit / Approve}
    REVIEW --> SEND_WORKER[Bulk Send Worker<br/>background thread]

    SEND_WORKER --> SMTP[Gmail SMTP TLS:587<br/>+ resume PDF attachment]
    SMTP -->|success| MARK_SENT[status = sent<br/>sent_at = now]
    SMTP -->|failure| MARK_FAIL[status = failed<br/>error_type logged]

    MARK_SENT --> PIPELINE[Create pipeline_lead<br/>stage = applied]
    MARK_SENT --> DELAY[Anti-spam delay<br/>3-8s random]
    DELAY --> SEND_WORKER

    subgraph IMAP_POLL[IMAP Reply Detection<br/>every 5 minutes]
        IMAP_CHECK[Search INBOX<br/>FROM recipients] --> MATCH{Subject match?}
        MATCH -->|yes| CLASSIFY[Classify reply<br/>interested / auto_reply / rejection / info]
        CLASSIFY --> UPDATE_STATUS[Update outreach<br/>status = replied]
        UPDATE_STATUS --> UPDATE_PIPE[Update pipeline stage]
    end

    subgraph BOUNCE_DETECT[Bounce Detection]
        MAILER[Search mailer-daemon<br/>+ delivery failures] --> EXTRACT_ADDR[Extract bounced address]
        EXTRACT_ADDR --> MARK_BOUNCE[status = failed<br/>error_type = bounced]
    end

    subgraph FOLLOWUP[Auto Follow-up Worker]
        ANALYZE[analyze_followups<br/>find overdue entries] --> GEN_FU[Generate follow-up<br/>Gemini, 60-100 words]
        GEN_FU --> SEND_FU[Send via SMTP]
        SEND_FU --> RECORD_FU[record_followup<br/>increment count]
    end
```

---

## 5. Auto-Apply Pipeline

```mermaid
flowchart TD
    START([Start Auto-Apply]) --> FETCH[get_unapplied_jobs<br/>or filter_unapplied<br/>smart_score >= 5.0]
    FETCH --> LOOP{Next Job}

    LOOP -->|no more jobs| DONE([status = done])
    LOOP -->|stop flag set| STOPPED([status = stopped])
    LOOP -->|quota exhausted| DONE

    LOOP --> PRECHECK[should_apply checks]

    PRECHECK --> DUP{Already applied?}
    DUP -->|yes| SKIP[Skip] --> LOOP

    PRECHECK --> QUOTA{Daily quota<br/>remaining?}
    QUOTA -->|0| DONE

    PRECHECK --> SCORE_GATE{smart_score<br/>< 3.5?}
    SCORE_GATE -->|yes| SKIP_LOW[Skip: low score] --> LOOP

    PRECHECK --> LIVE{Liveness check<br/>is URL active?}
    LIVE -->|expired| SKIP_DEAD[Skip: expired] --> LOOP
    LIVE -->|active / unknown| TIER

    TIER[Determine Apply Tier] --> TIER_P{score >= 7.0}
    TIER_P -->|yes| PREMIUM[PREMIUM<br/>personalize + LLM answers<br/>60-150s delay]
    TIER_P -->|no| TIER_S{score >= 5.0}
    TIER_S -->|yes| STANDARD[STANDARD<br/>personalize, no LLM answers]
    TIER_S -->|no| TIER_B{score >= 3.5}
    TIER_B -->|yes| BASIC[BASIC<br/>template email, no LLM]

    PREMIUM --> METHOD
    STANDARD --> METHOD
    BASIC --> METHOD

    METHOD{Determine Method} --> M_LI{LinkedIn URL<br/>+ page available<br/>+ budget < 120?}
    M_LI -->|yes| EASY_APPLY[LinkedIn Easy Apply]
    M_LI -->|no| M_EMAIL{Has email<br/>+ budget < 180?}
    M_EMAIL -->|yes| EMAIL_APPLY[Email Application]
    M_EMAIL -->|no| REDIRECT[Redirect / Manual]

    EASY_APPLY --> WARMUP[Human warm-up<br/>scroll, read, wait]
    WARMUP --> FILL[Fill form fields<br/>phone, city, resume]
    FILL --> QUESTIONS[Handle text questions<br/>known answers + LLM]
    QUESTIONS --> DROPDOWNS[Handle dropdowns<br/>+ radio buttons]
    DROPDOWNS --> SUBMIT[Submit application]
    SUBMIT --> LOG

    EMAIL_APPLY --> GEN_EMAIL[Generate email<br/>Gemini personalized or template]
    GEN_EMAIL --> SELECT_RESUME[Select best resume variant]
    SELECT_RESUME --> SEND[send_email_with_resume<br/>SMTP + PDF]
    SEND --> FOLLOWUP_REG[Register for follow-up tracking]
    FOLLOWUP_REG --> LOG

    REDIRECT --> LOG[log_application<br/>to applications table]
    LOG --> COUNTERS[Update platform counts<br/>+ progress counters]
    COUNTERS --> RATE[Rate limit delay<br/>per platform]
    RATE --> LOOP
```

---

## 6. Smart Filter Scoring

```mermaid
flowchart LR
    subgraph DIMENSIONS["6 Scoring Dimensions (each 0-10)"]
        ROLE["Role Match<br/>weight: 0.25<br/>TARGET_ROLES lookup"]
        SKILL["Skill Match<br/>weight: 0.25<br/>RESUME_SKILLS overlap"]
        DOMAIN["Domain Relevance<br/>weight: 0.20<br/>DOMAIN_KEYWORDS count"]
        EXP["Experience Fit<br/>weight: 0.15<br/>2yr candidate vs range"]
        QUALITY["Quality Signals<br/>weight: 0.10<br/>JD depth, funding, red flags"]
        LOCATION["Location Fit<br/>weight: 0.05<br/>remote > India > APAC > US"]
    end

    ROLE --> SUM
    SKILL --> SUM
    DOMAIN --> SUM
    EXP --> SUM
    QUALITY --> SUM
    LOCATION --> SUM

    SUM[Weighted Sum<br/>0-10 scale] --> BLEND{LLM fit_score<br/>available?}
    BLEND -->|yes| BLENDED["0.7 * rule + 0.3 * LLM"]
    BLEND -->|no| FINAL

    BLENDED --> FINAL[Final Score]

    FINAL --> V1{">= 5.0"}
    V1 -->|yes| APPLY[APPLY]
    V1 -->|no| V2{">= 3.5"}
    V2 -->|yes| CONSIDER[CONSIDER]
    V2 -->|no| SKIP_V[SKIP]
```

---

## 7. Threading Model

```mermaid
graph TB
    subgraph MAIN["Main Thread — FastAPI / Uvicorn"]
        REQ[HTTP Request Handlers<br/>11 route modules]
        STARTUP[on_event startup<br/>start IMAP polling]
    end

    subgraph BT["Browser Thread — Dedicated, long-lived"]
        WORKER[_browser_worker loop<br/>reads from _browser_cmd_q]
        PW[Playwright Context<br/>persistent profile]
        PAGE[Browser Page]
        WORKER --> PW --> PAGE
    end

    subgraph SCRAPER_POOL["Scraper Threads — daemon, per-source"]
        LI_T[LinkedIn sources<br/>sequential via browser queue]
        API_T1[API scraper thread 1]
        API_T2[API scraper thread 2]
        API_TN[API scraper thread N]
        WEB_T1[Web scraper thread 1<br/>own Playwright instance]
        WEB_T2[Web scraper thread 2<br/>own Playwright instance]
    end

    subgraph EMAIL_THREADS["Email Threads — daemon"]
        GEN_T[Bulk generate worker]
        SEND_T[Bulk send worker]
        FU_T[Auto follow-up worker]
    end

    subgraph IMAP_T["IMAP Thread — daemon, persistent"]
        POLL[_imap_poll_worker<br/>every 5 minutes]
    end

    subgraph APPLY_T["Auto-Apply Thread — daemon"]
        ENGINE[AutoApplyEngine.run<br/>single instance]
    end

    subgraph ORCH_T["Orchestrator Thread — daemon"]
        DAILY[run_daily_cycle<br/>scrape + score + apply]
    end

    subgraph DB["Thread-Local SQLite"]
        DB1[(Connection per thread<br/>init_db creates new)]
    end

    REQ -->|"_browser_cmd_q.put()"| WORKER
    REQ -->|"threading.Thread()"| SCRAPER_POOL
    REQ -->|"threading.Thread()"| EMAIL_THREADS
    REQ -->|"threading.Thread()"| APPLY_T
    REQ -->|"threading.Thread()"| ORCH_T
    STARTUP -->|"threading.Thread()"| IMAP_T

    LI_T -->|"_run_on_browser_thread()"| WORKER

    SCRAPER_POOL --> DB1
    EMAIL_THREADS --> DB1
    APPLY_T --> DB1
    ORCH_T --> DB1
    IMAP_T --> DB1
```

---

## 8. Browser State Machine

```mermaid
stateDiagram-v2
    [*] --> stopped

    stopped --> starting : user clicks Connect / start_browser
    starting --> ready : _start_browser succeeds<br/>Playwright launched
    starting --> error : launch failure<br/>profile lock, crash

    ready --> stopped : user clicks Disconnect / stop_browser
    ready --> ready : check_login (logged_in=true)
    ready --> ready : open_login navigates to /login

    error --> stopped : _stop_browser cleanup
    error --> starting : user retries Connect

    note right of stopped
        pw=None, browser=None, page=None
        running=False, logged_in=False
    end note

    note right of ready
        running=True, page available
        logged_in checked via /feed URL
    end note
```

---

## 9. Scraper State Machine

```mermaid
stateDiagram-v2
    [*] --> idle

    idle --> running : _scraper_coordinator starts<br/>sources initialized

    state running {
        [*] --> per_source
        state per_source {
            waiting --> running_src : scraper thread begins
            running_src --> done : scraper completes<br/>posts inserted
            running_src --> error_src : exception caught
        }
    }

    running --> done : all threads joined<br/>at least one source succeeded
    running --> error : all threads joined<br/>every source failed

    done --> idle : next scrape can start
    error --> idle : next scrape can start

    note right of running
        scraper_state.sources = {
            "linkedin": {status, log, progress},
            "remoteok": {status, log, progress},
            ...
        }
    end note
```

---

## 10. Error Flow Diagram

```mermaid
flowchart TD
    subgraph BROWSER_ERR["Browser Errors"]
        BC[Browser crash / profile lock] --> CLEAN[Clean Singleton* lock files]
        CLEAN --> RELAUNCH[Relaunch Playwright]
        RELAUNCH -->|success| READY[status = ready]
        RELAUNCH -->|fail| ERR_STATE[status = error<br/>user can retry]
    end

    subgraph LLM_ERR["LLM Errors"]
        OT[Ollama timeout / not running] --> GF[Gemini fallback]
        GF -->|API error or no key| RF[Regex fallback<br/>extract_roles + extract_location]
        GF -->|success| STRUCTURED[Structured extraction]
        RF --> PARTIAL[Partial extraction<br/>best effort]
    end

    subgraph SMTP_ERR["SMTP Errors"]
        AUTH[SMTPAuthenticationError] --> LOG_AUTH[Log error<br/>email features disabled]
        REFUSED[SMTPRecipientsRefused] --> MARK_FAIL_E[status=failed<br/>error_type=invalid_address]
        TIMEOUT_E[Socket timeout] --> MARK_FAIL_T[status=failed<br/>error_type=timeout]
        DISCONNECT[SMTPServerDisconnected] --> MARK_FAIL_D[status=failed<br/>error_type=connection]
    end

    subgraph SCRAPER_ERR["Scraper Errors"]
        S403[HTTP 403 / blocked] --> SKIP_SRC[Mark source error<br/>continue others]
        SNET[Network timeout] --> SKIP_SRC
        SDOM[DOM selector miss] --> EMPTY[0 posts found<br/>source = done]
    end

    subgraph DB_ERR["SQLite Errors"]
        LOCK[Database locked] --> WAL[WAL mode + thread-local conn]
        WAL --> RETRY[Auto-retry via init_db]
        OPCOL[Column not found] --> ALTER[ALTER TABLE ADD COLUMN<br/>e.g. smart_score]
    end
```

---

## 11. Daily Automation Cycle

```mermaid
sequenceDiagram
    participant USER as User / Cron
    participant ORCH as Orchestrator
    participant SCRAPER as Scraper Service
    participant FILTER as Smart Filter
    participant APPLY as AutoApplyEngine
    participant DB as SQLite

    USER->>ORCH: start_daily_cycle(max=500)
    activate ORCH
    ORCH->>ORCH: status = starting

    rect rgb(30, 30, 50)
    Note over ORCH,SCRAPER: Phase 1: Scraping
    ORCH->>ORCH: status = scraping
    ORCH->>SCRAPER: _scraper_coordinator(API sources)
    SCRAPER-->>DB: insert_posts (parallel threads)
    SCRAPER-->>ORCH: API scraping complete

    alt Browser running
        ORCH->>SCRAPER: _scraper_coordinator(browser sources)
        SCRAPER-->>DB: insert_posts
        SCRAPER-->>ORCH: Browser scraping complete
    else Browser not running
        ORCH->>ORCH: Skip browser scrapers
    end
    end

    rect rgb(30, 40, 30)
    Note over ORCH,FILTER: Phase 1.5: Scoring
    ORCH->>ORCH: status = scoring
    ORCH->>FILTER: score_all_unscored(limit=500)
    FILTER-->>DB: UPDATE posts SET smart_score
    FILTER-->>ORCH: scored N posts (APPLY/CONSIDER/SKIP)
    end

    rect rgb(40, 30, 30)
    Note over ORCH,APPLY: Phase 2: Auto-Apply
    ORCH->>ORCH: status = applying
    ORCH->>FILTER: filter_unapplied(threshold=5.0)
    FILTER-->>ORCH: N jobs above threshold
    ORCH->>APPLY: engine.run(max_applications=target)
    APPLY-->>DB: log_application per job
    APPLY-->>ORCH: apply cycle complete
    end

    rect rgb(30, 30, 40)
    Note over ORCH,DB: Phase 3: Report
    ORCH->>ORCH: status = reporting
    ORCH->>DB: get_today_quota + get_application_stats
    DB-->>ORCH: applied/failed/skipped counts
    ORCH->>ORCH: Emit report event
    end

    ORCH->>ORCH: status = done, running = false
    deactivate ORCH
```

---

## 12. Frontend Component Tree

```mermaid
graph TD
    APP[App] --> TOAST[ToastProvider]
    TOAST --> SHELL[AppShell]

    SHELL --> CHECK{Checking?}
    CHECK -->|yes| SPINNER[Loading Spinner]
    CHECK -->|no| GATE{Connected?}

    GATE -->|hard disconnect| CG[ConnectGate<br/>Launch + Login flow]
    GATE -->|soft expiry| BANNER[Session Expired Banner<br/>+ full app]
    GATE -->|connected| FULL[Full App Layout]

    FULL --> SIDEBAR[Sidebar<br/>navigation links]
    FULL --> BBAR[BrowserBar<br/>status dot + controls]
    FULL --> ROUTER[React Router]

    ROUTER --> DASH[/ Dashboard<br/>stats + quick actions]
    ROUTER --> FIND[/find FindJobs<br/>tabs: search, scraper, posts]
    ROUTER --> APPLY_P[/apply ApplyPage<br/>tabs: engine, history]
    ROUTER --> OUTREACH[/outreach OutreachPage<br/>tabs: email, leads]
    ROUTER --> PIPE[/pipeline Pipeline<br/>CRM kanban]
    ROUTER --> PIPE_D[/pipeline/:id LeadDetail]
    ROUTER --> INSIGHTS[/insights InsightsPage<br/>tabs: analytics, quality]
    ROUTER --> TOOLS[/ai-tools AITools]
    ROUTER --> SKILLS[/skills SkillsIntelligence]
    ROUTER --> SETTINGS[/settings SettingsPage]
```

---

## 13. Source Engine Decision Tree

```mermaid
flowchart TD
    SRC[Source key from config] --> CUSTOM{In CUSTOM_SOURCES?}

    CUSTOM -->|yes| CGROUP{Source group?}
    CGROUP -->|linkedin group| LI_ENGINE[LinkedIn Engine<br/>browser thread, sequential<br/>Playwright on main browser]
    CGROUP -->|api group / ats / multi| API_ENGINE[API Engine<br/>dedicated thread, HTTP only<br/>scrape_remoteok, scrape_himalayas, etc.]
    CGROUP -->|browser group| WEB_ENGINE[Web Engine<br/>dedicated thread, own Playwright<br/>anti-detection, headed mode]

    CUSTOM -->|no| GEN_API{In GENERIC_API_SOURCES?}
    GEN_API -->|yes| GAPI_ENGINE[Generic API Engine<br/>scrape_generic_api<br/>JSON endpoint + field mapping]
    GEN_API -->|no| GEN_HTML{In GENERIC_HTML_SOURCES?}
    GEN_HTML -->|yes| GHTML_ENGINE[Generic HTML Engine<br/>scrape_generic_html<br/>requests + BeautifulSoup + CSS selectors]
    GEN_HTML -->|no| UNKNOWN[Source not found<br/>skipped by coordinator]
```

---

## 14. Email Finder Strategy Chain

```mermaid
flowchart TD
    INPUT["Company name<br/>+ optional: website, author_name, location"] --> DOMAIN_R[Resolve domain<br/>extract from website URL]
    DOMAIN_R --> INFER{Domain found?}
    INFER -->|no| INFER_D[Infer domain from company name<br/>e.g. Acme Corp -> acme.com]
    INFER -->|yes| S1

    INFER_D --> S1

    S1["Strategy 1: Hunter.io API<br/>(if domain + API key configured)<br/>highest confidence"] --> S2

    S2["Strategy 2: Website Scraping<br/>(if website URL provided)<br/>scrape contact/careers pages"] --> S3

    S3["Strategy 3: DuckDuckGo Search<br/>company + email + location keywords"] --> COUNT{Found >= 2<br/>emails?}

    COUNT -->|yes| VERIFY_STEP
    COUNT -->|no| S4

    S4["Strategy 4: Google Search Fallback<br/>company + contact email query"] --> VERIFY_STEP

    VERIFY_STEP --> S5{Author name<br/>+ domain available?}
    S5 -->|yes| PERSON["Strategy 5: Person Patterns<br/>first.last@, f.last@, firstl@<br/>up to 8 guesses"]
    S5 -->|no| S6_CHECK

    S6_CHECK{Any emails<br/>found so far?}
    S6_CHECK -->|no + domain| GENERIC["Strategy 6: Generic Patterns<br/>info@, hr@, careers@, jobs@"]
    S6_CHECK -->|yes| VERIFY

    PERSON --> VERIFY[Verify pattern guesses<br/>MX + SMTP check, batch of 8]
    GENERIC --> VERIFY

    VERIFY --> COLLECT[Collect all unique emails]
    COLLECT --> SCORE_SORT[Score and sort<br/>by confidence]
    SCORE_SORT --> BEST["Return top 3 emails<br/>{email, source, score, verified}"]
```

---

## 15. Data Lifecycle

```mermaid
flowchart LR
    EXTERNAL["100+ External Sources<br/>LinkedIn, APIs, HTML, Browser"] -->|scrape| RAW[Raw Post Data]

    RAW -->|dedup by URL hash| NEW[New Posts]
    NEW -->|LLM / regex| EXTRACTED[Extracted Fields<br/>role, company, location, experience]
    EXTRACTED -->|rule-based + LLM blend| SCORED[Smart Score<br/>0-10, 6 dimensions]

    SCORED -->|INSERT| DB[(SQLite<br/>posts + jobs tables)]

    DB -->|filter >= 5.0| APPLY_QUEUE[Apply Queue]
    APPLY_QUEUE -->|Easy Apply / Email / Redirect| APPLIED[applications table<br/>status, method, timestamp]

    DB -->|filter has email + is_hiring| EMAIL_QUEUE[Email Queue]
    EMAIL_QUEUE -->|Gemini generate + SMTP send| OUTREACH[email_outreach table<br/>draft -> sent -> replied]

    OUTREACH -->|pipeline_leads| PIPELINE[Pipeline CRM<br/>applied -> replied -> interview -> offer]

    DB -->|skills analysis| INTEL[skill_mentions<br/>+ skill_demand_summary]

    DB -->|display| UI[React Frontend<br/>Dashboard, Posts, Pipeline, Insights]
    APPLIED -->|display| UI
    OUTREACH -->|display| UI
    PIPELINE -->|display| UI
    INTEL -->|display| UI
```

---

## 16. Skills Intelligence Analysis Flow

```mermaid
flowchart TD
    START([start_analysis]) --> P1

    subgraph P1["Phase 1: Regex Scan"]
        LOAD[Load all jobs<br/>with post content] --> SCAN[regex_extract_skills<br/>TECH_TAXONOMY patterns]
        SCAN --> EDU[regex_extract_education<br/>degree + field + requirement]
        EDU --> SAVE1[INSERT skill_mentions<br/>+ education_demands]
    end

    P1 --> USE_LLM{use_llm=true?}

    USE_LLM -->|yes| P2
    USE_LLM -->|no| P3

    subgraph P2["Phase 2: LLM Enrichment (optional)"]
        PICK[Pick top N jobs<br/>by smart_score] --> GEMINI_EXTRACT[Gemini: extract skills JSON<br/>structured output]
        GEMINI_EXTRACT --> MERGE[INSERT OR REPLACE<br/>skill_mentions source=llm]
    end

    P2 --> P3

    subgraph P3["Phase 3: Aggregation"]
        AGG[Rebuild skill_demand_summary<br/>COUNT per skill, percentage,<br/>required vs preferred] --> DONE_A[Analysis complete]
    end

    DONE_A --> DASHBOARD[Dashboard Data<br/>top skills by category<br/>education stats<br/>experience distribution]

    DONE_A --> GAP[Gap Analysis<br/>RESUME_SKILLS vs market demands<br/>strengths, gaps, underutilized<br/>readiness score]

    DONE_A --> TRENDS[Trend Data<br/>Gemini-powered, 24h cache<br/>hot tools, rising models]
```

---

## See Also

- [Architecture](ARCHITECTURE.md) -- system design, component interactions, threading
- [Services Reference](SERVICES_REFERENCE.md) -- every service, function, and constant
- [API Reference](API_REFERENCE.md) -- all REST endpoints
- [Database Schema](DATABASE_SCHEMA.md) -- all tables, relationships, key queries
