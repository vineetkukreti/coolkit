# JobAutomate — Alternate Voice Script (Longer Version)

**Total Duration:** ~4:15
**Voice:** Adam (ElevenLabs) or Marcus (Murf AI) — Authoritative yet conversational
**Tone:** Senior developer showcasing a personal project — confident, clear, slightly casual
**TTS Settings:** ElevenLabs: Stability 0.45, Similarity Boost 0.75, Style 0.30

---

## SECTION 1 — HOOK (0:00 — 0:30)

[SCENE: Black screen, or slow fade-in of browser tabs — job boards, LinkedIn, spreadsheets]

[Slow, deliberate pace]

"If you've ever applied for jobs manually... [PAUSE] you know how it goes."

[PAUSE]

"Open LinkedIn. [PAUSE] Search for roles. [PAUSE] Scroll through dozens of posts. [PAUSE] Copy-paste your resume. [PAUSE] Write a cover letter. [PAUSE] Hit apply."

[PAUSE]

"And then... [PAUSE] do it all over again. [PAUSE] A hundred times."

[Slightly faster, with dry humor]

"There had to be a better way."

[PAUSE]

---

## SECTION 2 — PRODUCT INTRODUCTION (0:30 — 0:55)

[SCENE: App loads — dark purple dashboard appears, "JA" logo glows in sidebar]

[Confident, proud tone]

"So I built [EMPHASIS] JobAutomate."

[PAUSE]

"It's a full-stack web app — FastAPI on the backend, React on the front — that automates the [EMPHASIS] entire job hunting workflow. From scraping LinkedIn posts... to finding hiring managers... to sending personalized cold emails... to actually applying for jobs."

[PAUSE]

"Let me walk you through it."

---

## SECTION 3 — DASHBOARD (0:55 — 1:30)

[SCENE: Dashboard view — stat cards, charts, domain breakdown visible]

[Guided tour tone — calm and informative]

"This is the dashboard. [PAUSE] At a glance, you can see everything that's happened so far."

[PAUSE]

"Four-hundred and thirty posts scraped. [PAUSE] Two-hundred and sixty-one of those are [EMPHASIS] active hiring posts. [PAUSE] And one-hundred and thirty-two came with direct email addresses — which is huge for outreach."

[PAUSE]

"Below the stats, there's a role distribution chart showing which job titles are most common in your scraped data... and a domain relevance breakdown — so you can see [EMPHASIS] how well the results match your target field."

[PAUSE]

"Everything is live. [PAUSE] It updates as you scrape."

---

## SECTION 4 — LINKEDIN SCRAPER (1:30 — 2:20)

[SCENE: Scraper tab opens — Step 1 of the wizard is visible]

[Slightly more energetic — this is the centerpiece feature]

"Now for the [EMPHASIS] main feature. The LinkedIn scraper."

[PAUSE]

"It's built as a four-step wizard."

[PAUSE]

[SCENE: Step 1 — Connect screen]

"Step one: Connect. [PAUSE] Hit Launch Browser, and it opens a Playwright-controlled Chrome instance. You log in to LinkedIn [EMPHASIS] once — your session is saved."

[PAUSE]

[SCENE: Step 2 — Configure screen]

"Step two: Configure. [PAUSE] Set how many posts you want to scrape. Default is one hundred. Simple."

[PAUSE]

[SCENE: Step 3 — Live terminal log scrolling]

"Step three — and this is where it gets interesting — is the live scrape. [PAUSE] Watch the terminal."

[PAUSE]

[Slower, reading the logs like they're appearing in real time]

"Searching... [PAUSE] 'hiring AI engineer healthcare.' [PAUSE] Extracting post content. [PAUSE] Email found. [PAUSE] Running LLM extraction — role, company, location — using a local Ollama model or Gemini API, depending on your setup."

[PAUSE]

[SCENE: Step 4 — Results summary cards]

"And step four: Results. [PAUSE] Forty-five posts found. Forty-two new and saved. [EMPHASIS] Eighteen came with emails. Thirty-one are confirmed hiring posts."

[PAUSE]

"From here, you can view all posts, jump straight into email outreach, or keep scraping."

---

## SECTION 5 — LINKEDIN POSTS TABLE (2:20 — 2:45)

[SCENE: Posts table — filters active, rows of data visible]

[Informative, matter-of-fact]

"The Posts tab gives you a full searchable table of everything you've collected."

[PAUSE]

"You can filter by role... by domain relevance — high, medium, or low — by whether a post has an email address, or by whether it's a [EMPHASIS] confirmed hiring post."

[PAUSE]

"Each row shows the author, their headline, the role, company, location, domain score, and any email found."

[PAUSE]

"It's essentially your [EMPHASIS] lead database. Organized, queryable, actionable."

---

## SECTION 6 — EMAIL OUTREACH (2:45 — 3:15)

[SCENE: Email Outreach tab — AI drafts visible, selection checkboxes active]

[Warm, a little impressed with itself]

"This is probably my favorite part. [PAUSE] Email Outreach."

[PAUSE]

"You select the posts that have email addresses. [PAUSE] Then hit Generate. [PAUSE] Gemini 2.5 Flash writes [EMPHASIS] personalized cold emails for each one — based on the post content, the role, and your profile."

[PAUSE]

"You can preview and edit every email before it goes out. [PAUSE] Or bulk generate and bulk send — straight through Gmail via SMTP."

[PAUSE]

"Every email sent is logged in the history. [PAUSE] You always know what was sent, when, and to whom."

---

## SECTION 7 — JOB SEARCH AND AUTO-APPLY (3:15 — 3:40)

[SCENE: Job Search tab — multi-platform results with match scores]

[Brisk, confident — covering two features efficiently]

"The Job Search tab pulls listings from LinkedIn, Naukri, and Wellfound — all at once. [PAUSE] Results are ranked by [EMPHASIS] match score against your resume skills. Highest relevance, first."

[PAUSE]

[SCENE: Auto-Apply tab — live status tracker, Playwright running]

"And then there's Auto-Apply. [PAUSE] Playwright handles LinkedIn Easy Apply — filling your resume, phone, email — automatically."

[PAUSE]

"But it's built with [EMPHASIS] safety in mind. Random delays. Human-like mouse movement. A hard cap of twenty applications per day. [PAUSE] Because the last thing you want is a banned account."

[PAUSE]

"Live status tracking shows you exactly what's happening, in real time."

---

## SECTION 8 — SETTINGS AND HISTORY (3:40 — 3:55)

[SCENE: Settings tab, then History tab]

[Quick, clean — wrapping up the tour]

"Settings is where you configure your profile, SMTP credentials, your Gemini API key, and your daily application safety limits."

[PAUSE]

"And History gives you a full log — every application, every status. [PAUSE] Applied. Skipped. Failed. Partial. [PAUSE] Nothing falls through the cracks."

---

## SECTION 9 — CLOSING AND CTA (3:55 — 4:15)

[SCENE: App overview shot — dashboard glowing, sidebar lit up]

[Sincere, developer-to-developer tone]

"JobAutomate is a personal project — built to solve a [EMPHASIS] real problem I faced. And honestly, it's the tool I wish I'd had when I was job hunting."

[PAUSE]

"The full source code is on GitHub. [PAUSE] If you find it useful, a star goes a long way. [PAUSE] And if you build something on top of it — I'd genuinely love to hear about it."

[PAUSE]

[Warm, closing]

"Thanks for watching."

---

## SUMMARY TABLE

| Section | Timestamp | Duration | Words |
|---|---|---|---|
| Hook | 0:00 | 30s | 85 |
| Product Intro | 0:30 | 25s | 70 |
| Dashboard | 0:55 | 35s | 105 |
| LinkedIn Scraper | 1:30 | 50s | 175 |
| Posts Table | 2:20 | 25s | 90 |
| Email Outreach | 2:45 | 30s | 105 |
| Job Search + Auto-Apply | 3:15 | 25s | 105 |
| Settings + History | 3:40 | 15s | 60 |
| Closing + CTA | 3:55 | 20s | 85 |
| **Total** | | **~4:15** | **~880 words** |

---

## TTS GENERATION COMMANDS

### ElevenLabs
```bash
curl -X POST "https://api.elevenlabs.io/v1/text-to-speech/pNInz6obpgDQGcFmaJgB" \
  -H "xi-api-key: YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "YOUR_SCRIPT_HERE",
    "model_id": "eleven_turbo_v2_5",
    "voice_settings": {
      "stability": 0.45,
      "similarity_boost": 0.75,
      "style": 0.30,
      "use_speaker_boost": true
    }
  }' \
  --output scene_X.mp3
```

### Murf AI
```bash
curl -X POST "https://api.murf.ai/v1/speech/generate" \
  -H "api-key: YOUR_MURF_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "voiceId": "en-US-marcus",
    "style": "Conversational",
    "text": "YOUR_SCRIPT_HERE",
    "format": "MP3",
    "sampleRate": 48000
  }' \
  --output scene_X.mp3
```

---

## PRODUCTION NOTES

- Strip all [SCENE:...] markers before feeding to TTS
- Replace [PAUSE] with periods + line breaks (or SSML `<break>` tags)
- For [EMPHASIS]: ElevenLabs handles naturally via context; Murf uses `<emphasis level="strong">word</emphasis>`
- Record Section 4 (Scraper) separately at slightly slower rate for the terminal reading moment
- Background music at 15-20% volume; cut music entirely during terminal log sequence for dramatic effect
