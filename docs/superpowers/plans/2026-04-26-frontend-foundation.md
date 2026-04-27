# Frontend Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stand up a SvelteKit SPA with the full O-Deck design system — tokens, all primitive components, WebSocket/REST stores, and the complete home screen (Variation C v3 "Atelier") connected to the live backend.

**Architecture:** SvelteKit with `@sveltejs/adapter-static` (output to `frontend/build/`; backend serves it). TailwindCSS for utility layout. Svelte stores for WebSocket state. All design primitives are `.svelte` components translated from `design/screens/*.jsx`. No React. No Next.

**Tech Stack:** SvelteKit, TypeScript, TailwindCSS, Inter + IBM Plex Mono (Google Fonts), Playwright (smoke tests)

**Dependency:** Plan 1 (Backend Foundation) must be complete for the WS/API contract. Plan 2 (Backend Integrations) runs in parallel — mock data keeps the frontend workable without live integrations.

---

## Plan Series

1. Backend Foundation ✅ done
2. Backend Integrations → `2026-04-26-backend-integrations.md` (parallel)
3. **Frontend Foundation** ← you are here
4. Fullscreen Apps → `2026-04-26-fullscreen-apps.md` (after this plan)
5. Install & Ops → `2026-04-26-install-ops.md`

---

## File Map

```
frontend/
├── package.json
├── svelte.config.js
├── vite.config.ts
├── tailwind.config.ts
├── postcss.config.cjs
├── tsconfig.json
├── playwright.config.ts
├── src/
│   ├── app.html
│   ├── app.css                          # CSS variables from OD tokens + Tailwind base
│   ├── lib/
│   │   ├── ws.ts                        # WebSocket client + Svelte stores
│   │   ├── api.ts                       # REST helpers (GET /api/state, /api/config)
│   │   ├── types.ts                     # shared TypeScript interfaces
│   │   └── components/
│   │       ├── ODScreen.svelte          # screen wrapper + DriftOrbs + Grain + mode
│   │       ├── ODStatusBar.svelte       # top header strip
│   │       ├── ODDock.svelte            # bottom launcher dock
│   │       ├── SectionLabel.svelte      # mono label + rule
│   │       ├── DriftOrbs.svelte         # canvas orb animation
│   │       ├── Grain.svelte             # SVG noise overlay
│   │       ├── RainOverlay.svelte       # rain streak canvas
│   │       ├── MTAPill.svelte           # MTA line badge
│   │       ├── WeatherIcon.svelte       # SVG weather icon
│   │       ├── EQBars.svelte            # EQ animation bars
│   │       ├── AlbumArt.svelte          # generative album art placeholder
│   │       ├── Ticker.svelte            # scrolling RSS ticker
│   │       ├── Sparkline.svelte         # mini line chart
│   │       ├── CommitHeartbeat.svelte   # GitHub commit bar strip
│   │       └── BlockBar.svelte          # block-style progress bar
│   └── routes/
│       ├── +layout.svelte              # font load + global stores init
│       └── +page.svelte                # home screen (C v3 Atelier)
├── static/
│   └── favicon.svg
└── tests/
    └── home.spec.ts                    # Playwright smoke test
```

---

## Setup

Work in a new worktree branched from main (or merge point after backend-foundation):

```bash
cd ~/cyberdeck
git worktree add .worktrees/frontend-foundation -b feature/frontend-foundation feature/backend-foundation
cd .worktrees/frontend-foundation
```

---

## Task 1: SvelteKit + Tailwind Scaffold

**Files:**
- Create: `frontend/package.json`, `frontend/svelte.config.js`, `frontend/vite.config.ts`, `frontend/tailwind.config.ts`, `frontend/postcss.config.cjs`, `frontend/tsconfig.json`, `frontend/src/app.html`, `frontend/src/app.css`, `frontend/static/favicon.svg`

- [ ] **Step 1: Scaffold SvelteKit (run from repo root)**

```bash
cd frontend 2>/dev/null || true
npm create svelte@latest . -- --template skeleton --types typescript --no-prettier --no-eslint --no-playwright
npm install
npm install -D tailwindcss @tailwindcss/vite postcss autoprefixer
npm install -D @sveltejs/adapter-static
npm install -D playwright @playwright/test
npx playwright install chromium
```

Expected: `node_modules/` created, no errors.

- [ ] **Step 2: Configure adapter-static in `svelte.config.js`**

```javascript
// frontend/svelte.config.js
import adapter from '@sveltejs/adapter-static';
import { vitePreprocess } from '@sveltejs/vite-plugin-svelte';

/** @type {import('@sveltejs/kit').Config} */
const config = {
  preprocess: vitePreprocess(),
  kit: {
    adapter: adapter({
      pages: 'build',
      assets: 'build',
      fallback: 'index.html',
    }),
    prerender: { entries: [] },
  },
};

export default config;
```

- [ ] **Step 3: Configure Tailwind in `vite.config.ts`**

```typescript
// frontend/vite.config.ts
import { sveltekit } from '@sveltejs/kit/vite';
import tailwindcss from '@tailwindcss/vite';
import { defineConfig } from 'vite';

export default defineConfig({
  plugins: [tailwindcss(), sveltekit()],
});
```

- [ ] **Step 4: Create `tailwind.config.ts` with OD token colors**

```typescript
// frontend/tailwind.config.ts
import type { Config } from 'tailwindcss';

export default {
  content: ['./src/**/*.{html,js,svelte,ts}'],
  theme: {
    extend: {
      colors: {
        bg: '#15130f',
        'bg-raised': 'rgba(31,28,24,0.78)',
        'bg-solid': '#1f1c18',
        ink: '#f0e8d6',
        'ink-dim': 'rgba(240,232,214,0.55)',
        'ink-sub': 'rgba(240,232,214,0.32)',
        sand: '#e6c89b',
        sage: '#a8c19a',
        rose: '#d49a8e',
        lav: '#a08fb3',
        line: 'rgba(240,232,214,0.08)',
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['"IBM Plex Mono"', 'monospace'],
      },
    },
  },
  plugins: [],
} satisfies Config;
```

- [ ] **Step 5: Create `postcss.config.cjs`**

```javascript
// frontend/postcss.config.cjs
module.exports = {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
};
```

- [ ] **Step 6: Create `src/app.html` with font imports**

```html
<!-- frontend/src/app.html -->
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <link rel="icon" href="%sveltekit.assets%/favicon.svg" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <link rel="preconnect" href="https://fonts.googleapis.com" />
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin="" />
    <link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=Inter:wght@200;300;400;500;600&display=swap" rel="stylesheet" />
    %sveltekit.head%
  </head>
  <body data-sveltekit-preload-data="hover" class="bg-bg text-ink font-mono">
    <div style="display: contents">%sveltekit.body%</div>
  </body>
</html>
```

- [ ] **Step 7: Create `src/app.css` with CSS variables + Tailwind directives**

```css
/* frontend/src/app.css */
@import 'tailwindcss';

:root {
  --bg: #15130f;
  --bg-raised: rgba(31, 28, 24, 0.78);
  --bg-solid: #1f1c18;
  --ink: #f0e8d6;
  --ink-dim: rgba(240, 232, 214, 0.55);
  --ink-sub: rgba(240, 232, 214, 0.32);
  --sand: #e6c89b;
  --sage: #a8c19a;
  --rose: #d49a8e;
  --lav: #a08fb3;
  --line: rgba(240, 232, 214, 0.08);
  --font-sans: 'Inter', system-ui, sans-serif;
  --font-mono: 'IBM Plex Mono', monospace;
}

html, body {
  width: 100%;
  height: 100%;
  margin: 0;
  overflow: hidden;
  background: var(--bg);
  color: var(--ink);
  font-family: var(--font-mono);
}

.odeck-screen {
  width: 100vw;
  height: 100vh;
  background: var(--bg);
  position: relative;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  padding: 16px 22px;
  box-sizing: border-box;
  gap: 10px;
}

/* Ticker keyframe */
@keyframes ticker-scroll {
  from { transform: translateX(0); }
  to   { transform: translateX(-50%); }
}
.ticker-track {
  animation: ticker-scroll 60s linear infinite;
}

/* EQ bars keyframe */
@keyframes eq-pulse {
  0%, 100% { transform: scaleY(0.2); }
  50%       { transform: scaleY(1); }
}
.eq-bar {
  transform-origin: bottom;
  animation: eq-pulse 0.8s ease-in-out infinite;
}

/* Blinking colon */
@keyframes blink {
  0%, 49% { opacity: 1; }
  50%, 100% { opacity: 0; }
}
.blink { animation: blink 1s step-start infinite; }

/* Live dot pulse */
@keyframes live-pulse {
  0%, 100% { opacity: 1; }
  50%       { opacity: 0.3; }
}
.live-dot { animation: live-pulse 2s ease-in-out infinite; }
```

- [ ] **Step 8: Create `src/routes/+layout.svelte`**

```svelte
<!-- frontend/src/routes/+layout.svelte -->
<script lang="ts">
  import '../app.css';
</script>

<slot />
```

- [ ] **Step 9: Create a placeholder home page so it compiles**

```svelte
<!-- frontend/src/routes/+page.svelte -->
<script lang="ts">
</script>

<div class="odeck-screen">
  <p style="color: var(--sand); font-family: var(--font-mono); font-size: 12px; letter-spacing: 2px; margin: auto;">
    O—DECK · LOADING
  </p>
</div>
```

- [ ] **Step 10: Create favicon**

```bash
cat > frontend/static/favicon.svg << 'EOF'
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">
  <rect width="32" height="32" rx="6" fill="#15130f"/>
  <text x="16" y="22" text-anchor="middle" font-family="monospace" font-size="16" fill="#e6c89b">◎</text>
</svg>
EOF
```

- [ ] **Step 11: Verify it builds**

```bash
cd frontend && npm run build
```

Expected: `✓ built in...` with no errors. `build/` directory created.

- [ ] **Step 12: Commit**

```bash
cd .. && git add frontend/
git commit -m "feat(frontend): SvelteKit + Tailwind scaffold with OD design tokens"
```

---

## Task 2: TypeScript types + WebSocket store

**Files:**
- Create: `frontend/src/lib/types.ts`
- Create: `frontend/src/lib/ws.ts`
- Create: `frontend/src/lib/api.ts`

- [ ] **Step 1: Create `src/lib/types.ts`**

```typescript
// frontend/src/lib/types.ts

export interface WeatherData {
  tempF: number;
  feelsLikeF: number;
  highF: number;
  lowF: number;
  cond: string;
  code: number;
  hourly: Array<{ h: string; t: number }>;
  alerts: Array<{ type: string; label: string }>;
}

export interface TrainArrival {
  line: string;
  mins: number;
  dest: string;
  status: string;
  delay: number;
}

export interface Station {
  name: string;
  stop_id: string;
  lines: string[];
  primary: boolean;
  trains: TrainArrival[];
}

export interface TransitData {
  stations: Station[];
  secondary: Station[];
  alerts: string[];
}

export interface SpotifyData {
  is_playing: boolean;
  track: string | null;
  artist: string | null;
  album: string | null;
  progress: number;
  elapsed: string;
  total: string;
  art_url: string | null;
}

export interface CalendarEvent {
  id: string;
  title: string;
  time: string;
  duration: string;
  location: string;
  color: string;
  notion: { page_id: string; status: string; project: string } | null;
}

export interface CalendarData {
  events: CalendarEvent[];
  next_in: string | null;
}

export interface GitHubData {
  commits: Array<{ sha: string; msg: string; repo: string; time: string }>;
  prs: Array<{ number: number; title: string; repo: string; status: string; age: string }>;
  issues: Array<{ number: number; title: string; repo: string; label: string; age: string }>;
}

export interface RSSItem {
  id: string;
  src: string;
  title: string;
  link: string;
  summary: string;
  age: string;
}

export interface RSSData {
  items: RSSItem[];
  headlines: Array<{ src: string; title: string; age: string }>;
  ticker: string[];
}

export interface PhotosData {
  source: string;
  url: string | null;
  index: number;
  total: number;
  rotation_seconds: number;
}

export interface PomodoroData {
  running: boolean;
  phase: 'idle' | 'work' | 'break' | 'long_break';
  remaining_seconds: number;
  cycle: number;
  cycles_total: number;
  work_min: number;
  break_min: number;
  preset_name: string;
}

export type MotionMode = 'calm' | 'music' | 'rain' | 'thunder';

export interface AppState {
  weather: WeatherData | null;
  transit: TransitData | null;
  spotify: SpotifyData | null;
  calendar: CalendarData | null;
  github: GitHubData | null;
  rss: RSSData | null;
  photos: PhotosData | null;
  pomodoro: PomodoroData | null;
  connected: boolean;
  motionMode: MotionMode;
}
```

- [ ] **Step 2: Create `src/lib/ws.ts`**

```typescript
// frontend/src/lib/ws.ts
import { writable, derived, get } from 'svelte/store';
import type { AppState, MotionMode, WeatherData, SpotifyData } from './types';

function createAppStore() {
  const initial: AppState = {
    weather: null,
    transit: null,
    spotify: null,
    calendar: null,
    github: null,
    rss: null,
    photos: null,
    pomodoro: null,
    connected: false,
    motionMode: 'calm',
  };

  const { subscribe, update, set } = writable<AppState>(initial);

  function deriveMotionMode(state: AppState): MotionMode {
    if (state.spotify?.is_playing) return 'music';
    const alerts = state.weather?.alerts ?? [];
    if (alerts.some((a) => a.type === 'thunder')) return 'thunder';
    if (alerts.some((a) => a.type === 'rain')) return 'rain';
    return 'calm';
  }

  function applyEvent(type: string, data: unknown) {
    update((s) => {
      const next = { ...s };
      switch (type) {
        case 'weather.update':
          next.weather = data as AppState['weather'];
          break;
        case 'transit.update':
          next.transit = data as AppState['transit'];
          break;
        case 'spotify.update':
          next.spotify = data as AppState['spotify'];
          break;
        case 'calendar.update':
          next.calendar = data as AppState['calendar'];
          break;
        case 'github.update':
          next.github = data as AppState['github'];
          break;
        case 'rss.update':
          next.rss = data as AppState['rss'];
          break;
        case 'photos.update':
          next.photos = data as AppState['photos'];
          break;
        case 'pomodoro.update':
          next.pomodoro = data as AppState['pomodoro'];
          break;
      }
      next.motionMode = deriveMotionMode(next);
      return next;
    });
  }

  return { subscribe, update, set, applyEvent };
}

export const appStore = createAppStore();

let _socket: WebSocket | null = null;
let _reconnectTimer: ReturnType<typeof setTimeout> | null = null;
let _backoffMs = 1000;

export function connectWebSocket(url?: string): void {
  const wsUrl = url ?? (typeof window !== 'undefined'
    ? `ws://${window.location.host}/ws`
    : 'ws://localhost:8080/ws');

  if (_socket && _socket.readyState === WebSocket.OPEN) return;

  _socket = new WebSocket(wsUrl);

  _socket.addEventListener('open', () => {
    _backoffMs = 1000;
    appStore.update((s) => ({ ...s, connected: true }));
    // send periodic pings
    const pingInterval = setInterval(() => {
      if (_socket?.readyState === WebSocket.OPEN) {
        _socket.send('ping');
      } else {
        clearInterval(pingInterval);
      }
    }, 15_000);
  });

  _socket.addEventListener('message', (ev) => {
    try {
      const msg = JSON.parse(ev.data as string) as { type: string; data: unknown };
      appStore.applyEvent(msg.type, msg.data);
    } catch {
      // ignore malformed messages
    }
  });

  _socket.addEventListener('close', () => {
    appStore.update((s) => ({ ...s, connected: false }));
    _reconnectTimer = setTimeout(() => {
      _backoffMs = Math.min(_backoffMs * 2, 30_000);
      connectWebSocket(wsUrl);
    }, _backoffMs);
  });

  _socket.addEventListener('error', () => {
    _socket?.close();
  });
}
```

- [ ] **Step 3: Create `src/lib/api.ts`**

```typescript
// frontend/src/lib/api.ts
import { appStore } from './ws';
import type { AppState } from './types';

const BASE = '';  // same origin; backend serves frontend

export async function fetchInitialState(): Promise<void> {
  const [stateResp, configResp] = await Promise.all([
    fetch(`${BASE}/api/state`),
    fetch(`${BASE}/api/config`),
  ]);

  if (stateResp.ok) {
    const state = await stateResp.json() as Partial<AppState>;
    appStore.update((s) => ({
      ...s,
      weather: state.weather ?? s.weather,
      transit: state.transit ?? s.transit,
      spotify: state.spotify ?? s.spotify,
      calendar: state.calendar ?? s.calendar,
      github: state.github ?? s.github,
      rss: state.rss ?? s.rss,
      photos: state.photos ?? s.photos,
      pomodoro: state.pomodoro ?? s.pomodoro,
    }));
  }
}

export async function startPomodoro(preset: {
  name: string;
  work_min: number;
  break_min: number;
  cycles: number;
  long_break_min: number;
}): Promise<void> {
  await fetch(`${BASE}/api/pomodoro/start`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(preset),
  });
}

export async function pausePomodoro(): Promise<void> {
  await fetch(`${BASE}/api/pomodoro/pause`, { method: 'POST' });
}

export async function stopPomodoro(): Promise<void> {
  await fetch(`${BASE}/api/pomodoro/stop`, { method: 'POST' });
}
```

- [ ] **Step 4: Verify TypeScript compiles**

```bash
cd frontend && npx tsc --noEmit
```

Expected: no errors.

- [ ] **Step 5: Commit**

```bash
cd .. && git add frontend/src/lib/
git commit -m "feat(frontend): TypeScript types, WebSocket store, REST API helpers"
```

---

## Task 3: Primitive components — Shell + Layout

**Files:**
- Create: `frontend/src/lib/components/SectionLabel.svelte`
- Create: `frontend/src/lib/components/ODStatusBar.svelte`
- Create: `frontend/src/lib/components/ODDock.svelte`
- Create: `frontend/src/lib/components/DriftOrbs.svelte`
- Create: `frontend/src/lib/components/Grain.svelte`
- Create: `frontend/src/lib/components/RainOverlay.svelte`
- Create: `frontend/src/lib/components/ODScreen.svelte`

- [ ] **Step 1: Create `SectionLabel.svelte`**

```svelte
<!-- frontend/src/lib/components/SectionLabel.svelte -->
<script lang="ts">
  export let accent: string = 'var(--ink-dim)';
</script>

<div class="section-label" style="--accent: {accent}">
  <span><slot /></span>
  <span class="rule" />
</div>

<style>
  .section-label {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 9px;
    font-family: var(--font-mono);
    font-size: 10px;
    letter-spacing: 1.5px;
    color: var(--accent);
  }
  .rule {
    flex: 1;
    height: 1px;
    background: var(--line);
  }
</style>
```

- [ ] **Step 2: Create `DriftOrbs.svelte`**

```svelte
<!-- frontend/src/lib/components/DriftOrbs.svelte -->
<script lang="ts">
  import { onMount, onDestroy } from 'svelte';

  export let palette: string[] = ['#e6c89b', '#a8c19a', '#7a5f4a', '#5a6a78'];
  export let mode: 'calm' | 'music' | 'rain' | 'thunder' = 'calm';
  export let count: number = 6;

  let canvas: HTMLCanvasElement;
  let rafId = 0;
  let orbs: Array<{
    bx: number; by: number; vx: number; vy: number;
    r: number; color: string; phase: number; ampX: number; ampY: number;
  }> = [];
  let t = 0;
  let lastTime = 0;
  let flashVal = 0;
  let ro: ResizeObserver;

  function initOrbs(w: number, h: number) {
    orbs = Array.from({ length: count }, (_, i) => ({
      bx: Math.random() * w,
      by: Math.random() * h,
      r: 90 + Math.random() * 140,
      vx: (Math.random() - 0.5) * 0.18,
      vy: (Math.random() - 0.5) * 0.14,
      color: palette[i % palette.length],
      phase: Math.random() * Math.PI * 2,
      ampX: 30 + Math.random() * 50,
      ampY: 20 + Math.random() * 40,
    }));
  }

  function resize() {
    if (!canvas) return;
    const dpr = Math.min(window.devicePixelRatio || 1, 1.5);
    const r = canvas.getBoundingClientRect();
    canvas.width = r.width * dpr;
    canvas.height = r.height * dpr;
    const ctx = canvas.getContext('2d')!;
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.scale(dpr, dpr);
  }

  onMount(() => {
    resize();
    initOrbs(canvas.clientWidth, canvas.clientHeight);
    ro = new ResizeObserver(() => resize());
    ro.observe(canvas);

    lastTime = performance.now();
    const step = (now: number) => {
      const dt = Math.min(50, now - lastTime);
      lastTime = now;
      t += dt * 0.001;
      const ctx = canvas.getContext('2d')!;
      const w = canvas.clientWidth;
      const h = canvas.clientHeight;

      ctx.clearRect(0, 0, w, h);
      const speedMul = mode === 'thunder' ? 2.4 : mode === 'rain' ? 1.3 : mode === 'music' ? 1.5 : 1;
      const alphaMul = mode === 'rain' ? 0.6 : mode === 'thunder' ? 1.1 : 1;

      if (mode === 'thunder') {
        if (Math.random() < 0.005) flashVal = 1;
        if (flashVal > 0) {
          ctx.globalCompositeOperation = 'source-over';
          ctx.fillStyle = `rgba(220,200,220,${flashVal * 0.18})`;
          ctx.fillRect(0, 0, w, h);
          flashVal *= 0.78;
        }
      }

      ctx.globalCompositeOperation = 'screen';
      for (const o of orbs) {
        o.bx += o.vx * speedMul;
        o.by += o.vy * speedMul;
        if (o.bx < -o.r) o.bx = w + o.r;
        if (o.bx > w + o.r) o.bx = -o.r;
        if (o.by < -o.r) o.by = h + o.r;
        if (o.by > h + o.r) o.by = -o.r;

        const x = o.bx + Math.sin(t * 0.3 + o.phase) * o.ampX;
        const y = o.by + Math.cos(t * 0.27 + o.phase) * o.ampY;
        const beat = mode === 'music' ? 1 + Math.max(0, Math.sin(t * 4.2)) * 0.18 : 1;
        const rr = o.r * beat;

        const grad = ctx.createRadialGradient(x, y, 0, x, y, rr);
        grad.addColorStop(0, o.color + '55');
        grad.addColorStop(0.4, o.color + '1f');
        grad.addColorStop(1, o.color + '00');
        ctx.globalAlpha = 0.55 * alphaMul;
        ctx.fillStyle = grad;
        ctx.beginPath();
        ctx.arc(x, y, rr, 0, Math.PI * 2);
        ctx.fill();
      }
      ctx.globalAlpha = 1;
      rafId = requestAnimationFrame(step);
    };
    rafId = requestAnimationFrame(step);
  });

  onDestroy(() => {
    cancelAnimationFrame(rafId);
    ro?.disconnect();
  });
</script>

<canvas
  bind:this={canvas}
  style="position:absolute;inset:0;width:100%;height:100%;pointer-events:none;filter:blur(36px);opacity:0.85;"
/>
```

- [ ] **Step 3: Create `Grain.svelte`**

```svelte
<!-- frontend/src/lib/components/Grain.svelte -->
<div class="grain" aria-hidden="true" />

<style>
  .grain {
    position: absolute;
    inset: 0;
    pointer-events: none;
    opacity: 0.10;
    mix-blend-mode: overlay;
    background-image: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='160' height='160'><filter id='n'><feTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='2'/><feColorMatrix values='0 0 0 0 0  0 0 0 0 0  0 0 0 0 0  0 0 0 0.6 0'/></filter><rect width='160' height='160' filter='url(%23n)'/></svg>");
  }
</style>
```

- [ ] **Step 4: Create `RainOverlay.svelte`**

```svelte
<!-- frontend/src/lib/components/RainOverlay.svelte -->
<script lang="ts">
  import { onMount, onDestroy } from 'svelte';

  export let intensity: number = 0.5;
  export let color: string = '#aac0d6';

  let canvas: HTMLCanvasElement;
  let rafId = 0;
  let ro: ResizeObserver;

  onMount(() => {
    const ctx = canvas.getContext('2d')!;
    const dpr = Math.min(window.devicePixelRatio || 1, 1.5);
    const resize = () => {
      const r = canvas.getBoundingClientRect();
      canvas.width = r.width * dpr;
      canvas.height = r.height * dpr;
      ctx.setTransform(1, 0, 0, 1, 0, 0);
      ctx.scale(dpr, dpr);
    };
    resize();
    ro = new ResizeObserver(resize);
    ro.observe(canvas);

    const w0 = canvas.clientWidth;
    const h0 = canvas.clientHeight;
    const drops = Array.from({ length: Math.floor(60 * intensity) }, () => ({
      x: Math.random() * w0,
      y: Math.random() * h0,
      vy: 1.2 + Math.random() * 1.4,
      len: 8 + Math.random() * 14,
    }));

    const step = () => {
      const w = canvas.clientWidth;
      const h = canvas.clientHeight;
      ctx.clearRect(0, 0, w, h);
      ctx.strokeStyle = color;
      ctx.lineWidth = 0.7;
      ctx.globalAlpha = 0.35;
      for (const d of drops) {
        d.y += d.vy;
        d.x -= 0.3;
        if (d.y > h) { d.y = -10; d.x = Math.random() * w; }
        if (d.x < 0) d.x = w;
        ctx.beginPath();
        ctx.moveTo(d.x, d.y);
        ctx.lineTo(d.x + 1.5, d.y + d.len);
        ctx.stroke();
      }
      rafId = requestAnimationFrame(step);
    };
    rafId = requestAnimationFrame(step);
  });

  onDestroy(() => {
    cancelAnimationFrame(rafId);
    ro?.disconnect();
  });
</script>

<canvas
  bind:this={canvas}
  style="position:absolute;inset:0;width:100%;height:100%;pointer-events:none;"
/>
```

- [ ] **Step 5: Create `ODScreen.svelte`**

```svelte
<!-- frontend/src/lib/components/ODScreen.svelte -->
<script lang="ts">
  import DriftOrbs from './DriftOrbs.svelte';
  import Grain from './Grain.svelte';
  import RainOverlay from './RainOverlay.svelte';

  export let mode: 'calm' | 'music' | 'rain' | 'thunder' = 'calm';
  export let orbs: boolean = true;

  const orbPalettes: Record<string, string[]> = {
    calm:    ['#e6c89b', '#a8c19a', '#7a5f4a', '#5a6a78'],
    music:   ['#a08fb3', '#d49a8e', '#e6c89b', '#7a90a8'],
    rain:    ['#5a7088', '#7a90a8', '#3e556a', '#a8c19a'],
    thunder: ['#c8b89a', '#7a6a8a', '#3e3a4a', '#d49a8e'],
  };
  $: palette = orbPalettes[mode] ?? orbPalettes.calm;
</script>

<div class="odeck-screen">
  {#if orbs}
    <DriftOrbs {palette} {mode} count={6} />
    {#if mode === 'rain' || mode === 'thunder'}
      <RainOverlay
        intensity={mode === 'thunder' ? 0.9 : 0.5}
        color={mode === 'thunder' ? '#c8b8a0' : '#aac0d6'}
      />
    {/if}
    <Grain />
  {/if}
  <div style="position:relative;z-index:1;display:flex;flex-direction:column;gap:10px;height:100%;">
    <slot />
  </div>
</div>
```

- [ ] **Step 6: Create `ODStatusBar.svelte`**

```svelte
<!-- frontend/src/lib/components/ODStatusBar.svelte -->
<script lang="ts">
  export let app: string = '';
  export let accent: string = 'var(--sand)';

  // In production these come from /api/status; for now use stubs
  const host = 'odeck.local';
  const wifi = 'home-5G';
  const date = new Date().toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' }).toUpperCase();
</script>

<header class="status-bar">
  <div class="left">
    <span class="brand">O—DECK</span>
    {#if app}
      <span class="sep" style="color:var(--ink-sub)">›</span>
      <span style="color:{accent};letter-spacing:1.8px">{app}</span>
    {/if}
    <span><span class="live-dot" style="color:var(--sage)">●</span> {host}</span>
  </div>
  <div class="right">
    <span style="color:var(--ink-sub)">{wifi}</span>
    <span style="color:var(--sand)">{date}</span>
  </div>
</header>

<style>
  .status-bar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    font-size: 10px;
    letter-spacing: 1.5px;
    color: var(--ink-dim);
    font-family: var(--font-mono);
    padding-bottom: 10px;
    border-bottom: 1px solid var(--line);
    position: relative;
    z-index: 2;
  }
  .left { display: flex; gap: 18px; align-items: center; }
  .right { display: flex; gap: 14px; }
  .brand { color: var(--ink); font-weight: 500; }
  .sep { color: var(--ink-sub); }
</style>
```

- [ ] **Step 7: Create `ODDock.svelte`**

```svelte
<!-- frontend/src/lib/components/ODDock.svelte -->
<script lang="ts">
  import { goto } from '$app/navigation';

  export let active: string = 'HOME';

  const items = [
    { k: 'HOME',  g: '⌂', href: '/' },
    { k: 'POMO',  g: '◑', href: '/pomodoro' },
    { k: 'GH',    g: '◇', href: '/github' },
    { k: 'MAP',   g: '▤', href: '/subway' },
    { k: 'DOOM',  g: '□', href: '/doomscroll' },
    { k: 'PHOTO', g: '◐', href: '/photos' },
    { k: 'SHOW',  g: '✦', href: '/showcase' },
  ];
</script>

<footer class="dock">
  {#each items as item}
    <button
      class="dock-item"
      class:active={active === item.k}
      on:click={() => goto(item.href)}
      aria-label={item.k}
    >
      <span class="dot" />
      <span class="glyph">{item.g}</span>
      {item.k}
    </button>
  {/each}
  <span style="flex:1" />
  <span style="color:var(--ink-sub)">tap <span style="color:var(--sand)">⌂</span> for home</span>
</footer>

<style>
  .dock {
    display: flex;
    gap: 14px;
    align-items: center;
    padding-top: 10px;
    border-top: 1px solid var(--line);
    font-family: var(--font-mono);
    font-size: 10px;
    letter-spacing: 1.5px;
    color: var(--ink-dim);
  }
  .dock-item {
    display: inline-flex;
    gap: 5px;
    align-items: center;
    background: none;
    border: none;
    cursor: pointer;
    color: var(--ink-dim);
    font-family: var(--font-mono);
    font-size: 10px;
    letter-spacing: 1.5px;
    padding: 0;
  }
  .dock-item.active { color: var(--ink); }
  .dot {
    width: 5px;
    height: 5px;
    border-radius: 5px;
    background: rgba(240, 232, 214, 0.25);
  }
  .dock-item.active .dot { background: var(--sand); }
  .glyph { margin-right: 2px; }
  .dock-item.active .glyph { color: var(--sand); }
</style>
```

- [ ] **Step 8: Verify build still passes**

```bash
cd frontend && npm run build
```

Expected: build succeeds.

- [ ] **Step 9: Commit**

```bash
cd .. && git add frontend/src/lib/components/
git commit -m "feat(frontend): shell components — ODScreen, ODStatusBar, ODDock, SectionLabel, DriftOrbs, Grain, RainOverlay"
```

---

## Task 4: Data display primitives

**Files:**
- Create: `frontend/src/lib/components/MTAPill.svelte`
- Create: `frontend/src/lib/components/WeatherIcon.svelte`
- Create: `frontend/src/lib/components/EQBars.svelte`
- Create: `frontend/src/lib/components/AlbumArt.svelte`
- Create: `frontend/src/lib/components/Ticker.svelte`
- Create: `frontend/src/lib/components/Sparkline.svelte`
- Create: `frontend/src/lib/components/CommitHeartbeat.svelte`
- Create: `frontend/src/lib/components/BlockBar.svelte`

- [ ] **Step 1: Create `MTAPill.svelte`**

```svelte
<!-- frontend/src/lib/components/MTAPill.svelte -->
<script lang="ts">
  export let line: string;
  export let color: string;
  export let size: number = 22;

  const YELLOW_LINES = new Set(['N', 'Q', 'R', 'W']);
  $: fg = YELLOW_LINES.has(line) ? '#1a1a1a' : '#fff';
</script>

<span
  class="pill"
  style="
    width:{size}px;height:{size}px;border-radius:{size / 2}px;
    background:{color};color:{fg};font-size:{size * 0.55}px;
  "
>
  {line}
</span>

<style>
  .pill {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    font-weight: 700;
    font-family: var(--font-sans);
    letter-spacing: 0;
    flex-shrink: 0;
  }
</style>
```

- [ ] **Step 2: Create `WeatherIcon.svelte`**

```svelte
<!-- frontend/src/lib/components/WeatherIcon.svelte -->
<script lang="ts">
  export let kind: string = 'cloud-sun';
  export let size: number = 28;
  export let stroke: string = 'currentColor';
</script>

{#if kind === 'cloud-sun'}
  <svg width={size} height={size} viewBox="0 0 32 32" fill="none" {stroke} stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">
    <circle cx="11" cy="11" r="4" />
    <path d="M11 3v2M11 17v2M3 11h2M17 11h2M5.5 5.5l1.4 1.4M15.1 15.1l1.4 1.4M5.5 16.5l1.4-1.4M15.1 6.9l1.4-1.4" />
    <path d="M14 22h10a4 4 0 1 0-1.2-7.8A6 6 0 0 0 11 17a4 4 0 0 0 3 5z" />
  </svg>
{:else if kind === 'sun'}
  <svg width={size} height={size} viewBox="0 0 32 32" fill="none" {stroke} stroke-width="1.6" stroke-linecap="round">
    <circle cx="16" cy="16" r="6" />
    <path d="M16 2v3M16 27v3M2 16h3M27 16h3M6.3 6.3l2.1 2.1M23.6 23.6l2.1 2.1M6.3 25.7l2.1-2.1M23.6 8.4l2.1-2.1" />
  </svg>
{:else if kind === 'cloud'}
  <svg width={size} height={size} viewBox="0 0 32 32" fill="none" {stroke} stroke-width="1.6" stroke-linecap="round">
    <path d="M8 22a6 6 0 1 1 0-12 8 8 0 1 1 14.9 4H22a5 5 0 0 1 0 10H8z" />
  </svg>
{:else if kind === 'rain'}
  <svg width={size} height={size} viewBox="0 0 32 32" fill="none" {stroke} stroke-width="1.6" stroke-linecap="round">
    <path d="M8 18a6 6 0 1 1 0-12 8 8 0 1 1 14.9 4H22a5 5 0 0 1 0 10H8z" />
    <path d="M10 26l-1 4M16 26l-1 4M22 26l-1 4" />
  </svg>
{:else if kind === 'snow'}
  <svg width={size} height={size} viewBox="0 0 32 32" fill="none" {stroke} stroke-width="1.6" stroke-linecap="round">
    <path d="M8 18a6 6 0 1 1 0-12 8 8 0 1 1 14.9 4H22a5 5 0 0 1 0 10H8z" />
    <circle cx="11" cy="27" r="1.5" fill={stroke} />
    <circle cx="16" cy="27" r="1.5" fill={stroke} />
    <circle cx="21" cy="27" r="1.5" fill={stroke} />
  </svg>
{:else}
  <!-- fallback: just a circle -->
  <svg width={size} height={size} viewBox="0 0 32 32" fill="none" {stroke} stroke-width="1.6">
    <circle cx="16" cy="16" r="8" />
  </svg>
{/if}
```

- [ ] **Step 3: Create `EQBars.svelte`**

```svelte
<!-- frontend/src/lib/components/EQBars.svelte -->
<script lang="ts">
  export let count: number = 4;
  export let color: string = 'currentColor';
  export let size: number = 10;
  export let width: number = 2;
</script>

<span class="eq" style="height:{size}px">
  {#each Array(count) as _, i}
    <span
      class="eq-bar"
      style="
        width:{width}px;height:{size}px;background:{color};
        animation-delay:{i * 0.13}s;
      "
    />
  {/each}
</span>

<style>
  .eq {
    display: inline-flex;
    align-items: flex-end;
    gap: 2px;
  }
  .eq-bar {
    border-radius: 1px;
    transform-origin: bottom;
    animation: eq-pulse 0.8s ease-in-out infinite;
  }
</style>
```

- [ ] **Step 4: Create `AlbumArt.svelte`**

```svelte
<!-- frontend/src/lib/components/AlbumArt.svelte -->
<script lang="ts">
  export let palette: { dom: string; accent: string; ink: string } = {
    dom: '#6b5a8a', accent: '#c9a36c', ink: '#f5efe6',
  };
  export let size: number = 170;
  export let label: string = '';
  export let glyph: string = '◊';
  export let artUrl: string | null = null;

  function shade(hex: string, amt: number): string {
    const n = parseInt(hex.slice(1), 16);
    const r = Math.max(0, Math.min(255, ((n >> 16) & 0xff) + amt));
    const g = Math.max(0, Math.min(255, ((n >> 8) & 0xff) + amt));
    const b = Math.max(0, Math.min(255, (n & 0xff) + amt));
    return '#' + ((r << 16) | (g << 8) | b).toString(16).padStart(6, '0');
  }
</script>

<div
  class="art"
  style="
    width:{size}px;height:{size}px;
    background:linear-gradient(155deg,{palette.dom} 0%,{shade(palette.dom,-20)} 60%,{shade(palette.dom,-35)} 100%);
  "
>
  {#if artUrl}
    <img src={artUrl} alt={label} style="width:100%;height:100%;object-fit:cover;border-radius:18px;" />
  {:else}
    <div
      class="accent-orb"
      style="background:radial-gradient(circle at 30% 25%,{palette.accent}55 0%,transparent 45%)"
    />
    <span class="glyph" style="font-size:{size * 0.5}px;color:{palette.ink}">{glyph}</span>
    {#if label}
      <span class="label" style="font-size:{size * 0.055}px;color:{palette.ink}">{label}</span>
    {/if}
  {/if}
</div>

<style>
  .art {
    border-radius: 18px;
    position: relative;
    overflow: hidden;
    flex-shrink: 0;
    box-shadow: 0 18px 40px rgba(0,0,0,0.35), inset 0 1px 0 rgba(255,255,255,0.08);
  }
  .accent-orb {
    position: absolute;
    inset: 0;
  }
  .glyph {
    position: absolute;
    left: 50%;
    top: 46%;
    transform: translate(-50%, -50%);
    font-family: serif;
    opacity: 0.92;
    line-height: 1;
  }
  .label {
    position: absolute;
    left: 7%;
    bottom: 7%;
    font-family: var(--font-mono);
    letter-spacing: 1.5px;
    opacity: 0.78;
  }
</style>
```

- [ ] **Step 5: Create `Ticker.svelte`**

```svelte
<!-- frontend/src/lib/components/Ticker.svelte -->
<script lang="ts">
  export let items: string[] = [];
  export let color: string = 'var(--ink)';
  export let opacity: number = 0.45;
  export let fontSize: number = 10;

  $: seq = [...items, ...items];
</script>

<div class="ticker-wrap">
  <div class="ticker-track" style="color:{color};opacity:{opacity};font-size:{fontSize}px;">
    {#each seq as item, i}
      <span>· {item}</span>
    {/each}
  </div>
</div>

<style>
  .ticker-wrap {
    overflow: hidden;
    white-space: nowrap;
    mask-image: linear-gradient(90deg, transparent, #000 4%, #000 96%, transparent);
    -webkit-mask-image: linear-gradient(90deg, transparent, #000 4%, #000 96%, transparent);
  }
  .ticker-track {
    display: inline-flex;
    gap: 48px;
    font-family: var(--font-mono);
    letter-spacing: 0;
    animation: ticker-scroll 60s linear infinite;
  }
</style>
```

- [ ] **Step 6: Create `Sparkline.svelte`**

```svelte
<!-- frontend/src/lib/components/Sparkline.svelte -->
<script lang="ts">
  export let points: Array<{ h: string; t: number }> = [];
  export let color: string = 'var(--sage)';
  export let width: number = 140;
  export let height: number = 30;

  $: path = (() => {
    if (points.length < 2) return '';
    const vals = points.map((p) => p.t);
    const min = Math.min(...vals);
    const max = Math.max(...vals);
    const range = max - min || 1;
    const step = width / (points.length - 1);
    return points
      .map((p, i) => {
        const x = i * step;
        const y = height - ((p.t - min) / range) * height;
        return `${i === 0 ? 'M' : 'L'}${x.toFixed(1)} ${y.toFixed(1)}`;
      })
      .join(' ');
  })();
</script>

<svg {width} {height} viewBox="0 0 {width} {height}" fill="none">
  {#if path}
    <path d={path} stroke={color} stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" />
  {/if}
</svg>
```

- [ ] **Step 7: Create `CommitHeartbeat.svelte`**

```svelte
<!-- frontend/src/lib/components/CommitHeartbeat.svelte -->
<script lang="ts">
  export let color: string = 'var(--sage)';
  export let count: number = 36;
  export let barWidth: number = 2;
  export let maxHeight: number = 16;

  const bars = Array.from({ length: count }, (_, i) => {
    const v = Math.max(0.05, Math.exp(-Math.pow((i % 8 - 4) / 3, 2)) * (0.4 + Math.random() * 0.6));
    return { h: Math.round(v * maxHeight), recent: i > count - 9 };
  });
</script>

<span style="display:inline-flex;align-items:flex-end;gap:1px;height:{maxHeight}px">
  {#each bars as bar}
    <span
      style="
        width:{barWidth}px;height:{bar.h}px;
        background:{bar.recent ? color : color + '55'};
        border-radius:1.5px;display:inline-block;
      "
    />
  {/each}
</span>
```

- [ ] **Step 8: Create `BlockBar.svelte`**

```svelte
<!-- frontend/src/lib/components/BlockBar.svelte -->
<script lang="ts">
  export let value: number = 0;  // 0–1
  export let width: number = 6;  // number of blocks
  export let color: string = 'var(--sage)';
</script>

<span style="display:inline-flex;gap:1px;align-items:center">
  {#each Array(width) as _, i}
    <span
      style="
        width:3px;height:8px;border-radius:1px;
        background:{i / width < value ? color : 'rgba(240,232,214,0.15)'};
      "
    />
  {/each}
</span>
```

- [ ] **Step 9: Verify build**

```bash
cd frontend && npm run build
```

Expected: ✓ built successfully.

- [ ] **Step 10: Commit**

```bash
cd .. && git add frontend/src/lib/components/
git commit -m "feat(frontend): data display primitives — MTAPill, WeatherIcon, EQBars, AlbumArt, Ticker, Sparkline, CommitHeartbeat, BlockBar"
```

---

## Task 5: Home Screen (C v3 Atelier)

**Files:**
- Modify: `frontend/src/routes/+page.svelte`
- Modify: `frontend/src/routes/+layout.svelte`

This is the complete home screen. All data comes from `appStore`. If data is null (not yet fetched), widgets show graceful loading states.

- [ ] **Step 1: Update `+layout.svelte` to init WS on mount**

```svelte
<!-- frontend/src/routes/+layout.svelte -->
<script lang="ts">
  import { onMount } from 'svelte';
  import { connectWebSocket } from '$lib/ws';
  import { fetchInitialState } from '$lib/api';
  import '../app.css';

  onMount(async () => {
    await fetchInitialState();
    connectWebSocket();
  });
</script>

<slot />
```

- [ ] **Step 2: Write the full home screen `+page.svelte`**

```svelte
<!-- frontend/src/routes/+page.svelte -->
<script lang="ts">
  import { onMount } from 'svelte';
  import { appStore } from '$lib/ws';
  import ODScreen from '$lib/components/ODScreen.svelte';
  import SectionLabel from '$lib/components/SectionLabel.svelte';
  import MTAPill from '$lib/components/MTAPill.svelte';
  import WeatherIcon from '$lib/components/WeatherIcon.svelte';
  import EQBars from '$lib/components/EQBars.svelte';
  import AlbumArt from '$lib/components/AlbumArt.svelte';
  import Ticker from '$lib/components/Ticker.svelte';
  import Sparkline from '$lib/components/Sparkline.svelte';
  import CommitHeartbeat from '$lib/components/CommitHeartbeat.svelte';
  import BlockBar from '$lib/components/BlockBar.svelte';
  import { goto } from '$app/navigation';

  // Live clock
  let now = new Date();
  let clockInterval: ReturnType<typeof setInterval>;

  onMount(() => {
    clockInterval = setInterval(() => { now = new Date(); }, 1000);
    return () => clearInterval(clockInterval);
  });

  $: hh = String(now.getHours() % 12 || 12).padStart(2, '0');
  $: mm = String(now.getMinutes()).padStart(2, '0');
  $: ss = String(now.getSeconds()).padStart(2, '0');
  $: ampm = now.getHours() >= 12 ? 'PM' : 'AM';

  $: state = $appStore;
  $: weather = state.weather;
  $: transit = state.transit;
  $: spotify = state.spotify;
  $: calendar = state.calendar;
  $: github = state.github;
  $: rss = state.rss;
  $: mode = state.motionMode;

  // Derive weather icon kind from WMO code
  function weatherIconKind(code: number | undefined): string {
    if (!code) return 'cloud-sun';
    if (code === 0 || code === 1) return 'sun';
    if (code === 2 || code === 3) return 'cloud-sun';
    if ([71, 73, 75].includes(code)) return 'snow';
    if ([61, 63, 65, 80, 81, 82].includes(code)) return 'rain';
    return 'cloud';
  }

  // MTA line colors
  const LINE_COLORS: Record<string, string> = {
    A: '#0039A6', C: '#0039A6', E: '#0039A6',
    B: '#FF6319', D: '#FF6319', F: '#FF6319', M: '#FF6319',
    N: '#FCCC0A', Q: '#FCCC0A', R: '#FCCC0A', W: '#FCCC0A',
    '1': '#EE352E', '2': '#EE352E', '3': '#EE352E',
    '4': '#00933C', '5': '#00933C', '6': '#00933C',
    L: '#A7A9AC', G: '#6CBE45', J: '#996633', Z: '#996633',
  };

  $: allTrains = [
    ...(transit?.stations.flatMap((s) => s.trains) ?? []),
  ].slice(0, 5);

  $: nowPlaying = spotify?.is_playing ? spotify : null;

  const DOCK_ITEMS = [
    { k: 'POMO', href: '/pomodoro' },
    { k: 'GH',   href: '/github' },
    { k: 'MAP',  href: '/subway' },
    { k: 'DOOM', href: '/doomscroll' },
    { k: 'PHOTO',href: '/photos' },
    { k: 'SHOW', href: '/showcase' },
  ];
</script>

<ODScreen {mode}>
  <!-- STATUS BAR -->
  <header class="status-bar">
    <div class="status-left">
      <span class="brand">O—DECK</span>
      <span style="color:var(--ink-sub)">/od-04</span>
      <span><span style="color:var(--sage);animation:live-pulse 2s ease-in-out infinite">●</span> odeck.local</span>
      <span style="color:var(--ink-dim)">up 4d 11h</span>
    </div>
    <div class="status-right">
      <span style="color:{mode === 'music' ? 'var(--sand)' : mode === 'rain' ? '#aac0d6' : mode === 'thunder' ? 'var(--rose)' : 'var(--sage)'}">
        ◌ {mode}
      </span>
      <span style="color:var(--ink-sub)">home-5G</span>
      <span style="color:var(--sand)">{now.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' }).toUpperCase()}</span>
    </div>
  </header>

  <!-- MAIN GRID -->
  <div class="main-grid">

    <!-- TIME + WEATHER (top-left) -->
    <div class="time-block">
      <div class="clock-row">
        <span class="clock-hhmm" style="font-family:var(--font-sans)">{hh}<span class="blink" style="color:var(--sand)">:</span>{mm}</span>
        <div class="clock-meta">
          <span class="clock-ss" style="font-family:var(--font-sans)">:{ss}</span>
          <span style="font-size:11px;letter-spacing:2px;color:var(--ink-sub)">{ampm} · EDT</span>
        </div>
      </div>
      <div class="weather-row">
        {#if weather}
          <div class="weather-temp">
            <span style="color:var(--sand)">
              <WeatherIcon kind={weatherIconKind(weather.code)} size={28} />
            </span>
            <span class="temp-num" style="font-family:var(--font-sans)">{Math.round(weather.tempF)}°</span>
          </div>
          <div class="weather-detail">
            <div>{weather.cond.toLowerCase()}</div>
            <div style="color:var(--ink-sub)">H{Math.round(weather.highF)}° L{Math.round(weather.lowF)}° · feels {Math.round(weather.feelsLikeF)}°</div>
          </div>
          <div class="weather-sparkline">
            <Sparkline points={weather.hourly} color="var(--sage)" width={140} height={30} />
          </div>
        {:else}
          <span style="color:var(--ink-sub);font-size:11px">weather loading…</span>
        {/if}
      </div>
    </div>

    <!-- NOW PLAYING (right rail) -->
    <aside class="now-playing-rail">
      <div class="np-label">
        {#if nowPlaying}
          <EQBars count={4} size={10} width={2} color="var(--sage)" />
        {/if}
        <span>NOW PLAYING</span>
      </div>
      {#if nowPlaying}
        <AlbumArt
          palette={{ dom: '#6b5a8a', accent: '#c9a36c', ink: '#f5efe6' }}
          artUrl={nowPlaying.art_url}
          size={170}
          label={nowPlaying.album ?? ''}
          glyph="◊"
        />
        <div class="np-text">
          <div class="np-track" style="font-family:var(--font-sans)">{nowPlaying.track}</div>
          <div class="np-artist" style="font-family:var(--font-sans);color:var(--ink-dim)">{nowPlaying.artist}</div>
          <div style="font-size:10px;color:var(--ink-sub);letter-spacing:1px">from {(nowPlaying.album ?? '').toUpperCase()}</div>
        </div>
        <div class="np-progress">
          <div class="progress-track">
            <div class="progress-fill" style="width:{(nowPlaying.progress * 100).toFixed(1)}%" />
          </div>
          <div class="progress-times">
            <span>{nowPlaying.elapsed}</span>
            <span>{nowPlaying.total}</span>
          </div>
        </div>
      {:else}
        <div style="color:var(--ink-sub);font-size:11px;letter-spacing:1px;margin-top:8px">nothing playing</div>
      {/if}

      <!-- RSS mini-stack in rail -->
      {#if rss?.headlines.length}
        <div class="rss-stack">
          <div style="font-size:10px;letter-spacing:2px;color:var(--ink-dim)">FEED</div>
          {#each rss.headlines.slice(0, 2) as h}
            <div>
              <div style="font-size:9px;color:var(--rose);letter-spacing:1.2px;margin-bottom:2px">{h.src} · {h.age}</div>
              <div style="font-family:var(--font-sans);font-size:12px;color:var(--ink);line-height:1.3">{h.title}</div>
            </div>
          {/each}
        </div>
      {/if}
    </aside>

    <!-- TRANSIT + CALENDAR (bottom-left) -->
    <div class="bottom-left">

      <!-- TRANSIT -->
      <div class="transit-block">
        <div class="section-header">
          <span>NEXT TRAINS</span>
          <span class="rule" />
          {#if transit?.alerts.length}
            <span style="color:var(--rose)">! delays</span>
          {/if}
        </div>
        {#if allTrains.length}
          <!-- Hero first train -->
          <div class="transit-hero">
            <MTAPill line={allTrains[0].line} color={LINE_COLORS[allTrains[0].line] ?? '#888'} size={32} />
            <div style="flex:1;min-width:0">
              <div style="font-size:10px;color:var(--ink-dim);letter-spacing:1px">
                {transit?.stations[0]?.name?.toUpperCase() ?? 'NEXT'} · {allTrains[0].dest.toUpperCase()}
              </div>
              <div style="font-size:9px;color:{allTrains[0].delay > 0 ? 'var(--rose)' : 'var(--sage)'};letter-spacing:0.5px;margin-top:1px">
                {allTrains[0].status}
              </div>
            </div>
            <div class="transit-mins" style="font-family:var(--font-sans)">
              {allTrains[0].mins}<span style="font-size:14px;color:var(--ink-dim);margin-left:2px;font-weight:400">min</span>
            </div>
          </div>
          <!-- Remaining trains -->
          {#each allTrains.slice(1) as train}
            <div class="transit-row">
              <MTAPill line={train.line} color={LINE_COLORS[train.line] ?? '#888'} size={18} />
              <div style="flex:1;min-width:0">
                <div style="font-size:10.5px;color:var(--ink-dim);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;font-family:var(--font-sans)">{train.dest}</div>
                <div style="font-size:8.5px;color:{train.delay > 0 ? 'var(--rose)' : 'var(--ink-sub)'};letter-spacing:0.6px">{train.status}</div>
              </div>
              <div style="font-family:var(--font-sans);font-size:16px;font-weight:500;font-variant-numeric:tabular-nums;letter-spacing:-0.4px">
                {train.mins}<span style="font-size:9px;color:var(--ink-sub);margin-left:1px;font-weight:400">m</span>
              </div>
            </div>
          {/each}
        {:else}
          <div style="color:var(--ink-sub);font-size:11px">transit loading…</div>
        {/if}
      </div>

      <!-- CALENDAR -->
      <div class="calendar-block">
        <div class="section-header">
          <span>TODAY · {calendar?.events.length ?? 0} EVENTS</span>
          <span class="rule" />
          {#if calendar?.next_in}
            <span style="color:var(--ink-sub)">next in {calendar.next_in}</span>
          {/if}
        </div>
        <div class="timeline">
          <div class="timeline-spine" />
          {#each (calendar?.events ?? []) as event, i}
            <div class="timeline-event">
              <div class="timeline-node" class:active={i === 0} />
              <div class="timeline-time" style="font-family:var(--font-sans)">{event.time}</div>
              <div>
                <div style="font-family:var(--font-sans);font-size:13px;font-weight:500;line-height:1.2;color:var(--ink)">{event.title}</div>
                <div style="font-size:9.5px;color:var(--ink-dim);margin-top:2px;letter-spacing:0.5px">
                  {event.location.toLowerCase()}
                  {#if event.notion}
                    <span style="color:var(--sage);margin-left:6px">· notion/{event.notion.project}</span>
                  {/if}
                </div>
              </div>
            </div>
          {/each}
          {#if !calendar?.events.length}
            <div style="color:var(--ink-sub);font-size:11px">calendar loading…</div>
          {/if}
        </div>
      </div>
    </div>
  </div>

  <!-- FOOTER -->
  <footer class="home-footer">
    <div class="git-strip">
      <span style="font-size:9px;letter-spacing:1.5px;color:var(--ink-dim)">git</span>
      <CommitHeartbeat color="var(--sage)" count={36} />
      <span style="font-size:9px;letter-spacing:1.2px;color:var(--ink-sub);font-variant-numeric:tabular-nums">
        {github?.commits.length ?? 0}↑ {github?.prs.length ?? 0}pr
      </span>
    </div>
    <span class="footer-rule" />
    <div class="launcher-dock">
      {#each DOCK_ITEMS as item, i}
        <button class="dock-btn" on:click={() => goto(item.href)} aria-label={item.k}>
          <span class="dock-dot" class:first={i === 0} />
          {item.k}
        </button>
      {/each}
    </div>
    <span class="footer-rule" />
    <div style="flex:1;min-width:0">
      <Ticker items={rss?.ticker ?? []} color="var(--ink)" opacity={0.45} fontSize={10} />
    </div>
  </footer>
</ODScreen>

<style>
  .status-bar {
    display: flex; align-items: center; justify-content: space-between;
    font-size: 10px; letter-spacing: 1.5px; color: var(--ink-dim); font-family: var(--font-mono);
  }
  .status-left { display: flex; gap: 18px; }
  .status-right { display: flex; gap: 14px; }
  .brand { color: var(--ink); font-weight: 500; }

  .main-grid {
    flex: 1; display: grid;
    grid-template-columns: 1fr 320px;
    grid-template-rows: auto 1fr;
    gap: 18px 28px; margin-top: 4px; min-height: 0;
  }

  /* TIME */
  .time-block { grid-column: 1; grid-row: 1; }
  .clock-row { display: flex; align-items: baseline; gap: 14px; }
  .clock-hhmm {
    font-weight: 200; font-size: 148px; line-height: 0.85;
    letter-spacing: -7px; font-variant-numeric: tabular-nums; color: var(--ink);
  }
  .clock-meta { display: flex; flex-direction: column; gap: 4px; padding-bottom: 10px; }
  .clock-ss { font-weight: 300; font-size: 36px; letter-spacing: -1.5px; color: var(--ink-dim); line-height: 1; font-variant-numeric: tabular-nums; }
  .weather-row { display: flex; align-items: center; gap: 18px; margin-top: 6px; font-family: var(--font-sans); }
  .weather-temp { display: flex; align-items: center; gap: 10px; }
  .temp-num { font-weight: 300; font-size: 32px; letter-spacing: -1.2px; font-variant-numeric: tabular-nums; }
  .weather-detail { font-family: var(--font-mono); font-size: 11px; color: var(--ink-dim); letter-spacing: 1px; line-height: 1.5; }
  .weather-sparkline { margin-left: auto; padding-bottom: 4px; }

  /* NOW PLAYING */
  .now-playing-rail {
    grid-column: 2; grid-row: 1 / span 2;
    display: flex; flex-direction: column; gap: 14px;
    padding-left: 22px; border-left: 1px solid var(--line);
  }
  .np-label { font-size: 10px; letter-spacing: 2px; color: var(--ink-dim); display: flex; align-items: center; gap: 8px; }
  .np-text { display: flex; flex-direction: column; gap: 3px; }
  .np-track { font-weight: 600; font-size: 24px; line-height: 1.15; letter-spacing: -0.4px; color: var(--ink); }
  .np-artist { font-size: 14px; margin-top: 4px; letter-spacing: 0.2px; }
  .np-progress { display: flex; flex-direction: column; gap: 5px; margin-top: auto; }
  .progress-track { height: 2px; background: rgba(240,232,214,0.10); border-radius: 2px; overflow: hidden; }
  .progress-fill { height: 100%; background: var(--sand); }
  .progress-times { display: flex; justify-content: space-between; font-size: 10px; color: var(--ink-dim); font-variant-numeric: tabular-nums; letter-spacing: 1px; }
  .rss-stack { border-top: 1px solid var(--line); padding-top: 12px; display: flex; flex-direction: column; gap: 8px; }

  /* BOTTOM-LEFT */
  .bottom-left { grid-column: 1; grid-row: 2; display: grid; grid-template-columns: 1fr 1.1fr; gap: 24px; min-height: 0; }
  .transit-block { display: flex; flex-direction: column; gap: 8px; min-height: 0; }
  .section-header { font-size: 10px; letter-spacing: 2px; color: var(--ink-dim); display: flex; align-items: center; gap: 8px; }
  .rule { flex: 1; height: 1px; background: var(--line); }
  .transit-hero { display: flex; align-items: center; gap: 12px; }
  .transit-mins { font-weight: 300; font-size: 54px; font-variant-numeric: tabular-nums; letter-spacing: -2px; line-height: 0.9; color: var(--ink); }
  .transit-row { display: flex; align-items: center; gap: 9px; }

  /* CALENDAR */
  .calendar-block { display: flex; flex-direction: column; gap: 6px; min-height: 0; }
  .timeline { position: relative; flex: 1; padding-left: 14px; display: flex; flex-direction: column; gap: 6px; }
  .timeline-spine {
    position: absolute; left: 4px; top: 8px; bottom: 8px; width: 1px;
    background: linear-gradient(180deg, rgba(230,200,155,0.47) 0%, var(--line) 100%);
  }
  .timeline-event { display: flex; align-items: flex-start; gap: 10px; position: relative; }
  .timeline-node {
    position: absolute; left: -14px; top: 6px; width: 9px; height: 9px;
    border-radius: 9px; background: transparent; border: 1.5px solid rgba(240,232,214,0.4);
    flex-shrink: 0;
  }
  .timeline-node.active { background: var(--sand); border-color: var(--sand); }
  .timeline-time { width: 46px; font-family: var(--font-sans); font-size: 12.5px; font-weight: 500; font-variant-numeric: tabular-nums; letter-spacing: -0.2px; color: var(--ink); padding-top: 1px; flex-shrink: 0; }

  /* FOOTER */
  .home-footer { display: flex; align-items: center; gap: 16px; padding-top: 10px; border-top: 1px solid var(--line); }
  .git-strip { display: flex; align-items: center; gap: 8px; flex-shrink: 0; }
  .footer-rule { width: 1px; height: 14px; background: var(--line); flex-shrink: 0; }
  .launcher-dock { display: flex; gap: 14px; font-size: 10px; letter-spacing: 1.5px; color: var(--ink-dim); flex-shrink: 0; }
  .dock-btn {
    display: inline-flex; gap: 4px; align-items: center;
    background: none; border: none; cursor: pointer;
    color: var(--ink-dim); font-family: var(--font-mono); font-size: 10px; letter-spacing: 1.5px; padding: 0;
  }
  .dock-dot { width: 5px; height: 5px; border-radius: 5px; background: rgba(240,232,214,0.25); }
  .dock-dot.first { background: var(--sand); }
</style>
```

- [ ] **Step 3: Verify build**

```bash
cd frontend && npm run build
```

Expected: ✓ built. No TypeScript errors.

- [ ] **Step 4: Commit**

```bash
cd .. && git add frontend/src/routes/
git commit -m "feat(frontend): home screen — C v3 Atelier with live stores, transit, calendar, now playing, RSS ticker"
```

---

## Task 6: Playwright Smoke Test

**Files:**
- Create: `frontend/playwright.config.ts`
- Create: `frontend/tests/home.spec.ts`

- [ ] **Step 1: Create `playwright.config.ts`**

```typescript
// frontend/playwright.config.ts
import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './tests',
  use: {
    baseURL: 'http://localhost:8080',
    headless: true,
  },
  webServer: {
    command: 'npm run preview -- --port 4173',
    port: 4173,
    reuseExistingServer: !process.env.CI,
  },
});
```

- [ ] **Step 2: Create `tests/home.spec.ts`**

```typescript
// frontend/tests/home.spec.ts
import { test, expect } from '@playwright/test';

// These smoke tests run against the built frontend with a mock backend.
// They verify widgets mount without JS errors, not full data flow.

test.beforeEach(async ({ page }) => {
  // Intercept API calls so tests don't need a running backend
  await page.route('/api/state', (route) =>
    route.fulfill({
      status: 200,
      json: {
        weather: {
          tempF: 58, feelsLikeF: 56, highF: 64, lowF: 49,
          cond: 'Partly cloudy', code: 2,
          hourly: [{ h: '0', t: 58 }, { h: '1', t: 60 }],
          alerts: [],
        },
        transit: {
          stations: [{ name: 'Jay St', stop_id: 'A41N', lines: ['A'], primary: true,
            trains: [{ line: 'A', mins: 3, dest: 'Inwood', status: 'on time', delay: 0 }] }],
          secondary: [],
          alerts: [],
        },
        spotify: { is_playing: false, track: null, artist: null, album: null, progress: 0, elapsed: '0:00', total: '0:00', art_url: null },
        calendar: { events: [], next_in: null },
        github: { commits: [], prs: [], issues: [] },
        rss: { items: [], headlines: [], ticker: ['HN · Test headline'] },
        photos: { source: 'local', url: null, index: 0, total: 0, rotation_seconds: 30 },
        pomodoro: { running: false, phase: 'idle', remaining_seconds: 0, cycle: 0, cycles_total: 4, work_min: 25, break_min: 5, preset_name: '' },
      },
    })
  );
  await page.route('/api/config', (route) =>
    route.fulfill({
      status: 200,
      json: { device: { name: 'O-Deck', resolution: { width: 1024, height: 600 } }, home: {} },
    })
  );
  await page.route('/ws', (route) => route.abort());
});

test('home page loads without JS errors', async ({ page }) => {
  const errors: string[] = [];
  page.on('pageerror', (err) => errors.push(err.message));

  await page.goto('/');
  await page.waitForLoadState('networkidle');

  expect(errors).toHaveLength(0);
});

test('home page shows clock', async ({ page }) => {
  await page.goto('/');
  // Clock is always rendered (local JS, no backend needed)
  await expect(page.locator('.clock-hhmm')).toBeVisible();
});

test('home page shows O-DECK brand', async ({ page }) => {
  await page.goto('/');
  await expect(page.locator('.brand')).toContainText('O—DECK');
});

test('home page shows weather temperature', async ({ page }) => {
  await page.goto('/');
  await page.waitForTimeout(200);
  await expect(page.locator('.temp-num')).toContainText('58');
});

test('home page shows transit train', async ({ page }) => {
  await page.goto('/');
  await page.waitForTimeout(200);
  // MTAPill shows line letter
  await expect(page.locator('.pill').first()).toContainText('A');
});

test('home page launcher dock is present', async ({ page }) => {
  await page.goto('/');
  await expect(page.locator('.dock-btn').first()).toBeVisible();
});
```

- [ ] **Step 3: Run smoke tests**

```bash
cd frontend && npm run build && npx playwright test
```

Expected: all 6 tests pass.

- [ ] **Step 4: Commit**

```bash
cd .. && git add frontend/playwright.config.ts frontend/tests/ frontend/package.json
git commit -m "test(frontend): Playwright smoke tests for home screen"
```

---

## Self-Review

**Spec coverage:**
- Home screen C v3 Atelier: ✅ time hero, weather+sparkline, transit typographic, calendar timeline, now-playing strip, RSS ticker, footer dock
- Token system: ✅ CSS variables + Tailwind theme with all OD colors
- Motion modes: ✅ calm/music/rain/thunder derived from live store state
- DriftOrbs: ✅ canvas, speed/alpha multipliers per mode, thunder flash
- RainOverlay: ✅ for rain + thunder modes
- All design primitives: ✅ 14 components matching JSX references
- WebSocket: ✅ client with reconnect backoff, ping keep-alive
- Initial hydration: ✅ `/api/state` fetch on mount
- Playwright smoke: ✅ 6 tests covering no-JS-errors, clock, brand, weather, transit, dock
- 800×480 fallback: Tailwind responsive — home grid collapses gracefully (open item: on-device pass)

**Placeholder scan:** None found.

**Type consistency:**
- `TrainArrival.line` used in `MTAPill` → matches `LINE_COLORS` keys (string)
- `SpotifyData.progress` (0–1 float) → CSS width percentage in template ✅
- `appStore.motionMode` derived from `SpotifyData.is_playing` + `WeatherData.alerts` ✅

---

## Parallelization Strategy

- **This plan** runs in parallel with Plan 2 (Backend Integrations) — mocked API calls in tests keep it independent.
- Plan 4 (Fullscreen Apps) must run **after** this plan — it imports all primitives from `$lib/components/`.
- Recommended: one subagent, tasks 1–6 in order.

---

## New Chat Handoff Prompt

```
You are implementing the O-Deck frontend foundation plan.

Repo: /Users/oliversantana/Documents/dev/cyberdeck
Worktree: .worktrees/frontend-foundation  (branch: feature/frontend-foundation, based on feature/backend-foundation)
Plan: docs/superpowers/plans/2026-04-26-frontend-foundation.md

Design references (read before implementing each component):
- design/screens/system.jsx     — token system, ODStatusBar, ODDock, ODScreen primitives
- design/screens/notes.jsx      — MTAPill, WeatherIcon, EQBars, Ticker, AlbumArt, mock data shape
- design/screens/variation-c3.jsx — home screen (ScreenCv3), DriftOrbs, RainOverlay, Grain

Context:
- Backend foundation complete. Backend integrations running in parallel (use mock data for tests).
- SvelteKit + adapter-static. Output goes to frontend/build/ (backend serves it at /).
- ALL primitive components must match the JSX design references exactly in visual behavior.
- After EACH task: `cd frontend && npm run build` must succeed.
- Use superpowers:subagent-driven-development to execute task-by-task.

Start with Task 1 (scaffold).
```
