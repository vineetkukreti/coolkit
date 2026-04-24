# JobAutomate — Product Demo Video Storyboard
**Total Duration**: 3 minutes 30 seconds
**Aspect Ratio**: 16:9 (1920x1080)
**FPS**: 30
**Theme**: Dark UI screencasts with motion graphics overlays
**Color Palette**:
  - Background: Deep black (#0a0a0f)
  - Brand purple: (#7c3aed / #6b21a8 range)
  - Green accent: (#22c55e) — success, active, found
  - White text: (#f1f5f9)
  - Dim gray: (#4b5563) — inactive, locked states
  - Orange: (#f97316) — warnings, duplicates, skipped
**Fonts**: Inter (UI text), Geist Mono (terminal/code)

---

## VISUAL FLOW OVERVIEW

```
[HOOK] ──> [APP INTRO] ──> [DASHBOARD] ──> [SCRAPER x4 steps] ──> [POSTS DB]
 0:00         0:15            0:25              0:50                  1:40
   |            |               |                    |                   |
   v            v               v                    v                   v
[CLOSING] <── [SETTINGS] <── [AUTO-APPLY] <── [EMAIL OUTREACH]
  3:15           3:00            2:30               2:00
```

---

## SCENE 1: THE HOOK
**Timecode**: 0:00 – 0:15
**Duration**: 15 seconds
**Goal**: Establish the pain point. Viewer must feel the grind before seeing the solution.

---

### SHOT 1.1 — Opening Black (0:00 – 0:00.5)
**Duration**: 0.5 seconds
**Frame Type**: Full black
**Camera**: Static
**Composition**: Pure black. No elements.
**Motion**: None — hard cut in from black
**Text/Graphics**: None
**Mood/Lighting**: Absolute black. Cold and empty.
**Notes**: This half-second of silence creates tension. No title card, no music — just darkness before the hook hits.

```
+--------------------------------------------------+
|                                                  |
|                    [BLACK]                       |
|                                                  |
+--------------------------------------------------+
```

**Transition**: Hard cut to Shot 1.2

---

### SHOT 1.2 — Overloaded Browser Tabs (0:00.5 – 0:02.5)
**Duration**: 2 seconds
**Frame Type**: Medium — browser window fill
**Camera**: Static. Very slow zoom-in (1.0x to 1.04x over 2s) — barely perceptible creep.
**Composition**: Browser window fills the frame. 15+ open tabs in the tab bar, nearly all LinkedIn job listings — the favicons and titles repeat. One job listing visible in the main area. The sheer number of tabs communicates exhaustion.
**Key Elements**:
  - Foreground: Tab bar — 15+ tabs, LinkedIn blue favicons repeating
  - Midground: A generic LinkedIn job listing (role, company, "Easy Apply" button)
  - Background: OS desktop visible at screen edges
**Motion**: Slow creeping zoom into the tab bar to emphasize the clutter.
**Text/Graphics**: None. Let the visual speak.
**Mood/Lighting**: Bright white of the browser — jarring contrast to the dark world that follows.
**Notes**: Use a real or mockup browser screenshot. The point is "too many tabs = overwhelm."

```
+--------------------------------------------------+
| [LI][LI][LI][LI][LI][LI][LI][LI][LI][LI][+]... |
|--------------------------------------------------|
|  AI Engineer — Google                            |
|  Mountain View, CA  · Full-time                  |
|  [Easy Apply]                                    |
+--------------------------------------------------+
     [tab bar overloaded — 15+ tabs visible]
```

**Transition**: Hard cut (0.1s) to Shot 1.3

---

### SHOT 1.3 — Rejection Email Inbox (0:02.5 – 0:04.5)
**Duration**: 2 seconds
**Frame Type**: Medium — email client fill
**Camera**: Static for 0.5s, then fast pan downward through inbox (0.8s), then hold.
**Composition**: Email inbox. Subject lines dominate the frame. 8–10 visible rows of rejection emails. The reader doesn't need to read every word — the pattern of rejections is immediately recognizable.
**Key Elements**:
  - Foreground: Email list, subject lines readable
  - Midground: Preview pane — first few lines of a rejection body
  - Background: Email client chrome, unread counts
**Motion**: Fast downward pan through the inbox to show the sheer volume. The scroll feels overwhelming.
**Text/Graphics**: Subject lines tell the story — no additional overlays needed.
**Mood/Lighting**: Cold white/gray of email. Clinical and bleak.
**Notes**: Subject lines to show (mock text, no real names):
  "We regret to inform you..."
  "Unfortunately, we have moved forward..."
  "Thank you for your interest, however..."
  "After careful consideration..."
  "We have decided to pursue other candidates..."
  "Thank you for applying — we won't be moving forward..."

```
+--------------------------------------------------+
|  Inbox (47)                               [icon] |
|  [x] We regret to inform you...      2h ago      |
|  [x] Unfortunately, we have...       3h ago      |
|  [x] Thank you for applying...       5h ago      |
|  [x] We have moved forward...        Yesterday   |
|  [x] We regret to inform you...      Yesterday   |
|  [x] After careful consideration...  2 days ago  |
|  [x] We have decided to pursue...    2 days ago  |
|  [x] Thank you for your interest...  3 days ago  |
+--------------------------------------------------+
     [fast pan downward through list]
```

**Transition**: Hard cut (0.1s) to Shot 1.4

---

### SHOT 1.4 — Job Tracking Spreadsheet (0:04.5 – 0:06.5)
**Duration**: 2 seconds
**Frame Type**: Medium — spreadsheet fill
**Camera**: Slow zoom-out (1.15x to 1.0x) — a "reveal of scale" that exposes just how many rows exist.
**Composition**: Google Sheets or Excel. Column headers: Company, Role, Date Applied, Status, Follow-up. 50+ visible rows. Status column shows a parade of "Rejected", "No Response", "Ghost", "Pending" — mostly in shades of gray and red.
**Key Elements**:
  - Foreground: Column headers, top 5 rows clearly visible
  - Midground: Rows 6–30, readable but compressed
  - Background: Row 50+ visible — the spreadsheet has no end
**Motion**: Zoom-out from 1.15x reveals the row count — the viewer realizes how much labor went into this.
**Text/Graphics**: None — column labels and status text tell the story.
**Mood/Lighting**: Cold spreadsheet white. Fluorescent-feeling. Exhausting.

```
+--------------------------------------------------+
|  A: Company  B: Role   C: Applied  D: Status     |
|  Google      SWE       Mar 1       Rejected       |
|  Meta        AI Eng    Mar 2       No Response    |
|  Amazon      MLE       Mar 3       Ghost          |
|  Microsoft   Dev       Mar 4       Pending        |
|  Apple       iOS Eng   Mar 5       Rejected       |
|  Stripe      Backend   Mar 6       No Response    |
|  ...         ...       ...         ...            |
|  (row 52 visible at bottom edge)                 |
+--------------------------------------------------+
     [zoom-out reveals the full exhausting scope]
```

**Transition**: Fade to black (0.3s) — the white of the spreadsheet fades into darkness

---

### SHOT 1.5 — Hero Text Reveal (0:06.5 – 0:15)
**Duration**: 8.5 seconds
**Frame Type**: Full screen — dark background
**Camera**: Static
**Composition**: Pure deep black (#0a0a0f). Single line of white text, perfectly centered horizontally and vertically. The text appears character by character in a typewriter animation. After the full text resolves, a green cursor blinks at the end for 2 seconds, then disappears. The shot holds for 1 more second before the scene transition.
**Key Elements**:
  - Foreground: White text, large — approximately 52px at 1080p
  - Midground: Nothing
  - Background: Deep black with an extremely subtle purple vignette at the edges (barely visible)
**Motion**:
  - Typewriter animation: ~3 seconds to type the full sentence
  - Cursor blinks green (#22c55e) at 500ms interval for 2 seconds after text completes
  - Cursor disappears (fade-out 0.3s)
  - Hold on text for 1.5 seconds
**Text/Graphics**:
  - Text: "What if you could automate all of this?"
  - Font: Geist Mono (monospace — matches the terminal aesthetic of the app)
  - Color: White (#f1f5f9)
**Mood/Lighting**: This is the pivot. Dark = pain. The green cursor is the first hint of the solution's color palette.
**Notes**: The green cursor blink is a deliberate design choice — it primes the viewer for the app's green accent before the logo is revealed. It signals: "the terminal is about to show you something."

```
+--------------------------------------------------+
|                                                  |
|                                                  |
|  "What if you could automate all of this?_"     |
|                                         ^        |
|                              [green blinking cursor]
|                                                  |
|                                                  |
+--------------------------------------------------+
     [text types out character by character, 3s]
     [cursor blinks green for 2s, then fades]
     [hold on text for 1.5s]
```

**Transition to Scene 2**: Fade to black (0.5s), then Scene 2 begins

---

## SCENE 2: APP INTRO
**Timecode**: 0:15 – 0:25
**Duration**: 10 seconds
**Goal**: Introduce the product confidently. Premium feel. Build anticipation before entering the app.

---

### SHOT 2.1 — Logo Emergence from Black (0:15 – 0:18)
**Duration**: 3 seconds
**Frame Type**: Full screen — centered logo reveal
**Camera**: Static. The logo scales up from 0.3x to 1.0x using ease-out-back over 1.2 seconds — a slight overshoot that gives it a premium bounce.
**Composition**: Dead center. The "JA" purple square icon appears first as a small shape, then springs to full size. At full size, the "JobAutomate" wordmark fades and slides in from the right.
**Key Elements**:
  - Center: "JA" purple square icon (matches app sidebar logo exactly — same proportions, same purple #7c3aed, same white "JA" lettering)
  - Right of icon: "JobAutomate" white wordmark
**Motion**:
  - Icon: scales from 0.3x to 1.0x (ease-out-back, 1.2s) — starts at frame center
  - Wordmark: slides in from right (+20px) while fading from 0 to 1 opacity (0.8s, starts at 0.4s delay)
**Text/Graphics**:
  - Icon: Purple square (#7c3aed) with "JA" in white, bold
  - Wordmark: "JobAutomate" in white, same weight as seen in app sidebar
**Mood/Lighting**: The purple icon is the only light source in the frame. Premium, purposeful, quiet.
**Notes**: The icon must be pixel-accurate to what appears in the app sidebar. Same aspect ratio, same shade of purple. This consistency is what makes the intro feel seamless when the app loads.

```
+--------------------------------------------------+
|                                                  |
|                                                  |
|              [ JA ]   JobAutomate                |
|              [purple] [white, slides in right]   |
|                                                  |
|                                                  |
+--------------------------------------------------+
     [icon springs up from small]  [wordmark fades in]
```

**Transition**: Logo stays, tagline builds below

---

### SHOT 2.2 — Tagline + Tech Stack (0:18 – 0:24)
**Duration**: 6 seconds
**Frame Type**: Full screen — logo + tagline + badges composition
**Camera**: Static
**Composition**: The logo from 2.1 shifts upward by ~35px (smooth ease-in-out, 0.5s) to make room. Tagline appears below it. Then five tech badge pills appear in a horizontal row beneath the tagline, left-to-right with stagger.
**Key Elements**:
  - Upper-center: [ JA ] JobAutomate logo (shifted up)
  - Center: Tagline text (medium weight, #a1a1aa — slightly dimmer than logo)
  - Lower-center: Five badge pills in a row
**Motion**:
  - Logo shifts up 35px (ease-in-out, 0.5s)
  - Tagline: slides up from 10px below + fades in (0.4s, starts at 0.3s delay)
  - Badges: appear left-to-right, each 0.1s stagger, scale-bounce (ease-out-back on scale, from 0.6x to 1.0x)
**Text/Graphics**:
  - Tagline: "AI-Powered LinkedIn Job Auto-Applier"
  - Badge 1: "Python" — blue-gray pill
  - Badge 2: "FastAPI" — teal pill
  - Badge 3: "React" — sky blue pill
  - Badge 4: "Playwright" — green pill
  - Badge 5: "Gemini AI" — purple/indigo pill
  - Badge style: semi-transparent dark background, 1px border in matching accent color, small text
**Mood/Lighting**: The staggered badge arrivals feel like a team walking onto a stage — each bringing its capability. By the time all five are visible, the viewer understands the technical depth.

```
+--------------------------------------------------+
|                                                  |
|              [ JA ]   JobAutomate                |
|        AI-Powered LinkedIn Job Auto-Applier      |
|                                                  |
|  [Python] [FastAPI] [React] [Playwright] [Gemini]|
|    ^pop      ^pop     ^pop      ^pop        ^pop  |
|          (0.1s stagger between each)             |
|                                                  |
+--------------------------------------------------+
```

**Transition**: Brief hold (0.5s on complete frame), then zoom-punch dive into the app

---

### SHOT 2.3 — Dive-In Transition (0:24 – 0:25)
**Duration**: 1 second
**Frame Type**: Full screen — transition
**Camera**: Rapid zoom-in from 1.0x to 3.0x, center-focused. The logo blurs out, black stretches, and the dashboard materializes underneath.
**Motion**: Rapid zoom punch — 0.5 seconds of zoom, 0.5 seconds of blur resolving into the dashboard.
**Notes**: This is a cinematic portal device — "diving into the interface." Sound design note: a low whoosh or UI activation sound pairs perfectly here.

**Transition to Scene 3**: Hard cut into the Dashboard at zoom level 1.0x

---

## SCENE 3: DASHBOARD
**Timecode**: 0:25 – 0:50
**Duration**: 25 seconds
**Goal**: Establish scope. Show the breadth of data JobAutomate manages. Make the numbers feel significant.

---

### SHOT 3.1 — Full Dashboard Establishing Shot (0:25 – 0:29)
**Duration**: 4 seconds
**Frame Type**: Wide — full app viewport
**Camera**: Static for 1 second (orientation), then slow zoom-in begins toward the stats cards area (1.0x to 1.12x over 3 seconds).
**Composition**: Complete JobAutomate app. Purple sidebar on left (~20% width). Main content fills 80%. "Dashboard" is active in the sidebar (purple highlight). Stats cards row visible at top of main area. Charts visible below.
**Key Elements**:
  - Foreground: Sidebar — "JA" logo at top, nav items. "Dashboard" is active (purple background highlight on the nav item)
  - Midground: Four stat cards in a row, glassmorphism surfaces with colored icons and large white numbers
  - Background: Two chart sections below the cards row
**Motion**: Slow creeping zoom in toward the stats cards. The zoom endpoint is the cards row — framing the next shot.
**Text/Graphics**: Optional light callout arrow pointing to sidebar: "Navigation" — appears at 1.5s, fades by 3s.
**Mood/Lighting**: The dark UI glows. Purple sidebar is the visual anchor left. Cards emit a subtle warm light from their glass surfaces.

```
+--------------------------------------------------+
| [JA]         |  Dashboard                        |
| JobAutomate  |  ---------------------------------|
|______________|  [  430  ] [  261  ] [  132  ]    |
| > Dashboard  |  [Total  ] [Hiring ] [w/Email]    |
|   Job Search |  ---------------------------------|
|   Auto-Apply |  [Role Distribution Chart]        |
|   LI Posts   |                                   |
|   Email Out  |  [Domain Relevance Chart]         |
|   History    |                                   |
|   Settings   |                                   |
+--------------------------------------------------+
  [purple sidebar]      [glassmorphism cards glow]
```

**Transition**: Continue zoom — dissolves into Shot 3.2

---

### SHOT 3.2 — Stat Cards Zoom + Animated Callouts (0:29 – 0:38)
**Duration**: 9 seconds
**Frame Type**: Medium — stat cards row fills the frame
**Camera**: Slow pan left-to-right across all cards (smooth, 7 seconds total).
**Composition**: The three (or four) main stat cards fill the horizontal width. As the camera pans to center each card, a green ripple pulses from the number, and a floating callout label slides in from above.
**Key Elements**:
  - Card 1 (leftmost): Large white number "430" — icon in purple
  - Card 2: Large white number "261" — icon in green
  - Card 3: Large white number "132" — icon in blue
  - Card 4 (if present): Additional metric
**Motion**:
  - Camera pans left-to-right at a gentle pace (full traversal = 7 seconds)
  - On each card entering center frame:
    - Green ripple circle pulsates outward from the number (2 rings, opacity fading)
    - White callout pill slides down from 8px above: label + number
    - Counter animation: number counts up from 0 to final value (0.8s, ease-out)
**Text/Graphics**:
  - Callout pills: dark background (rgba 0,0,0,0.85), 1px white border at 20% opacity, white text
  - "430 Posts Scraped" — Card 1
  - "261 Hiring Managers" — Card 2
  - "132 With Direct Email" — Card 3
**Mood/Lighting**: The counter animation and ripple pulse make the numbers feel alive — this is real data, not a mockup.
**Notes**: The counter animation (0 to final value in 0.8s, ease-out) is a staple product demo technique. Each number should feel like a mini celebration as it locks in to its final value.

```
Camera panning right. Card 2 now centered:

+--------------------------------------------------+
|              [261 Hiring Managers]               |
|                     ^ callout pill               |
|                                                  |
|    [430]    |    [ 261 ]    |    [132]            |
|    (past)   | [green ripple]|   (upcoming)        |
|             |  counter: 261 |                    |
|             |  Hiring Found |                    |
+--------------------------------------------------+
     [green ripple pulses from number]
     [counter counts 0 → 261 over 0.8s]
```

**Transition**: Zoom out slightly to reveal charts area below cards

---

### SHOT 3.3 — Role Distribution Chart Animation (0:38 – 0:45)
**Duration**: 7 seconds
**Frame Type**: Medium — chart section fills frame
**Camera**: Starts at zoomed-in stat cards, pulls back to reveal chart section below (1.1x to 1.0x, ease-in-out over 1.5s), then slow zoom-in on chart (1.0x to 1.08x over 4s).
**Composition**: The Role Distribution chart (horizontal bar chart or donut) fills the left 65% of the frame. Chart bars/segments animate in from zero. A callout highlights the dominant category.
**Key Elements**:
  - Chart title: "Role Distribution"
  - Horizontal bars — one per role type, extending left-to-right
  - Labels and counts at end of each bar
**Motion**:
  - Bars animate in: each bar extends from 0% to full width, staggered by 0.2s per bar (ease-out)
  - Top bar (dominant role) animates first and is longest
  - A callout arrow slides in pointing to the tallest bar at 3s
**Text/Graphics**:
  - Chart title: "Role Distribution" (white, above chart)
  - Callout arrow: "AI Engineer — most common role"
  - Bar labels: role names + counts (e.g., "AI Engineer — 186")
**Mood/Lighting**: Colored bars against the dark glassmorphism card background. Clean contrast.
**Notes**: If the actual dashboard uses a donut chart instead of bars, replace bars with segment fill animation (each segment sweeps in clockwise from 0 degrees).

```
+--------------------------------------------------+
|  Role Distribution                               |
|  +------------------------------------------+   |
|  | AI Engineer    [========================] |   |
|  | Data Engineer  [====================]     |   |
|  | ML Engineer    [=================]        |   |
|  | DevOps         [============]             |   |
|  | Backend Dev    [=========]                |   |
|  +------------------------------------------+   |
|     ^ callout: "AI Engineer — most common role"  |
+--------------------------------------------------+
     [bars animate in from left, 0.2s stagger]
```

**Transition**: Pan down to Domain Relevance section

---

### SHOT 3.4 — Domain Relevance Breakdown (0:45 – 0:50)
**Duration**: 5 seconds
**Frame Type**: Medium — domain section
**Camera**: Static, gentle pull-back (1.08x to 1.0x) to frame the section cleanly
**Composition**: Domain Relevance breakdown. Color-coded categories: High (green), Medium (yellow), Low (gray), Unknown (dim). Counts per category visible.
**Key Elements**:
  - High relevance bar/segment: green (#22c55e)
  - Medium: yellow (#eab308)
  - Low: gray (#4b5563)
**Motion**:
  - Category fills animate from 0% to full (0.3s stagger between rows)
  - Count numbers animate up (counter, 0.6s each)
**Text/Graphics**:
  - Section title: "Domain Relevance"
  - Callout bubble (appears at 2.5s): "Filter by High to find quality leads"
**Mood/Lighting**: Green dominates the top row, confirming that the scraper found relevant posts. This sets up the scraper deep-dive that follows.
**Notes**: The callout here acts as a teaser for Scene 5 (filtering by domain in the Posts Database).

**Transition to Scene 4**: Sidebar "LinkedIn Posts" (or scraper item) is highlighted by animated cursor. The cursor clicks. Page slides in from the right. The LinkedIn Scraper header appears.

---

## SCENE 4: LINKEDIN SCRAPER (THE STAR FEATURE)
**Timecode**: 0:50 – 1:40
**Duration**: 50 seconds
**Goal**: This is the centerpiece of the product. Show all four steps with deliberate pacing. The live terminal log is the "money shot" — give it maximum screen time.

---

### SHOT 4.1 — Navigate to Scraper (0:50 – 0:53)
**Duration**: 3 seconds
**Frame Type**: Wide — full app viewport
**Camera**: Static
**Composition**: Full app visible. Animated mouse cursor enters from the main content area and moves to the sidebar, targeting the LinkedIn Scraper / LinkedIn Posts nav item.
**Key Elements**:
  - Animated mouse cursor (large, 32x32px, visible against dark background)
  - Sidebar nav item being targeted
  - Page transition: Scraper page slides in from the right
**Motion**:
  - Cursor arcs smoothly from center-right to sidebar (0.8s path, ease-in-out)
  - Click: cursor scale-down + ring ripple at click point
  - Page slides in from right (0.35s, ease-out): "LinkedIn Scraper" heading + step progress bar appear
**Text/Graphics**:
  - As page loads: "LinkedIn Scraper" heading
  - Subtitle: "Connect, scrape, and extract hiring posts"
  - Step progress bar: [1:Connect] ── [2:Configure] ── [3:Scrape] ── [4:Results]
  - Step 1 is active (purple filled circle, numbered "1"). Steps 2–4 are outlined/dim.
**Mood/Lighting**: The step progress bar is the roadmap. Its presence tells the viewer: "there are four things about to happen, and I'll see all of them."
**Notes**: The step bar must match the real UI from 8_Scraper_Connect.png exactly: numbered circles (1, 2, 3, 4), connected by lines, active step is filled/colored, inactive steps are outlined.

```
+--------------------------------------------------+
| [JA]         |  LinkedIn Scraper                 |
| JobAutomate  |  Connect, scrape, and extract...  |
|______________|  [1]────────[2]────────[3]────[4] |
|   Dashboard  |  Connect  Configure  Scrape  Res. |
|   Job Search |  (active)  (dim)     (dim)  (dim) |
| > LI Scraper |                                   |
|   Auto-Apply |  [Connect card appears below]     |
+--------------------------------------------------+
     [cursor click on sidebar]  [page slides in from right]
```

**Transition**: Step 1 card expands into full view

---

### SHOT 4.2 — Step 1: Connect to LinkedIn (0:53 – 1:04)
**Duration**: 11 seconds
**Frame Type**: Medium — Step 1 card dominates
**Camera**: Static. Slow zoom-in from 1.0x to 1.08x over the duration, centering on the "Launch Browser" button by the end.
**Composition**: Matches 8_Scraper_Connect.png directly. "Connect to LinkedIn" card with glassmorphism surface. "Browser is stopped" status row with a red/orange dot. Three buttons below: green "Launch Browser" (primary), dim "Open Chrome Login", dim "Verify Connection". Red "Not Connected" badge in card's top-right corner. Below the card, "Configure Scraping" section is visible but dimmed/locked.
**Key Elements**:
  - Foreground: Connect card — clean glassmorphism surface, visible border
  - Midground: "Browser is stopped" row — red dot + status text
  - Background: "Configure Scraping" section, dimmed (locked)
**Motion**:
  - Shot opens: static for 1.5 seconds. Viewer reads the state.
  - At 1.5s: animated cursor enters frame from right, arcs toward "Launch Browser" button
  - Cursor hover: button brightens slightly (hover state — green gets slightly lighter)
  - Cursor click at 2s: scale-down click animation + ring ripple at button center
  - Button enters loading state: spinner animation, text changes to "Launching..."
  - 1.5 seconds later: status row updates — red dot → yellow dot → green dot, text → "Browser active"
  - "Not Connected" badge in top-right changes: red background fades, green fades in, text changes to "Connected"
  - Step 1 circle in the progress bar fills with a green checkmark
  - "Configure Scraping" section below loses its dimming — it brightens to indicate it is now unlocked
**Text/Graphics**:
  - Callout at shot start: small pill pointing to "Not Connected" badge — "Status: Not Connected"
  - After connection: callout updates — "Connected!" with green checkmark icon
  - Overlay label (bottom-left corner throughout): "Step 1: Launch browser instance"
**Mood/Lighting**: The red-to-green transformation of the badge is the core visual beat of this shot. The green = success color language is being established here and will repeat throughout.
**Notes**: This is a direct replication of the 8_Scraper_Connect.png UI state. The "Launch Browser" button is already green in that screenshot — it is the natural eye magnet. The dimmed "Configure Scraping" section below creates visual anticipation.

```
BEFORE click (initial state — matches screenshot):
+--------------------------------------------------+
|  Connect to LinkedIn            [Not Connected]  |
|  ------------------------------------------------|
|  [red dot] Browser is stopped                    |
|  ------------------------------------------------|
|  [Launch Browser]  [Open Login]  [Verify]        |
|  (green/primary)   (dim)         (dim)           |
+--------------------------------------------------+
|  Configure Scraping  [DIMMED / LOCKED]           |
+--------------------------------------------------+

AFTER click sequence completes:
+--------------------------------------------------+
|  Connect to LinkedIn              [Connected]    |
|  ------------------------------------------------|
|  [green dot] Browser active                      |
|  ------------------------------------------------|
|  [Launch Browser v] [Open Login v] [Verify v]    |
+--------------------------------------------------+
|  Configure Scraping  [NOW ACTIVE / UNLOCKED]     |
+--------------------------------------------------+
     [green ripple from "Connected" badge]
     [step 1 circle gets green checkmark]
```

**Transition**: Step 1 circle gets checkmark in progress bar. Camera pans down to the Configure section as it expands.

---

### SHOT 4.3 — Step 2: Configure Scraping (1:04 – 1:09)
**Duration**: 5 seconds
**Frame Type**: Medium — Configure card fills frame
**Camera**: Static. Quick pan down from Step 1 card to Configure section (0.5s), then static.
**Composition**: The Configure Scraping card is now active and fully expanded. Shows a number input for "Max Posts" and potentially a query/keyword field. Mouse cursor types a value and then clicks "Start Scraping."
**Key Elements**:
  - Card header: "Configure Scraping" — active (not dimmed)
  - Input field: Max posts — cursor types "48"
  - "Start Scraping" button — changes from dim to active (green) as input is valid
**Motion**:
  - Camera pans down to configure card (0.5s pan)
  - Step 2 circle in progress bar activates (purple filled, numbered "2")
  - Cursor clicks into max posts field — field gets focus ring (green border)
  - Typing animation: "4" then "8" appear character-by-character with keypress audio cue
  - "Start Scraping" button activates: gray → green (transition 0.3s)
  - Cursor moves to "Start Scraping" and clicks
**Text/Graphics**:
  - Callout bubble: "Set how many posts to scrape per session"
  - Field label: "Max Posts" with typed value "48" visible
  - Overlay label: "Step 2: Configure search parameters"
**Mood/Lighting**: The activation of the "Start Scraping" button (dim → green) is the trigger moment. The color change signals: "we are ready to go."

```
+--------------------------------------------------+
| [v:Connect] [2:Configure] [3:Scrape] [4:Results] |
|                                                  |
|  Configure Scraping                              |
|  ------------------------------------------------|
|  Max Posts: [ 48 ]  <-- cursor typed this        |
|  ------------------------------------------------|
|  [Start Scraping]  <-- now green/active          |
|      ^ cursor moves here and clicks              |
+--------------------------------------------------+
     [button: dim gray → green on valid input]
```

**Transition**: Smash cut to the live scraping terminal — maximum impact

---

### SHOT 4.4 — Step 3: Live Terminal Scraping Log (1:09 – 1:29)
**Duration**: 20 seconds
**Goal**: This is the "money shot" of the entire video. Spend the full 20 seconds here. The scrolling terminal log is what makes the product feel real, powerful, and technical. Do not rush it.
**Frame Type**: Medium-wide — the full scraper page with terminal dominating the lower 60%
**Camera**: Static for the first 5 seconds (let the terminal establish itself). Then a very slow downward creep follows the text (barely perceptible auto-scroll tracking). At 15 seconds, slow zoom-in (1.0x to 1.08x) to pull the viewer closer to the log text.
**Composition**: Matches 8b_Scraper_Live_Log.png exactly.
  - Top area: Progress bar with Step 3 (Scrape) active — pulsing green indicator on the step circle
  - Subtitle: "Scraping in progress..." in green (#22c55e) with animated ellipsis (... cycles)
  - Query counter: "Query 5 of 48" — updates every few seconds
  - Purple horizontal progress bar below the query label — fills incrementally
  - Green badge top-right: "23 posts found" — increments live
  - Red "Stop" button top-right
  - Terminal box: black background (#000000), fills lower 60% of main content area
  - Log lines in monospace font, color-coded, scrolling upward
**Key Elements**:
  - Green: timestamps, post numbers (#22c55e)
  - White: normal log text, extracted names
  - Cyan: company names
  - Yellow: email addresses
  - Red/Orange: "DUP" prefix lines
  - Purple/dim: file-hash references
**Motion**:
  - Log lines appear one-by-one, each sliding up from below the terminal window (instant reveal, not slow fade — the terminal is fast)
  - Auto-scroll: new lines push old lines upward naturally
  - Query counter updates: "Query 5 of 48" → "6 of 48" → "7 of 48" (at ~6s intervals)
  - Progress bar fills incrementally with each query
  - Posts found badge increments: 23 → 24 → 25 → 26... (with each post extraction line)
  - Cursor is NOT visible during this shot — the automation is running on its own
**Text/Graphics**:
  Four callout boxes appear sequentially, each at a specific log line type. They appear at 3s, 7s, 12s, 17s respectively. Each callout holds for 3 seconds then fades:
  - Callout 1 (3s): Green border — points to a "Searching:" line — "Playwright navigates LinkedIn search"
  - Callout 2 (7s): Blue border — points to "Extracted N new posts" line — "Posts scraped from current page"
  - Callout 3 (12s): Yellow border — points to a line with an email — "Email auto-extracted from post content"
  - Callout 4 (17s): Orange border — points to "DUP:" line — "Smart deduplication — no repeated saves"
  - Overlay label (bottom-left, persistent): "Step 3: Real-time Playwright automation"
**Mood/Lighting**: Pure black terminal background. The green text glows. The scrolling lines feel like watching a machine work. This is the "awe" moment — the product is doing something the viewer has never automated before.
**Notes**: Exact log line format from 8b_Scraper_Live_Log.png (replicate this format precisely):
  "10:21:14  Searching: hiring AI engineers healthcare (5/48)"
  "10:21:16  Extracted 12 new posts from page"
  "10:21:17  LLM extracting role & company..."
  "10:21:19  #21 Rahul Sharma | AI Engineer @ MedAI | High | careers@medai.io"
  "10:21:19  #22 Priya Patel | DevAI Eng @ Curai2 | High | priya@curai.io"
  "10:21:20  DUP: Already in database (content hash match)"
  "10:21:22  Searching: LLM engineer medical AI (6/48)"
  The pipe-delimited format (Name | Role | Domain | Email) is clean and readable even during a demo recording.

```
+--------------------------------------------------+
| [v] Connect [v] Configure [3:Scrape*] [4] Result |
|  "Scraping in progress..."         [26 found][X] |
|  Query 6 of 48  [===========>              ]     |
|  +--------------------------------------------+  |
|  | 10:21:14  Searching: hiring AI eng... (5/48)|  |
|  | 10:21:16  Extracted 12 new posts from page  |  |
|  | 10:21:17  LLM extracting role & company...  |  |
|  | 10:21:19  #21 R.Sharma | AI Eng | High |email| |
|  | 10:21:19  #22 P.Patel  | DevAI  | High |email| |
|  | 10:21:20  DUP: Already in database (match)  |  |
|  | 10:21:22  Searching: LLM engineer med... <──── new line sliding up
|  | 10:21:23  Extracted 9 new posts from page   |  |
|  +--------------------------------------------+  |
|    ^ callout 1      ^ callout 3      ^ callout 4  |
+--------------------------------------------------+
   [green text on pure black]  [lines auto-scroll]
   [badge increments: 23 → 24 → 25 → 26...]
```

**Transition**: Time-lapse effect — terminal scrolls at 5x speed for 0.4 seconds, then smash cut to the Results screen

---

### SHOT 4.5 — Step 4: Scraping Complete Results (1:29 – 1:40)
**Duration**: 11 seconds
**Frame Type**: Medium-wide — full results screen
**Camera**: Static for 3 seconds (let the results cards animate in), then slow pan left-to-right across the cards row (4 seconds), then pull back to show "What's Next?" section (2 seconds).
**Composition**: Matches 8c_Scraper_Results.png exactly.
  - Top: All four step circles now have green checkmarks
  - Heading: "Scraping Complete!" in green (#22c55e), large
  - Subtitle: "45 posts extracted from 12 queries in 4m 32s" in dim text
  - Five result cards in a row: 45 Total Found, 42 New Saved, 3 Duplicates, 18 With Email, 31 Hiring Posts
  - Below cards: "What's Next?" section with three CTA buttons
**Key Elements**:
  - "Scraping Complete!" heading — green, large
  - All four checkmarks in step bar
  - Five stat cards with colored icons (from screenshot: purple, green, orange, blue, pink-red)
  - "What's Next?" section: purple "View All Posts", green "Start Email Outreach", outlined "Scrape More"
**Motion**:
  - Shot opens on the resolved Results screen
  - "Scraping Complete!" heading: scale-in bounce (from 1.2x to 1.0x, ease-out-back, 0.4s)
  - Step bar: all four checkmarks animate in left-to-right (0.25s stagger between each)
  - Result cards: pop in left-to-right (0.4s stagger, scale 0.6x to 1.0x, ease-out-back)
  - Numbers in cards: count up from 0 to final value (0.8s each, triggered as card appears)
  - "What's Next?" section: slides up from 15px below + fades in (0.6s, after all cards done)
  - Cursor enters at 8s and moves to "Start Email Outreach" green button — hovers (button glows slightly)
**Text/Graphics**:
  - Callout pills appear above each card as it pops in (appear with card, fade after 3s):
    - Above card 1 (45): "Total Found"
    - Above card 2 (42): "New Saved"
    - Above card 3 (3): "Smart Dedup"
    - Above card 4 (18): "Ready for Outreach"
    - Above card 5 (31): "Active Hiring"
  - Overlay label: "Step 4: Results Summary"
**Mood/Lighting**: This is the payoff. All-green step bar + "Scraping Complete!" + five cards popping in + numbers counting up = a cascade of success signals. The viewer should feel satisfied.
**Notes**: Card icon colors from 8c_Scraper_Results.png (replicate exactly):
  Card 1 (45 Total Found): purple icon
  Card 2 (42 New Saved): green icon
  Card 3 (3 Duplicates): orange icon
  Card 4 (18 With Email): blue icon
  Card 5 (31 Hiring Posts): pink/red icon

```
+--------------------------------------------------+
| [v:Connect] [v:Configure] [v:Scrape] [v:Results] |
|                                                  |
|  [v] Scraping Complete!                          |
|  45 posts extracted from 12 queries in 4m 32s    |
|                                                  |
|  [45]      [42]     [3]      [18]    [31]        |
|  Total     Saved    Dups     Email   Hiring       |
|  (pop)     (pop)    (pop)    (pop)   (pop)        |
|  0→45      0→42     0→3      0→18    0→31         |
|                                                  |
|  What's Next?                                    |
|  [View All Posts] [Start Email Outreach] [More]  |
|                    ^ cursor hovers/glows          |
+--------------------------------------------------+
     [cards pop in left-to-right, 0.4s stagger]
     [numbers count up as each card appears]
```

**Transition to Scene 5**: Cursor clicks "View All Posts" — page slides to Posts Database

---

## SCENE 5: POSTS DATABASE
**Timecode**: 1:40 – 2:00
**Duration**: 20 seconds
**Goal**: Show that scraped data is organized, filterable, and actionable. Set up the email outreach flow.

---

### SHOT 5.1 — Posts Table Full View (1:40 – 1:46)
**Duration**: 6 seconds
**Frame Type**: Wide — full posts table viewport
**Camera**: Static for 2 seconds (orientation), then slow scroll downward to reveal more rows (camera tracks down, 3 seconds), then back to top (0.5s snap-back).
**Composition**: Data table with alternating dark rows. Column headers across the top. Filter/search bar above the table. Row count label. Pagination at bottom.
**Key Elements**:
  - Table headers: Author | Role | Company | Domain | Has Email | Hiring | Date
  - 8–10 visible rows of realistic scraped data
  - Row count: "Showing 42 posts"
  - Filter bar above: search input + dropdown filters
**Motion**:
  - Table fades in with page (0.5s)
  - Row count label animates: "Showing 42 posts" (counter, 0 → 42, 0.6s)
  - Row list appears with staggered fade-in from top (0.05s per row)
**Text/Graphics**:
  - Callout: "42 scraped posts organized in searchable database"
  - Callout on "Has Email" column header: small arrow — "Contact info auto-extracted"
**Mood/Lighting**: The structured, orderly table is a visual relief after the chaotic terminal logs. Order from chaos — the scraper created this database.

```
+--------------------------------------------------+
|  LinkedIn Posts                   Showing 42     |
|  [Search...] [Domain: All v] [Email: All v]      |
|  -------------------------------------------------|
|  Author       | Role    | Company  | Dmn | Email  |
|  -------------------------------------------------|
|  R. Sharma    | AI Eng  | Musk2    | Hi  |  [v]   |
|  P. Patel     | DevAI   | Curve2   | Hi  |  [v]   |
|  A. Kumar     | Data E. | Monsoon  | Med |  [x]   |
|  S. Singh     | ML Eng  | TechCo   | Hi  |  [v]   |
|  V. Mehta     | Backend | StartupX | Lo  |  [x]   |
|  D. Nair      | AI Res  | HealthAI | Hi  |  [v]   |
|  ...                                             |
+--------------------------------------------------+
     [rows stagger in from top, 0.05s each]
```

**Transition**: Shot flows into 5.2 as cursor activates filter controls

---

### SHOT 5.2 — Applying Filters in Real Time (1:46 – 1:54)
**Duration**: 8 seconds
**Frame Type**: Medium — filter bar + table top
**Camera**: Static. Brief zoom-in onto the filter bar (1.0x to 1.06x over 1s) then holds.
**Composition**: Zoomed into the filter bar area. Dropdowns open and options are selected. Table rows update instantly as each filter is applied.
**Key Elements**:
  - Domain dropdown: opens, "High" is selected
  - Has Email toggle: activates
  - Row count updates after each filter
**Motion**:
  - Cursor clicks Domain dropdown: opens (slides down with 0.2s animation)
  - Cursor selects "High": item highlights, dropdown closes
  - Table row count: "42 posts" → "25 posts" (counter animates down, 0.4s)
  - Cursor clicks Has Email toggle: toggles on (pill animates green)
  - Table row count: "25 posts" → "18 posts" (counter animates down, 0.4s)
  - Active filter pills appear below filter bar: "[Domain: High ×]  [Has Email ×]"
**Text/Graphics**:
  - Active filter pills animate in (slide up + fade)
  - Callout bubble: "Laser-focus on your best leads"
  - Row count changing: the number update is itself the callout
**Mood/Lighting**: The instant filter response communicates a fast, well-engineered app. Each filter tightens the funnel visually.

```
+--------------------------------------------------+
|  [Search...] [Domain: High v] [Email: Yes v]     |
|  Active: [Domain: High x]  [Has Email x]         |
|  Showing 18 posts  (animated: 42 → 25 → 18)      |
|  -------------------------------------------------|
|  R. Sharma  | AI Eng | Musk2  | HIGH | [email v]  |
|  P. Patel   | DevAI  | Curve2 | HIGH | [email v]  |
|  D. Nair    | AI Res | HealthA| HIGH | [email v]  |
|  (only high-domain + has-email rows remain)       |
+--------------------------------------------------+
     [filter pills animate in]  [row count ticks down]
```

**Transition**: Cursor clicks a row to open detail view

---

### SHOT 5.3 — Post Detail Panel (1:54 – 2:00)
**Duration**: 6 seconds
**Frame Type**: Medium — detail panel / expanded row
**Camera**: Static. Slight zoom-in on the detail panel as it opens (0.3s).
**Composition**: Clicking a row opens a detail panel (slides in from the right, or expands inline below the row). Shows full extracted data: Author name, role, company, extracted email (partially redacted: r***@musk2.io), LinkedIn post URL, domain score badge, post excerpt, action buttons.
**Key Elements**:
  - Author info: name, role, company
  - Email field: semi-obscured (privacy), green dot next to it ("Email found")
  - Domain score badge: "High" in green
  - Action buttons: "Send Email" (green, primary), "Mark Reviewed" (outlined)
**Motion**:
  - Panel slides in from right OR expands downward (ease-out, 0.4s)
  - Email field: green dot pulses once as it becomes visible
  - Domain "High" badge glows briefly
  - Cursor moves to "Send Email" button at 4s and hovers (button brightens)
**Text/Graphics**:
  - Callout pointing to email: "Email extracted from post content"
  - Callout on domain badge: "Relevance scored by AI"
**Mood/Lighting**: The detail panel is rich with actionable data. The cursor ending on "Send Email" creates a natural handoff to the next scene.

**Transition to Scene 6**: Cursor clicks "Send Email" — smooth wipe transition to Email Outreach

---

## SCENE 6: AI EMAIL OUTREACH
**Timecode**: 2:00 – 2:30
**Duration**: 30 seconds
**Goal**: Demonstrate that AI generates high-quality, personalized cold emails. Show the human-in-the-loop edit and send flow.

---

### SHOT 6.1 — Email Outreach Page Overview (2:00 – 2:04)
**Duration**: 4 seconds
**Frame Type**: Wide — full email outreach viewport
**Camera**: Static for 1.5s (orientation), then slow zoom-in to the AI generate button (1.0x to 1.07x)
**Composition**: Email Outreach page. Split layout: left panel = list of posts selected for outreach, right panel = email composer (empty initially). Prominent "Generate with AI" button in the composer panel.
**Key Elements**:
  - Left panel: Post list, 2–3 posts with checkboxes checked (purple fill)
  - Right panel: Empty compose form — To (pre-filled from post), Subject (empty), Body (empty)
  - Prominent "Generate with AI" button — center of composer
**Motion**:
  - Page slides in from right (from previous scene transition)
  - Checkboxes on 2 posts show as already selected (checked state)
  - "Generate with AI" button pulses with a gentle glow (3-pulse animation, subtle)
**Text/Graphics**:
  - Callout: "Select posts, generate personalized emails instantly"
  - Left panel label: "2 posts selected"
  - "To:" field pre-filled: the email from the post detail

```
+--------------------------------------------------+
|  Email Outreach                                  |
|  +---Post List---------+---Compose Email------+  |
|  | [v] R.Sharma / AI   |  To: r***@musk2.io   |  |
|  | [v] P.Patel / DevAI |  Subject: ___        |  |
|  | [ ] A.Kumar / Data  |  Body:               |  |
|  |                     |                      |  |
|  |  2 selected         |  [Generate with AI]  |  |
|  |                     |    ^ pulsing glow     |  |
|  +---------------------+----------------------+  |
+--------------------------------------------------+
     [checkboxes checked]   [AI button pulses]
```

**Transition**: Cursor clicks "Generate with AI"

---

### SHOT 6.2 — AI Email Generation in Progress (2:04 – 2:08)
**Duration**: 4 seconds
**Frame Type**: Medium — composer right panel
**Camera**: Static
**Composition**: The composer panel shows loading state, then text begins generating.
**Key Elements**:
  - 1-second loading state: "Generating..." with spinner or pulsing dots
  - Subject line appears first (typewriter, fast — 0.5s)
  - Email body generates paragraph by paragraph
  - "Gemini AI" small badge appears bottom-right of compose box
**Motion**:
  - Spinner/dots: 1 second
  - Subject field: fills with text via typewriter (fast, 0.5s)
  - Body: generates paragraph by paragraph via typewriter (paragraph 1 → paragraph 2 → signature)
  - Gemini badge fades in at 2s with a subtle shimmer
**Text/Graphics**:
  - Subject generates: "Saw your post about the AI Engineer role at Musk2"
  - Body generates (personalized cold email):
    "Hi Rahul,
    I came across your LinkedIn post about the AI Engineer opening at Musk2. Your work on [specific detail from post] caught my attention — it aligns closely with what I've been building..."
  - Badge: small "Gemini AI" pill, bottom-right corner of compose area
  - Callout appearing at 2.5s: "Personalized using post content + your profile"
**Mood/Lighting**: The typewriter generation is the "magic" moment. Text appearing in real-time makes the AI feel present and active, not canned.
**Notes**: The email body should look genuinely good — not a template. Mention the person's name, their company, reference something specific from their post. This quality is what differentiates AI-generated from spam.

```
+--------------------------------------+
|  To: r***@musk2.io                   |
|  Subject: Saw your post about the... | <- typewriter
|  -----------------------------------  |
|  Hi Rahul,                           |  <- generates
|                                      |
|  I came across your LinkedIn post    |  <- generates
|  about the AI Engineer opening at    |
|  Musk2. Your work on healthcare AI   |
|  caught my attention...          _   |
|                   [cursor blinks]    |
|              [Gemini AI badge right] |
+--------------------------------------+
     [text generates character-by-character]
```

**Transition**: Generation completes — composer becomes active/editable

---

### SHOT 6.3 — Review, Edit, and Send (2:08 – 2:22)
**Duration**: 14 seconds
**Frame Type**: Medium — full composer panel
**Camera**: Static. Very slow zoom-in on the email body (1.0x to 1.12x over 10s) to make the text legible.
**Composition**: Completed AI-generated email fills the compose view. The email is fully readable. Cursor enters and makes a small edit to demonstrate editability. Then moves to "Send Email" button.
**Key Elements**:
  - Complete subject line
  - Complete email body (3–4 paragraphs, ~140 words)
  - "Send Email" green button below
  - Word count or character count visible (optional)
**Motion**:
  - Camera slowly zooms in (makes email body text large enough to read key phrases)
  - At 5s: cursor enters composer, clicks into body text, selects a word (double-click selection highlight)
  - Cursor types a replacement word (backspace + type — shows editability)
  - At 10s: cursor moves down to "Send Email" button
  - At 11s: click — button enters loading state (0.5s), then:
    - Button changes to green checkmark + "Sent"
    - Toast notification slides in from top-right: "Email sent to r***@musk2.io" (green, 2s hold)
**Text/Graphics**:
  - Callout near subject line: "AI-generated, fully editable before sending"
  - Toast: "Email sent to r***@musk2.io" — green background, white text, slides in from top-right
  - Overlay label: "Human-in-the-loop — review before every send"
**Mood/Lighting**: The edit step is critically important messaging — this is not an automated spam cannon. The human reviews and approves each email. The send confirmation is satisfying.

**Transition**: Zoom out to reveal email history panel (6.4) — the sent email appears in history

---

### SHOT 6.4 — Email Sent History (2:22 – 2:30)
**Duration**: 8 seconds
**Frame Type**: Medium — email history list
**Camera**: Static. Slow downward pan through the history list (2 seconds), then back to a framing that shows all statuses.
**Composition**: An email history section below the compose area, or a history tab/page. A list of previously sent emails. Each row: recipient name, subject preview, sent date, and a status badge.
**Key Elements**:
  - List of 5–6 sent emails
  - Status badges: "Sent" (blue), "Opened" (yellow), "Replied" (green)
  - The most recent email (just sent in 6.3) appears at the top with "Sent" badge
**Motion**:
  - New sent email slides into the top of the list (comes from above the list)
  - Status "Sent" badge animates in (pop-in, 0.3s)
  - Camera pans slowly down to reveal older emails with different statuses
  - "Replied" badge on one email pulses green once — draws the eye
**Text/Graphics**:
  - Callout next to "Replied" badge: "Someone replied — track every response"
  - Overlay label: "Full delivery and engagement tracking"
**Mood/Lighting**: The "Replied" status in green is the highest value signal in this scene. Someone responded to an AI-generated email. The loop closed.

**Transition to Scene 7**: Navigate to Auto-Apply section via sidebar or CTA button

---

## SCENE 7: AUTO-APPLY ENGINE
**Timecode**: 2:30 – 3:00
**Duration**: 30 seconds
**Goal**: Show browser automation in action. Emphasize safety guardrails. Make the viewer comfortable with automation.

---

### SHOT 7.1 — Auto-Apply Page Overview (2:30 – 2:37)
**Duration**: 7 seconds
**Frame Type**: Wide — full auto-apply viewport
**Camera**: Static for 1.5s (orientation), slow zoom toward the safety configuration panel (1.0x to 1.08x over 5s)
**Composition**: Auto-Apply page. Header "Auto-Apply Engine" or "Auto-Apply". Left/top: configuration panel with safety settings visible. Right/bottom: status panel showing queue and live results.
**Key Elements**:
  - Configuration: "Max applies/day: 20", "Delay between: 45s", "Min domain score: High"
  - Status panel: empty initially (queue = 18, Applied = 0, Skipped = 0)
  - "Start Auto-Apply" button — green, primary
**Motion**:
  - Page slides in from right
  - Config values appear card by card with fade-in stagger
  - Cursor enters and clicks "Start Auto-Apply" button at 5s
**Text/Graphics**:
  - Callout on "Max 20/day": "Rate limiting prevents LinkedIn flags"
  - Callout on "Delay 45s": "Randomized delays mimic human timing"
  - Overlay label: "Auto-Apply with built-in safety guardrails"
**Mood/Lighting**: The safety settings are visible and prominent before the apply button is clicked. This communicates responsible design.

```
+--------------------------------------------------+
|  Auto-Apply Engine                               |
|  +---Config-----------+---Status--------------+ |
|  | Max per day: [20]  |  Queue:    18 posts    | |
|  | Delay (sec): [45]  |  Applied:   0          | |
|  | Min Domain:  [High]|  Skipped:   0          | |
|  | Target role: [AI E]|  Errors:    0          | |
|  |                    |                        | |
|  |  [Start Auto-Apply]|                        | |
|  |   ^ cursor clicks  |                        | |
|  +--------------------+------------------------+ |
+--------------------------------------------------+
     [callouts on safety settings]
```

**Transition**: Click fires — engine starts. Shot flows into 7.2.

---

### SHOT 7.2 — Live Apply Status Queue (2:37 – 2:53)
**Duration**: 16 seconds
**Frame Type**: Medium — status panel dominates
**Camera**: Static
**Composition**: The status panel is now active. Job items process through the queue one by one. Each item shows a brief "Processing..." state, then resolves to a status badge. The overall counters at the top update.
**Key Elements**:
  - Top counters: "Applied: 3 | Skipped: 1 | Remaining: 14" — update live
  - Progress bar: fills incrementally
  - Queue list: items appear and process
  - "Applied" badge: green
  - "Skipped" badge: orange/dim
**Motion**:
  - Items drop into the queue one at a time, ~2 seconds apart (simulates the delay between applies)
  - Each item: appears with job info → shows "Processing..." spinner (0.5s) → status badge slides in from right
  - "Applied" badge: green, slides in from right with a brief green flash on the row
  - "Skipped" badge: orange, slides in with a dim orange flash
  - Counter at top increments with each resolution: "Applied: 1 → 2 → 3"
  - Progress bar fills: each apply = +5.5% of the daily limit (20 max)
**Text/Graphics**:
  - Callout on an "Applied" item: "Applied via Playwright browser automation"
  - Callout on a "Skipped" item: "Skipped: score below threshold"
  - Overlay label: "Automated applying — you stay in control"
**Mood/Lighting**: The 2-second cadence creates a rhythm. "Applied... Applied... Skipped... Applied..." The alternation signals intelligence — not spamming every job, but selectively applying.

```
+--------------------------------------------------+
|  Applied: 3  |  Skipped: 1  |  Remaining: 14    |
|  [=========>               ] Daily: 3/20         |
|  -------------------------------------------------|
|  R.Sharma  | AI Eng  | Musk2  |  [Applied  v]    |
|  P.Patel   | DevAI   | Curve2 |  [Applied  v]    |
|  A.Kumar   | Data E. | Monsoon|  [Skipped  -]    |
|  S.Singh   | ML Eng  | TechCo |  [Processing...] |
|                               |  -> [Applied v]   |
|  (next item drops into queue below)              |
+--------------------------------------------------+
     [2s between each item]  [badges slide in from right]
     [counters increment]    [progress bar fills]
```

**Transition**: Zoom out slightly and pan to the safety dashboard section

---

### SHOT 7.3 — Safety Dashboard Closeup (2:53 – 3:00)
**Duration**: 7 seconds
**Frame Type**: Medium — safety indicators panel
**Camera**: Static. Gentle zoom-in on the rate limit and health indicators (1.0x to 1.07x over 5s).
**Composition**: A safety/health panel section. Shows: today's applies vs limit (3/20), cooldown countdown timer, and an account health status indicator.
**Key Elements**:
  - "Today's Applies" gauge: 3 filled of 20 slots — progress bar with "3/20" label
  - "Next Apply in: 42s" countdown — counting down live
  - "Account Health: Healthy" — green indicator with green dot
**Motion**:
  - Rate limit bar: shows 3 of 20 slots filled (animated fill at shot start)
  - Cooldown timer counts down: 42 → 41 → 40 → ... (real-time, each second)
  - Account health indicator: green dot pulses gently (slow 2s pulse, repeating)
**Text/Graphics**:
  - Callout on rate limit: "LinkedIn-safe daily limit"
  - Callout on countdown: "Randomized delays — never the same interval"
  - Callout on health: "Zero flags detected"
**Mood/Lighting**: The green "Healthy" status and the thoughtful rate limiting communicate trustworthiness. This tool was built carefully.

**Transition to Scene 8**: Navigate to Settings via sidebar cursor click

---

## SCENE 8: SETTINGS AND WRAP-UP
**Timecode**: 3:00 – 3:15
**Duration**: 15 seconds
**Goal**: Quick confirmation that setup is simple. One-time configuration, then fully automated.

---

### SHOT 8.1 — Settings Page Fast Pan (3:00 – 3:08)
**Duration**: 8 seconds
**Frame Type**: Wide → Medium (starts wide, camera pans down through sections)
**Camera**: Quick downward pan through the settings page — 1.5 seconds per section. Not dwelling, just touching each area.
**Composition**: Settings page with multiple collapsible or stacked sections. The camera visits three areas: Profile, SMTP Configuration, API Keys.
**Key Elements**:
  - Section 1 — Profile: Name, job title, target role keywords
  - Section 2 — SMTP Config: Email address + password (shown as dots)
  - Section 3 — API Keys: Gemini key (shown as dots), LinkedIn credentials
**Motion**:
  - Camera pans downward at consistent speed
  - Each section gets a callout label that slides in as the camera reaches it, then fades as the camera moves past
  - All password / key fields are visibly obscured with bullet dots (●●●●●●●●)
**Text/Graphics**:
  - Section callouts (each holds 1.5s, fades as camera moves on):
    - "Profile: Your background and target roles"
    - "SMTP: Email sending configuration"
    - "API Keys: Gemini + LinkedIn credentials"
  - Final callout at bottom: "One-time setup. Then fully automated."
  - Callout on any password field: "Credentials stored locally — never sent to any server"
**Mood/Lighting**: The visible password dots on sensitive fields signal security consciousness without needing to explain it.

```
+--------------------------------------------------+
|  Settings                                        |
|  +---------------------------------------------+ |
|  | Profile                          [section 1] | |
|  | Name: Vineet Kukreti             ^callout     | |
|  | Title: AI Engineer / ML Engineer             | |
|  +---------------------------------------------+ |
|  | SMTP Configuration               [section 2] | |
|  | Email: user@gmail.com            ^callout     | |
|  | Password: ●●●●●●●●●●                         | |
|  +---------------------------------------------+ |
|  | API Keys                         [section 3] | |
|  | Gemini API Key: ●●●●●●●●●●●●●●  ^callout     | |
|  +---------------------------------------------+ |
|         "One-time setup. Then fully automated."  |
+--------------------------------------------------+
     [camera pans down]  [callouts per section]
```

**Transition**: Quick zoom-out from Settings, brief montage, then fade to black for closing

---

### SHOT 8.2 — Greatest Hits Montage (3:08 – 3:15)
**Duration**: 7 seconds
**Frame Type**: Wide — rapid cuts, 4 screens
**Camera**: Each cut is a full-viewport screenshot — no camera movement within each cut
**Composition**: Four screens, each holding for ~1.5 seconds. Hard cuts between them. No transitions — pure cinematic pace.
  - Screen 1: Dashboard with all stat cards populated (the "scope" shot)
  - Screen 2: Scraper live terminal log scrolling — green text on black (the "power" shot)
  - Screen 3: Scraper Results with all five cards visible (the "payoff" shot)
  - Screen 4: Email history with "Replied" status visible (the "outcome" shot)
**Motion**: Hard cuts only. Let the images accumulate in the viewer's memory.
**Text/Graphics**: None — pure visual. The UI speaks for itself.
**Mood/Lighting**: This rapid montage creates a sense of breadth. "The whole system, compressed into 7 seconds." The contrast between the terminal black (shot 2) and the more structured dashboard/results views creates visual rhythm.

**Transition**: Last screen fades to black (0.5s) — architecture diagram emerges

---

## SCENE 9: CLOSING
**Timecode**: 3:15 – 3:30
**Duration**: 15 seconds
**Goal**: Leave the viewer with a clear understanding of the system architecture, a CTA to star the repo, and the creator's identity.

---

### SHOT 9.1 — Architecture Flow Diagram (3:15 – 3:21)
**Duration**: 6 seconds
**Frame Type**: Full screen — dark background, animated diagram
**Camera**: Static
**Composition**: Clean deep black background (#0a0a0f). A horizontal flow diagram. Five component nodes appear left-to-right, each with an icon and label, connected by animated arrows.
**Key Elements** (left to right):
  - Node 1: LinkedIn icon — label "LinkedIn"
  - Arrow: "→ scrapes →"
  - Node 2: Browser/Playwright icon — label "Playwright"
  - Arrow: "→ processes →"
  - Node 3: AI/LLM icon — label "Gemini AI"
  - Arrow: "→ stores →"
  - Node 4: Database icon — label "SQLite"
  - Arrow: "→ sends →"
  - Node 5: Email icon — label "SMTP"
**Motion**:
  - Title appears first: "How it works" (fade-in, 0.4s)
  - Nodes appear left-to-right: each pops in (scale 0.6x to 1.0x, ease-out-back, 0.3s)
  - After each node, its connecting arrow draws from left to right (like a line being drawn, 0.3s)
  - Stagger: 0.4s between each node appearance
  - Final state holds for 1.5 seconds — all 5 nodes + 4 arrows visible
**Text/Graphics**:
  - Title above: "How it works"
  - Node labels below each icon
  - Arrow labels between nodes (small, dim text)
**Mood/Lighting**: White and purple nodes on deep black. The drawn arrows feel like electrical connections forming. Clean, precise, technical.

```
+--------------------------------------------------+
|  How it works                                    |
|                                                  |
|  [LinkedIn] → scrapes → [Playwright]             |
|                              |                   |
|                         processes                |
|                              v                   |
|                         [Gemini AI]              |
|                              |                   |
|                           stores                 |
|                              v                   |
|    [SMTP] ← sends ──── [SQLite DB]               |
|                                                  |
|  OR as simpler horizontal read:                  |
|  [LI] ──> [Playwright] ──> [Gemini] ──> [SQLite] ──> [SMTP]
+--------------------------------------------------+
     [nodes pop in left-to-right]
     [arrows draw between them]
```

**Notes**: A horizontal single-row layout is cleaner for video (easier to read left-to-right). Use the linear version: [LinkedIn] → [Playwright] → [Gemini AI] → [SQLite] → [SMTP]

**Transition**: Diagram fades, GitHub CTA appears

---

### SHOT 9.2 — GitHub CTA (3:21 – 3:26)
**Duration**: 5 seconds
**Frame Type**: Full screen — CTA
**Camera**: Static
**Composition**: Deep black background. GitHub octocat logo centered. Repository URL below. Animated star CTA below that. Tagline at the bottom.
**Key Elements**:
  - GitHub octocat (white on black) — scales in first
  - Repository URL: "github.com/vineetkukreti34/job-automate" (or actual URL)
  - Star CTA: outline star icon → fills gold with a sparkle animation
  - Tagline: "Open source. Built with Python + React."
**Motion**:
  - GitHub logo: scale-in from 0.4x to 1.0x (ease-out-back, 0.6s)
  - URL: fades in (0.4s, 0.4s delay)
  - Star: outline state for 0.5s → animates to filled gold with a sparkle burst
  - Star label: "Star the repo" fades in with the star animation
  - Tagline: fades in last (0.4s, after star animation)
**Text/Graphics**:
  - URL text (white)
  - "Star the repo" label next to star icon
  - "Open source. Built with Python + React." (dim gray, small)
**Mood/Lighting**: The gold star is the warmest, brightest element in the frame. It draws the eye to the CTA immediately.

```
+--------------------------------------------------+
|                                                  |
|              [GitHub Octocat Logo]               |
|                                                  |
|        github.com/vineetkukreti34/job-automate   |
|                                                  |
|              [★] Star the repo                   |
|         (outline → gold fill + sparkle)          |
|                                                  |
|         Open source. Built with Python + React.  |
|                                                  |
+--------------------------------------------------+
     [star animates: outline → gold fill]
```

**Transition**: Star fills. Brief hold (0.5s). Fade to black for credits.

---

### SHOT 9.3 — End Card (3:26 – 3:30)
**Duration**: 4 seconds
**Frame Type**: Full screen — credits
**Camera**: Static
**Composition**: "JA" JobAutomate logo centered (same as Scene 2 intro — the bookend). Three credit lines below, fading in sequentially.
**Key Elements**:
  - Logo: [ JA ] JobAutomate (same proportions as Scene 2)
  - Credit line 1: "Built by Vineet Kukreti"
  - Credit line 2: "AI-Powered LinkedIn Job Automation"
  - Credit line 3: "Python · FastAPI · React · Playwright · Gemini AI"
**Motion**:
  - Logo fades in (0.8s)
  - Credit lines fade in, 0.4s stagger between each
  - Hold complete frame for 1.5 seconds
  - Final hard cut to black
**Text/Graphics**:
  - Logo: same as intro
  - Credits: white, centered, fading
**Mood/Lighting**: The return of the intro logo closes the loop. The bookend structure — opening and closing with the same logo on the same deep black — gives the video a complete, intentional feel.

```
+--------------------------------------------------+
|                                                  |
|              [ JA ]   JobAutomate                |
|                                                  |
|                Built by Vineet Kukreti           |
|          AI-Powered LinkedIn Job Automation      |
|   Python · FastAPI · React · Playwright · Gemini |
|                                                  |
+--------------------------------------------------+
     [logo fades in first]  [credits stagger below]
     [hold 1.5s]  [hard cut to black]
```

---

## COMPLETE TIMING REFERENCE

| Scene | Name                    | Start | End   | Duration | Shots |
|-------|-------------------------|-------|-------|----------|-------|
| 1     | The Hook                | 0:00  | 0:15  | 15s      | 5     |
| 2     | App Intro               | 0:15  | 0:25  | 10s      | 3     |
| 3     | Dashboard               | 0:25  | 0:50  | 25s      | 4     |
| 4     | LinkedIn Scraper        | 0:50  | 1:40  | 50s      | 5     |
| 5     | Posts Database          | 1:40  | 2:00  | 20s      | 3     |
| 6     | AI Email Outreach       | 2:00  | 2:30  | 30s      | 4     |
| 7     | Auto-Apply Engine       | 2:30  | 3:00  | 30s      | 3     |
| 8     | Settings + Wrap-Up      | 3:00  | 3:15  | 15s      | 2     |
| 9     | Closing                 | 3:15  | 3:30  | 15s      | 3     |
|       | **TOTAL**               |       |       | **3:30** | **32**|

---

## SCENE TIME ALLOCATION RATIONALE

- **Scene 4 (50s) is the longest** — it earns this time. The scraper is the most technically impressive and differentiated feature. The live terminal log needs at least 20 seconds to land with impact.
- **Scenes 6 and 7 (30s each)** — enough time to show the AI email generation typewriter animation and the live apply queue without rushing.
- **Scene 1 (15s)** — the hook must be tight. Every second of the problem statement without the product showing is a risk of losing the viewer.

---

## ANIMATION SYSTEM

### Easing Reference
| Use case | Easing | Feel |
|----------|--------|------|
| Logo reveals, card pop-ins, badge arrivals | ease-out-back | Bouncy, alive |
| Camera moves (zoom, pan) | ease-in-out | Smooth, professional |
| Counter animations | ease-out | Decelerates to final number |
| Progress bar fills | linear | Mechanical, precise |
| Fade-ins (text, panels) | ease-out | Clean |
| Page slide transitions | ease-out | Crisp navigation |

### Color Semantic System (applied across all motion graphics)
| Color | Meaning | Hex |
|-------|---------|-----|
| Green | Success, active, connected, found, applied | #22c55e |
| Purple | Brand, in-progress, selected | #7c3aed |
| Orange | Warning, duplicate, skipped | #f97316 |
| Blue | Email, informational | #3b82f6 |
| Yellow-gold | Star CTA, medium priority | #eab308 |
| Red | Error, not connected, stop | #ef4444 |
| White | Primary text, numbers | #f1f5f9 |
| Dim gray | Inactive, locked, secondary | #4b5563 |

### Callout Pill Style
- Background: rgba(0, 0, 0, 0.85) — very dark, nearly opaque
- Border: 1px solid rgba(255, 255, 255, 0.18)
- Text: #f1f5f9, 12–13px, Inter Regular
- Arrow: 6px triangle pointing toward the target element
- Appear: slide up 8px + fade in, 0.3s ease-out
- Disappear: fade out only, 0.25s ease-in
- Duration on screen: 2.5–3 seconds unless persistent

---

## TRANSITION VOCABULARY

| From                  | To                    | Transition Type             | Duration |
|-----------------------|-----------------------|-----------------------------|----------|
| Scene 1 (Hook end)    | Scene 2 (Logo)        | Fade through black          | 0.5s     |
| Scene 2 (Dive-in)     | Scene 3 (Dashboard)   | Zoom punch + hard cut       | 0.5s     |
| Scene 3 → Scene 4     | Scraper page          | Slide from right (nav)      | 0.35s    |
| Step 1 → Step 2       | Within Scene 4        | Pan down + expand           | 0.5s     |
| Step 2 → Step 3       | Terminal log          | Smash cut                   | 0s       |
| Step 3 → Step 4       | Results screen        | Time-lapse + smash cut      | 0.4s     |
| Scene 4 → Scene 5     | Posts database        | Slide from right (nav)      | 0.35s    |
| Scene 5 → Scene 6     | Email outreach        | Slide from right (nav)      | 0.35s    |
| Scene 6 → Scene 7     | Auto-apply            | Slide from right (nav)      | 0.35s    |
| Scene 7 → Scene 8     | Settings              | Slide from right (nav)      | 0.35s    |
| Scene 8 montage end   | Scene 9 Architecture  | Fade through black          | 0.5s     |
| Architecture          | GitHub CTA            | Fade                        | 0.4s     |
| GitHub CTA            | End card              | Fade through black          | 0.5s     |
| End card              | Final black           | Hard cut                    | 0s       |

---

## PRODUCTION CHECKLIST

### Screen Recording Setup
- Resolution: 1920x1080 minimum. 2560x1440 preferred (export down to 1080p).
- Browser zoom level: 100% — the UI was designed at this level.
- Cursor size: 32x32px minimum, use a cursor enhancement tool (Cursor Pro on Mac, KDE cursor settings on Linux) to ensure visibility in recordings.
- Mouse movement: smooth, no jerking. If using cursor software, enable smoothing.
- Mic: mute or use a separate audio track for narration. Do not rely on screen recording audio.

### Key App States to Capture
These specific states must be recorded. Each is a distinct app condition that cannot be easily faked in post:

1. Scraper Step 1 — "Not Connected" state (8_Scraper_Connect.png state): red badge, red dot, Launch Browser green button, locked Configure section below.
2. Scraper Step 1 — transition to "Connected" state: status dot going red → green, badge changing.
3. Scraper Step 3 — live terminal log scrolling (8b_Scraper_Live_Log.png state): run a real scrape with 10–20 posts minimum. Record at least 30 seconds of live scrolling.
4. Scraper Step 4 — "Scraping Complete!" results screen (8c_Scraper_Results.png state): all four checkmarks, five stat cards populated.
5. Dashboard — with stats populated after a real scrape run.
6. Posts table — with filters active (Domain: High, Has Email: Yes).
7. Email compose — with an AI-generated email visible in full.
8. Auto-apply — with at least 3–4 items showing "Applied" / "Skipped" badges.
9. Settings — all three sections visible.

### Post-Production Notes
- Ken Burns effects (zoom/pan): apply in DaVinci Resolve or Premiere as post-processing effects on the screen recording — never zoom the browser during recording.
- Callout overlays: create as separate After Effects / Motion / Resolve Fusion layers.
- Counter animations: native AE number counter effect, or use Resolve's text animation.
- Terminal text: if the live log is too fast or too slow, record at normal speed and adjust playback speed in the editor. Aim for lines to appear every 0.5–1 second.
- Color grading: apply a subtle vignette (darkness at screen edges), and a very slight cool temperature shift (-5 on the color wheel) to unify all scenes under a consistent mood.
- Music: bring in at 0:15 (Scene 2 logo reveal). Upbeat, techy instrumental — lo-fi electronic or cinematic tech. Avoid anything too "corporate."

### Sound Design Cues (Reference Timecodes)
| Timecode | Sound Event |
|----------|-------------|
| 0:00–0:15 | Silence or low ambient drone |
| 0:15 | Music starts — upbeat electronic/lo-fi |
| 0:53 (Step 1 click) | Button click SFX + soft success chime |
| 1:09 (Scraping starts) | Terminal startup beep, then subtle data-processing ambience under music |
| 1:29 (Scraping complete) | Success chime — brief, satisfying |
| 2:04 (AI generation starts) | Soft processing sound — hum or sparkle |
| 2:19 (Email sent) | Email whoosh SFX |
| 3:21 (Star button) | Sparkle/star SFX |
| 3:26–3:30 (End card) | Music fades to silence |
