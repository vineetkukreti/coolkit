# JobAutomate — Video Narration Script

**Total Duration:** ~3 minutes 30 seconds
**Voice Style:** Confident male, mid-20s, developer tone — like explaining to a friend. Not salesy.
**TTS Service:** ElevenLabs (Voice: "Josh" or "Antoni") / Murf.ai (Voice: "Marcus")
**Pace:** 150-160 words per minute

---

## SCENE 1: THE HOOK (0:00 — 0:18)

```
[SCENE: Dark screen with typing cursor, then montage of LinkedIn tabs, rejection emails, messy spreadsheets]

[PAUSE 0.5s]

You open LinkedIn. [PAUSE 0.3s] Scroll through hundreds of posts. [PAUSE 0.3s]
Copy an email. Paste it into Gmail. Write a cold email from scratch.
[PAUSE 0.3s] Repeat. [PAUSE 0.2s] Fifty times. [PAUSE 0.5s]

What if all of that [EMPHASIS] — the scraping, the filtering,
the emails, even the applying — [EMPHASIS] was fully automated?

[PAUSE 0.8s]
```

**Word count:** ~52 | **Est. time:** 18 seconds

---

## SCENE 2: APP INTRO + LOGO REVEAL (0:18 — 0:30)

```
[SCENE: Logo animates in — purple "JA" icon, "JobAutomate" text reveals]
[SCENE: Tech stack badges appear: Python, FastAPI, React, Playwright, Gemini AI, SQLite]

This is [EMPHASIS] JobAutomate.
An AI-powered system that scrapes LinkedIn hiring posts,
extracts job data using LLMs, generates personalized cold emails,
and auto-applies to jobs — [EMPHASIS] all from one dashboard.

[PAUSE 0.5s]

Let me show you how it works.

[PAUSE 0.8s]
```

**Word count:** ~46 | **Est. time:** 12 seconds

---

## SCENE 3: DASHBOARD OVERVIEW (0:30 — 0:52)

```
[SCENE: Full dashboard view fades in. Stats cards animate with counting numbers]

Here's the dashboard. [PAUSE 0.3s]
It gives you the full picture at a glance.

[SCENE: Camera zooms into stats cards one by one]

430 LinkedIn posts scraped. [PAUSE 0.2s]
261 confirmed hiring posts. [PAUSE 0.2s]
132 posts with direct email addresses. [PAUSE 0.3s]

[SCENE: Role distribution chart animates]

The role breakdown shows AI Engineer is the most common at 186 posts,
followed by GenAI Engineer, Data Engineer, and ML Engineer.

[SCENE: Domain relevance pie chart]

And every post is scored for healthcare domain relevance —
High, Medium, or Low — since that's my target niche.

[PAUSE 0.6s]
```

**Word count:** ~85 | **Est. time:** 22 seconds

---

## SCENE 4: LINKEDIN SCRAPER — THE STAR FEATURE (0:52 — 1:50)

```
[SCENE: Navigate to Scraper page. 4-step wizard visible: Connect > Configure > Scrape > Results]

Now the main feature — the LinkedIn scraper. [PAUSE 0.3s]
It's a four-step process.

[SCENE: Step 1 — "Connect to LinkedIn" card, "Launch Browser" button highlighted]

Step one — connect. [PAUSE 0.2s]
Hit Launch Browser and it opens a real Chromium instance with your saved LinkedIn session.
No credentials stored, no tokens — just a persistent browser profile.

[PAUSE 0.5s]

[SCENE: Step 2 — Configure scraping, max posts slider]

Step two — configure how many posts to scrape. Default is 100.

[PAUSE 0.3s]

[SCENE: Step 3 — Live terminal log scrolling. Green text on dark background.
Lines appearing: "Searching: hiring AI engineer healthcare (5/48)"
"Extracted 12 new posts from page"
"#25 Rahul Sharma | AI Engineer @ MedAI | High | careers@medai.io"]

Step three is where the magic happens. [PAUSE 0.3s]

The scraper runs 48 targeted search queries across LinkedIn —
healthcare AI first, then broader AI and ML roles. [PAUSE 0.3s]

It scrolls through results, expands truncated posts,
and extracts everything — author name, headline, full content, and email addresses.

[PAUSE 0.3s]

[SCENE: Highlight the LLM extraction line in the log]

Then each post gets sent to a local LLM — Ollama running qwen2.5
— which extracts the [EMPHASIS] role, company, location, and experience level.
If Ollama isn't available, it falls back to Gemini Flash.

[PAUSE 0.3s]

[SCENE: Log shows duplicate detection: "DUP: Already in database (content hash match)" in orange/red]

Duplicates are automatically detected and skipped,
so you can run this daily and only new posts get saved.

[PAUSE 0.5s]

[SCENE: Step 4 — Results summary. Cards animate in: "45 Total Found", "42 New Saved", "3 Duplicates", "18 With Email", "31 Hiring Posts"]

And here are the results. [PAUSE 0.3s]
45 posts found, 42 new ones saved, 18 with email addresses,
and 31 confirmed hiring posts. [PAUSE 0.3s]
All stored in a local SQLite database.

[PAUSE 0.6s]
```

**Word count:** ~230 | **Est. time:** 58 seconds

---

## SCENE 5: LINKEDIN POSTS DATABASE (1:50 — 2:10)

```
[SCENE: Navigate to "LinkedIn Posts" page. Table view with rows of data]

Over in the Posts tab, you get a searchable, filterable table
of every post in your database. [PAUSE 0.3s]

[SCENE: Click filter — domain: "High", toggle: "Has Email", toggle: "Is Hiring"]

Filter by domain relevance, [PAUSE 0.1s] email availability, [PAUSE 0.1s]
hiring status, [PAUSE 0.1s] or specific roles. [PAUSE 0.3s]

[SCENE: Expand a post row to show details — author, headline, role, company, email, content preview]

Each post shows the author, their role, company, location,
and the extracted email — ready for outreach.

[PAUSE 0.6s]
```

**Word count:** ~72 | **Est. time:** 20 seconds

---

## SCENE 6: AI-POWERED EMAIL OUTREACH (2:10 — 2:42)

```
[SCENE: Navigate to "Email Outreach" page. List of outreach-ready posts]

Now here's where it gets [EMPHASIS] really powerful. [PAUSE 0.3s]

The Email Outreach tab shows every post that has an email address
and a hiring signal. [PAUSE 0.3s]

[SCENE: Click "Generate Email" on a post. Loading spinner, then AI-generated email appears]

Click generate, and Gemini 2.5 Flash writes a personalized cold email
— not a generic template. [PAUSE 0.2s]
It references the specific post, matches your skills to their requirements,
and keeps it under 150 words. [PAUSE 0.3s]

[SCENE: Show the email preview — subject line + body. Edit fields visible]

You can preview, edit, and tweak before sending. [PAUSE 0.3s]

[SCENE: Click "Send". Success toast notification]

Hit send, and it goes out through your Gmail SMTP. [PAUSE 0.3s]

[SCENE: Show "Bulk Generate" selecting multiple posts, then "Bulk Send"]

And yes — you can bulk generate and bulk send
across dozens of contacts in one go.

[PAUSE 0.6s]
```

**Word count:** ~130 | **Est. time:** 32 seconds

---

## SCENE 7: AUTO-APPLY ENGINE (2:42 — 3:08)

```
[SCENE: Navigate to "Auto-Apply" page. Job cards with "Apply" buttons]

The Auto-Apply engine takes it even further. [PAUSE 0.3s]

[SCENE: Show the Playwright browser automating a LinkedIn Easy Apply form — filling fields, clicking buttons]

It uses Playwright to automate LinkedIn Easy Apply —
filling in your resume, phone number, and email,
then stepping through each form page automatically.

[PAUSE 0.3s]

[SCENE: Safety dashboard panel — rate limits highlighted]

And it's built with safety-first design. [PAUSE 0.2s]
Max 20 applications per day. [PAUSE 0.1s]
Max 15 per session. [PAUSE 0.1s]
Random delays between 30 to 90 seconds between jobs. [PAUSE 0.2s]
Human-like mouse movements and scrolling. [PAUSE 0.3s]

All to keep your LinkedIn account safe.

[PAUSE 0.6s]
```

**Word count:** ~100 | **Est. time:** 26 seconds

---

## SCENE 8: ARCHITECTURE + CLOSING (3:08 — 3:30)

```
[SCENE: Animated architecture diagram flows in:
LinkedIn (Playwright) → Scroll & Extract → Local LLM (Ollama) → SQLite DB → Email Outreach / Auto-Apply]

Under the hood — Playwright handles the browser automation,
a local LLM extracts structured data from raw post text,
SQLite stores everything with dedup,
and Gemini generates the outreach emails.

[PAUSE 0.5s]

[SCENE: GitHub repo card with star button. "JobAutomate" logo]

The entire project is open source. [PAUSE 0.3s]
Link in the description. [PAUSE 0.2s]
If this saved you time, drop a star on the repo. [PAUSE 0.3s]

[SCENE: End card — "Built by Vineet Kukreti" + LinkedIn + GitHub links]

Thanks for watching.

[PAUSE 1.0s]
```

**Word count:** ~80 | **Est. time:** 22 seconds

---

## TOTAL SUMMARY

| Scene | Duration | Words |
|-------|----------|-------|
| 1. Hook | 18s | 52 |
| 2. App Intro | 12s | 46 |
| 3. Dashboard | 22s | 85 |
| 4. Scraper | 58s | 230 |
| 5. Posts DB | 20s | 72 |
| 6. Email Outreach | 32s | 130 |
| 7. Auto-Apply | 26s | 100 |
| 8. Closing | 22s | 80 |
| **TOTAL** | **~3:30** | **~795** |

---

## TTS GENERATION NOTES

### ElevenLabs Settings
- **Voice:** Josh (American, confident, young) or Antoni (British, clean)
- **Stability:** 0.50 (natural variation)
- **Similarity Boost:** 0.75
- **Style:** 0.30 (slight expressiveness)
- **Speaker Boost:** ON

### Murf.ai Alternative
- **Voice:** Marcus (US, Conversational)
- **Speed:** 1.0x
- **Pitch:** Default
- **Emphasis:** Use built-in emphasis markers on [EMPHASIS] words

### Pauses
- Generate each scene as a separate audio clip for easier editing
- Add 0.5s silence between scenes in post-production
- [PAUSE Xs] markers = insert silence of X seconds in TTS or editing

### Pronunciation Guide
- "Ollama" = oh-LAH-mah
- "qwen" = chwen (rhymes with "when")
- "SQLite" = S-Q-Lite (spell out S-Q then "lite")
- "FastAPI" = Fast-A-P-I
- "Gemini" = JEM-in-eye
- "SMTP" = S-M-T-P (spell out)
- "Playwright" = PLAY-right
