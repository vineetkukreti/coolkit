# CareerKit -- Project Context

## What Is This?

Full-stack job hunting automation: scrapes 120+ job sources, extracts structured data via LLM, scores/ranks jobs, auto-applies, and sends personalized cold emails. Built for a solo healthcare AI engineer job search.

## Quick Reference

| Component | Details |
|-----------|---------|
| Backend | FastAPI on port 8000 (`backend/server.py`) |
| Frontend | React 19 + Vite 8 on port 5173 (`frontend-src/`) |
| Database | SQLite (WAL) at `data/linkedin_jobs.db` (schema in `backend/db.py`) |
| Config | Secrets in `config/.env`, profile in `backend/config.py`, sources in `backend/config_sources.py` |
| Launch | `./run.sh` (or `--prod`, `--back`, `--front`) |

## Architecture

```
React SPA --> /api proxy --> FastAPI --> {Playwright, Ollama/Gemini, SQLite, Gmail SMTP}
```

- **Threading**: Dedicated browser thread (Playwright Queue), daemon threads for scraping/email/auto-apply, thread-local SQLite connections
- **LLM chain**: Ollama (qwen2.5:7b, local) --> Gemini 2.5 Flash-Lite (API fallback) --> Regex (last resort)
- **Dedup**: 4-layer -- URL unique index, content_hash (SHA256), normalized prefix match, LLM dedup

## Key Files

| Area | Files |
|------|-------|
| Routes (11) | `backend/routes/{jobs,scraper,browser,posts,email,pipeline,leads,settings,tools,auto_apply,skills_intel}.py` |
| Services (21) | `backend/services/{scraper_service,browser_service,email_service,auto_apply,smart_filter,ai_tools,orchestrator,ats_scanner,company_signals,email_ab_test,followup_cadence,import_leads,liveness,logger,pattern_analysis,quality_dashboard,referral_detector,resume_selector,skills_intel}.py` |
| Scrapers | `backend/scrapers/{linkedin_jobs,linkedin_posts,linkedin_feed,linkedin_hashtags,linkedin_deep,api_scrapers,web_scrapers,generic_scrapers,web,helpers}.py` |
| Extraction | `backend/extractors/{pipeline,text,fitness}.py`, `backend/llm/{client,extraction}.py` |
| Email Finder | `backend/email_finder/{strategies,enrich,cron}.py` -- 7-strategy email discovery |
| Frontend Pages (19) | `frontend-src/src/pages/{Dashboard,FindJobs,ApplyPage,OutreachPage,InsightsPage,Pipeline,LeadDetail,AITools,SkillsIntelligence,Settings,JobSearch,Scraper,Posts,EmailOutreach,EmailAnalytics,AutoApply,AppHistory,QualityDashboard,StartupLeads}.jsx` |
| Frontend Components (7) | `frontend-src/src/components/{Sidebar,BrowserBar,ConnectGate,Toast,FilterBar,PageTabs,Onboarding}.jsx` |
| Frontend API | `frontend-src/src/lib/api.js` -- 75+ endpoint functions |
| Source Config | `backend/config_sources.py` -- 120+ sources across 20 groups |

## Conventions

- Routes are thin -- delegate to services, return `{status, message, ...}`
- Thread safety: `threading.Lock()` + state dicts for background workers
- Browser commands go through `_browser_cmd_q` Queue (all Playwright on one thread)
- Frontend: polling (2-5s intervals), hooks + Context (no Redux), dark theme, purple accent `#A855F7`
- Toast notifications via `useToast()` hook from `ToastProvider` context
- Tab state persisted via URL search params (`?tab=scraper`)

## Error Patterns

- **Routes**: try/except returning `JSONResponse(status_code=..., content={status, message})`
- **Services**: return dicts with status/error keys, or raise exceptions caught by routes
- **DB**: WAL mode prevents most locks; `check_same_thread=False` with thread-local connections
- **Frontend**: Toast notifications for user-facing errors; loading states on async operations
- **Common failures**: browser not connected (start browser first), Ollama down (falls back to Gemini), SMTP auth (check config/.env), scraper 403/429 (per-source error isolation)

## Don't Touch

- `config/.env` -- real API keys and SMTP credentials
- `data/browser_profiles/` -- persistent LinkedIn login session
- `backend/config.py` PROFILE section -- real personal data

## Documentation

| Doc | Purpose |
|-----|---------|
| `docs/ARCHITECTURE.md` | System design, component interactions, threading |
| `docs/API_REFERENCE.md` | All REST endpoints with curl examples |
| `docs/DATABASE_SCHEMA.md` | All tables, relationships, key queries |
| `docs/SERVICES_REFERENCE.md` | Every service, function, and constant |
| `docs/SETUP_GUIDE.md` | Installation, configuration, usage |
| `docs/CONFIGURATION.md` | All config options, env vars, source setup |
| `docs/SYSTEM_DIAGRAMS.md` | 16 Mermaid diagrams for all data flows |
| `docs/AI_CONTEXT.md` | Comprehensive AI assistant context |
| `docs/CONTRIBUTING.md` | Dev workflow, PR process, adding scrapers/endpoints |
| `docs/SECURITY.md` | Credential handling, sensitive data, ethics |
| `docs/TROUBLESHOOTING.md` | Common issues, debugging, reset procedures |
| `docs/CHANGELOG.md` | Version history and release notes |

## See Also

- `docs/AI_CONTEXT.md` for the exhaustive deep-dive (architecture decisions, recovery patterns, step-by-step common tasks)
- `frontend-src/src/lib/api.js` for the complete frontend API surface
- `backend/config_sources.py` for the full source registry (120+ sources)
