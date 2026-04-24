# Job Portal Research — Vineet Corp Intel Brief
**Compiled by**: Chintu, AI Tools & Productivity Scout
**Date**: April 24, 2026
**Target Profile**: AI Engineer, 2yr exp, India-based, targeting Remote roles in Japan / Europe / UAE / US / Singapore

---

> LEGEND — Access Types:
> - API-Free: Public API, no cost
> - API-Paid: API access behind a paid plan
> - API-Auth: Free API but requires registration/OAuth
> - RSS: RSS/Atom feed available
> - Scrapable-Easy: Plain HTML, no bot protection
> - Scrapable-Medium: Light JS rendering, minor anti-bot
> - Scrapable-Hard: Cloudflare / heavy anti-bot
> - Blocked: Actively hostile to scrapers

> Anti-bot levels: None / Light / Cloudflare / Heavy

---

## CATEGORY 1 — GLOBAL MEGA-PLATFORMS

### 1. LinkedIn Jobs
- **URL**: https://www.linkedin.com/jobs/
- **Type**: Scrapable-Hard (official API deprecated for job search)
- **Region Focus**: Global
- **AI/ML Job Volume**: Very High (100,000+)
- **Login Required**: Yes (for full listings)
- **Anti-bot**: Heavy — rate limits after ~10 pages per IP, requires session cookies
- **Notes**: Best coverage globally. JobSpy library wraps it. Proxycurl shut down Jan 2025 after LinkedIn lawsuit. Use rotating residential proxies + session auth. Guest mode limited. Unofficial scraping via JobSpy (python-jobspy on PyPI) is the current best open-source option. Apify LinkedIn actor available ($0.005/result).

### 2. Indeed
- **URL**: https://www.indeed.com / https://in.indeed.com
- **Type**: Scrapable-Medium (best scraping yield right now per JobSpy benchmarks)
- **Region Focus**: Global (localised domains per country)
- **AI/ML Job Volume**: Very High (150,000+)
- **Login Required**: No (for browsing)
- **Anti-bot**: Cloudflare (manageable with proper headers in 2026)
- **Notes**: Publisher Jobs API was deprecated in 2023. Now scraping-only. JobSpy reports "no rate limiting" on Indeed as of 2025. Use country-specific domains (indeed.co.jp, indeed.de, indeed.ae, etc.). Scrapfly has a 2026 guide. Glassdoor and Indeed merged under Recruit Holdings July 2025.

### 3. Glassdoor
- **URL**: https://www.glassdoor.com
- **Type**: Scrapable-Hard
- **Region Focus**: Global (US-heavy)
- **AI/ML Job Volume**: High (50,000+)
- **Login Required**: Yes (login via Indeed since Feb 2026)
- **Anti-bot**: Heavy — Cloudflare + aggressive bot detection. Patchright (stealth Playwright fork) needed. Vanilla Selenium blocked before first HTML byte loads.
- **Notes**: Merged with Indeed under Recruit Holdings July 2025. Login now handled entirely through Indeed Login — any old Glassdoor-specific login scrapers are broken. Persist cookies (gdId, cf_clearance, GSESSIONID). Salary data is the main value-add here beyond job listings.

### 4. Google Jobs (via Google Search)
- **URL**: https://jobs.google.com (aggregator via Search)
- **Type**: Scrapable-Hard (Google SERP scraping)
- **Region Focus**: Global
- **AI/ML Job Volume**: Very High (aggregates everything)
- **Login Required**: No
- **Anti-bot**: Heavy — Google's bot detection
- **Notes**: JobSpy includes Google Jobs scraping. SerpAPI ($50/mo) gives clean structured access. Best for broad discovery. Not a first-party job board — aggregates from ATS and other boards.

### 5. ZipRecruiter
- **URL**: https://www.ziprecruiter.com
- **Type**: Scrapable-Medium + has unofficial API via scrapers
- **Region Focus**: US-primary, some global
- **AI/ML Job Volume**: High (US-centric)
- **Login Required**: No
- **Anti-bot**: Light-Medium
- **Notes**: JobSpy covers ZipRecruiter. Apify ZipRecruiter actor available. ScrapingBee and ScrapingRobot have dedicated ZipRecruiter APIs. Primarily US-focused — limited value for Japan/Europe targeting.

### 6. Monster / Foundit Global
- **URL**: https://www.monster.com / https://www.foundit.in (India)
- **Type**: Scrapable-Medium
- **Region Focus**: US, India, some global
- **AI/ML Job Volume**: Medium
- **Login Required**: No (browsing)
- **Anti-bot**: Light
- **Notes**: Monster India rebranded to Foundit. Monster.com still active for US. RSS feeds available on some regional versions. Volume lower than LinkedIn/Indeed.

---

## CATEGORY 2 — REMOTE-FIRST JOB BOARDS

### 7. RemoteOK
- **URL**: https://remoteok.com
- **Type**: API-Free + Scrapable-Easy
- **Region Focus**: Global Remote
- **AI/ML Job Volume**: Medium-High (tagged by stack: Python, ML, AI)
- **Login Required**: No
- **Anti-bot**: None
- **Notes**: Has a public JSON API at https://remoteok.com/api — completely free, no auth needed. Returns structured JSON with company, position, tags, salary, date. Probably the easiest legitimate data source in this list. Gold mine. Aggregates from other boards + direct posts.
- **Install/Access**: `curl https://remoteok.com/api` — done.

### 8. We Work Remotely (WWR)
- **URL**: https://weworkremotely.com
- **Type**: RSS + Scrapable-Easy
- **Region Focus**: Global Remote
- **AI/ML Job Volume**: Medium (curated, ~500 active at any time)
- **Login Required**: No
- **Anti-bot**: None
- **Notes**: Has RSS feeds per category. Programming category feed: https://weworkremotely.com/categories/remote-programming-jobs.rss. Founded 2013, well-established, strict remote-only policy. Tech/Programming category most relevant. Listings include salary + timezone requirements.

### 9. Remotive
- **URL**: https://remotive.com
- **Type**: API-Auth (free tier) + RSS
- **Region Focus**: Global Remote
- **AI/ML Job Volume**: Medium (AI/ML section active)
- **Login Required**: No for browsing
- **Anti-bot**: Light
- **Notes**: Has an unofficial JSON API. Remote jobs listed at https://remotive.com/api/remote-jobs. Filter by category=software-dev. Has dedicated AI/ML subcategory at https://remotive.com/remote-jobs/ai-ml. One of the cleanest datasets available.
- **Install/Access**: `curl "https://remotive.com/api/remote-jobs?category=software-dev&limit=100"`

### 10. FlexJobs
- **URL**: https://www.flexjobs.com
- **Type**: Scrapable-Hard (paywalled)
- **Region Focus**: Global (US-heavy)
- **AI/ML Job Volume**: Medium
- **Login Required**: Yes (paid subscription ~$15-25/mo)
- **Anti-bot**: Cloudflare
- **Notes**: All jobs are hand-screened for legitimacy — high signal, low noise. But paywall makes scraping difficult and legally gray. Better to pay for a subscription and use their search UI.

### 11. Remote.co
- **URL**: https://remote.co/remote-jobs/
- **Type**: Scrapable-Easy
- **Region Focus**: Global Remote
- **AI/ML Job Volume**: Low-Medium
- **Login Required**: No
- **Anti-bot**: None
- **Notes**: Clean HTML, no JS rendering required. Curated listings. Hand-selected categories. Lower volume but higher quality. Dev/tech category relevant.

### 12. Working Nomads
- **URL**: https://www.workingnomads.com/jobs
- **Type**: API-Free + RSS
- **Region Focus**: Global Remote (timezone-flexible)
- **AI/ML Job Volume**: Low-Medium
- **Login Required**: No
- **Anti-bot**: None
- **Notes**: Has a public API endpoint. Focuses on 100% remote, travel-friendly roles. Daily updates. Good for timezone-agnostic remote positions. JSON feed available.

### 13. NoDesk
- **URL**: https://nodesk.co/remote-jobs/
- **Type**: Scrapable-Easy (aggregator)
- **Region Focus**: Global Remote
- **AI/ML Job Volume**: Medium (aggregates from 20+ boards)
- **Login Required**: No
- **Anti-bot**: None
- **Notes**: Aggregates from WWR, HackerNews, StackOverflow and more. No account required. Filter by EMEA for Europe-specific remote roles. Clean HTML pages.

### 14. Jobgether
- **URL**: https://jobgether.com
- **Type**: Scrapable-Medium
- **Region Focus**: Global Remote (strong Europe coverage)
- **AI/ML Job Volume**: Medium-High (200,000+ total listings claimed)
- **Login Required**: No
- **Anti-bot**: Light
- **Notes**: Claims 200,000+ remote jobs. Strong European remote coverage. Established 2020. One of the better aggregators for EMEA remote roles.

### 15. EURemoteJobs / EU Remote Jobs
- **URL**: https://euremotejobs.com
- **Type**: Scrapable-Easy
- **Region Focus**: Europe Remote (EMEA timezone)
- **AI/ML Job Volume**: Low-Medium
- **Login Required**: No
- **Anti-bot**: None
- **Notes**: Manually curated. Focused on European timezone-compatible remote roles. Smaller volume but highly targeted. Good for Vineet's Europe targeting.

### 16. Remote in Europe
- **URL**: https://remoteineurope.com
- **Type**: Scrapable-Easy
- **Region Focus**: Europe Remote
- **AI/ML Job Volume**: Low-Medium
- **Login Required**: No
- **Anti-bot**: None
- **Notes**: Curated remote roles open to European candidates. Programming, Design, Product categories. Clean site.

### 17. RemotifyEurope
- **URL**: https://remotifyeurope.com
- **Type**: Scrapable-Easy
- **Region Focus**: Europe Remote
- **AI/ML Job Volume**: Low-Medium
- **Login Required**: No
- **Anti-bot**: None
- **Notes**: Fast growing, newer platform. European timezone focused. Worth monitoring.

### 18. Remote Rocketship
- **URL**: https://www.remoterocketship.com
- **Type**: Scrapable-Medium
- **Region Focus**: Global Remote (country-filtered pages)
- **AI/ML Job Volume**: Medium
- **Login Required**: No
- **Anti-bot**: Light
- **Notes**: Has country-specific AI Engineer pages. Example: https://www.remoterocketship.com/country/europe/jobs/ai-engineer/ — directly relevant.

---

## CATEGORY 3 — AI / ML / TECH SPECIFIC

### 19. AIJobs.net / aijobs.ai
- **URL**: https://aijobs.net / https://aijobs.ai
- **Type**: Scrapable-Easy (aijobs.net has RSS)
- **Region Focus**: Global
- **AI/ML Job Volume**: High (10,000+ AI-specific roles)
- **Login Required**: No
- **Anti-bot**: None-Light
- **Notes**: Leading dedicated AI job board. Updated daily. Covers research, engineering, data science. Both startups and big tech. One of THE destinations for AI roles. aijobs.ai positions itself as "the leading source." RSS available on aijobs.net.

### 20. AiMLJobs.fyi / AIML Jobs
- **URL**: https://www.aimljobs.fyi
- **Type**: Scrapable-Easy
- **Region Focus**: Global (startup-heavy)
- **AI/ML Job Volume**: Medium
- **Login Required**: No
- **Anti-bot**: None
- **Notes**: Curated specifically for AI startups. Smaller but high signal. Newer platform.

### 21. MachineLearningJobs.com
- **URL**: https://machinelearningjobs.com
- **Type**: Scrapable-Easy
- **Region Focus**: Global
- **AI/ML Job Volume**: Medium
- **Login Required**: No
- **Anti-bot**: None
- **Notes**: Niche ML-specific board. Curated. Lower volume than LinkedIn but pure signal.

### 22. Remotive AI/ML Section
- **URL**: https://remotive.com/remote-jobs/ai-ml
- **Type**: API-Free (via Remotive API with category filter)
- **Region Focus**: Global Remote
- **AI/ML Job Volume**: Medium
- **Login Required**: No
- **Anti-bot**: None
- **Notes**: Subset of Remotive — dedicated AI/ML remote section. Use API: `?category=ai-ml`

### 23. DataJobs.com
- **URL**: https://datajobs.com
- **Type**: Scrapable-Medium
- **Region Focus**: US-heavy, some global
- **AI/ML Job Volume**: Low-Medium (data science + data engineering)
- **Login Required**: No
- **Anti-bot**: Light
- **Notes**: Founded by industry experts. Two categories: data science/analytics and data technology. Some postings may be stale — verify freshness before scraping.

### 24. KDnuggets Jobs
- **URL**: https://www.kdnuggets.com/jobs/index.html
- **Type**: Scrapable-Easy (aggregator/linklist)
- **Region Focus**: Global (academic + industry)
- **AI/ML Job Volume**: Low (curated links, not hosted listings)
- **Login Required**: No
- **Anti-bot**: None
- **Notes**: Acts as an aggregator — clicks through to external boards. Strong for academic AI positions. Not worth deep scraping; more useful as a discovery source to find other boards.

### 25. BuiltIn (AI/ML Section)
- **URL**: https://builtin.com/jobs/remote/dev-engineering/search/artificial-intelligence-engineer
- **Type**: Scrapable-Medium
- **Region Focus**: US-focused tech companies
- **AI/ML Job Volume**: Medium-High
- **Login Required**: No
- **Anti-bot**: Light-Medium
- **Notes**: US startup and tech company focused. Good for US remote roles from known tech companies. Has city-specific hubs (NYC, Chicago, LA, etc.).

### 26. EU Data Jobs
- **URL**: https://eudatajobs.com
- **Type**: Scrapable-Easy
- **Region Focus**: Europe (Data + AI)
- **AI/ML Job Volume**: Medium
- **Login Required**: No
- **Anti-bot**: None
- **Notes**: "Best job board for European data and AI professionals." Dedicated to EU data/AI roles. Worth scraping specifically for Vineet's Europe target.

---

## CATEGORY 4 — STARTUP-FOCUSED

### 27. Wellfound (formerly AngelList Talent)
- **URL**: https://wellfound.com/jobs
- **Type**: Scrapable-Medium (no official API)
- **Region Focus**: Global (startup-heavy, US + remote)
- **AI/ML Job Volume**: High (AI/ML is a top category)
- **Login Required**: Yes (free account)
- **Anti-bot**: Medium
- **Notes**: 12M+ active candidates (2025). 50% engineers. Shows salary, equity, funding upfront. Heavy on YC-backed companies. Free to browse with account. No public API — scraping requires session cookie. High-value signal for startup roles.

### 28. YCombinator Jobs / Work at a Startup
- **URL**: https://www.ycombinator.com/jobs / https://workatastartup.com
- **Type**: Scrapable-Medium
- **Region Focus**: Global (YC portfolio companies)
- **AI/ML Job Volume**: Medium-High (AI dominant in recent YC batches)
- **Login Required**: No for browsing
- **Anti-bot**: Light
- **Notes**: Lists jobs at all YC-backed startups. Given YC's recent AI focus (W24, S24, W25 batches heavily AI), this is a goldmine for AI Engineer roles. Clean HTML.

### 29. F6S
- **URL**: https://www.f6s.com/jobs
- **Type**: Scrapable-Easy
- **Region Focus**: Global (startup-heavy, EU strong)
- **AI/ML Job Volume**: Medium
- **Login Required**: No
- **Anti-bot**: None-Light
- **Notes**: Strong European startup presence. Good complement to Wellfound for EU startup ecosystem. Free job listings, accelerator-backed companies.

### 30. Welcome to the Jungle (Otta)
- **URL**: https://www.welcometothejungle.com (UK: app.otta.com)
- **Type**: Scrapable-Medium
- **Region Focus**: Europe + US (startup and scale-up)
- **AI/ML Job Volume**: Medium-High
- **Login Required**: Partial (can browse without, full filters need account)
- **Anti-bot**: Light-Medium
- **Notes**: Otta was acquired by Welcome to the Jungle (French co). 5.3M monthly visitors (Dec 2025). Machine learning-based job matching. Salary visible upfront. Strong for European tech companies. Highly relevant for EU targeting.

### 31. Startup.jobs
- **URL**: https://startup.jobs
- **Type**: Scrapable-Easy
- **Region Focus**: Global (US + international startups)
- **AI/ML Job Volume**: Low-Medium
- **Login Required**: No
- **Anti-bot**: None
- **Notes**: Clean, simple board. Startup-focused. Good volume of engineering roles. No fluff.

### 32. Work In Startups (UK)
- **URL**: https://workinstartups.com
- **Type**: Scrapable-Easy
- **Region Focus**: UK startups
- **AI/ML Job Volume**: Low-Medium
- **Login Required**: No
- **Anti-bot**: None
- **Notes**: UK-specific startup jobs. Good for UK remote roles from startup ecosystem.

---

## CATEGORY 5 — INDIA-SPECIFIC

### 33. Naukri.com
- **URL**: https://www.naukri.com
- **Type**: Scrapable-Medium (no public API)
- **Region Focus**: India (largest Indian job board)
- **AI/ML Job Volume**: Very High (12,555+ Generative AI jobs alone as of Apr 2026)
- **Login Required**: No for browsing, Yes for applying
- **Anti-bot**: Medium — some Cloudflare challenges
- **Notes**: India's #1 job board. 60M+ registered job seekers. 500,000+ listings. Critical for Indian market visibility. Has AI-enabled hiring suite. For remote international roles with India-based hiring, Naukri is essential. Has company email scraping potential via recruiter profiles.

### 34. Foundit (formerly Monster India)
- **URL**: https://www.foundit.in
- **Type**: Scrapable-Medium
- **Region Focus**: India (some SEA coverage)
- **AI/ML Job Volume**: High
- **Login Required**: No for browsing
- **Anti-bot**: Light-Medium
- **Notes**: Monster India rebranded. Popular among IT, finance, marketing. Lower signal than Naukri for pure AI/ML roles but decent volume.

### 35. Cutshort
- **URL**: https://cutshort.io
- **Type**: Scrapable-Hard (AI-matching platform, JS-heavy)
- **Region Focus**: India (tech/startup focused)
- **AI/ML Job Volume**: Medium-High
- **Login Required**: Yes (mandatory for browsing)
- **Anti-bot**: Medium
- **Notes**: Considered the best TECH hiring platform in India. 3.5M+ curated tech profiles. AI-driven matching. But walled garden — requires account to see listings. Good for India-based AI/ML roles at startups. Cannot scrape without auth.

### 36. Instahyre
- **URL**: https://www.instahyre.com
- **Type**: Scrapable-Hard (login-walled)
- **Region Focus**: India (premium tech talent)
- **AI/ML Job Volume**: Medium
- **Login Required**: Yes
- **Anti-bot**: Medium
- **Notes**: AI-driven matching, 3.5M+ vetted tech professionals. Premium tier. Walled garden. Better used as a platform to SET UP a profile and let companies approach you, rather than scraping it.

### 37. IIMJobs
- **URL**: https://www.iimjobs.com
- **Type**: Scrapable-Medium
- **Region Focus**: India (mid-senior roles)
- **AI/ML Job Volume**: Medium
- **Login Required**: No for browsing
- **Anti-bot**: Light
- **Notes**: Focuses on mid-senior and managerial roles. If targeting lead/senior AI roles with India-based hiring, this is the place. MBA + tech cross-section. Good for AI Product Manager type roles too.

### 38. Hirist.tech
- **URL**: https://www.hirist.tech
- **Type**: Scrapable-Easy
- **Region Focus**: India (tech-only)
- **AI/ML Job Volume**: Medium
- **Login Required**: No
- **Anti-bot**: None-Light
- **Notes**: Tech-only job board for India. Clean and focused. Good signal-to-noise. Underrated compared to Naukri.

### 39. Internshala (Freshers + Entry Level)
- **URL**: https://internshala.com
- **Type**: Scrapable-Medium
- **Region Focus**: India
- **AI/ML Job Volume**: Medium (heavy internship + entry-level AI)
- **Login Required**: No for browsing
- **Anti-bot**: Light
- **Notes**: Strong for entry-to-mid AI/ML roles. Also lists work-from-home positions. Good for India-based AI internships and junior roles.

### 40. TimesJobs
- **URL**: https://www.timesjobs.com
- **Type**: Scrapable-Medium
- **Region Focus**: India
- **AI/ML Job Volume**: Medium
- **Login Required**: No
- **Anti-bot**: Light
- **Notes**: Part of Times Internet. Decent volume. Lower signal than Naukri for pure tech but worth including.

---

## CATEGORY 6 — JAPAN-SPECIFIC

### 41. TokyoDev
- **URL**: https://www.tokyodev.com/jobs
- **Type**: Scrapable-Easy
- **Region Focus**: Japan (English-speaking developers)
- **AI/ML Job Volume**: Low-Medium (but highly curated)
- **Login Required**: No
- **Anti-bot**: None
- **Notes**: THE resource for English-speaking software engineers targeting Japan. Jobs require no Japanese. Many accept applications from abroad. Fully remote Japan-based roles listed separately at /jobs/fully-remote. AI-native platform listings present. Set up job alerts.

### 42. Japan Dev (japan-dev.com)
- **URL**: https://japan-dev.com/jobs
- **Type**: Scrapable-Easy
- **Region Focus**: Japan (English-friendly IT roles)
- **AI/ML Job Volume**: Low-Medium (~273 active IT jobs)
- **Login Required**: No
- **Anti-bot**: None
- **Notes**: 273 vetted IT jobs for English speakers. Hand-curated. Visa sponsorship often listed. Modern work culture focus. Accepts applications from abroad. Easy to scrape. Smaller volume = higher quality signal.

### 43. GaijinPot Jobs
- **URL**: https://jobs.gaijinpot.com
- **Type**: Scrapable-Easy
- **Region Focus**: Japan (English speakers)
- **AI/ML Job Volume**: Low (more teaching/ESL heavy, but IT section exists)
- **Login Required**: No
- **Anti-bot**: None
- **Notes**: Broad Japan job board for English speakers. More general than TokyoDev. IT section available. Language teaching dominates but tech roles present.

### 44. Daijob
- **URL**: https://www.daijob.com/en/
- **Type**: Scrapable-Medium
- **Region Focus**: Japan (bilingual professionals)
- **AI/ML Job Volume**: Medium
- **Login Required**: No for browsing
- **Anti-bot**: Light
- **Notes**: Japan's #1 job site for multilinguals. Most postings require business-level Japanese (JLPT N2+). Useful for roles at multinationals in Japan. Strong international company network. Caveat: Japanese language requirement for most AI roles.

### 45. Ikigai Connections
- **URL**: https://www.ikigaiconnections.com/japan/
- **Type**: Scrapable-Easy
- **Region Focus**: Japan
- **AI/ML Job Volume**: Low
- **Login Required**: No
- **Anti-bot**: None
- **Notes**: Niche Japan job aggregator/recruiter connector. Smaller but occasionally lists tech roles for internationals.

### 46. LinkedIn Japan
- **URL**: https://www.linkedin.com/jobs/ (filter Japan)
- **Type**: Scrapable-Hard
- **Region Focus**: Japan (via location filter)
- **AI/ML Job Volume**: Medium
- **Login Required**: Yes
- **Anti-bot**: Heavy
- **Notes**: Use JobSpy with location="Japan" filter. Many Japan-based remote AI roles from multinationals posted here.

---

## CATEGORY 7 — EUROPE-SPECIFIC

### 47. EuroTechJobs
- **URL**: https://www.eurotechjobs.com
- **Type**: Scrapable-Easy
- **Region Focus**: Europe (tech-focused)
- **AI/ML Job Volume**: Medium
- **Login Required**: No
- **Anti-bot**: None-Light
- **Notes**: Dedicated European tech job board. Software developer roles dominate. Good for EU-based and EU-remote positions.

### 48. Landing.jobs
- **URL**: https://landing.jobs
- **Type**: Scrapable-Medium
- **Region Focus**: Europe (strong Portugal, Spain, UK, Germany)
- **AI/ML Job Volume**: Medium
- **Login Required**: Partial
- **Anti-bot**: Light
- **Notes**: European tech hiring platform. Transparent salary. Relocation-friendly listings. Strong for southern/western Europe tech scene.

### 49. SwissDevJobs
- **URL**: https://swissdevjobs.ch
- **Type**: Scrapable-Easy
- **Region Focus**: Switzerland (tech)
- **AI/ML Job Volume**: Low-Medium
- **Login Required**: No
- **Anti-bot**: None
- **Notes**: Switzerland-specific dev jobs. Clean, simple. Swiss AI/ML market is well-paying. Worth scraping for EU Switzerland target.

### 50. Berlin Startup Jobs
- **URL**: https://berlinstartupjobs.com
- **Type**: Scrapable-Easy
- **Region Focus**: Berlin, Germany (startup ecosystem)
- **AI/ML Job Volume**: Low-Medium
- **Login Required**: No
- **Anti-bot**: None
- **Notes**: Berlin startup ecosystem jobs. Germany is one of Europe's top AI hiring markets. Many remote-friendly startups based here.

### 51. No Fluff Jobs
- **URL**: https://nofluffjobs.com
- **Type**: Scrapable-Medium + RSS
- **Region Focus**: Poland + Central/Eastern Europe
- **AI/ML Job Volume**: Medium
- **Login Required**: No
- **Anti-bot**: Light
- **Notes**: Strong CEE (Central Eastern Europe) coverage. Salary transparency required by platform. All salaries posted publicly — excellent for benchmarking. Remote filter available. Poland + Czech Republic tech market.

### 52. Jobs.ie / IrishJobs
- **URL**: https://www.irishjobs.ie
- **Type**: Scrapable-Medium
- **Region Focus**: Ireland
- **AI/ML Job Volume**: Low-Medium
- **Login Required**: No
- **Anti-bot**: Light
- **Notes**: Ireland's tech scene (Dublin = EU HQ for Google, Meta, Apple, etc.). Worth including for EU targeting.

### 53. Jobgether (EU Remote)
- **URL**: https://jobgether.com/remote-jobs/europe
- **Type**: Scrapable-Medium
- **Region Focus**: Europe Remote
- **AI/ML Job Volume**: Medium-High
- **Login Required**: No
- **Anti-bot**: Light
- **Notes**: Already listed in Category 2 — but calling out the EU-specific filter URL here for targeted scraping.

### 54. Workhap
- **URL**: https://workhap.com
- **Type**: Scrapable-Easy
- **Region Focus**: Europe Remote
- **AI/ML Job Volume**: Low-Medium
- **Login Required**: No
- **Anti-bot**: None
- **Notes**: Europe-focused remote work platform. Newer but growing.

---

## CATEGORY 8 — UAE / MIDDLE EAST

### 55. Bayt.com
- **URL**: https://www.bayt.com
- **Type**: Scrapable-Medium (JobSpy added Bayt recently)
- **Region Focus**: UAE + Middle East (GCC countries)
- **AI/ML Job Volume**: Medium (13,000+ UAE jobs; 20+ AI Engineer roles in Dubai)
- **Login Required**: No for browsing
- **Anti-bot**: Light-Medium
- **Notes**: The go-to job site in Middle East since 2000. 44M professionals, 40,000+ employers. JobSpy (cullenwatson fork) includes Bayt scraping. UAE ranked #1 globally for hiring sentiment in 2025 (+48% Net Employment Outlook). AI Engineer roles in Dubai available.

### 56. GulfTalent
- **URL**: https://www.gulftalent.com
- **Type**: Scrapable-Medium
- **Region Focus**: GCC / Middle East (UAE, Saudi Arabia, Qatar, Kuwait)
- **AI/ML Job Volume**: Medium (7,400+ active UAE jobs)
- **Login Required**: No
- **Anti-bot**: Light
- **Notes**: Leading professional job site for ME/Gulf region. 9M professionals. Strong for IT managers, senior engineers, solutions architects. Finance + engineering heavy.

### 57. Dubizzle Jobs
- **URL**: https://www.dubizzle.com/jobs/
- **Type**: Scrapable-Medium
- **Region Focus**: UAE (classifieds-evolved)
- **AI/ML Job Volume**: Low-Medium
- **Login Required**: No
- **Anti-bot**: Light
- **Notes**: Originally classifieds, now a significant UAE job platform. Popular among small businesses and startups. Lower signal for senior AI roles but good for broad UAE coverage.

### 58. Naukrigulf
- **URL**: https://www.naukrigulf.com
- **Type**: Scrapable-Medium
- **Region Focus**: Gulf countries (UAE, Saudi, Qatar, Bahrain, Oman, Kuwait)
- **AI/ML Job Volume**: Medium
- **Login Required**: No
- **Anti-bot**: Light
- **Notes**: Naukri's Gulf-focused platform. Bridges Indian talent to Gulf jobs. Particularly strong for India-based candidates targeting UAE. High relevance for Vineet.

### 59. Qureos
- **URL**: https://www.qureos.com
- **Type**: Scrapable-Medium
- **Region Focus**: MENA region
- **AI/ML Job Volume**: Low-Medium
- **Login Required**: No
- **Anti-bot**: Light
- **Notes**: AI-powered hiring platform for MENA. Growing fast. UAE + Saudi focused.

### 60. LinkedIn UAE
- **URL**: https://www.linkedin.com/jobs/ (filter UAE/Dubai)
- **Type**: Scrapable-Hard
- **Region Focus**: UAE via filter
- **AI/ML Job Volume**: High
- **Login Required**: Yes
- **Anti-bot**: Heavy
- **Notes**: JobSpy with location="Dubai" or "United Arab Emirates". Many multinational AI roles posted here.

---

## CATEGORY 9 — US-FOCUSED

### 61. Dice
- **URL**: https://www.dice.com
- **Type**: Scrapable-Medium (RSS available)
- **Region Focus**: US Tech
- **AI/ML Job Volume**: High (tech-only board)
- **Login Required**: No for browsing
- **Anti-bot**: Light
- **Notes**: Tech-professionals-only board. Strong US coverage. No general/non-tech noise. RSS feeds available. Great for US remote AI/ML roles. Skill-filtered search available.

### 62. Built In
- **URL**: https://builtin.com
- **Type**: Scrapable-Medium
- **Region Focus**: US tech companies
- **AI/ML Job Volume**: High (AI Engineer category prominent)
- **Login Required**: No
- **Anti-bot**: Light-Medium
- **Notes**: City-specific hubs + remote section. AI Engineer remote jobs page: https://builtin.com/jobs/remote/dev-engineering/search/artificial-intelligence-engineer. US startup and scale-up heavy.

### 63. USAJobs (Federal)
- **URL**: https://www.usajobs.gov
- **Type**: API-Free (official government API)
- **Region Focus**: US Federal Government
- **AI/ML Job Volume**: Low-Medium (growing AI/data roles)
- **Login Required**: No for API
- **Anti-bot**: None (official API)
- **Notes**: Official US Federal Government jobs API. Free, no auth for search. Growing number of AI/data science roles in government (DoD, NSA, HHS, etc.). Note: US federal jobs generally require US citizenship — limited relevance for Vineet unless targeting remote contractor roles.

### 64. GovernmentJobs.com (NEOGOV)
- **URL**: https://www.governmentjobs.com
- **Type**: Scrapable-Medium
- **Region Focus**: US State/Local Government
- **AI/ML Job Volume**: Low
- **Login Required**: No
- **Anti-bot**: Light
- **Notes**: US public sector (#1 public sector board). City, county, state government jobs. Limited relevance for AI Engineer targeting remote international.

### 65. Hired.com
- **URL**: https://hired.com
- **Type**: Scrapable-Hard (profile-first, invite-only model)
- **Region Focus**: US + UK tech
- **AI/ML Job Volume**: Medium
- **Login Required**: Yes (create profile, companies reach out)
- **Anti-bot**: Medium
- **Notes**: Reverse job search — create profile, get interview requests with salary upfront. High signal. US and UK focus. Requires profile setup, not bulk scraping. Better used as a candidate platform than scraped.

---

## CATEGORY 10 — SINGAPORE & SOUTHEAST ASIA

### 66. MyCareersFuture (MCF)
- **URL**: https://www.mycareersfuture.gov.sg
- **Type**: API-Free (government open data)
- **Region Focus**: Singapore (Citizens + PRs primarily)
- **AI/ML Job Volume**: Medium (80,000+ total listings)
- **Login Required**: No for browsing
- **Anti-bot**: None (government portal)
- **Notes**: Singapore government-run job portal by Workforce Singapore + GovTech. AI-powered matching. Integrated with Career Conversion Programmes (CCPs). Primarily targets Singapore Citizens and PRs — foreigners may face restrictions applying but listings are publicly accessible. Worth scraping for Singapore remote AI roles.

### 67. JobStreet Singapore
- **URL**: https://www.jobstreet.com.sg
- **Type**: Scrapable-Medium
- **Region Focus**: Singapore + SEA (Malaysia, Philippines, Indonesia)
- **AI/ML Job Volume**: Medium-High (60,000+ Singapore listings)
- **Login Required**: No for browsing
- **Anti-bot**: Light-Medium
- **Notes**: Undisputed market leader for Singapore/SEA recruitment. 60,000+ SG job postings. Partnered with JobsDB in Singapore. Part of SEEK Group. Key platform for Singapore AI roles.

### 68. JobsDB Singapore
- **URL**: https://sg.jobsdb.com
- **Type**: Scrapable-Medium
- **Region Focus**: Singapore, Hong Kong, Thailand
- **AI/ML Job Volume**: Medium
- **Login Required**: No for browsing
- **Anti-bot**: Light
- **Notes**: Partners with JobStreet under SEEK Group in Singapore. Functions as a job search aggregator pulling from multiple SG sources. Strong HK and Thailand coverage too.

### 69. Tech for Public Good (Singapore Gov)
- **URL**: https://techhiring.open.gov.sg
- **Type**: Scrapable-Easy
- **Region Focus**: Singapore Government tech
- **AI/ML Job Volume**: Low-Medium
- **Login Required**: No
- **Anti-bot**: None
- **Notes**: Singapore government tech hiring portal (GovTech). Software engineers, product managers, designers. Building government digital services. Interesting for Singapore-based roles.

### 70. LinkedIn Singapore
- **URL**: https://www.linkedin.com/jobs/ (Singapore filter)
- **Type**: Scrapable-Hard
- **Region Focus**: Singapore via filter
- **AI/ML Job Volume**: High
- **Login Required**: Yes
- **Anti-bot**: Heavy
- **Notes**: Strong MNC and startup AI hiring in Singapore on LinkedIn. Use JobSpy with location="Singapore".

---

## CATEGORY 11 — FREELANCE / CONTRACT WITH FULL-TIME ROLES

### 71. Arc.dev
- **URL**: https://arc.dev/remote-jobs/machine-learning
- **Type**: Scrapable-Medium
- **Region Focus**: Global Remote (US companies)
- **AI/ML Job Volume**: Medium (vetted, curated)
- **Login Required**: Yes for applying (profile creation)
- **Anti-bot**: Light
- **Notes**: Accepts only 1% of developer applicants (stricter than Toptal's 3%). Covers both freelance and full-time remote roles. AI/ML Engineer listings available. Strong for senior-level remote positions from US companies. Vetting required but once in, high-quality matches.

### 72. Toptal
- **URL**: https://www.toptal.com/jobs
- **Type**: Scrapable-Hard (invite-only, application required)
- **Region Focus**: Global (US company clients)
- **AI/ML Job Volume**: Low-Medium (premium roles)
- **Login Required**: Yes (vetting required)
- **Anti-bot**: Medium
- **Notes**: Claims top 3% of freelancers. $60-95+/hr rates. Full-time roles too. Very selective — screening test + interview + trial project required. High pay if you get through. Not bulk-scrapable.

### 73. Turing
- **URL**: https://www.turing.com
- **Type**: Application-Required (not scrapable for job listings)
- **Region Focus**: Global (US clients)
- **AI/ML Job Volume**: Medium (full-time remote)
- **Login Required**: Yes (developer application)
- **Anti-bot**: Medium
- **Notes**: Founded 2018. Committed to full-time (not freelance) remote roles. Vetting by ex-Google/Facebook/Microsoft engineers. Identifies top 1% global devs. $3,000-$15,000/mo. Not a job board to scrape — a talent network to join. Relevant for Vineet as a CANDIDATE platform.

### 74. Gun.io
- **URL**: https://gun.io
- **Type**: Application-Required
- **Region Focus**: US clients (global devs)
- **AI/ML Job Volume**: Low-Medium
- **Login Required**: Yes
- **Anti-bot**: Light
- **Notes**: Software-development-only talent platform. Popular with startups and enterprises. $75-150/hr freelance, $6,000-12,000+/mo full-time contracts. Need to apply as developer.

### 75. Lemon.io
- **URL**: https://lemon.io
- **Type**: Application-Required
- **Region Focus**: Eastern Europe focus (global clients)
- **AI/ML Job Volume**: Low-Medium
- **Login Required**: Yes (application)
- **Anti-bot**: Light
- **Notes**: Focuses on Eastern European talent pool. $50-90/hr. Monthly long-term staff augmentation. Apply as dev, then matched to clients. Not bulk-scrapable.

### 76. Contra
- **URL**: https://contra.com
- **Type**: Scrapable-Medium
- **Region Focus**: Global Remote (freelance + full-time)
- **AI/ML Job Volume**: Low-Medium
- **Login Required**: No for browsing
- **Anti-bot**: Light
- **Notes**: Commission-free freelance platform. Increasingly includes full-time remote roles. Clean UI. Newer platform growing fast.

### 77. Upwork (Full-time Contracts)
- **URL**: https://www.upwork.com
- **Type**: API-Auth (Upwork API available with approval)
- **Region Focus**: Global
- **AI/ML Job Volume**: Very High (massive volume, variable quality)
- **Login Required**: Yes
- **Anti-bot**: Medium
- **Notes**: Primarily freelance but long-term contracts blur into full-time. Official API exists (requires application approval). High volume but significant noise. Worth filtering for AI/ML fixed-price and long-term contracts.

---

## CATEGORY 12 — GOVERNMENT / PUBLIC SECTOR

### 78. USAJobs
- **URL**: https://www.usajobs.gov
- **Type**: API-Free
- **Region Focus**: US Federal
- **AI/ML Job Volume**: Low-Medium
- **Login Required**: No (API)
- **Anti-bot**: None
- **Notes**: Already covered in Category 9. Official API documented at developer.usajobs.gov.

### 79. UK Civil Service Jobs
- **URL**: https://www.civilservicejobs.service.gov.uk
- **Type**: Scrapable-Easy
- **Region Focus**: UK Government
- **AI/ML Job Volume**: Low (growing digital/data roles)
- **Login Required**: No for browsing
- **Anti-bot**: None-Light
- **Notes**: UK government tech roles. GCHQ, NCSC, HMRC, Cabinet Office all post digital roles here. Data Scientist and Machine Learning roles appear occasionally. Government security clearance often required.

### 80. Careers@Gov (Singapore)
- **URL**: https://careers.pageuppeople.com/688/cwlive/en/listing/
- **Type**: Scrapable-Easy
- **Region Focus**: Singapore Government
- **AI/ML Job Volume**: Low-Medium
- **Login Required**: No
- **Anti-bot**: None
- **Notes**: Official Singapore public service jobs. Tech roles are listed here. Ties to GovTech Singapore which actively hires AI/ML engineers.

### 81. MeitY (India Gov IT)
- **URL**: https://www.meity.gov.in/offerings/vacancies
- **Type**: Scrapable-Easy
- **Region Focus**: India Government IT
- **AI/ML Job Volume**: Low
- **Login Required**: No
- **Anti-bot**: None
- **Notes**: Ministry of Electronics and IT India vacancies. CDAC, NIC, STPI roles. Limited relevance for remote targeting but useful for India market awareness.

---

## CATEGORY 13 — ATS / COMPANY AGGREGATOR BOARDS

These platforms power career pages for thousands of companies. Scraping them gives access to direct company postings.

### 82. Greenhouse
- **URL**: https://boards.greenhouse.io/[company]
- **Type**: API-Free (public job listings endpoint)
- **Region Focus**: Global (all companies using Greenhouse ATS)
- **AI/ML Job Volume**: Very High (thousands of companies)
- **Login Required**: No
- **Anti-bot**: None (public API)
- **Notes**: Greenhouse exposes a public JSON API for each company's listings at: `https://boards-api.greenhouse.io/v1/boards/{company}/jobs`. No auth needed. This is GOLD — directly access structured job data from any Greenhouse-powered company (Stripe, Airbnb, Figma, etc.). OpenJobRadar integrates with Greenhouse natively.

### 83. Lever
- **URL**: https://jobs.lever.co/[company]
- **Type**: API-Free (public JSON endpoint)
- **Region Focus**: Global
- **AI/ML Job Volume**: Very High
- **Login Required**: No
- **Anti-bot**: None
- **Notes**: Similar to Greenhouse — public JSON API at `https://api.lever.co/v0/postings/{company}?mode=json`. Free, no auth. Another goldmine. Covers companies like Netflix, GitHub, etc.

### 84. Ashby
- **URL**: https://jobs.ashbyhq.com/[company]
- **Type**: API-Free (public JSON endpoint)
- **Region Focus**: Global (startup-heavy)
- **AI/ML Job Volume**: High (fast growing ATS)
- **Login Required**: No
- **Anti-bot**: None
- **Notes**: Fastest growing ATS in 2025 (6.5x usage growth). Public API: `https://api.ashbyhq.com/posting-api/job-board/{companyId}`. Covers many AI/ML startups. Apify has dedicated Ashby scrapers too.

### 85. Workable
- **URL**: https://apply.workable.com/[company]
- **Type**: Scrapable-Easy + API-Auth
- **Region Focus**: Global (SMB-heavy, EU strong)
- **AI/ML Job Volume**: Medium-High
- **Login Required**: No for public listings
- **Anti-bot**: Light
- **Notes**: Popular in Europe (founded in Athens). Workable has an API for job postings. Apify has a Workable scraper actor. Good EU company coverage.

### 86. SmartRecruiters
- **URL**: https://careers.smartrecruiters.com/[company]
- **Type**: API-Free (public jobs endpoint)
- **Region Focus**: Global (enterprise-heavy)
- **AI/ML Job Volume**: High
- **Login Required**: No
- **Anti-bot**: None
- **Notes**: Enterprise ATS. Public API available. Covers large companies. Worth crawling for big tech/enterprise AI roles.

### 87. iCIMS
- **URL**: https://careers-[company].icims.com
- **Type**: Scrapable-Medium
- **Region Focus**: Global (US enterprise heavy)
- **AI/ML Job Volume**: High (enterprise scale)
- **Login Required**: No
- **Anti-bot**: Light
- **Notes**: Major enterprise ATS. Used by Fortune 500 companies. No single public API like Greenhouse — company-specific URLs. OpenJobRadar supports it.

### 88. Workday
- **URL**: https://[company].wd5.myworkdayjobs.com
- **Type**: Scrapable-Hard (heavy JS rendering)
- **Region Focus**: Global (enterprise)
- **AI/ML Job Volume**: Very High
- **Login Required**: No for browsing
- **Anti-bot**: Medium-Heavy (JS-rendered, needs Playwright/Puppeteer)
- **Notes**: Used by major enterprises (Microsoft, Salesforce, etc.). Requires headless browser for scraping. OpenJobRadar and Apify have Workday scrapers. High value but technically challenging.

---

## CATEGORY 14 — NICHE TECH / COMMUNITY BOARDS

### 89. Hacker News — Who Is Hiring
- **URL**: https://news.ycombinator.com/jobs + monthly threads
- **Type**: API-Free (HN Algolia API)
- **Region Focus**: Global (startup/tech heavy)
- **AI/ML Job Volume**: Medium (high quality, 1st-of-month threads)
- **Login Required**: No
- **Anti-bot**: None
- **Notes**: Monthly "Who is Hiring?" thread on first weekday of month. HNHIRING.com (https://hnhiring.com) indexes all posts back to 2018 (58,879+ job ads). Remote filter: https://hnhiring.com/locations/remote. Apify scraper available. n8n workflow template exists. Very high-signal for startup + remote AI roles. Algolia API: `https://hn.algolia.com/api/v1/search` with tag=job.

### 90. HNHIRING.com
- **URL**: https://hnhiring.com
- **Type**: Scrapable-Easy (third-party HN indexer)
- **Region Focus**: Global (HN community)
- **AI/ML Job Volume**: Medium
- **Login Required**: No
- **Anti-bot**: None
- **Notes**: Best way to search HN Who Is Hiring threads. Searchable, filterable. Easier than direct HN scraping.

### 91. StackOverflow Jobs (Successor Boards)
- **URL**: StackOverflow shuttered its job board in 2022. Current alternatives:
  - https://stackoverflow.co/teams/job-boards/ (employer product)
  - Remote4me.com (aggregates from multiple boards)
- **Type**: N/A (original board dead)
- **Region Focus**: N/A
- **Notes**: StackOverflow Jobs is DEAD since March 2022. Community-maintained alternatives: Remote4me aggregates from 20+ boards including former SO-adjacent sources. Dice.com absorbed much of the SO developer audience.

### 92. GitHub Jobs
- **URL**: DEAD — shut down May 2022
- **Type**: Defunct
- **Notes**: GitHub Jobs shut down. The github.com/about/careers page for GitHub's own jobs is live but that's different. Use HN, Wellfound, and RemoteOK for the developer community now.

### 93. Remote4me
- **URL**: https://remote4me.com
- **Type**: Scrapable-Easy (aggregator)
- **Region Focus**: Global Remote
- **AI/ML Job Volume**: Medium (aggregates 20+ boards)
- **Login Required**: No
- **Anti-bot**: None
- **Notes**: Aggregates from StackOverflow (historical), HackerNews, WWR, and others. Good single-stop for developer remote roles.

### 94. Cord.co
- **URL**: https://cord.co
- **Type**: Scrapable-Medium (verification-walled)
- **Region Focus**: UK + Europe tech
- **AI/ML Job Volume**: Medium
- **Login Required**: Yes (pre-verified candidate profiles)
- **Anti-bot**: Light
- **Notes**: Every person on Cord is pre-verified and actively looking. Auto-schedules interviews. UK/EU tech companies. Better as a candidate platform than a scraping target.

---

## CATEGORY 15 — CRYPTO / WEB3 (with AI roles)

### 95. CryptoJobsList
- **URL**: https://cryptojobslist.com
- **Type**: Scrapable-Easy + RSS
- **Region Focus**: Global (remote-heavy)
- **AI/ML Job Volume**: Medium (Web3 + AI crossover roles growing)
- **Login Required**: No
- **Anti-bot**: None
- **Notes**: Launched 2017, one of oldest crypto job boards. Updated daily. Web3 AI Engineer roles growing rapidly as blockchain companies build AI layers. 218+ Web3 jobs listed (Apr 2026).

### 96. Web3.career
- **URL**: https://web3.career
- **Type**: Scrapable-Easy
- **Region Focus**: Global Remote
- **AI/ML Job Volume**: Medium (73,926 total Web3 jobs)
- **Login Required**: No
- **Anti-bot**: None
- **Notes**: "#1 Web3 Job Board." AI + blockchain engineering roles. Growing intersection of AI and DeFi/crypto infrastructure.

### 97. Crypto.jobs
- **URL**: https://crypto.jobs
- **Type**: Scrapable-Easy
- **Region Focus**: Global Remote
- **AI/ML Job Volume**: Medium
- **Login Required**: No
- **Anti-bot**: None
- **Notes**: 3,590+ Web3 jobs (2026). Broad crypto/blockchain coverage. AI roles appear in smart contract AI, LLM for DeFi, etc.

### 98. Remote3.co
- **URL**: https://www.remote3.co
- **Type**: Scrapable-Easy
- **Region Focus**: Global Remote (Web3)
- **AI/ML Job Volume**: Low-Medium
- **Login Required**: No
- **Anti-bot**: None
- **Notes**: Web3-focused remote jobs. Smaller volume. AI roles present.

---

## CATEGORY 16 — HEALTHCARE AI SPECIFIC

### 99. Health eCareers
- **URL**: https://www.healthecareers.com
- **Type**: Scrapable-Medium
- **Region Focus**: US Healthcare
- **AI/ML Job Volume**: Low (AI-specific roles growing)
- **Login Required**: No for browsing
- **Anti-bot**: Light
- **Notes**: Healthcare jobs board with growing AI/ML section. Medical AI roles — clinical decision support, imaging AI, NLP for EHR. US-centric. Limited relevance for Vineet's international targeting but included for completeness.

### 100. IQVIA AI/ML Careers
- **URL**: https://jobs.iqvia.com/en/ai-machine-learning-careers
- **Type**: Scrapable-Easy (direct career page)
- **Region Focus**: Global (IQVIA is a healthcare data company)
- **AI/ML Job Volume**: Low-Medium
- **Login Required**: No
- **Anti-bot**: None
- **Notes**: IQVIA specifically has an AI/ML careers hub. Illustrates that healthcare data companies are aggressively hiring AI engineers. Include in scrape of company career pages.

---

## CATEGORY 17 — DATA SCIENCE SPECIFIC

### 101. Kaggle Jobs (CLOSED)
- **URL**: https://www.kaggle.com/jobs (CLOSED)
- **Type**: DEFUNCT
- **Notes**: Kaggle Jobs board is officially closed ("The Jobs Board is Closing" per official Kaggle announcement). Use the Kaggle community forums and Kaggle Datasets for job market data, not job listings.

### 102. KDnuggets Jobs
- **URL**: https://www.kdnuggets.com/jobs/index.html
- **Type**: Scrapable-Easy (aggregator/link list)
- **Region Focus**: Global (academic + industry)
- **AI/ML Job Volume**: Low-Medium (curated links)
- **Login Required**: No
- **Anti-bot**: None
- **Notes**: Acts as aggregator — links out to external boards. Strong academic AI signal. Listed in Category 3 as well — included here for category completeness.

### 103. DataSpace Jobs
- **URL**: https://dataspace.com/data-job-seekers/data-science-job-boards/
- **Type**: Directory/Aggregator
- **Region Focus**: Global
- **AI/ML Job Volume**: Aggregated
- **Notes**: A roundup/directory of data science job boards — use to discover additional niche boards rather than scraping directly.

---

## CATEGORY 18 — ACADEMIC / RESEARCH

### 104. AcademicJobsOnline (AJO)
- **URL**: https://academicjobsonline.org/ajo/AI
- **Type**: Scrapable-Easy
- **Region Focus**: Global (University + Research)
- **AI/ML Job Volume**: Medium (dedicated AI section)
- **Login Required**: No for browsing
- **Anti-bot**: None
- **Notes**: Has a dedicated AI section. University faculty, postdoc, research scientist roles. If Vineet is open to research positions (IIT-adjacent, RIKEN Japan, EPFL Europe, etc.), this is the source.

### 105. Euraxess
- **URL**: https://euraxess.ec.europa.eu/jobs
- **Type**: API-Free (EU Open Data API available)
- **Region Focus**: Europe (Research)
- **AI/ML Job Volume**: Medium (EU research institutions)
- **Login Required**: No
- **Anti-bot**: None
- **Notes**: European Commission-run researcher mobility portal. AI/ML research positions at EU universities and institutes. Free API. Excellent for EU academic AI targeting.

### 106. Nature Careers
- **URL**: https://www.nature.com/naturecareers/jobs
- **Type**: Scrapable-Medium
- **Region Focus**: Global (Academic/Research)
- **AI/ML Job Volume**: Low-Medium
- **Login Required**: No for browsing
- **Anti-bot**: Light
- **Notes**: Nature Publishing Group's job board. High-prestige academic and research roles. AI/ML research positions from top institutions globally.

### 107. ResearchGate Jobs
- **URL**: https://www.researchgate.net/jobs
- **Type**: Scrapable-Medium (login-preferred)
- **Region Focus**: Global Academic
- **AI/ML Job Volume**: Low
- **Login Required**: Partial
- **Anti-bot**: Light
- **Notes**: Academic networking platform with job listings. Research-focused. Lower volume but high academic signal.

---

## CATEGORY 19 — JOB BOARD AGGREGATOR APIs

These are META-aggregators — one API call hits multiple boards.

### 108. Adzuna API
- **URL**: https://developer.adzuna.com
- **Type**: API-Free (with registration)
- **Region Focus**: Global (28+ countries)
- **AI/ML Job Volume**: Very High (aggregates millions of listings)
- **Login Required**: Yes (free API key registration)
- **Anti-bot**: N/A (official API)
- **Notes**: FREE public API with registration. Aggregates jobs from hundreds of boards globally. Covers US, UK, India, Germany, France, Australia, UAE, Singapore, and more. Returns structured JSON. THIS IS A PRIORITY INTEGRATION. Rate limits apply on free tier. Documented at developer.adzuna.com. Apify also has an Adzuna scraper for extra reach.

### 109. Jooble API
- **URL**: https://jooble.org (API via partnership)
- **Type**: API-Auth (REST API, partnership required)
- **Region Focus**: Global (70+ countries)
- **AI/ML Job Volume**: Very High
- **Login Required**: Yes (API key via application)
- **Anti-bot**: N/A (official API)
- **Notes**: REST API for global job search results. Available to developers via partners agreement. Aggregates from hundreds of sources globally. Very broad coverage.

### 110. CareerJet API
- **URL**: https://www.careerjet.com/partners/api/
- **Type**: API-Free (affiliate/partner API)
- **Region Focus**: Global (90+ countries)
- **AI/ML Job Volume**: Very High
- **Login Required**: Yes (partner registration)
- **Anti-bot**: N/A (official API)
- **Notes**: Careerjet is a global job search engine aggregating from thousands of boards. Partner API available. 90+ country coverage including Japan, UAE, Singapore, Europe. High global reach.

### 111. SerpAPI (Google Jobs)
- **URL**: https://serpapi.com/google-jobs-api
- **Type**: API-Paid ($50/mo for 5,000 searches)
- **Region Focus**: Global (via Google Jobs)
- **AI/ML Job Volume**: Very High
- **Login Required**: Yes (paid account)
- **Anti-bot**: N/A (official API)
- **Notes**: Clean structured access to Google Jobs results. Since Google aggregates from all ATS/boards, this is the widest possible net. Paid but worth it for scale. Best global coverage from a single API.

### 112. RapidAPI — Jobs Search API
- **URL**: https://rapidapi.com/search/jobs
- **Type**: API-Paid (various tiers)
- **Region Focus**: Global
- **AI/ML Job Volume**: Very High
- **Login Required**: Yes (RapidAPI account)
- **Anti-bot**: N/A
- **Notes**: Multiple job search APIs on RapidAPI marketplace. "Jobs Search Realtime Data" API fetches from LinkedIn, Indeed, ZipRecruiter, Glassdoor simultaneously. Pay-per-call model. Used in the n8n workflow template for multi-board scraping.

---

## CATEGORY 20 — OPEN SOURCE SCRAPERS (GitHub)

Tools to build your own scraping pipeline:

### 113. JobSpy (python-jobspy)
- **URL**: https://github.com/speedyapply/JobSpy (maintained fork) | original: https://github.com/cullenwatson/jobspy
- **Type**: Open Source Python Library
- **Covers**: LinkedIn, Indeed, Glassdoor, Google Jobs, ZipRecruiter, Bayt
- **Install**: `pip install python-jobspy`
- **Notes**: THE go-to open source job scraper. Active maintenance. Returns pandas DataFrame or CSV. cullenwatson original + speedyapply fork both active. TypeScript port available (ts-jobspy). Indeed works best — no rate limiting. LinkedIn rate limits after ~10 pages per IP. This should be the CORE of Vineet's scraping stack.

### 114. JobFunnel
- **URL**: https://github.com/PaulMcInnis/JobFunnel
- **Type**: Open Source Python (ARCHIVED)
- **Notes**: HISTORICAL ARTIFACT — archived. Boards moved to heavy anti-automation. Listed here as a learning reference only. DO NOT use for production scraping.

### 115. ts-jobspy (TypeScript)
- **URL**: https://github.com/alpharomercoma/ts-jobspy
- **Type**: Open Source TypeScript
- **Notes**: TypeScript rewrite of python-jobspy. Useful for Node.js/Next.js projects.

### 116. HN Who Is Hiring Scraper (n8n + Apify)
- **URL**: https://n8n.io/workflows/2924-hacker-news-job-listing-scraper-and-parser/
- **Type**: n8n Workflow Template
- **Notes**: Parses monthly HN "Who is Hiring?" threads into structured data. Free to use with n8n.

### 117. speedyapply/2026-AI-College-Jobs
- **URL**: https://github.com/speedyapply/2026-AI-College-Jobs
- **Type**: Curated GitHub Repo (updated daily)
- **Notes**: Daily-updated AI/ML internship and new grad job list. More useful as a data source than a scraper tool.

---

## CATEGORY 21 — ADDITIONAL DISCOVERED PLATFORMS

### 118. Relocate.me
- **URL**: https://relocate.me
- **Type**: Scrapable-Medium
- **Region Focus**: Global (relocation-friendly roles)
- **AI/ML Job Volume**: Medium
- **Login Required**: No
- **Anti-bot**: Light
- **Notes**: Jobs that offer relocation packages. Tech/engineering heavy. Good for Japan/Europe targeting where visa sponsorship + relocation is offered. Blog also lists other job boards.

### 119. Jobright.ai
- **URL**: https://jobright.ai
- **Type**: AI Job Aggregator (US-focused)
- **Region Focus**: US-heavy
- **AI/ML Job Volume**: High (aggregates from many sources)
- **Login Required**: Yes
- **Anti-bot**: Medium
- **Notes**: AI job search copilot aggregating millions of listings. Primarily US-focused. Autofill + tracking features. Some concerns about fake/expired postings in database. Better as an AUTO-APPLY tool than a scraping target.

### 120. Simplify.jobs
- **URL**: https://simplify.jobs
- **Type**: Chrome Extension + Job Aggregator
- **Region Focus**: US-heavy
- **AI/ML Job Volume**: High
- **Login Required**: Yes
- **Notes**: Chrome extension that autofills job applications on 100+ sites. Tracks submissions. AI-assisted responses. More useful as an application TOOL than a data source.

### 121. OpenJobRadar
- **URL**: https://openjobradar.com
- **Type**: API/Integration Platform
- **Region Focus**: Global
- **AI/ML Job Volume**: Very High (12+ ATS platforms)
- **Login Required**: Yes
- **Notes**: Natively integrates with Greenhouse, Lever, Workday, Ashby, SmartRecruiters, and 12+ ATS platforms. Monitor specific companies across ATS systems. Useful for building a company watchlist scraper.

### 122. Remotive Europe Jobs
- **URL**: https://remotive.com/remote-europe-jobs
- **Type**: API-Free (Remotive API with location filter)
- **Region Focus**: Europe Remote
- **AI/ML Job Volume**: Medium
- **Notes**: Remotive filtered for Europe. URL filter + API category for EU-specific remote AI roles.

### 123. WorkingNomads Remote Europe
- **URL**: https://www.workingnomads.com/remote-europe-jobs
- **Type**: API-Free
- **Region Focus**: Europe Remote
- **AI/ML Job Volume**: Low-Medium
- **Notes**: European remote roles from Working Nomads API.

### 124. Pallet (Community Job Boards)
- **URL**: https://pallet.xyz
- **Type**: Scrapable-Easy
- **Region Focus**: Global (community-curated)
- **AI/ML Job Volume**: Low-Medium
- **Login Required**: No
- **Anti-bot**: None
- **Notes**: Platform for communities to run their own job boards. Various AI/ML communities run boards here. Check specific community boards (e.g., AI Twitter community boards hosted on Pallet).

### 125. Lensa
- **URL**: https://lensa.com
- **Type**: Scrapable-Medium (AI matching platform)
- **Region Focus**: US-heavy
- **AI/ML Job Volume**: High (AI matching)
- **Login Required**: No for browsing
- **Anti-bot**: Light
- **Notes**: AI-powered job aggregator. Matches candidates to roles. Broad US coverage. Aggregates from many boards.

---

## PRIORITY MATRIX — WHERE TO START

### TIER 1 — Integrate First (High value, low friction)

| Platform | Why |
|---|---|
| RemoteOK API | Free JSON API, no auth, tagged by stack, global remote |
| Remotive API | Free, no auth, AI/ML category filter, clean JSON |
| Greenhouse API | Free, no auth, direct from company ATS — 1000s of companies |
| Lever API | Free, no auth, same as above for Lever-using companies |
| Ashby API | Free, no auth, fastest growing ATS covering AI startups |
| Adzuna API | Free with registration, 28+ countries, structured JSON |
| HN Hiring (Algolia) | Free, monthly gold mine for startup AI roles |
| Working Nomads API | Free, clean, remote-focused |

### TIER 2 — Worth Scraping (Medium effort, high value)

| Platform | Why |
|---|---|
| Indeed (JobSpy) | Massive volume, JobSpy works well, no rate limiting |
| Wellfound | Startup AI roles, salary/equity transparency |
| YCombinator Jobs | YC batches are now 70%+ AI companies |
| TokyoDev | THE Japan English dev board |
| Japan Dev | Curated, visa-friendly Japan roles |
| EuroTechJobs | EU tech coverage |
| Bayt (JobSpy) | UAE — JobSpy now covers Bayt |
| JobStreet SG | Singapore market leader |
| Naukri | India — mandatory for India market |
| No Fluff Jobs | Poland/CEE with salary transparency |
| EU Data Jobs | Europe AI/Data specific |
| CryptoJobsList | Web3+AI crossover roles |
| AcademicJobsOnline | Research positions globally |

### TIER 3 — Add Later (Harder, diminishing returns)

| Platform | Why |
|---|---|
| LinkedIn (JobSpy) | Rate limited, but still best for senior roles |
| Glassdoor | Merged with Indeed, heavy protection |
| Workday | Requires Playwright, high enterprise value |
| FlexJobs | Paywall, but high-quality listings |
| Toptal/Turing | Application required, not scrapable |

---

## OPEN SOURCE TOOLS SHORTLIST

```bash
# Core scraping library — install this first
pip install python-jobspy

# Quick test
python -c "
from jobspy import scrape_jobs
jobs = scrape_jobs(
    site_name=['linkedin', 'indeed', 'glassdoor', 'google', 'zip_recruiter', 'bayt'],
    search_term='AI Engineer',
    location='remote',
    results_wanted=50
)
print(jobs[['title', 'company', 'location', 'site']].head(20))
"
```

```bash
# RemoteOK free API — zero setup
curl https://remoteok.com/api | python -m json.tool | head -100

# Remotive free API — AI/ML category
curl "https://remotive.com/api/remote-jobs?category=software-dev&limit=100"

# Greenhouse company API (example: Stripe)
curl "https://boards-api.greenhouse.io/v1/boards/stripe/jobs"

# Lever company API (example: Netflix)
curl "https://api.lever.co/v0/postings/netflix?mode=json"

# Ashby company API (example: Anthropic)
curl "https://api.ashbyhq.com/posting-api/job-board/anthropic"

# HN Algolia API — current month jobs
curl "https://hn.algolia.com/api/v1/search?tags=job&hitsPerPage=100"
```

---

## DEAD / DISCONTINUED PLATFORMS (Do NOT waste time on these)

| Platform | Status | Notes |
|---|---|---|
| StackOverflow Jobs | DEAD (March 2022) | Shut down permanently |
| GitHub Jobs | DEAD (May 2022) | Shut down permanently |
| Kaggle Jobs | DEAD | "Jobs Board is Closing" — official announcement |
| AngelList Talent | REBRANDED | Now Wellfound — use wellfound.com |
| Proxycurl | SHUT DOWN (July 2025) | LinkedIn sued them, they closed |
| JobFunnel | ARCHIVED | Anti-bot improvements made it obsolete |
| Monster.com (India) | REBRANDED | Now Foundit (foundit.in) |
| Indeed Publisher API | DEPRECATED (2023) | No longer available — scraping only |

---

## ANTI-BOT DIFFICULTY CHART (Summary)

| Difficulty | Platforms |
|---|---|
| None (easiest) | RemoteOK, WWR (RSS), Remotive, Remote.co, HN Jobs, NoDesk, Greenhouse API, Lever API, Ashby API, TokyoDev, Japan Dev, F6S, CryptoJobsList, AcademicJobsOnline |
| Light | Indeed (via JobSpy), ZipRecruiter, Wellfound, Bayt, GulfTalent, JobStreet, Naukri, Dice, EuroTechJobs, Startup.jobs |
| Cloudflare/Medium | LinkedIn (session needed), Glassdoor (Patchright needed), Cutshort, Instahyre |
| Heavy/Blocked | LinkedIn (without auth), Glassdoor (sans stealth), FlexJobs (paywall) |

---

## SOURCES

- [Top AI Job Boards 2026 — Uxcel](https://uxcel.com/blog/top-ai-job-boards)
- [Top 12 Sites for ML Remote Jobs — ThirstySprout](https://www.thirstysprout.com/post/machine-learning-remote-jobs)
- [8 Best Job Boards for AI/ML/DS — NoCode Institute](https://www.nocodeinstitute.io/post/best-job-boards-for-ai-ml-data-science-careers-in-2025)
- [JobSpy GitHub (speedyapply fork)](https://github.com/speedyapply/JobSpy)
- [Top 8 AI Job Scraping Software — Thunderbit](https://thunderbit.com/blog/job-scraping-software)
- [Best Proxycurl Alternative 2026 — DEV Community](https://dev.to/agenthustler/best-proxycurl-alternative-in-2026-apify-linkedin-scrapers-vs-scrapingdog-vs-linkdapi-11n7)
- [Job Board Scraper API — ScraperAPI](https://www.scraperapi.com/solutions/job-boards-scraper/)
- [TokyoDev — Software Developer Jobs Japan](https://www.tokyodev.com/)
- [Japan Dev — 273 IT Jobs for English Speakers](https://japan-dev.com/jobs)
- [GaijinPot Jobs](https://jobs.gaijinpot.com/)
- [Best Job Portals for Foreigners in Japan](https://rirekishobuilder.com/blogs/best-job-portals-for-foreigners-in-japan)
- [EuroTechJobs](https://www.eurotechjobs.com/)
- [Remote in Europe](https://remoteineurope.com/)
- [EU Data Jobs](https://eudatajobs.com/search)
- [GulfTalent](https://www.gulftalent.com/)
- [Top 10 Job Boards UAE 2025 — Mintly](https://www.trymintly.com/blogs/top-10-job-boards-in-the-uae-for-2025)
- [9 Best UAE Job Sites 2026 — SaviorHire](https://www.saviorhire.com/post/best-job-websites-in-uae)
- [MyCareersFuture Singapore](https://www.mycareersfuture.gov.sg/)
- [Complete List Singapore Job Portals 2026 — ResumeWriter.sg](https://www.resumewriter.sg/blog/complete-list-of-job-sites-in-singapore/)
- [Top 20+ Job Boards India — GoHire](https://gohire.io/blog/job-boards-india-for-smbs)
- [Best Job Portals India — Keka](https://www.keka.com/best-job-portals-in-india)
- [Wellfound Startup Job Search](https://wellfound.com/)
- [Adzuna Developer API](https://developer.adzuna.com/)
- [Public APIs — Jobs Category](https://publicapis.dev/category/jobs)
- [CryptoJobsList](https://cryptojobslist.com)
- [Web3.career](https://web3.career/)
- [Crypto.jobs](https://crypto.jobs)
- [KDnuggets Jobs](https://www.kdnuggets.com/jobs/index.html)
- [Data Science Job Board Roundup — DataSpace](https://dataspace.com/data-job-seekers/data-science-job-boards/)
- [HNHIRING — All HN Jobs](https://hnhiring.com/)
- [HN Who Is Hiring Scraper — n8n](https://n8n.io/workflows/2924-hacker-news-job-listing-scraper-and-parser/)
- [Career Page Job Scraper (Greenhouse, Lever, ATS) — Apify](https://apify.com/scrapepilot/career-page-job-scraper----greenhouse-lever-any-ats/input-schema)
- [OpenJobRadar ATS Integrations](https://openjobradar.com/integrations)
- [How to Build Job Board with Greenhouse/Lever — Unified.to](https://unified.to/blog/how_to_build_a_job_board_that_connects_to_greenhouse_lever_and_60_ats_platforms_with_a_unified_api)
- [Toptal vs Turing vs Arc — Arc Employer Blog](https://arc.dev/employer-blog/toptal-turing-gigster-andela-arc/)
- [USAJobs](https://www.usajobs.gov/)
- [Tech for Public Good Singapore](https://techhiring.open.gov.sg/)
- [JobSpy (cullenwatson original)](https://github.com/cullenwatson/jobspy)
- [python-jobspy PyPI](https://pypi.org/project/python-jobspy/)
- [Glassdoor Scraping 2026 — DEV Community](https://dev.to/vhub_systems_ed5641f65d59/how-to-scrape-glassdoor-reviews-and-salaries-without-getting-blocked-in-2026-3599)
- [How to Scrape Indeed.com 2026 — Scrapfly](https://scrapfly.io/blog/posts/how-to-scrape-indeedcom)
- [Jobgether — Largest Remote Job Platform](https://jobgether.com/)
- [EU Remote Jobs](https://euremotejobs.com/)
- [Daijob.com](https://www.daijob.com/en/)
- [Naukri Generative AI Jobs](https://www.naukri.com/generative-ai-jobs)
- [AcademicJobsOnline — AI Section](https://academicjobsonline.org/ajo/AI)
- [Euraxess EU Research Jobs](https://euraxess.ec.europa.eu/jobs)
- [50 Remote Job Boards for Developers 2026 — Fueler](https://fueler.io/blog/remote-job-boards-for-developers-hiring)
- [33 Best Remote Job Boards 2026 — Freaking Nomads](https://freakingnomads.com/best-remote-job-boards/)

---

*Chintu out.*
