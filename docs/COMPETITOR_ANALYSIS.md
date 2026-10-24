# Competitor Feature Map & Gap Analysis

Clean-room study of commercial job-search tools, built from their public product pages, docs and demos
(no decompiling, no private APIs, no copied code). Each feature was re-implemented from scratch in coolkit.

## Feature map

| Feature | Who sells it | coolkit status |
|---|---|---|
| Multi-board job aggregation | Jobright, LinkedIn, Indeed | ✅ existing — 120+ sources (`config_sources.py`) |
| AI match score / job evaluation | Jobright, Teal, Jobscan | ✅ existing — `smart_filter`, `/api/tools/evaluate` |
| ATS keyword match report | Jobscan, Teal, Resume Worded | ✅ existing — `ats_scorer` |
| Tailored resume per JD | Teal, Kickresume, Rezi | ✅ existing — `/api/tools/tailor-cv`, `resume_selector` |
| Auto-apply bots | LazyApply, Sonara, LoopCV | ✅ existing — `auto_apply` |
| Cold email + follow-up cadence | Apollo, Lemlist, Hunter | ✅ existing — `email_service`, `followup_cadence`, A/B tests |
| Email finder | Hunter, RocketReach, Apollo | ✅ existing — `email_finder/` (7 strategies) |
| Kanban application tracker | Huntr, Teal, Simplify | ✅ existing — Pipeline page |
| Ghost-job / stale-post detection | Jobright, Hiring Cafe | ✅ existing — `ghost_detector`, `liveness` |
| Referral / warm intro finder | Jobright "insider connections", LinkedIn | ✅ existing — `referral_detector` |
| Company research | Final Round, Careerflow | ✅ existing — `/api/tools/deep-dive` |
| Interview prep pack | Huntr, Final Round | ✅ existing — `/api/tools/interview-prep` |
| **Browser extension: one-click save + match score** | Teal, Huntr, Simplify, Jobright | 🆕 added — `extension/` |
| **Browser extension: ATS form autofill** | Simplify Copilot, Careerflow | 🆕 added — `extension/` |
| **Cover letter generator (tones)** | Teal, Kickresume, Careerflow | 🆕 added — `/api/copilot/cover-letter` |
| **Salary range + negotiation coach** | Levels.fyi, Glassdoor, Jobright | 🆕 added — `/api/copilot/salary` (LLM estimate) |
| **LinkedIn profile optimizer** | Careerflow, Jobscan, Teal | 🆕 added — `/api/copilot/linkedin` |
| **Mock interview with answer grading** | Final Round AI, Yoodli, Huntr | 🆕 added — `/api/copilot/mock-interview/*` |
| **Weekly goals + daily streak** | Huntr, Teal | 🆕 added — `/api/goals` |
| **Custom-question autofill (text, select, radio, checkbox)** | Simplify+ , Jobright | 🆕 added, extended — answer bank (below) |

## Next candidates (not built yet)

| Feature | Who sells it | Notes |
|---|---|---|
| Voice mock interview (speech-to-text, pace/filler analysis) | Yoodli, Final Round | Browser `SpeechRecognition` → existing grader |
| Real-time interview copilot | Final Round AI | Ethically grey in live interviews — skip or practice-only |
| Resume builder with PDF templates | Kickresume, Rezi, Teal | Needs a template renderer (WeasyPrint / react-pdf) |
| Offer comparison | Levels.fyi | `/compare-offers` skill exists; needs a UI page |
| Workday / custom-widget dropdowns | Simplify | Non-native listboxes (`role=listbox`) aren't filled yet |
| Gmail/Calendar interview auto-scheduling sync | Huntr, Teal | `inbox_tracker` already detects interviews |
| Live salary data | Levels.fyi, AmbitionBox | No free API; scraping is ToS-restricted |

## How the competitors solve custom questions, and what coolkit does differently

What you can see from the outside: Simplify and Jobright scan the form, send each unanswered question
with your profile to an LLM, and fill in the result. Each application is answered fresh, so your
corrections from the last form are lost.

coolkit's version (`services/answer_bank.py` + `extension/popup.js:formAgent`):

1. **Bank first:** each question is normalized and fuzzy-matched (difflib ≥ 0.88) against *your* past answers.
2. **One batched LLM call** only for the questions the bank misses, with the profile and JD as context.
   Choice answers are forced onto a real option, and an answer that doesn't match any option is dropped, never guessed.
3. **Learns from corrections:** "Remember my answers" saves the final form values. User answers are never overwritten by
   AI answers. Answers that name a company ("Why Acme?") are reused only for that company.
4. **Colour-coded review:** green = your answer, purple = AI, amber = low confidence. Nothing is ever auto-submitted.
