# O-Deck UI/UX Design Handoff

Date: 2026-04-26
Status: Design baseline for implementation
Source inputs:
- `docs/superpowers/specs/2026-04-26-cyberdeck-dashboard-design.md`
- `design/design-chat-context.md`
- `design/screens/*`

## 1) Design Intent

The O-Deck interface should feel like an ambient desk object first, utility surface second. The product sits at ~4 ft viewing distance, runs in dark mode full-time, and must remain legible while adding subtle motion and personality.

Primary intent:
- Glanceable at distance
- Calm but alive (not static, not noisy)
- Personal cyberdeck identity ("O-DECK", callsign language)
- Functional density where needed (fullscreen apps), restraint on home

## 2) Final Direction (Current)

The preferred direction is Variation C evolved to C v3 ("Atelier"):
- Editorial cyberdeck tone over "car UI" tone
- Asymmetric composition instead of rigid card grid
- Time as dominant hero
- Now Playing as right-side vertical strip (type-forward, smaller art)
- Warm-neutral dark palette with secondary cool/sage accents
- Slow blurred motion background (drifting orbs), not busy flow-field particles
- Light data animation for liveness (seconds, train drift, heartbeat, ticker)

This is the default visual baseline for v1 implementation.

## 3) Visual System

### 3.1 Color Tokens

From `design/screens/system.jsx`:

- `bg`: `#15130f`
- `bgRaised`: `rgba(31,28,24,0.78)`
- `bgSolid`: `#1f1c18`
- `ink`: `#f0e8d6`
- `inkDim`: `rgba(240,232,214,0.55)`
- `inkSub`: `rgba(240,232,214,0.32)`
- `accentSand`: `#e6c89b`
- `accentSage`: `#a8c19a`
- `accentRose`: `#d49a8e`
- `accentLav`: `#a08fb3`
- `line`: `rgba(240,232,214,0.08)`

Guidance:
- Keep base UI neutral-dark.
- Use `accentSand` as primary action/emphasis tone.
- Use `accentSage` for healthy/live states.
- Use `accentRose` for warning/anomaly/delay.
- Use `accentLav` mainly for music/showcase modulation.

### 3.2 Typography

- Sans: `Inter` for high-importance readable UI copy and large numerals.
- Mono: `IBM Plex Mono` for system labels, status strips, metadata.

Behavior:
- Hero time and major metrics should use thin/regular sans with tabular numerals.
- Operational metadata should remain mono with increased letter spacing.
- Do not overuse all-caps in body copy; reserve for compact labels.

### 3.3 Shape + Surface

- Rounded corners only where it improves scan grouping.
- Prefer separators/spacing over heavy card chrome.
- Keep line contrast low (`line`) to avoid hard UI edges in ambient mode.

## 4) Motion + Atmosphere

Motion should communicate "alive system" without demanding attention.

### 4.1 Background Motion

Preferred ambient layer:
- Blurred drifting orb fields (`DriftOrbs`)
- Mode-reactive palettes: `calm`, `music`, `rain`, `thunder`
- Optional rain overlay when weather mode requires it
- Subtle grain overlay for texture

Rules:
- Keep slow velocities and low contrast.
- Avoid dense particle fields on home.
- No abrupt flashes except restrained thunder events.

### 4.2 UI Liveness Cues

Allowed:
- Live seconds next to clock
- Gentle blinking colon
- Transit countdown drift simulation (in design prototypes; in production tie to real updates)
- RSS ticker crawl
- GitHub heartbeat mini-strip
- EQ bars for now playing indicator

Avoid:
- Cursor typing animation on home
- Multiple high-frequency loops in same visual zone

## 5) Home Screen Information Architecture

Layout at 1024x600:
- Top status strip
- Main area: left content + right now-playing rail
- Bottom utility strip: git heartbeat, launcher tokens, ticker

Left side:
- Hero time (dominant)
- Inline weather + sparkline
- Transit panel with large next arrival and compact subsequent trains
- Calendar timeline ribbon with clear "next in" cue

Right side:
- Now Playing section
- Album art (reduced vs prior iterations)
- Track/artist/album text hierarchy
- Horizontal progress bar (not circular ring)
- Small feed preview stack

Footer:
- Git heartbeat summary
- Compact launcher affordances (`POMO`, `GH`, `MAP`, `DOOM`, `PHOTO`, `SHOW`)
- Continuous RSS ticker

## 6) Fullscreen App Design Patterns

All fullscreen apps share:
- `ODScreen` shell
- `ODStatusBar` header
- `ODDock` footer launcher
- Shared token and type system

### 6.1 Pomodoro

- Ambient focus mode
- Large central countdown
- Circular progress acceptable in fullscreen focus context
- Cycle dots and session metadata below
- Soft rose accent priority

### 6.2 Transit Detail

- Four-station matrix (primary + secondary)
- Large minute numerals for first arrivals
- Delay status inline and color-coded
- Alert banner anchored near bottom

### 6.3 Calendar

- Day timeline + "now" marker
- Weekly mini-grid context
- "Up next" agenda list
- Notion metadata appears inline when joined

### 6.4 GitHub

- Activity heartbeat strip
- Recent commits list with diff hints
- Open PR + assigned issue panels
- Status-tag treatment (review/open/bug/feat/etc.)

### 6.5 Doomscroll

- Feed list on left, selected story detail on right
- QR handoff pattern to phone is primary action
- Keep article reading off-device

### 6.6 Photo

- Full-bleed photo with minimal chrome
- Tiny source/position metadata only
- Low-contrast progress line for rotation

### 6.7 Showcase

- Full-bleed generative visual state
- Tiny corner identifier only
- Tap-to-return affordance should remain discoverable but minimal

### 6.8 Subway Map

- Abstract live map treatment (not literal MTA map clone)
- Animated train markers + key station labels
- Legend and status counts in low-chrome strip

### 6.9 Diagnostics

- Dense operational table view
- Integration status + perf snapshots + log tail
- Minimal atmosphere; clarity beats mood

## 7) Data Presentation Rules

- Use large numerics for time and transit minutes.
- Keep at most 1-2 dominant visual anchors per screen.
- Surface staleness/failure gently but clearly (color + microcopy).
- Show joined Notion metadata only when join confidence is valid.
- Keep MTA line colors semantically accurate.

## 8) Resolution + Responsiveness

Target first: `1024x600`.

Fallback strategy:
- Preserve hierarchy before adding detail.
- On smaller widths (e.g. `800x480`), collapse secondary feed details first.
- Keep touch targets workable without inflating visual clutter.
- Avoid pixel-perfect hardcoding; prefer proportional spacing and grid adaptation.

## 9) Accessibility + Legibility for Desk Distance

- Maintain high luminance contrast between `ink` and `bg`.
- Keep key numerics/labels readable at 4 ft.
- Avoid thin low-contrast text for critical values.
- Reserve animation as ambient reinforcement, not required comprehension channel.

## 10) Implementation Notes (Frontend)

- Build from shared token system (`system.jsx` -> CSS variables / Tailwind theme).
- Implement reusable primitives:
  - Section label
  - Status bar
  - Dock
  - Ticker
  - MTA pill
  - Sparkline
  - Commit heartbeat
- Create explicit motion modes (`calm`, `music`, `rain`, `thunder`) driven by real integration state:
  - Spotify playing -> `music`
  - Weather rain -> `rain`
  - Weather thunder/storm alert -> `thunder`
  - Else -> `calm`

Performance guardrails for Pi:
- Keep canvas counts low.
- Cap animation complexity and frame rate where possible.
- Prefer CSS transforms/opacities over layout-heavy animation.

## 11) Open Items

- Exact intensity envelope for background orbs on real hardware
- Keep/cut ASCII system meter in home status line (currently optional)
- Final spacing/tightness after first on-device readability pass

## 12) Acceptance for Design Completion

Design is ready for implementation when:
- Home matches C v3 hierarchy and tone
- Motion feels alive but non-distracting on Pi hardware
- Fullscreen apps share coherent shell and token language
- Primary ambient goals (glanceability + personality + calmness) are met
- No screen regresses into overly brown/gray or "car dashboard" feel
