# CareerKit — Project Context

## What Is This?

Full-stack job hunting automation: scrapes 100+ job sources → LLM extraction → smart scoring → auto-apply + cold email outreach. Built for a solo healthcare AI engineer job search.

## Quick Reference

- **Backend**: FastAPI on port 8000 (`backend/server.py`)
- **Frontend**: React + Vite on port 5173 (`frontend-src/`)
- **Database**: SQLite at `data/linkedin_jobs.db` (schema in `backend/db.py`)
- **Config**: Secrets in `config/.env`, profile in `backend/config.py`, sources in `backend/config_sources.py`
- **Launch**: `./run.sh` (or `--prod`, `--back`, `--front`)

## Architecture

```
React SPA → /api proxy → FastAPI → {Playwright, Ollama/Gemini, SQLite, Gmail SMTP}
```

Threading: Dedicated browser thread (Playwright), daemon threads for scraping/email/auto-apply, thread-local SQLite connections.

LLM chain: Ollama (local, free) → Gemini API (fallback) → Regex (last resort).

## Key Files

| Area | Files |
|------|-------|
| Routes | `backend/routes/{jobs,scraper,browser,posts,email,pipeline,leads,settings,tools,auto_apply}.py` |
| Services | `backend/services/{scraper_service,browser_service,email_service,auto_apply,smart_filter,ai_tools,orchestrator}.py` |
| Scrapers | `backend/scrapers/{linkedin_jobs,linkedin_posts,api_scrapers,web_scrapers,generic_scrapers}.py` |
| Extraction | `backend/extractors/{pipeline,text,fitness}.py`, `backend/llm/{client,extraction}.py` |
| Frontend API | `frontend-src/src/lib/api.js` (all endpoints) |
| Pages | `frontend-src/src/pages/*.jsx` (13 pages) |

## Conventions

- Routes are thin — delegate to services
- Thread safety: locks + state dicts for background workers
- Browser commands go through `_browser_cmd_q` Queue
- Frontend uses polling (2-5s) for real-time updates, no WebSocket
- No Redux — React hooks + Context (Toast only)
- Dark theme, purple accent (`#A855F7`)

## Don't Touch

- `config/.env` — Contains real API keys and SMTP credentials
- `data/browser_profiles/` — Persistent LinkedIn login session
- `backend/config.py` PROFILE section — Has real personal data

## Documentation

Full docs in `docs/`:
- `ARCHITECTURE.md` — System design, component interactions, threading
- `API_REFERENCE.md` — All REST endpoints
- `DATABASE_SCHEMA.md` — All tables, relationships, key queries
- `SETUP_GUIDE.md` — Installation, configuration, usage
- `SYSTEM_DIAGRAMS.md` — Mermaid diagrams for all data flows
- `AI_CONTEXT.md` — Comprehensive context for AI assistants
- `SERVICES_REFERENCE.md` — Every service, function, and constant
