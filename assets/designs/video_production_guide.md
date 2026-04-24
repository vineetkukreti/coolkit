# JobAutomate — Video Production Guide

**Video Title:** "I Built an AI That Applies to Jobs For Me (Open Source)"
**Alt Titles:**
- "This AI Scrapes LinkedIn & Applies to Jobs Automatically"
- "I Automated My Entire Job Search with AI"

**Duration:** ~3:30
**Format:** Product demo / developer showcase
**Platform:** YouTube, LinkedIn, Twitter/X

---

## PRODUCTION PIPELINE

### Phase 1: Pre-Production (You Are Here)
- [x] Narration script (`video_script.md`)
- [x] Scene-by-scene storyboard (`video_storyboard.md`)
- [x] Sound design plan (`video_sound_design.md`)
- [x] Thumbnail spec (`video_thumbnail.md`)
- [x] Production guide (this file)

### Phase 2: Asset Capture
- [ ] Screen record the actual app (see Recording Guide below)
- [ ] Generate TTS audio from script
- [ ] Download background music + SFX

### Phase 3: Editing
- [ ] Assemble screen recordings following storyboard
- [ ] Sync narration audio to visuals
- [ ] Add text overlays, callouts, transitions
- [ ] Add motion graphics (number counters, diagrams)
- [ ] Mix audio (voice + music + SFX)

### Phase 4: Polish
- [ ] Color grade for consistent dark theme look
- [ ] Add intro/outro animations
- [ ] Create thumbnail image
- [ ] Export final video (1080p, 30fps)
- [ ] Write YouTube description + tags

---

## SCREEN RECORDING GUIDE

### Software
- **OBS Studio** (free) or **Kooha** (Linux, simple)
- Resolution: 1920x1080
- FPS: 30
- Format: MKV (convert to MP4 after)

### Recordings Needed

**Recording 1: Dashboard Walkthrough (30s)**
1. Start the app: `./start.sh`
2. Open http://localhost:8000 in browser
3. Browser should be full-screen, no URL bar clutter
4. Slowly scroll through dashboard
5. Hover over stats cards and charts

**Recording 2: Scraper Full Flow (60s)**
1. Navigate to "LinkedIn Scraper" in sidebar
2. Click through Step 1 (Connect) — Launch Browser
3. Step 2 (Configure) — Set max posts to 50
4. Step 3 (Scrape) — Let it run, capture the live log
5. Step 4 (Results) — Capture the summary cards
6. NOTE: You need to be logged into LinkedIn for this to work

**Recording 3: Posts Database (15s)**
1. Navigate to "LinkedIn Posts" in sidebar
2. Show the full table
3. Apply filters: Domain=High, Has Email=on, Is Hiring=on
4. Expand one post to show details

**Recording 4: Email Outreach (25s)**
1. Navigate to "Email Outreach" in sidebar
2. Click "Generate Email" on a post
3. Wait for AI to generate
4. Show the email preview
5. (Optional) Click Send if you want to show that flow

**Recording 5: Auto-Apply (20s)**
1. Navigate to "Auto-Apply" in sidebar
2. Show the job search results
3. Show the safety settings panel
4. (Optional) Run an actual auto-apply if safe to demo

**Recording 6: Settings (10s)**
1. Navigate to "Settings" in sidebar
2. Quick scroll through: Profile, SMTP, API keys, Safety limits

### Recording Tips
- Use a clean browser profile (no extensions showing)
- Close all other tabs
- Hide system notifications
- Mouse movements should be smooth and deliberate
- Pause 1-2 seconds on important elements before moving

---

## TTS AUDIO GENERATION

### Option A: ElevenLabs (Recommended)
1. Go to https://elevenlabs.io
2. Select voice: "Josh" or "Antoni"
3. Settings: Stability=0.50, Similarity=0.75, Style=0.30
4. Generate each scene separately (8 audio clips)
5. Export as MP3/WAV
6. Replace [PAUSE Xs] with actual silence in editing

### Option B: Murf.ai
1. Go to https://murf.ai
2. Select voice: "Marcus" (US, Conversational)
3. Paste script, adjust emphasis on [EMPHASIS] words
4. Generate and export

### Option C: Free TTS
1. Google Cloud TTS (free tier)
2. Use "en-US-Neural2-J" (male, natural)
3. SSML tags for pauses: `<break time="500ms"/>`

---

## EDITING SOFTWARE

### Recommended: DaVinci Resolve (Free)
- Professional grade, free
- Great color grading
- Built-in motion graphics (Fusion)
- Audio mixing built in

### Alternative: Kdenlive (Free, Linux-native)
- Lighter weight
- Good for basic assembly
- Add text overlays

### Alternative: CapCut (Free, web-based)
- Fastest for simple edits
- Auto-captions
- Easy text animations

---

## TEXT OVERLAYS NEEDED

| Timecode | Text | Style |
|----------|------|-------|
| 0:10 | "What if all of this was fully automated?" | Large, white, center, fade-in word by word |
| 0:18 | "JobAutomate" | Logo + purple glow |
| 0:22 | "AI-Powered LinkedIn Job Auto-Applier" | Subtitle, typewriter |
| 0:26 | Tech stack badges | Small pills, stagger-in |
| 1:10 | "48 targeted search queries" | Callout with arrow |
| 1:25 | "Local LLM extracts structured data" | Floating tooltip |
| 1:42 | "Automatic dedup" | Callout on DUP line |
| 2:16 | "Powered by Gemini 2.5 Flash" | Small badge |
| 2:58 | "Built for account safety" | Shield icon + text |
| 3:18 | "Star the repo" | Golden glow on star |

---

## MOTION GRAPHICS NEEDED

1. **Number Counter** — Stats cards counting from 0 to final value
2. **Progress Bar** — Filling animation for scraper progress
3. **Architecture Diagram** — Nodes + arrows appearing sequentially
4. **Checkmark Animations** — Green checkmarks on wizard steps
5. **Data Flow Particles** — Moving dots along architecture arrows
6. **Email Typewriter** — AI email text appearing character by character

### Tools for Motion Graphics
- **DaVinci Resolve Fusion** — Built-in node-based compositing
- **Natron** (free After Effects alternative)
- **CSS animations rendered to video** (if using Remotion)

---

## YOUTUBE METADATA

### Title
"I Built an AI That Applies to Jobs For Me (Open Source)"

### Description
```
I got tired of manually applying to hundreds of jobs on LinkedIn, so I built JobAutomate — an AI-powered system that scrapes LinkedIn hiring posts, extracts job data using local LLMs, generates personalized cold emails with Gemini AI, and auto-applies to jobs using browser automation.

Features:
- Scrapes 430+ LinkedIn hiring posts automatically
- Extracts role, company, location using local LLM (Ollama)
- AI-generated personalized cold emails (Gemini 2.5 Flash)
- Automated LinkedIn Easy Apply with anti-ban safety
- Beautiful dark-themed dashboard
- Open source!

Tech Stack: Python, FastAPI, React, Playwright, SQLite, Gemini AI, Ollama

GitHub: [repo link]
LinkedIn: linkedin.com/in/vineetkukretii

Timestamps:
0:00 - The Problem
0:18 - Introducing JobAutomate
0:30 - Dashboard Overview
0:52 - LinkedIn Scraper (Main Feature)
1:50 - Posts Database
2:10 - AI Email Outreach
2:42 - Auto-Apply Engine
3:08 - Architecture & Closing

#AI #LinkedIn #JobSearch #Automation #Python #OpenSource
```

### Tags
```
ai job search, linkedin automation, job auto apply, ai engineer, linkedin scraper, cold email ai, playwright automation, job hunting automation, open source project, python fastapi, gemini ai, ollama, job search tool, linkedin easy apply bot, ai cold email, career automation
```

### End Screen
- Subscribe button (top right)
- Next video suggestion (bottom right)
- Link to GitHub repo (bottom left)

---

## SOCIAL MEDIA CLIPS

### Clip 1: Twitter/X (30s)
- Scenes 4.4 + 4.6 (scraper running + results)
- Caption: "Built an AI that scrapes LinkedIn, extracts job data with LLMs, generates cold emails, and auto-applies. All open source."

### Clip 2: LinkedIn (45s)
- Scenes 1 + 4 + 6 (hook + scraper + email)
- Caption: "Tired of manually applying to jobs? I built a tool for that. [link]"

### Clip 3: Instagram/TikTok Reel (15s)
- Fast montage: Dashboard → Scraper log → Email generated → "Applied!"
- Trending audio or original with bass drop
- Text overlay: "POV: You automated your entire job search"

---

## FILE ORGANIZATION

```
designs/
  video_script.md           # Full narration script with TTS markers
  video_storyboard.md       # Scene-by-scene visual breakdown
  video_sound_design.md     # Music, SFX, and audio mixing plan
  video_thumbnail.md        # Thumbnail design specification
  video_production_guide.md # This file — master production guide

recordings/                 # Create this folder for screen recordings
  01_dashboard.mkv
  02_scraper_flow.mkv
  03_posts_database.mkv
  04_email_outreach.mkv
  05_auto_apply.mkv
  06_settings.mkv

audio/                      # Create this folder for audio
  narration/
    scene_01_hook.mp3
    scene_02_intro.mp3
    scene_03_dashboard.mp3
    scene_04_scraper.mp3
    scene_05_posts.mp3
    scene_06_email.mp3
    scene_07_autoapply.mp3
    scene_08_closing.mp3
  music/
    background_track.mp3
  sfx/
    typing.mp3
    click.mp3
    success.mp3
    whoosh.mp3
    counter_tick.mp3

exports/                    # Final exports
  jobAutomate_demo_final.mp4
  thumbnail_1280x720.png
  twitter_clip_30s.mp4
  linkedin_clip_45s.mp4
  tiktok_reel_15s.mp4
```
