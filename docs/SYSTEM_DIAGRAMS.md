# CareerKit System Diagrams

## 1. High-Level System Architecture

```mermaid
graph TB
    subgraph Frontend["Frontend (React + Vite)"]
        UI[Dashboard UI]
        API_CLIENT[API Client]
    end

    subgraph Backend["Backend (FastAPI)"]
        ROUTES[Route Handlers]
        SERVICES[Service Layer]
        SCRAPERS[Scraper Engine]
        LLM_ENGINE[LLM Engine]
        EMAIL_SVC[Email Service]
        AUTO_APPLY[Auto-Apply Engine]
    end

    subgraph External["External Systems"]
        LINKEDIN[LinkedIn]
        JOB_BOARDS[100+ Job Boards]
        OLLAMA[Ollama Local LLM]
        GEMINI[Gemini API]
        GMAIL[Gmail SMTP]
    end

    subgraph Storage["Storage"]
        SQLITE[(SQLite DB)]
        BROWSER_PROFILE[Browser Profiles]
        ENV[.env Config]
    end

    UI --> API_CLIENT
    API_CLIENT -->|HTTP /api/*| ROUTES
    ROUTES --> SERVICES
    SERVICES --> SCRAPERS
    SERVICES --> LLM_ENGINE
    SERVICES --> EMAIL_SVC
    SERVICES --> AUTO_APPLY

    SCRAPERS -->|Playwright| LINKEDIN
    SCRAPERS -->|HTTP| JOB_BOARDS
    LLM_ENGINE -->|Primary| OLLAMA
    LLM_ENGINE -->|Fallback| GEMINI
    EMAIL_SVC --> GMAIL
    AUTO_APPLY -->|Playwright| LINKEDIN

    SERVICES --> SQLITE
    SCRAPERS --> BROWSER_PROFILE
    SERVICES --> ENV
```

## 2. Data Flow — Scraping Pipeline

```mermaid
flowchart TD
    START([User clicks Start Scraper]) --> DISPATCH{Source Type?}

    DISPATCH -->|LinkedIn| BROWSER[Playwright Browser Thread]
    DISPATCH -->|API Source| HTTP[HTTP Client Thread]
    DISPATCH -->|HTML Source| SOUP[BeautifulSoup Thread]
    DISPATCH -->|Browser Source| PLAY2[Playwright Own Thread]

    BROWSER --> JS[Inject extract_posts.js]
    JS --> RAW_POSTS[Raw Post Data]

    HTTP --> JSON_PARSE[Parse JSON Response]
    JSON_PARSE --> RAW_POSTS

    SOUP --> CSS[CSS Selector Extraction]
    CSS --> RAW_POSTS

    PLAY2 --> DOM[DOM Extraction]
    DOM --> RAW_POSTS

    RAW_POSTS --> PIPELINE[Processing Pipeline]

    subgraph PIPELINE_DETAIL["extractors/pipeline.py"]
        DEDUP{Dedup Check} -->|Duplicate| SKIP[Skip]
        DEDUP -->|New| EMAIL_EXT[Extract Emails]
        EMAIL_EXT --> LLM_EXT[LLM Extraction]
        LLM_EXT --> DOMAIN[Score Domain Relevance]
        DOMAIN --> HIRING[Detect Hiring Intent]
        HIRING --> FITNESS{Fitness Check}
        FITNESS -->|Bad Fit| SKIP
        FITNESS -->|Good Fit| INSERT[Insert to DB]
    end

    PIPELINE --> DEDUP
    INSERT --> DB[(SQLite)]
    SKIP --> CALLBACK[Emit Progress Event]
    INSERT --> CALLBACK
    CALLBACK --> UI_UPDATE[Update UI via Polling]
```

## 3. Data Flow — Email Outreach

```mermaid
flowchart TD
    READY[Outreach-Ready Posts] --> GENERATE{Generate Emails}

    GENERATE -->|Bulk| WORKER1[Email Worker Thread]
    GENERATE -->|Single| SINGLE[Single Generation]

    WORKER1 --> GEMINI[Gemini 2.5 Flash-Lite]
    SINGLE --> GEMINI

    subgraph GEMINI_PROMPT["Gemini System Prompt"]
        PROFILE[Candidate Profile]
        PROJECTS[5 Past Projects]
        RULES[Rules: 120-180 words<br/>No cliches, specific refs]
    end

    GEMINI --> DRAFT[Save as Draft]
    DRAFT --> REVIEW{Human Review}

    REVIEW -->|Edit| UPDATE[Update Draft]
    REVIEW -->|Approve| SEND_QUEUE[Send Queue]

    SEND_QUEUE --> BLOCKLIST{Blocklist Check}
    BLOCKLIST -->|Blocked| SKIP[Skip]
    BLOCKLIST -->|OK| SMTP[Gmail SMTP TLS:587]

    SMTP --> ATTACH{Attach Resume?}
    ATTACH -->|Yes| PDF[Attach PDF]
    ATTACH -->|No| SEND

    PDF --> SEND[Send Email]
    SEND --> LOG[Log to email_outreach]
    LOG --> PIPELINE[Create Pipeline Lead]
```

## 4. Data Flow — Auto-Apply

```mermaid
flowchart TD
    START([Start Auto-Apply]) --> FETCH[Fetch Unapplied Jobs<br/>Limit: 600]
    FETCH --> RANK[Rank by fit_score + domain_relevance]
    RANK --> LOOP{Next Job}

    LOOP -->|Done| COMPLETE([Complete])
    LOOP -->|Job| BUDGET{Platform Budget OK?}

    BUDGET -->|Exceeded| SKIP_PLATFORM[Skip Platform]
    BUDGET -->|OK| RATE{Rate Limit Delay}

    RATE --> METHOD{Apply Method?}

    METHOD -->|LinkedIn Easy Apply| WARM[Human Warm-up<br/>Scroll, Read, Wait]
    WARM --> FILL[Fill Form Fields]
    FILL --> SUBMIT[Submit Application]

    METHOD -->|Email| DRAFT[Generate Email]
    DRAFT --> SMTP_SEND[Send via SMTP]

    METHOD -->|Redirect| OPEN[Open URL in Browser]

    SUBMIT --> LOG[Log to applications]
    SMTP_SEND --> LOG
    OPEN --> LOG

    LOG --> QUOTA[Update Daily Quota]
    QUOTA --> LOOP

    SKIP_PLATFORM --> LOOP
```

## 5. LLM Extraction Chain

```mermaid
flowchart TD
    TEXT[Raw Post Text] --> TRY_OLLAMA{Ollama Available?}

    TRY_OLLAMA -->|Yes| OLLAMA[Ollama qwen2.5:7b<br/>localhost:11434]
    TRY_OLLAMA -->|No| TRY_GEMINI

    OLLAMA --> PARSE1{Valid JSON?}
    PARSE1 -->|Yes| RESULT[Extracted Data]
    PARSE1 -->|No| TRY_GEMINI

    TRY_GEMINI[Gemini 2.5 Flash-Lite] --> PARSE2{Valid JSON?}
    PARSE2 -->|Yes| RESULT
    PARSE2 -->|No| REGEX

    REGEX[Regex Fallback] --> ROLE[extract_roles: keyword match]
    REGEX --> LOC[extract_location: pattern match]
    REGEX --> EXP[extract_experience: year patterns]
    ROLE --> RESULT
    LOC --> RESULT
    EXP --> RESULT

    RESULT --> OUTPUT["{ role, company,<br/>location, experience,<br/>tech_stack, fit_reasons }"]
```

## 6. Threading Model

```mermaid
graph TB
    subgraph MAIN["Main Thread (FastAPI/Uvicorn)"]
        FASTAPI[Request Handler]
    end

    subgraph BROWSER_THREAD["Browser Thread (Dedicated)"]
        PW[Playwright Engine]
        PAGE[Browser Page]
        CMD_Q[Command Queue]
    end

    subgraph DAEMON_THREADS["Daemon Threads"]
        SCRAPER_T[Scraper Threads<br/>1 per source]
        EMAIL_T[Email Worker<br/>Singleton]
        APPLY_T[Auto-Apply Worker<br/>Singleton]
    end

    subgraph DB_THREADS["Thread-Local DB"]
        DB1[SQLite Conn 1]
        DB2[SQLite Conn 2]
        DB3[SQLite Conn N]
    end

    FASTAPI -->|Put command| CMD_Q
    CMD_Q -->|Execute| PW
    PW --> PAGE

    FASTAPI -->|Spawn| SCRAPER_T
    FASTAPI -->|Spawn| EMAIL_T
    FASTAPI -->|Spawn| APPLY_T

    SCRAPER_T -->|Commands via Queue| CMD_Q
    APPLY_T -->|Commands via Queue| CMD_Q

    SCRAPER_T --> DB1
    EMAIL_T --> DB2
    APPLY_T --> DB3
```

## 7. Frontend Page Flow

```mermaid
flowchart TD
    LAUNCH([Open App]) --> CHECK{Backend<br/>Reachable?}

    CHECK -->|No| UNREACHABLE[Error Screen]
    CHECK -->|Yes| BROWSER{Browser<br/>Running?}

    BROWSER -->|No| CONNECT_GATE[ConnectGate:<br/>Launch Browser]
    BROWSER -->|Yes| LOGIN{LinkedIn<br/>Logged In?}

    LOGIN -->|No| LOGIN_PROMPT[ConnectGate:<br/>Login to LinkedIn]
    LOGIN -->|Yes| SETUP{First Time?}

    SETUP -->|Yes| ONBOARDING[4-Step Wizard]
    SETUP -->|No| DASHBOARD

    ONBOARDING --> DASHBOARD[Dashboard]

    DASHBOARD --> SEARCH[Job Search]
    DASHBOARD --> POSTS[Posts DB]
    DASHBOARD --> SCRAPER[Scraper]
    DASHBOARD --> AUTO[Auto-Apply]
    DASHBOARD --> EMAIL[Email Outreach]
    DASHBOARD --> PIPE[Pipeline CRM]
    DASHBOARD --> LEADS[Startup Leads]
    DASHBOARD --> ANALYTICS[Analytics]
    DASHBOARD --> HISTORY[App History]
    DASHBOARD --> TOOLS[AI Tools]
    DASHBOARD --> SETTINGS[Settings]

    PIPE --> DETAIL[Lead Detail]
```

## 8. Source Distribution

```
100+ Job Sources
├── LinkedIn Family (6)
│   ├── LinkedIn Search
│   ├── LinkedIn Feed
│   ├── LinkedIn Hashtags
│   ├── LinkedIn Deep Fetch
│   ├── LinkedIn Career Links
│   └── LinkedIn Email Enricher
│
├── API Sources — No Browser (12)
│   ├── RemoteOK
│   ├── Himalayas
│   ├── HN Jobs
│   ├── Remotive
│   ├── Working Nomads
│   ├── WWR RSS
│   ├── USAJobs
│   ├── SmartRecruiters
│   └── Euraxess
│
├── ATS Aggregators (3)
│   ├── Greenhouse API
│   ├── Lever API
│   └── Ashby API
│
├── Browser Sources (10)
│   ├── Indeed
│   ├── Wellfound
│   ├── YC Jobs
│   ├── Naukri
│   ├── Arc.dev
│   └── ...
│
└── HTML Sources — BeautifulSoup (62+)
    ├── Remote: Remote.co, NoDesk, FlexJobs
    ├── AI/ML: AIJobs, AIMLJobs, KDNuggets
    ├── Regional: TokyoDev, JapanDev, Bayt, Naukri
    ├── Academic: Nature, ResearchGate, Euraxess
    └── General: Monster, Dice, Glassdoor
```

## 9. Smart Filter Scoring

```
Score (0-10) = weighted sum of:

┌─────────────────────────────┬────────┬───────────────────────────────┐
│ Factor                      │ Weight │ Logic                         │
├─────────────────────────────┼────────┼───────────────────────────────┤
│ Role Match                  │  3.0   │ Is role in TARGET_ROLES?      │
│ Domain Relevance            │  2.5   │ High=3, Medium=2, Low=1       │
│ Experience Fit              │  2.0   │ Within 0-3 year range?        │
│ Location Preference         │  1.5   │ In ACTIVE_REGIONS?            │
│ Tech Stack Match            │  1.0   │ Overlap with RESUME_SKILLS    │
└─────────────────────────────┴────────┴───────────────────────────────┘

Threshold: score >= 5.0 → Auto-apply candidate
           score >= 7.0 → Priority application
           score < 3.0  → Skip
```

## 10. Daily Automation Cycle

```
┌─────────────────────────────────────────────────────┐
│              DAILY CRON (8 AM Weekdays)              │
│                scripts/daily_run.py                  │
└───────────────────────┬─────────────────────────────┘
                        │
                        v
┌───────────────────────────────────────────────────────┐
│              ORCHESTRATOR                              │
│              services/orchestrator.py                  │
│                                                       │
│  1. SCRAPE  ─────── 100+ sources in parallel         │
│      │              ├── LinkedIn (browser)             │
│      │              ├── APIs (HTTP)                    │
│      │              └── HTML (BeautifulSoup)           │
│      │                                                │
│  2. EXTRACT ─────── LLM + Regex extraction           │
│      │              ├── Ollama (local)                 │
│      │              └── Gemini (fallback)              │
│      │                                                │
│  3. FILTER  ─────── Smart scoring (0-10)             │
│      │              ├── Role relevance                 │
│      │              ├── Domain fit                     │
│      │              └── Experience match               │
│      │                                                │
│  4. APPLY   ─────── Auto-apply engine                │
│      │              ├── LinkedIn Easy Apply            │
│      │              ├── Email applications             │
│      │              └── Rate-limited + humanized       │
│      │                                                │
│  5. OUTREACH ────── Cold email generation            │
│                     ├── Gemini-personalized emails     │
│                     └── Gmail SMTP send                │
└───────────────────────────────────────────────────────┘
                        │
                        v
┌──────────────────────────────────────────────┐
│  EMAIL ENRICHMENT CRON (Every 2 Hours)        │
│  scripts/run_email_finder.sh                  │
│  ├── Find emails: web scrape + DuckDuckGo     │
│  └── Verify: SMTP ping (every 12 hours)       │
└──────────────────────────────────────────────┘
```
