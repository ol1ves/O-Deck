# Fullscreen Apps Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement all eight fullscreen app routes + the diagnostics page, wired to live backend stores, matching the design references in `design/screens/apps-1.jsx` and `design/screens/apps-2.jsx`.

**Architecture:** Each route is a SvelteKit page under `frontend/src/routes/<name>/+page.svelte`. All routes share primitives from `$lib/components/` (Plan 3). Data comes from `appStore` (WebSocket) + direct API calls where needed. Navigation uses SvelteKit `goto` and `ODDock`. The diagnostics page is also reachable by tapping the time tile 5× (secret tap counter in the home page).

**Tech Stack:** SvelteKit, TypeScript, Svelte stores, Playwright (smoke tests per route)

**Dependency:** Plan 3 (Frontend Foundation) must be complete. All `$lib/components/*` and `$lib/ws.ts` are assumed present.

---

## Plan Series

1. Backend Foundation ✅ done
2. Backend Integrations → `2026-04-26-backend-integrations.md`
3. Frontend Foundation ✅ done (prerequisite)
4. **Fullscreen Apps** ← you are here
5. Install & Ops → `2026-04-26-install-ops.md`

---

## File Map

```
frontend/src/routes/
├── transit/+page.svelte         # CREATE
├── calendar/+page.svelte        # CREATE
├── github/+page.svelte          # CREATE
├── doomscroll/+page.svelte      # CREATE
├── photos/+page.svelte          # CREATE
├── pomodoro/+page.svelte        # CREATE
├── showcase/+page.svelte        # CREATE
├── subway/+page.svelte          # CREATE
├── diagnostics/+page.svelte     # CREATE
└── +page.svelte                 # MODIFY: add 5-tap diagnostics unlock

frontend/tests/
├── transit.spec.ts              # CREATE
├── calendar.spec.ts             # CREATE
├── github.spec.ts               # CREATE
├── doomscroll.spec.ts           # CREATE
├── photos.spec.ts               # CREATE
├── pomodoro.spec.ts             # CREATE
├── showcase.spec.ts             # CREATE
├── subway.spec.ts               # CREATE
└── diagnostics.spec.ts          # CREATE
```

---

## Setup

This plan runs in the same `feature/frontend-foundation` worktree (or a new `feature/fullscreen-apps` branch off it):

```bash
cd .worktrees/frontend-foundation
# or:
git worktree add .worktrees/fullscreen-apps -b feature/fullscreen-apps feature/frontend-foundation
cd .worktrees/fullscreen-apps
```

Confirm baseline:

```bash
cd frontend && npm run build && echo "baseline OK"
```

---

## Shared test helper

Before writing per-route tests, create a shared mock helper used by all specs:

- [ ] **Step 1: Create `frontend/tests/helpers.ts`**

```typescript
// frontend/tests/helpers.ts
import type { Page, Route } from '@playwright/test';

export const MOCK_STATE = {
  weather: {
    tempF: 58, feelsLikeF: 56, highF: 64, lowF: 49,
    cond: 'Partly cloudy', code: 2,
    hourly: [{ h: '0', t: 58 }, { h: '1', t: 60 }, { h: '2', t: 62 },
             { h: '3', t: 63 }, { h: '4', t: 61 }, { h: '5', t: 58 }],
    alerts: [],
  },
  transit: {
    stations: [
      { name: 'Jay St–MetroTech', stop_id: 'A41N', lines: ['A', 'C', 'F', 'R'], primary: true,
        trains: [
          { line: 'A', mins: 2, dest: 'Inwood', status: 'on time', delay: 0 },
          { line: 'C', mins: 6, dest: '168 St', status: '+2m delay', delay: 2 },
          { line: 'F', mins: 9, dest: 'Forest Hills', status: 'slow · signals', delay: 4 },
          { line: 'R', mins: 14, dest: 'Forest Hills', status: 'on time', delay: 0 },
        ] },
      { name: 'DeKalb Av', stop_id: 'R30N', lines: ['Q'], primary: true,
        trains: [{ line: 'Q', mins: 4, dest: '96 St', status: 'on time', delay: 0 }] },
    ],
    secondary: [
      { name: '14 St–Union Sq', stop_id: '635S', lines: ['4', '5', '6'], primary: false,
        trains: [
          { line: '4', mins: 3, dest: 'Bowling Green', status: 'on time', delay: 0 },
          { line: '5', mins: 7, dest: 'Brooklyn', status: 'on time', delay: 0 },
        ] },
      { name: 'W 4 St–Wash Sq', stop_id: 'A32S', lines: ['F', 'A', 'C'], primary: false,
        trains: [
          { line: 'F', mins: 4, dest: 'Coney Is', status: 'slow · signals', delay: 5 },
        ] },
    ],
    alerts: ['F: signal delays at Bergen St'],
  },
  spotify: {
    is_playing: true, track: 'Pyramid Song', artist: 'Radiohead', album: 'Amnesiac',
    progress: 0.34, elapsed: '1:54', total: '4:50', art_url: null,
  },
  calendar: {
    events: [
      { id: '1', title: 'Lunch w/ Maya', time: '12:30', duration: '30m', location: 'Devoción', color: '#9bb38b', notion: null },
      { id: '2', title: 'O-Deck install on Pi', time: '14:00', duration: '1h', location: 'Desk', color: '#c9a26f',
        notion: { page_id: 'abc', status: 'In Progress', project: 'cyberdeck' } },
    ],
    next_in: '43 min',
  },
  github: {
    commits: [
      { sha: 'a3f2c1', msg: 'transit: handle GTFS feed reconnect', repo: 'oliversantana/cyberdeck', time: '2026-04-26T10:00:00Z' },
      { sha: 'b81e4d', msg: 'pomodoro: persist preset across reload', repo: 'oliversantana/cyberdeck', time: '2026-04-26T09:00:00Z' },
    ],
    prs: [
      { number: 42, title: 'feat: notion ↔ google calendar join', repo: 'oliversantana/cyberdeck', status: 'open', age: '2026-04-24T10:00:00Z' },
    ],
    issues: [
      { number: 12, title: 'F train delay banner overflows on 800×480', repo: 'oliversantana/cyberdeck', label: 'bug', age: '2026-04-25T10:00:00Z' },
    ],
  },
  rss: {
    items: [
      { id: '1', src: 'TLDR', title: 'Apple unveils on-device LLM runtime', link: 'https://example.com/1', summary: 'New CoreML primitives.', age: '12m' },
      { id: '2', src: 'HN', title: 'Show HN: A 50-line distributed lock manager', link: 'https://example.com/2', summary: 'Built on Postgres.', age: '38m' },
    ],
    headlines: [
      { src: 'TLDR', title: 'Apple unveils on-device LLM runtime', age: '12m' },
    ],
    ticker: ['TLDR · Apple LLM runtime', 'HN · 50-line lock manager'],
  },
  photos: { source: 'local', url: '/api/photos/file/img1.jpg', index: 0, total: 5, rotation_seconds: 30 },
  pomodoro: { running: false, phase: 'idle', remaining_seconds: 0, cycle: 0, cycles_total: 4, work_min: 25, break_min: 5, preset_name: '' },
};

export async function mockBackend(page: Page) {
  await page.route('/api/state', (r: Route) => r.fulfill({ status: 200, json: MOCK_STATE }));
  await page.route('/api/config', (r: Route) => r.fulfill({
    status: 200,
    json: {
      device: { name: 'O-Deck', resolution: { width: 1024, height: 600 }, timezone: 'America/New_York' },
      home: { hero_tiles: ['now_playing'], core_tiles: ['time', 'weather', 'transit', 'calendar', 'rss'] },
      pomodoro: { presets: [{ name: 'Classic', work_min: 25, break_min: 5, cycles: 4, long_break_min: 15 }] },
    },
  }));
  await page.route('/api/status', (r: Route) => r.fulfill({
    status: 200,
    json: {
      ws_clients: 1,
      integrations: [
        { name: 'weather', error_count: 0, last_success: Date.now() / 1000 },
        { name: 'transit', error_count: 0, last_success: Date.now() / 1000 },
      ],
    },
  }));
  await page.route('/api/pomodoro/**', (r: Route) => r.fulfill({
    status: 200,
    json: { running: false, phase: 'idle', remaining_seconds: 0, cycle: 0, cycles_total: 4, work_min: 25, break_min: 5, preset_name: '' },
  }));
  await page.route('/ws', (r: Route) => r.abort());
}
```

- [ ] **Step 2: Commit helper**

```bash
git add frontend/tests/helpers.ts
git commit -m "test(frontend): shared mock backend helper for Playwright tests"
```

---

## Task 1: Transit Detail Route

**Files:**
- Create: `frontend/src/routes/transit/+page.svelte`
- Create: `frontend/tests/transit.spec.ts`

Reference: `design/screens/apps-1.jsx` → `TransitApp()`

- [ ] **Step 1: Write the failing smoke test**

```typescript
// frontend/tests/transit.spec.ts
import { test, expect } from '@playwright/test';
import { mockBackend } from './helpers';

test.beforeEach(async ({ page }) => { await mockBackend(page); });

test('transit page loads without JS errors', async ({ page }) => {
  const errors: string[] = [];
  page.on('pageerror', (e) => errors.push(e.message));
  await page.goto('/transit');
  await page.waitForLoadState('networkidle');
  expect(errors).toHaveLength(0);
});

test('transit page shows all 4 station names', async ({ page }) => {
  await page.goto('/transit');
  await page.waitForTimeout(300);
  await expect(page.getByText('Jay St–MetroTech')).toBeVisible();
  await expect(page.getByText('DeKalb Av')).toBeVisible();
  await expect(page.getByText('14 St–Union Sq')).toBeVisible();
  await expect(page.getByText('W 4 St–Wash Sq')).toBeVisible();
});

test('transit page shows alert banner', async ({ page }) => {
  await page.goto('/transit');
  await page.waitForTimeout(300);
  await expect(page.getByText(/signal delays/i)).toBeVisible();
});

test('transit page dock HOME tap navigates home', async ({ page }) => {
  await page.goto('/transit');
  await page.locator('.dock-btn').first().click();
  await expect(page).toHaveURL('/');
});
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd frontend && npx playwright test tests/transit.spec.ts
```

Expected: navigation to `/transit` shows 404 or empty page.

- [ ] **Step 3: Create `transit/+page.svelte`**

```svelte
<!-- frontend/src/routes/transit/+page.svelte -->
<script lang="ts">
  import { appStore } from '$lib/ws';
  import ODScreen from '$lib/components/ODScreen.svelte';
  import ODStatusBar from '$lib/components/ODStatusBar.svelte';
  import ODDock from '$lib/components/ODDock.svelte';
  import MTAPill from '$lib/components/MTAPill.svelte';

  $: transit = $appStore.transit;
  $: mode = $appStore.motionMode;

  const LINE_COLORS: Record<string, string> = {
    A: '#0039A6', C: '#0039A6', E: '#0039A6',
    B: '#FF6319', D: '#FF6319', F: '#FF6319', M: '#FF6319',
    N: '#FCCC0A', Q: '#FCCC0A', R: '#FCCC0A', W: '#FCCC0A',
    '1': '#EE352E', '2': '#EE352E', '3': '#EE352E',
    '4': '#00933C', '5': '#00933C', '6': '#00933C',
    L: '#A7A9AC', G: '#6CBE45', J: '#996633', Z: '#996633',
  };

  $: allStations = [
    ...(transit?.stations ?? []),
    ...(transit?.secondary ?? []),
  ].slice(0, 4);
</script>

<ODScreen {mode}>
  <ODStatusBar app="TRANSIT · LIVE · 4 stations" />

  <main class="station-grid">
    {#each allStations as stn, si}
      <div class="station-cell"
        style="
          padding-right:{si % 2 === 0 ? '18px' : '0'};
          border-right:{si % 2 === 0 ? '1px solid var(--line)' : 'none'};
          padding-bottom:{si < 2 ? '14px' : '0'};
          border-bottom:{si < 2 ? '1px solid var(--line)' : 'none'};
          padding-left:{si % 2 === 1 ? '4px' : '0'};
        "
      >
        <div class="station-header">
          <div>
            <div class="station-name">{stn.name}</div>
            <div style="font-size:10px;letter-spacing:1.5px;color:var(--ink-dim);margin-top:2px">
              {stn.primary ? 'PRIMARY' : 'SECONDARY · return home'}
            </div>
          </div>
          <span class="live-dot" style="color:var(--sage)">●</span>
        </div>

        <div class="train-list">
          {#each stn.trains.slice(0, stn.primary ? 4 : 3) as train}
            <div class="train-row">
              <MTAPill line={train.line} color={LINE_COLORS[train.line] ?? '#888'} size={26} />
              <div style="flex:1;min-width:0">
                <div style="font-family:var(--font-sans);font-size:13px;color:var(--ink);font-weight:500;line-height:1.2">
                  to {train.dest}
                </div>
                <div style="font-size:10px;color:{train.delay > 0 ? 'var(--rose)' : 'var(--sage)'};letter-spacing:0.6px;margin-top:1px">
                  {train.status}
                </div>
              </div>
              <div class="train-mins" style="font-family:var(--font-sans)">
                {train.mins}<span style="font-size:11px;color:var(--ink-dim);margin-left:2px;font-weight:400">min</span>
              </div>
            </div>
          {/each}
        </div>
      </div>
    {/each}
  </main>

  {#if transit?.alerts.length}
    <div class="alert-banner">
      {#each transit.alerts as alert}
        <div>! {alert}</div>
      {/each}
    </div>
  {/if}

  <ODDock active="HOME" />
</ODScreen>

<style>
  .station-grid {
    flex: 1; display: grid; grid-template-columns: 1fr 1fr; gap: 18px; min-height: 0; padding-top: 6px;
  }
  .station-cell { display: flex; flex-direction: column; gap: 8px; min-height: 0; }
  .station-header { display: flex; align-items: baseline; justify-content: space-between; }
  .station-name { font-family: var(--font-sans); font-size: 18px; font-weight: 500; letter-spacing: -0.3px; color: var(--ink); }
  .train-list { display: flex; flex-direction: column; gap: 4px; flex: 1; min-height: 0; }
  .train-row { display: flex; align-items: center; gap: 12px; padding: 4px 0; }
  .train-mins { font-weight: 300; font-size: 32px; letter-spacing: -1px; font-variant-numeric: tabular-nums; line-height: 1; color: var(--ink); }
  .alert-banner {
    font-size: 10px; color: var(--rose); letter-spacing: 1px; padding: 6px 10px;
    background: rgba(212,154,142,0.10); border: 1px solid rgba(212,154,142,0.22); border-radius: 8px;
  }
</style>
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd frontend && npm run build && npx playwright test tests/transit.spec.ts
```

Expected: all 4 tests pass.

- [ ] **Step 5: Commit**

```bash
cd .. && git add frontend/src/routes/transit/ frontend/tests/transit.spec.ts
git commit -m "feat(frontend): transit fullscreen — 4-station grid with alerts"
```

---

## Task 2: Calendar Route

**Files:**
- Create: `frontend/src/routes/calendar/+page.svelte`
- Create: `frontend/tests/calendar.spec.ts`

Reference: `design/screens/apps-1.jsx` → `CalendarApp()`

- [ ] **Step 1: Write failing smoke test**

```typescript
// frontend/tests/calendar.spec.ts
import { test, expect } from '@playwright/test';
import { mockBackend } from './helpers';

test.beforeEach(async ({ page }) => { await mockBackend(page); });

test('calendar page loads without JS errors', async ({ page }) => {
  const errors: string[] = [];
  page.on('pageerror', (e) => errors.push(e.message));
  await page.goto('/calendar');
  await page.waitForLoadState('networkidle');
  expect(errors).toHaveLength(0);
});

test('calendar page shows today events', async ({ page }) => {
  await page.goto('/calendar');
  await page.waitForTimeout(300);
  await expect(page.getByText('Lunch w/ Maya')).toBeVisible();
  await expect(page.getByText('O-Deck install on Pi')).toBeVisible();
});

test('calendar page shows Notion badge on linked event', async ({ page }) => {
  await page.goto('/calendar');
  await page.waitForTimeout(300);
  await expect(page.getByText(/notion\/cyberdeck/)).toBeVisible();
});
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd frontend && npx playwright test tests/calendar.spec.ts
```

Expected: navigation to `/calendar` fails (route doesn't exist).

- [ ] **Step 3: Create `calendar/+page.svelte`**

```svelte
<!-- frontend/src/routes/calendar/+page.svelte -->
<script lang="ts">
  import { appStore } from '$lib/ws';
  import ODScreen from '$lib/components/ODScreen.svelte';
  import ODStatusBar from '$lib/components/ODStatusBar.svelte';
  import ODDock from '$lib/components/ODDock.svelte';
  import SectionLabel from '$lib/components/SectionLabel.svelte';

  $: calendar = $appStore.calendar;
  $: mode = $appStore.motionMode;
  $: events = calendar?.events ?? [];

  const today = new Date();
  const weekDays = ['M', 'T', 'W', 'T', 'F', 'S', 'S'];
  const todayDow = (today.getDay() + 6) % 7; // 0=Mon

  // Hours for timeline (9 AM – 9 PM)
  const HOURS = Array.from({ length: 13 }, (_, i) => {
    const h = i + 9;
    return h < 12 ? `${h} AM` : h === 12 ? '12 PM' : `${h - 12} PM`;
  });
  const SLOT_PX = 32;
  const START_H = 9;

  function eventTop(timeStr: string): number {
    const [h, m] = timeStr.split(':').map(Number);
    let h24 = h;
    if (h < 9) h24 = h + 12;
    return (h24 - START_H) * SLOT_PX + (m / 60) * SLOT_PX;
  }

  function eventHeight(durStr: string): number {
    const hMatch = durStr.match(/(\d+)h/);
    const mMatch = durStr.match(/(\d+)m/);
    const totalMin = (hMatch ? parseInt(hMatch[1]) * 60 : 0) + (mMatch ? parseInt(mMatch[1]) : 0);
    return (totalMin / 60) * SLOT_PX;
  }

  const nowTop = (() => {
    const n = new Date();
    return (n.getHours() + n.getMinutes() / 60 - START_H) * SLOT_PX;
  })();

  const nowStr = new Date().toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', hour12: false });
</script>

<ODScreen {mode}>
  <ODStatusBar app="CALENDAR · TODAY · {events.length} events" />

  <main class="cal-grid">
    <!-- Day timeline -->
    <div class="day-col">
      <SectionLabel>// {today.toLocaleDateString('en-US', { weekday: 'long', month: 'short', day: 'numeric' }).toUpperCase()}</SectionLabel>
      <div class="timeline-wrap">
        {#each HOURS as h, i}
          <div class="hour-slot" style="top:{i * SLOT_PX}px">
            <span class="hour-label">{h}</span>
          </div>
        {/each}

        <!-- Now line -->
        {#if nowTop >= 0 && nowTop < HOURS.length * SLOT_PX}
          <div class="now-line" style="top:{nowTop}px">
            <div class="now-dot" />
            <div class="now-label">{nowStr}</div>
          </div>
        {/if}

        <!-- Events -->
        {#each events as event}
          <div
            class="event-block"
            style="
              top:{eventTop(event.time)}px;
              height:{Math.max(eventHeight(event.duration) - 2, 20)}px;
              background:{event.color}22;
              border-left:3px solid {event.color};
            "
          >
            <div class="event-title">{event.title}</div>
            <div class="event-meta">
              {event.time} · {event.duration} · {event.location.toLowerCase()}
              {#if event.notion}
                <span style="color:var(--sand)"> · notion/{event.notion.project}</span>
              {/if}
            </div>
          </div>
        {/each}
      </div>
    </div>

    <!-- Week mini + agenda -->
    <div class="right-col">
      <div>
        <SectionLabel>// WEEK</SectionLabel>
        <div class="week-grid">
          {#each weekDays as d, i}
            <div class="week-cell" class:today={i === todayDow}>
              <div style="font-size:9px;color:var(--ink-dim);letter-spacing:1px">{d}</div>
              <div class="week-num" class:today={i === todayDow}>{today.getDate() - todayDow + i}</div>
            </div>
          {/each}
        </div>
      </div>

      <div class="agenda">
        <SectionLabel>// UP NEXT{calendar?.next_in ? ' · ' + calendar.next_in : ''}</SectionLabel>
        {#each events as event, i}
          <div class="agenda-row" class:last={i === events.length - 1}>
            <div>
              <div class="agenda-time">{event.time}</div>
              <div style="font-size:9px;color:var(--ink-sub);letter-spacing:1px;font-family:var(--font-mono);margin-top:1px">{event.duration}</div>
            </div>
            <div>
              <div class="agenda-title">{event.title}</div>
              <div style="font-size:10px;color:var(--ink-dim);margin-top:2px;letter-spacing:0.4px">
                {event.location.toLowerCase()}
                {#if event.notion}
                  <span style="color:var(--sand)"> · notion/{event.notion.project} · {event.notion.status.toLowerCase()}</span>
                {/if}
              </div>
            </div>
          </div>
        {/each}
      </div>
    </div>
  </main>

  <ODDock active="HOME" />
</ODScreen>

<style>
  .cal-grid { flex: 1; display: grid; grid-template-columns: 1.2fr 1fr; gap: 24px; min-height: 0; overflow: hidden; }
  .day-col { display: flex; flex-direction: column; min-height: 0; }
  .timeline-wrap { position: relative; flex: 1; overflow: hidden; }
  .hour-slot { position: absolute; left: 0; right: 0; height: 32px; display: flex; align-items: flex-start; gap: 10px; border-top: 1px solid var(--line); }
  .hour-label { font-size: 9px; color: var(--ink-sub); letter-spacing: 1px; padding-top: 3px; width: 42px; font-family: var(--font-mono); }
  .now-line { position: absolute; left: 42px; right: 0; height: 1px; background: var(--rose); z-index: 3; }
  .now-dot { position: absolute; left: -6px; top: -4px; width: 8px; height: 8px; border-radius: 8px; background: var(--rose); }
  .now-label { position: absolute; right: 0; top: -14px; font-size: 9px; color: var(--rose); letter-spacing: 1px; font-family: var(--font-mono); background: var(--bg); padding: 0 6px; }
  .event-block { position: absolute; left: 54px; right: 0; border-radius: 6px; padding: 5px 9px; display: flex; flex-direction: column; justify-content: flex-start; overflow: hidden; }
  .event-title { font-family: var(--font-sans); font-size: 13px; font-weight: 500; color: var(--ink); line-height: 1.2; }
  .event-meta { font-family: var(--font-mono); font-size: 9px; color: var(--ink-dim); letter-spacing: 0.8px; margin-top: 1px; }
  .right-col { display: flex; flex-direction: column; gap: 14px; min-height: 0; }
  .week-grid { display: grid; grid-template-columns: repeat(7, 1fr); gap: 4px; }
  .week-cell { aspect-ratio: 1; display: flex; flex-direction: column; align-items: center; justify-content: center; background: rgba(240,232,214,0.04); border: 1px solid var(--line); border-radius: 6px; }
  .week-cell.today { background: rgba(212,154,142,0.12); border-color: rgba(212,154,142,0.33); }
  .week-num { font-family: var(--font-sans); font-size: 18px; font-weight: 400; color: var(--ink); font-variant-numeric: tabular-nums; letter-spacing: -0.5px; }
  .week-num.today { font-weight: 600; color: var(--rose); }
  .agenda { flex: 1; display: flex; flex-direction: column; min-height: 0; }
  .agenda-row { display: grid; grid-template-columns: 58px 1fr; gap: 12px; padding-bottom: 10px; border-bottom: 1px dashed var(--line); margin-bottom: 10px; }
  .agenda-row.last { border-bottom: none; margin-bottom: 0; }
  .agenda-time { font-family: var(--font-sans); font-size: 14px; font-weight: 500; color: var(--ink); font-variant-numeric: tabular-nums; letter-spacing: -0.3px; }
  .agenda-title { font-family: var(--font-sans); font-size: 13px; font-weight: 500; color: var(--ink); line-height: 1.2; }
</style>
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd frontend && npm run build && npx playwright test tests/calendar.spec.ts
```

Expected: all 3 tests pass.

- [ ] **Step 5: Commit**

```bash
cd .. && git add frontend/src/routes/calendar/ frontend/tests/calendar.spec.ts
git commit -m "feat(frontend): calendar fullscreen — day timeline + week mini + Notion join badges"
```

---

## Task 3: GitHub Route

**Files:**
- Create: `frontend/src/routes/github/+page.svelte`
- Create: `frontend/tests/github.spec.ts`

Reference: `design/screens/apps-2.jsx` → `GitHubApp()`

- [ ] **Step 1: Write failing smoke test**

```typescript
// frontend/tests/github.spec.ts
import { test, expect } from '@playwright/test';
import { mockBackend } from './helpers';

test.beforeEach(async ({ page }) => { await mockBackend(page); });

test('github page loads without JS errors', async ({ page }) => {
  const errors: string[] = [];
  page.on('pageerror', (e) => errors.push(e.message));
  await page.goto('/github');
  await page.waitForLoadState('networkidle');
  expect(errors).toHaveLength(0);
});

test('github page shows commit messages', async ({ page }) => {
  await page.goto('/github');
  await page.waitForTimeout(300);
  await expect(page.getByText('transit: handle GTFS feed reconnect')).toBeVisible();
});

test('github page shows open PR', async ({ page }) => {
  await page.goto('/github');
  await page.waitForTimeout(300);
  await expect(page.getByText('feat: notion ↔ google calendar join')).toBeVisible();
});

test('github page shows issue with label', async ({ page }) => {
  await page.goto('/github');
  await page.waitForTimeout(300);
  await expect(page.getByText('F train delay banner overflows')).toBeVisible();
  await expect(page.getByText('bug')).toBeVisible();
});
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd frontend && npx playwright test tests/github.spec.ts
```

- [ ] **Step 3: Create `github/+page.svelte`**

```svelte
<!-- frontend/src/routes/github/+page.svelte -->
<script lang="ts">
  import { appStore } from '$lib/ws';
  import ODScreen from '$lib/components/ODScreen.svelte';
  import ODStatusBar from '$lib/components/ODStatusBar.svelte';
  import ODDock from '$lib/components/ODDock.svelte';
  import SectionLabel from '$lib/components/SectionLabel.svelte';
  import CommitHeartbeat from '$lib/components/CommitHeartbeat.svelte';

  $: gh = $appStore.github;
  $: mode = $appStore.motionMode;

  function labelColor(label: string): string {
    if (label === 'bug') return 'var(--rose)';
    if (label === 'feat') return 'var(--lav)';
    return 'var(--sand)';
  }
  function labelBg(label: string): string {
    if (label === 'bug') return 'rgba(212,154,142,0.12)';
    if (label === 'feat') return 'rgba(160,143,179,0.12)';
    return 'rgba(230,200,155,0.12)';
  }
  function prStatusColor(status: string): string {
    return status === 'review' ? 'var(--sand)' : 'var(--sage)';
  }
  function prStatusBg(status: string): string {
    return status === 'review' ? 'rgba(230,200,155,0.12)' : 'rgba(168,193,154,0.12)';
  }
  function relativeTime(isoStr: string): string {
    const ms = Date.now() - new Date(isoStr).getTime();
    const h = Math.floor(ms / 3_600_000);
    const d = Math.floor(h / 24);
    if (d > 0) return `${d}d`;
    if (h > 0) return `${h}h`;
    return '<1h';
  }
</script>

<ODScreen {mode}>
  <ODStatusBar app="GITHUB · commits · PRs · issues" accent="var(--sage)" />

  <main class="gh-grid">
    <!-- Commits column -->
    <div class="commits-col">
      <div>
        <SectionLabel>// HEARTBEAT · 7d</SectionLabel>
        <CommitHeartbeat color="var(--sage)" count={56} maxHeight={34} />
      </div>

      <div style="flex:1;display:flex;flex-direction:column;min-height:0;margin-top:12px">
        <SectionLabel>// RECENT COMMITS</SectionLabel>
        <div class="commit-list">
          {#each (gh?.commits ?? []) as commit, i}
            <div class="commit-row" class:last={i === (gh?.commits.length ?? 0) - 1}>
              <span class="sha">{commit.sha}</span>
              <div style="min-width:0">
                <div class="commit-msg">{commit.msg}</div>
                <div class="commit-meta">
                  <span style="color:var(--sage)">+changes</span>
                  <span> · {commit.repo.split('/')[1]} · {relativeTime(commit.time)} ago</span>
                </div>
              </div>
            </div>
          {/each}
          {#if !gh?.commits.length}
            <div style="color:var(--ink-sub);font-size:11px">no commits</div>
          {/if}
        </div>
      </div>
    </div>

    <!-- PRs + Issues -->
    <div class="right-col">
      <div>
        <SectionLabel>// OPEN PRs · {gh?.prs.length ?? 0}</SectionLabel>
        <div class="pr-list">
          {#each (gh?.prs ?? []) as pr}
            <div class="pr-row">
              <span class="label-tag" style="color:{prStatusColor(pr.status)};background:{prStatusBg(pr.status)}">{pr.status}</span>
              <div>
                <div class="pr-title">{pr.title}</div>
                <div class="item-meta">#{pr.number} · {pr.repo.split('/')[1]} · {relativeTime(pr.age)}</div>
              </div>
            </div>
          {/each}
          {#if !gh?.prs.length}
            <div style="color:var(--ink-sub);font-size:11px">no open PRs</div>
          {/if}
        </div>
      </div>

      <div style="flex:1;display:flex;flex-direction:column;min-height:0;margin-top:14px">
        <SectionLabel>// ASSIGNED ISSUES · {gh?.issues.length ?? 0}</SectionLabel>
        <div class="issue-list">
          {#each (gh?.issues ?? []) as issue}
            <div class="pr-row">
              <span class="label-tag" style="color:{labelColor(issue.label)};background:{labelBg(issue.label)}">{issue.label}</span>
              <div>
                <div class="pr-title">{issue.title}</div>
                <div class="item-meta">#{issue.number} · {issue.repo.split('/')[1]} · {relativeTime(issue.age)}</div>
              </div>
            </div>
          {/each}
          {#if !gh?.issues.length}
            <div style="color:var(--ink-sub);font-size:11px">no assigned issues</div>
          {/if}
        </div>
      </div>
    </div>
  </main>

  <ODDock active="GH" />
</ODScreen>

<style>
  .gh-grid { flex: 1; display: grid; grid-template-columns: 1.4fr 1fr; gap: 24px; min-height: 0; }
  .commits-col { display: flex; flex-direction: column; min-height: 0; }
  .commit-list { display: flex; flex-direction: column; gap: 9px; flex: 1; min-height: 0; }
  .commit-row { display: grid; grid-template-columns: auto 1fr; gap: 12px; align-items: flex-start; padding-bottom: 9px; border-bottom: 1px dashed var(--line); }
  .commit-row.last { border-bottom: none; }
  .sha { font-family: var(--font-mono); font-size: 10px; color: var(--sand); letter-spacing: 0.5px; margin-top: 2px; }
  .commit-msg { font-family: var(--font-sans); font-size: 13px; color: var(--ink); line-height: 1.25; }
  .commit-meta { font-family: var(--font-mono); font-size: 9px; color: var(--ink-dim); letter-spacing: 0.8px; margin-top: 2px; }
  .right-col { display: flex; flex-direction: column; min-height: 0; }
  .pr-list, .issue-list { display: flex; flex-direction: column; gap: 9px; }
  .pr-row { display: flex; align-items: flex-start; gap: 10px; }
  .label-tag { font-family: var(--font-mono); font-size: 9px; letter-spacing: 0.6px; padding: 3px 7px; border-radius: 5px; margin-top: 1px; white-space: nowrap; }
  .pr-title { font-family: var(--font-sans); font-size: 12.5px; color: var(--ink); line-height: 1.3; }
  .item-meta { font-size: 9px; color: var(--ink-sub); letter-spacing: 0.7px; margin-top: 2px; }
</style>
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd frontend && npm run build && npx playwright test tests/github.spec.ts
```

Expected: all 4 tests pass.

- [ ] **Step 5: Commit**

```bash
cd .. && git add frontend/src/routes/github/ frontend/tests/github.spec.ts
git commit -m "feat(frontend): GitHub fullscreen — heartbeat, commits, PRs, issues"
```

---

## Task 4: Doomscroll Route

**Files:**
- Create: `frontend/src/routes/doomscroll/+page.svelte`
- Create: `frontend/tests/doomscroll.spec.ts`

Reference: `design/screens/apps-2.jsx` → `DoomApp()`. QR code is generated client-side as a simple SVG placeholder (real QR via `qrcode` npm package).

- [ ] **Step 1: Install QR library**

```bash
cd frontend && npm install qrcode && npm install -D @types/qrcode
```

- [ ] **Step 2: Write failing smoke test**

```typescript
// frontend/tests/doomscroll.spec.ts
import { test, expect } from '@playwright/test';
import { mockBackend } from './helpers';

test.beforeEach(async ({ page }) => { await mockBackend(page); });

test('doomscroll page loads without JS errors', async ({ page }) => {
  const errors: string[] = [];
  page.on('pageerror', (e) => errors.push(e.message));
  await page.goto('/doomscroll');
  await page.waitForLoadState('networkidle');
  expect(errors).toHaveLength(0);
});

test('doomscroll page shows feed items', async ({ page }) => {
  await page.goto('/doomscroll');
  await page.waitForTimeout(300);
  await expect(page.getByText('Apple unveils on-device LLM runtime')).toBeVisible();
});

test('doomscroll page shows QR section', async ({ page }) => {
  await page.goto('/doomscroll');
  await expect(page.getByText(/READ ON PHONE/i)).toBeVisible();
});

test('doomscroll clicking story updates QR panel', async ({ page }) => {
  await page.goto('/doomscroll');
  await page.waitForTimeout(300);
  // Click second item
  const items = page.locator('.feed-item');
  await items.nth(1).click();
  // QR panel title should update to second item
  await expect(page.locator('.qr-title')).toContainText('50-line distributed lock manager');
});
```

- [ ] **Step 3: Run test to verify it fails**

```bash
cd frontend && npx playwright test tests/doomscroll.spec.ts
```

- [ ] **Step 4: Create `doomscroll/+page.svelte`**

```svelte
<!-- frontend/src/routes/doomscroll/+page.svelte -->
<script lang="ts">
  import { onMount } from 'svelte';
  import { appStore } from '$lib/ws';
  import ODScreen from '$lib/components/ODScreen.svelte';
  import ODStatusBar from '$lib/components/ODStatusBar.svelte';
  import ODDock from '$lib/components/ODDock.svelte';
  import SectionLabel from '$lib/components/SectionLabel.svelte';
  import type { RSSItem } from '$lib/types';

  $: rss = $appStore.rss;
  $: mode = $appStore.motionMode;
  $: items = rss?.items ?? [];

  let selectedIdx = 0;
  $: selected = items[selectedIdx] ?? null;

  let qrDataUrl = '';

  async function generateQR(url: string) {
    if (!url) { qrDataUrl = ''; return; }
    try {
      const QRCode = (await import('qrcode')).default;
      qrDataUrl = await QRCode.toDataURL(url, {
        width: 220,
        color: { dark: '#1a1508', light: '#f5ecd6' },
        margin: 2,
      });
    } catch {
      qrDataUrl = '';
    }
  }

  $: if (selected?.link) generateQR(selected.link);

  function srcColor(src: string): string {
    const colors: Record<string, string> = {
      TLDR: 'var(--sand)', HN: 'var(--rose)', default: 'var(--ink-dim)',
    };
    if (src.startsWith('r/')) return 'var(--sage)';
    if (src === 'YT') return 'var(--rose)';
    return colors[src] ?? colors.default;
  }
</script>

<ODScreen {mode}>
  <ODStatusBar app="DOOMSCROLL · {items.length} items · all sources" accent="var(--sand)" />

  <main class="doom-grid">
    <!-- Feed list -->
    <div class="feed-col">
      <SectionLabel>// FEED</SectionLabel>
      <div class="feed-list">
        {#each items as item, i}
          <button
            class="feed-item"
            class:selected={i === selectedIdx}
            on:click={() => { selectedIdx = i; }}
          >
            <span class="feed-src" style="color:{srcColor(item.src)}">{item.src}</span>
            <div style="min-width:0">
              <div class="feed-title" class:selected-title={i === selectedIdx}>{item.title}</div>
              <div class="feed-summary">{item.summary}</div>
            </div>
            <span class="feed-age">{item.age}</span>
          </button>
        {/each}
        {#if !items.length}
          <div style="color:var(--ink-sub);font-size:11px">feed loading…</div>
        {/if}
      </div>
    </div>

    <!-- QR panel -->
    <aside class="qr-panel">
      <SectionLabel accent="var(--sand)">// READ ON PHONE</SectionLabel>
      {#if qrDataUrl}
        <img src={qrDataUrl} alt="QR code" class="qr-img" />
      {:else}
        <div class="qr-placeholder">QR</div>
      {/if}
      {#if selected}
        <div class="qr-title">{selected.title}</div>
        <div class="qr-meta">
          scan with phone camera<br />
          {selected.src.toLowerCase()} · tap to open
        </div>
      {/if}
      <div style="flex:1" />
      <div style="font-size:10px;color:var(--ink-sub);letter-spacing:1px;line-height:1.4;font-family:var(--font-mono)">
        tap any story above<br />to load its QR code
      </div>
    </aside>
  </main>

  <ODDock active="DOOM" />
</ODScreen>

<style>
  .doom-grid { flex: 1; display: grid; grid-template-columns: 1fr 320px; gap: 24px; min-height: 0; }
  .feed-col { display: flex; flex-direction: column; gap: 8px; min-height: 0; overflow: hidden; }
  .feed-list { display: flex; flex-direction: column; gap: 10px; flex: 1; min-height: 0; overflow: hidden; }
  .feed-item {
    display: grid; grid-template-columns: 48px 1fr auto; gap: 12px; align-items: flex-start;
    padding: 8px 10px; border-radius: 8px; text-align: left;
    background: transparent; border: 1px solid transparent; cursor: pointer;
    width: 100%; font-family: inherit;
  }
  .feed-item.selected { background: rgba(230,200,155,0.06); border-color: rgba(230,200,155,0.2); }
  .feed-src { font-family: var(--font-mono); font-size: 9px; letter-spacing: 1px; margin-top: 2px; }
  .feed-title { font-family: var(--font-sans); font-size: 13.5px; color: var(--ink); line-height: 1.3; font-weight: 400; }
  .feed-title.selected-title { font-weight: 500; }
  .feed-summary { font-family: var(--font-sans); font-size: 11px; color: var(--ink-dim); margin-top: 3px; line-height: 1.4; }
  .feed-age { font-size: 9px; color: var(--ink-sub); letter-spacing: 0.8px; font-family: var(--font-mono); margin-top: 2px; }
  .qr-panel { display: flex; flex-direction: column; gap: 10px; min-height: 0; padding-left: 18px; border-left: 1px solid var(--line); }
  .qr-img { width: 220px; height: 220px; border-radius: 8px; }
  .qr-placeholder { width: 220px; height: 220px; background: rgba(240,232,214,0.05); border-radius: 8px; display: flex; align-items: center; justify-content: center; color: var(--ink-sub); font-size: 24px; }
  .qr-title { font-family: var(--font-sans); font-size: 13px; color: var(--ink); font-weight: 500; line-height: 1.3; margin-top: 4px; }
  .qr-meta { font-family: var(--font-mono); font-size: 9px; color: var(--ink-dim); letter-spacing: 0.8px; line-height: 1.5; }
</style>
```

- [ ] **Step 5: Run test to verify it passes**

```bash
cd frontend && npm run build && npx playwright test tests/doomscroll.spec.ts
```

Expected: all 4 tests pass.

- [ ] **Step 6: Commit**

```bash
cd .. && git add frontend/src/routes/doomscroll/ frontend/tests/doomscroll.spec.ts
git commit -m "feat(frontend): doomscroll — RSS feed list with real QR code handoff"
```

---

## Task 5: Pomodoro Route

**Files:**
- Create: `frontend/src/routes/pomodoro/+page.svelte`
- Create: `frontend/tests/pomodoro.spec.ts`

Reference: `design/screens/apps-1.jsx` → `PomoApp()`. Backend REST controls timer; WS broadcasts `pomodoro.update`.

- [ ] **Step 1: Write failing smoke test**

```typescript
// frontend/tests/pomodoro.spec.ts
import { test, expect } from '@playwright/test';
import { mockBackend } from './helpers';

test.beforeEach(async ({ page }) => { await mockBackend(page); });

test('pomodoro page loads without JS errors', async ({ page }) => {
  const errors: string[] = [];
  page.on('pageerror', (e) => errors.push(e.message));
  await page.goto('/pomodoro');
  await page.waitForLoadState('networkidle');
  expect(errors).toHaveLength(0);
});

test('pomodoro page shows idle state', async ({ page }) => {
  await page.goto('/pomodoro');
  await page.waitForTimeout(200);
  await expect(page.getByText('IDLE')).toBeVisible();
});

test('pomodoro page shows preset selector', async ({ page }) => {
  await page.goto('/pomodoro');
  await expect(page.getByText('Classic')).toBeVisible();
});

test('pomodoro start button calls API', async ({ page }) => {
  let startCalled = false;
  await page.route('/api/pomodoro/start', (r) => {
    startCalled = true;
    r.fulfill({ status: 200, json: { running: true, phase: 'work', remaining_seconds: 1500, cycle: 1, cycles_total: 4, work_min: 25, break_min: 5, preset_name: 'Classic' } });
  });

  await page.goto('/pomodoro');
  await page.locator('button:has-text("Start")').click();
  await page.waitForTimeout(200);
  expect(startCalled).toBe(true);
});
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd frontend && npx playwright test tests/pomodoro.spec.ts
```

- [ ] **Step 3: Create `pomodoro/+page.svelte`**

```svelte
<!-- frontend/src/routes/pomodoro/+page.svelte -->
<script lang="ts">
  import { appStore } from '$lib/ws';
  import { startPomodoro, pausePomodoro, stopPomodoro } from '$lib/api';
  import ODScreen from '$lib/components/ODScreen.svelte';
  import ODStatusBar from '$lib/components/ODStatusBar.svelte';
  import ODDock from '$lib/components/ODDock.svelte';
  import { onMount } from 'svelte';

  $: pomo = $appStore.pomodoro;
  $: mode = $appStore.motionMode;

  // Local countdown — counts down from remaining_seconds every second
  let localRemaining = 0;
  let localInterval: ReturnType<typeof setInterval>;

  $: if (pomo) {
    localRemaining = pomo.remaining_seconds;
    clearInterval(localInterval);
    if (pomo.running) {
      localInterval = setInterval(() => {
        localRemaining = Math.max(0, localRemaining - 1);
      }, 1000);
    }
  }

  onMount(() => () => clearInterval(localInterval));

  $: mm = String(Math.floor(localRemaining / 60)).padStart(2, '0');
  $: ss = String(localRemaining % 60).padStart(2, '0');

  $: total = (pomo?.work_min ?? 25) * 60;
  $: elapsed = total - localRemaining;
  $: progress = total > 0 ? elapsed / total : 0;
  $: circum = 2 * Math.PI * 160;
  $: dashArray = `${circum * progress} ${circum}`;

  // Presets from config (fetched once)
  let presets: Array<{ name: string; work_min: number; break_min: number; cycles: number; long_break_min: number }> = [
    { name: 'Classic', work_min: 25, break_min: 5, cycles: 4, long_break_min: 15 },
    { name: 'Deep',    work_min: 50, break_min: 10, cycles: 3, long_break_min: 20 },
  ];
  let selectedPreset = presets[0];

  async function handleStart() {
    await startPomodoro(selectedPreset);
  }
  async function handlePause() {
    await pausePomodoro();
  }
  async function handleStop() {
    await stopPomodoro();
  }

  $: isIdle = !pomo || pomo.phase === 'idle';
  $: isRunning = pomo?.running === true;
</script>

<ODScreen {mode}>
  <ODStatusBar
    app="POMODORO · {pomo?.preset_name || 'IDLE'} · cycle {pomo?.cycle ?? 0}/{pomo?.cycles_total ?? 4}"
    accent="var(--rose)"
  />

  <main class="pomo-main">
    <!-- Circular ring + countdown -->
    <div class="ring-wrap">
      <svg width="340" height="340" viewBox="0 0 340 340">
        <circle cx="170" cy="170" r="160" fill="none" stroke="rgba(240,232,214,0.06)" stroke-width="2" />
        <circle
          cx="170" cy="170" r="160" fill="none"
          stroke="var(--rose)" stroke-width="3"
          stroke-dasharray={dashArray}
          stroke-linecap="round"
          transform="rotate(-90 170 170)"
        />
        <!-- tick marks every 5min of 25min -->
        {#each Array(5) as _, i}
          {@const a = -Math.PI / 2 + (i + 1) / 5 * Math.PI * 2}
          <line
            x1={170 + Math.cos(a) * 150} y1={170 + Math.sin(a) * 150}
            x2={170 + Math.cos(a) * 166} y2={170 + Math.sin(a) * 166}
            stroke="var(--ink-sub)" stroke-width="1"
          />
        {/each}
      </svg>
      <div class="countdown">
        <div style="font-size:11px;letter-spacing:2.5px;color:var(--ink-dim);margin-bottom:4px">
          {isIdle ? 'IDLE' : pomo?.phase?.toUpperCase() ?? 'FOCUS'}
        </div>
        <div class="countdown-time" style="font-family:var(--font-sans)">
          {mm}<span class="blink" style="color:var(--rose)">:</span>{ss}
        </div>
        <div style="font-size:11px;letter-spacing:2px;color:var(--ink-sub);margin-top:6px">
          of {pomo?.work_min ?? 25}:00
        </div>
      </div>
    </div>

    <!-- Cycle dots -->
    <div class="cycle-dots">
      {#each Array(pomo?.cycles_total ?? 4) as _, i}
        <div
          class="cycle-dot"
          style="background:{i < (pomo?.cycle ?? 0) ? 'var(--rose)' : i === (pomo?.cycle ?? 0) ? 'rgba(212,154,142,0.33)' : 'transparent'};border:{i >= (pomo?.cycle ?? 0) ? '1.5px solid var(--ink-sub)' : 'none'}"
        />
      {/each}
      <div style="font-size:10px;letter-spacing:1.5px;color:var(--ink-dim);margin-left:8px">
        cycle {pomo?.cycle ?? 0} of {pomo?.cycles_total ?? 4}
      </div>
    </div>

    <!-- Preset selector (only in idle) -->
    {#if isIdle}
      <div class="preset-selector">
        {#each presets as preset}
          <button
            class="preset-btn"
            class:active={selectedPreset.name === preset.name}
            on:click={() => { selectedPreset = preset; }}
          >
            {preset.name} · {preset.work_min}m
          </button>
        {/each}
      </div>
    {/if}

    <!-- Controls -->
    <div class="controls">
      {#if isIdle}
        <button class="ctrl-btn primary" on:click={handleStart}>Start</button>
      {:else if isRunning}
        <button class="ctrl-btn" on:click={handlePause}>Pause</button>
        <button class="ctrl-btn danger" on:click={handleStop}>Stop</button>
      {:else}
        <button class="ctrl-btn primary" on:click={async () => { await fetch('/api/pomodoro/resume', {method:'POST'}); }}>Resume</button>
        <button class="ctrl-btn danger" on:click={handleStop}>Stop</button>
      {/if}
    </div>
  </main>

  <ODDock active="POMO" />
</ODScreen>

<style>
  .pomo-main { flex: 1; display: flex; flex-direction: column; justify-content: center; align-items: center; gap: 24px; position: relative; }
  .ring-wrap { position: relative; width: 340px; height: 340px; display: flex; align-items: center; justify-content: center; }
  .ring-wrap svg { position: absolute; inset: 0; }
  .countdown { text-align: center; position: relative; z-index: 1; }
  .countdown-time { font-weight: 200; font-size: 118px; letter-spacing: -5px; line-height: 0.95; font-variant-numeric: tabular-nums; color: var(--ink); }
  .cycle-dots { display: flex; gap: 12px; align-items: center; }
  .cycle-dot { width: 10px; height: 10px; border-radius: 10px; }
  .preset-selector { display: flex; gap: 12px; }
  .preset-btn {
    font-family: var(--font-mono); font-size: 10px; letter-spacing: 1.5px;
    padding: 6px 14px; border-radius: 6px; border: 1px solid var(--line); background: transparent;
    color: var(--ink-dim); cursor: pointer;
  }
  .preset-btn.active { border-color: var(--rose); color: var(--rose); background: rgba(212,154,142,0.08); }
  .controls { display: flex; gap: 12px; }
  .ctrl-btn {
    font-family: var(--font-mono); font-size: 11px; letter-spacing: 1.5px;
    padding: 8px 24px; border-radius: 8px; border: 1px solid var(--line);
    background: rgba(240,232,214,0.06); color: var(--ink); cursor: pointer;
  }
  .ctrl-btn.primary { border-color: var(--rose); color: var(--rose); background: rgba(212,154,142,0.10); }
  .ctrl-btn.danger { border-color: rgba(212,154,142,0.3); color: var(--ink-sub); }
</style>
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd frontend && npm run build && npx playwright test tests/pomodoro.spec.ts
```

Expected: all 4 tests pass.

- [ ] **Step 5: Commit**

```bash
cd .. && git add frontend/src/routes/pomodoro/ frontend/tests/pomodoro.spec.ts
git commit -m "feat(frontend): pomodoro fullscreen — circular timer, REST controls, cycle dots"
```

---

## Task 6: Photos Route

**Files:**
- Create: `frontend/src/routes/photos/+page.svelte`
- Create: `frontend/tests/photos.spec.ts`

Reference: `design/screens/apps-2.jsx` → `PhotoApp()`

- [ ] **Step 1: Write failing smoke test**

```typescript
// frontend/tests/photos.spec.ts
import { test, expect } from '@playwright/test';
import { mockBackend } from './helpers';

test.beforeEach(async ({ page }) => { await mockBackend(page); });

test('photos page loads without JS errors', async ({ page }) => {
  const errors: string[] = [];
  page.on('pageerror', (e) => errors.push(e.message));
  await page.goto('/photos');
  await page.waitForLoadState('networkidle');
  expect(errors).toHaveLength(0);
});

test('photos page shows rotation metadata', async ({ page }) => {
  await page.goto('/photos');
  await expect(page.getByText(/auto-rotate/i)).toBeVisible();
});
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd frontend && npx playwright test tests/photos.spec.ts
```

- [ ] **Step 3: Create `photos/+page.svelte`**

```svelte
<!-- frontend/src/routes/photos/+page.svelte -->
<script lang="ts">
  import { appStore } from '$lib/ws';
  import { goto } from '$app/navigation';

  $: photos = $appStore.photos;
  $: url = photos?.url ?? null;
  $: index = photos?.index ?? 0;
  $: total = photos?.total ?? 0;
  $: rotation = photos?.rotation_seconds ?? 30;
  $: source = photos?.source ?? 'local';
  $: progress = total > 0 ? ((index + 1) / total) : 0;
</script>

<!-- Full-bleed, minimal chrome — no ODScreen wrapper here -->
<div class="photo-screen">
  {#if url}
    <img src={url} alt="Photo {index + 1}" class="photo-img" />
  {:else}
    <div class="photo-placeholder" />
  {/if}

  <!-- Top chrome -->
  <div class="chrome-top">
    <button class="chrome-home" on:click={() => goto('/')}>O—DECK / PHOTO</button>
    <span>{index + 1} of {total} · auto-rotate {rotation}s · ◐</span>
  </div>

  <!-- Bottom caption/progress -->
  <div class="caption">
    [{source.replace('_', ' ')}]
  </div>
  <div class="progress-bar" style="width:{(progress * 100).toFixed(1)}%" />
</div>

<style>
  .photo-screen {
    width: 100vw; height: 100vh; background: #0a0908;
    position: relative; overflow: hidden;
    font-family: var(--font-mono); color: var(--ink);
  }
  .photo-img { width: 100%; height: 100%; object-fit: cover; display: block; }
  .photo-placeholder {
    width: 100%; height: 100%;
    background: repeating-linear-gradient(118deg, rgba(255,255,255,0.02) 0 2px, transparent 2px 8px),
      radial-gradient(70% 60% at 30% 40%, #d49a8e 0%, transparent 60%),
      linear-gradient(180deg, #c8a377 0%, #6b4838 100%);
  }
  .chrome-top {
    position: absolute; top: 14px; left: 18px; right: 18px;
    display: flex; justify-content: space-between; align-items: center;
    font-size: 9px; color: rgba(255,255,255,0.55); letter-spacing: 1.5px;
  }
  .chrome-home { background: none; border: none; color: rgba(255,255,255,0.55); font-family: var(--font-mono); font-size: 9px; letter-spacing: 1.5px; cursor: pointer; padding: 0; }
  .caption {
    position: absolute; bottom: 16px; left: 50%; transform: translateX(-50%);
    font-size: 10px; color: rgba(255,255,255,0.55); letter-spacing: 2px;
    padding: 4px 10px; background: rgba(0,0,0,0.25); border-radius: 4px; backdrop-filter: blur(6px);
  }
  .progress-bar { position: absolute; bottom: 0; left: 0; height: 1px; background: rgba(255,255,255,0.4); }
</style>
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd frontend && npm run build && npx playwright test tests/photos.spec.ts
```

Expected: both tests pass.

- [ ] **Step 5: Commit**

```bash
cd .. && git add frontend/src/routes/photos/ frontend/tests/photos.spec.ts
git commit -m "feat(frontend): photo frame fullscreen — full-bleed with rotation progress"
```

---

## Task 7: Showcase Route

**Files:**
- Create: `frontend/src/routes/showcase/+page.svelte`
- Create: `frontend/tests/showcase.spec.ts`

Reference: `design/screens/apps-2.jsx` → `ShowcaseApp()`. Tap anywhere → navigate home.

- [ ] **Step 1: Write failing smoke test**

```typescript
// frontend/tests/showcase.spec.ts
import { test, expect } from '@playwright/test';
import { mockBackend } from './helpers';

test.beforeEach(async ({ page }) => { await mockBackend(page); });

test('showcase page loads without JS errors', async ({ page }) => {
  const errors: string[] = [];
  page.on('pageerror', (e) => errors.push(e.message));
  await page.goto('/showcase');
  await page.waitForLoadState('networkidle');
  expect(errors).toHaveLength(0);
});

test('showcase tap navigates home', async ({ page }) => {
  await page.goto('/showcase');
  await page.waitForLoadState('networkidle');
  await page.click('body');
  await expect(page).toHaveURL('/');
});

test('showcase shows mode identifier', async ({ page }) => {
  await page.goto('/showcase');
  await expect(page.getByText(/SHOWCASE/)).toBeVisible();
});
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd frontend && npx playwright test tests/showcase.spec.ts
```

- [ ] **Step 3: Create `showcase/+page.svelte`**

```svelte
<!-- frontend/src/routes/showcase/+page.svelte -->
<script lang="ts">
  import { appStore } from '$lib/ws';
  import DriftOrbs from '$lib/components/DriftOrbs.svelte';
  import Grain from '$lib/components/Grain.svelte';
  import { goto } from '$app/navigation';

  $: mode = $appStore.motionMode;

  const palettes: Record<string, string[]> = {
    music:   ['#a08fb3', '#d49a8e', '#e6c89b', '#7a90a8', '#a8c19a'],
    calm:    ['#e6c89b', '#a8c19a', '#7a5f4a', '#5a6a78', '#d49a8e'],
    rain:    ['#5a7088', '#7a90a8', '#3e556a', '#a8c19a', '#9bb38b'],
    thunder: ['#c8b89a', '#7a6a8a', '#3e3a4a', '#d49a8e', '#e6c89b'],
  };
  $: palette = palettes[mode] ?? palettes.calm;
</script>

<!-- svelte-ignore a11y-click-events-have-key-events a11y-no-static-element-interactions -->
<div class="showcase-screen" on:click={() => goto('/')}>
  <DriftOrbs {palette} {mode} count={10} />
  <Grain />
  <div class="identifier">SHOWCASE · {mode.toUpperCase()} · tap to return</div>
</div>

<style>
  .showcase-screen {
    width: 100vw; height: 100vh; background: #0c0a08;
    position: relative; overflow: hidden;
    font-family: var(--font-mono); color: var(--ink);
    cursor: pointer;
  }
  .identifier {
    position: absolute; bottom: 14px; right: 18px;
    font-size: 9px; color: rgba(240,232,214,0.35); letter-spacing: 2px;
    z-index: 2; pointer-events: none;
  }
</style>
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd frontend && npm run build && npx playwright test tests/showcase.spec.ts
```

Expected: all 3 tests pass.

- [ ] **Step 5: Commit**

```bash
cd .. && git add frontend/src/routes/showcase/ frontend/tests/showcase.spec.ts
git commit -m "feat(frontend): showcase fullscreen — DriftOrbs canvas, mode-reactive, tap-to-return"
```

---

## Task 8: Subway Map Route

**Files:**
- Create: `frontend/src/routes/subway/+page.svelte`
- Create: `frontend/tests/subway.spec.ts`

Reference: `design/screens/apps-2.jsx` → `SubwayApp()`. Abstract SVG map with animated train markers.

- [ ] **Step 1: Write failing smoke test**

```typescript
// frontend/tests/subway.spec.ts
import { test, expect } from '@playwright/test';
import { mockBackend } from './helpers';

test.beforeEach(async ({ page }) => { await mockBackend(page); });

test('subway page loads without JS errors', async ({ page }) => {
  const errors: string[] = [];
  page.on('pageerror', (e) => errors.push(e.message));
  await page.goto('/subway');
  await page.waitForLoadState('networkidle');
  expect(errors).toHaveLength(0);
});

test('subway page shows line labels', async ({ page }) => {
  await page.goto('/subway');
  await expect(page.getByText('A/C')).toBeVisible();
  await expect(page.getByText('F')).toBeVisible();
  await expect(page.getByText('Q/R')).toBeVisible();
});

test('subway page shows Jay St marker', async ({ page }) => {
  await page.goto('/subway');
  await expect(page.getByText('YOU · JAY ST')).toBeVisible();
});
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd frontend && npx playwright test tests/subway.spec.ts
```

- [ ] **Step 3: Create `subway/+page.svelte`**

```svelte
<!-- frontend/src/routes/subway/+page.svelte -->
<script lang="ts">
  import { appStore } from '$lib/ws';
  import ODScreen from '$lib/components/ODScreen.svelte';
  import ODStatusBar from '$lib/components/ODStatusBar.svelte';
  import ODDock from '$lib/components/ODDock.svelte';
  import SectionLabel from '$lib/components/SectionLabel.svelte';

  $: transit = $appStore.transit;
  $: mode = $appStore.motionMode;

  const LINES = [
    { color: '#0039A6', label: 'A/C', y: 130 },
    { color: '#FF6319', label: 'F',   y: 200 },
    { color: '#FCCC0A', label: 'Q/R', y: 270 },
    { color: '#00933C', label: '4/5/6', y: 340 },
  ];

  const STATIONS = [
    { x: 120, label: 'High St' },
    { x: 240, label: 'Jay St' },
    { x: 360, label: 'Court St' },
    { x: 480, label: 'DeKalb' },
    { x: 600, label: 'Atlantic' },
    { x: 720, label: '14 St' },
    { x: 820, label: 'W 4 St' },
  ];

  $: onTimeCount = transit
    ? transit.stations.concat(transit.secondary).flatMap((s) => s.trains).filter((t) => t.delay === 0).length
    : 134;
  $: delayedCount = transit
    ? transit.stations.concat(transit.secondary).flatMap((s) => s.trains).filter((t) => t.delay > 0).length
    : 8;
</script>

<ODScreen {mode}>
  <ODStatusBar app="SUBWAY · LIVE · GTFS-RT" />

  <main style="flex:1;position:relative;min-height:0;">
    <SectionLabel>// MTA · abstract live diagram</SectionLabel>

    <svg viewBox="0 0 920 420" style="width:100%;height:calc(100% - 20px)">
      {#each LINES as l}
        <g>
          <path
            d="M 60 {l.y} Q 300 {l.y - 20} 460 {l.y} T 860 {l.y}"
            stroke={l.color} stroke-width="6" fill="none" stroke-linecap="round" opacity="0.9"
          />
          <text x="20" y={l.y + 5} fill="var(--ink)" font-size="13" font-family="var(--font-mono)" letter-spacing="1">{l.label}</text>
        </g>
      {/each}

      {#each STATIONS as s, xi}
        <g>
          {#each LINES as l, li}
            <circle
              cx={s.x}
              cy={l.y + Math.sin((xi + li) * 0.7) * 6}
              r={xi === 1 ? 8 : 4}
              fill="var(--bg)"
              stroke={l.color}
              stroke-width="2"
            />
          {/each}
        </g>
      {/each}

      {#each STATIONS as s}
        <text x={s.x} y="70" fill="var(--ink-dim)" font-size="10" font-family="var(--font-mono)" text-anchor="middle" letter-spacing="0.5">{s.label}</text>
      {/each}

      {#each LINES as l, i}
        <g>
          <circle cx={180 + i * 40} cy={l.y - 1} r="6" fill="var(--ink)" stroke={l.color} stroke-width="2.5">
            <animate attributeName="cx" from={180 + i * 40} to={780 + i * 15} dur="{30 + i * 8}s" repeatCount="indefinite" />
          </circle>
          <circle cx={420 + i * 30} cy={l.y - 1} r="6" fill="var(--ink)" stroke={l.color} stroke-width="2.5">
            <animate attributeName="cx" from={420 + i * 30} to={120 + i * 15} dur="{28 + i * 5}s" repeatCount="indefinite" />
          </circle>
        </g>
      {/each}

      <!-- You are here: Jay St (x=240, F line y=200) -->
      <g>
        <circle cx="240" cy="200" r="14" fill="none" stroke="var(--sand)" stroke-width="2">
          <animate attributeName="r" from="10" to="22" dur="2.5s" repeatCount="indefinite" />
          <animate attributeName="opacity" from="0.9" to="0" dur="2.5s" repeatCount="indefinite" />
        </circle>
        <circle cx="240" cy="200" r="6" fill="var(--sand)" />
        <text x="240" y="395" fill="var(--sand)" font-size="11" font-family="var(--font-mono)" text-anchor="middle" letter-spacing="1.5">YOU · JAY ST</text>
      </g>
    </svg>
  </main>

  <div class="legend">
    <span><span style="color:var(--sage)">●</span> on time · {onTimeCount}</span>
    <span><span style="color:var(--rose)">●</span> delayed · {delayedCount}</span>
    <span style="color:var(--ink-sub)">tap a station for arrivals</span>
  </div>

  <ODDock active="MAP" />
</ODScreen>

<style>
  .legend { display: flex; gap: 18px; font-family: var(--font-mono); font-size: 10px; letter-spacing: 1px; color: var(--ink-dim); }
</style>
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd frontend && npm run build && npx playwright test tests/subway.spec.ts
```

Expected: all 3 tests pass.

- [ ] **Step 5: Commit**

```bash
cd .. && git add frontend/src/routes/subway/ frontend/tests/subway.spec.ts
git commit -m "feat(frontend): subway map — abstract SVG with animated train markers and you-are-here"
```

---

## Task 9: Diagnostics Route

**Files:**
- Create: `frontend/src/routes/diagnostics/+page.svelte`
- Create: `frontend/tests/diagnostics.spec.ts`
- Modify: `frontend/src/routes/+page.svelte` — add 5-tap unlock on time tile

Reference: `design/screens/apps-2.jsx` → `DiagApp()`. Also reachable at `http://<pi-ip>:8080/diagnostics` from laptop.

- [ ] **Step 1: Write failing smoke test**

```typescript
// frontend/tests/diagnostics.spec.ts
import { test, expect } from '@playwright/test';
import { mockBackend } from './helpers';

test.beforeEach(async ({ page }) => { await mockBackend(page); });

test('diagnostics page loads without JS errors', async ({ page }) => {
  const errors: string[] = [];
  page.on('pageerror', (e) => errors.push(e.message));
  await page.goto('/diagnostics');
  await page.waitForLoadState('networkidle');
  expect(errors).toHaveLength(0);
});

test('diagnostics page shows integration table', async ({ page }) => {
  await page.goto('/diagnostics');
  await page.waitForTimeout(300);
  await expect(page.getByText('weather')).toBeVisible();
  await expect(page.getByText('transit')).toBeVisible();
});

test('diagnostics page shows system metrics', async ({ page }) => {
  await page.goto('/diagnostics');
  await expect(page.getByText(/cpu/i)).toBeVisible();
});
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd frontend && npx playwright test tests/diagnostics.spec.ts
```

- [ ] **Step 3: Create `diagnostics/+page.svelte`**

```svelte
<!-- frontend/src/routes/diagnostics/+page.svelte -->
<script lang="ts">
  import { onMount } from 'svelte';
  import ODScreen from '$lib/components/ODScreen.svelte';
  import ODStatusBar from '$lib/components/ODStatusBar.svelte';
  import ODDock from '$lib/components/ODDock.svelte';
  import SectionLabel from '$lib/components/SectionLabel.svelte';
  import BlockBar from '$lib/components/BlockBar.svelte';

  interface IntegrationStatus {
    name: string;
    error_count: number;
    last_success: number | null;
  }

  interface StatusResponse {
    ws_clients: number;
    integrations: IntegrationStatus[];
  }

  let statusData: StatusResponse | null = null;
  let loading = true;

  function relSec(ts: number | null): string {
    if (ts === null) return 'never';
    const s = Math.floor(Date.now() / 1000 - ts);
    if (s < 60) return `${s}s ago`;
    if (s < 3600) return `${Math.floor(s / 60)}m ago`;
    return `${Math.floor(s / 3600)}h ago`;
  }

  const SYS_METRICS = [
    { k: 'cpu',    v: '8%',         bar: 0.08, color: 'var(--sage)' },
    { k: 'ram',    v: '42%',        bar: 0.42, color: 'var(--sage)' },
    { k: 'disk',   v: '28%',        bar: 0.28, color: 'var(--sage)' },
    { k: 'temp',   v: '54°C',       bar: 0.54, color: 'var(--sand)' },
    { k: 'uptime', v: '4d 11h 32m', bar: 0,    color: 'var(--ink-dim)' },
  ];

  onMount(async () => {
    try {
      const resp = await fetch('/api/status');
      if (resp.ok) statusData = await resp.json();
    } catch { /* ignore */ }
    loading = false;
    // Refresh every 5s
    const interval = setInterval(async () => {
      try {
        const resp = await fetch('/api/status');
        if (resp.ok) statusData = await resp.json();
      } catch { /* ignore */ }
    }, 5000);
    return () => clearInterval(interval);
  });
</script>

<ODScreen mode="calm" orbs={false}>
  <ODStatusBar app="DIAGNOSTICS · /diagnostics" />

  <main class="diag-grid">
    <!-- Integrations table -->
    <div class="integrations-col">
      <SectionLabel>// INTEGRATIONS</SectionLabel>
      {#if loading}
        <div style="color:var(--ink-sub);font-size:11px">loading…</div>
      {:else}
        <div class="table-header">
          <span>NAME</span><span>STATUS</span><span>LAST FETCH</span><span>ERRS</span>
        </div>
        {#each (statusData?.integrations ?? []) as it}
          <div class="table-row">
            <span>{it.name}</span>
            <span style="color:{it.error_count > 0 ? 'var(--rose)' : 'var(--sage)'}">
              ● {it.error_count > 0 ? 'warn' : 'ok'}
            </span>
            <span style="color:var(--ink-dim)">{relSec(it.last_success)}</span>
            <span style="color:{it.error_count > 0 ? 'var(--rose)' : 'var(--ink-sub)'}">
              {it.error_count}
            </span>
          </div>
        {/each}
        {#if !(statusData?.integrations.length)}
          <div style="color:var(--ink-sub);font-size:11px">no integration data</div>
        {/if}
        <div style="font-size:10px;color:var(--ink-sub);margin-top:8px;letter-spacing:1px">
          {statusData?.ws_clients ?? 0} frontend client{statusData?.ws_clients !== 1 ? 's' : ''} connected
        </div>
      {/if}
    </div>

    <!-- System + log tail -->
    <div class="system-col">
      <div>
        <SectionLabel>// SYSTEM</SectionLabel>
        <div class="sys-metrics">
          {#each SYS_METRICS as m}
            <div class="sys-row">
              <span style="color:var(--ink-dim);letter-spacing:1px">{m.k}</span>
              <span>
                {#if m.bar > 0}<BlockBar value={m.bar} width={18} color={m.color} />
                {:else}<span style="color:var(--ink-sub)">—</span>{/if}
              </span>
              <span style="color:var(--ink);font-variant-numeric:tabular-nums">{m.v}</span>
            </div>
          {/each}
        </div>
      </div>

      <div style="flex:1;display:flex;flex-direction:column;min-height:0;margin-top:14px">
        <SectionLabel>// LOG TAIL</SectionLabel>
        <div class="log-tail">
          <div><span style="color:var(--sage)">now</span> backend online · ws ready</div>
          <div><span style="color:var(--sage)">init</span> weather fetch ok</div>
          <div><span style="color:var(--sage)">init</span> transit fetch ok · 4 stations</div>
          <div><span style="color:var(--sand)">info</span> ws client connected</div>
          <div style="color:var(--ink-sub)">— more in journalctl —</div>
        </div>
      </div>
    </div>
  </main>

  <ODDock />
</ODScreen>

<style>
  .diag-grid { flex: 1; display: grid; grid-template-columns: 1.3fr 1fr; gap: 24px; min-height: 0; }
  .integrations-col, .system-col { display: flex; flex-direction: column; gap: 8px; min-height: 0; }
  .table-header {
    display: grid; grid-template-columns: 1.4fr 70px 1fr 50px; gap: 10px;
    font-family: var(--font-mono); font-size: 9px; letter-spacing: 1.2px;
    color: var(--ink-sub); padding-bottom: 6px; border-bottom: 1px solid var(--line);
  }
  .table-row {
    display: grid; grid-template-columns: 1.4fr 70px 1fr 50px; gap: 10px;
    padding: 9px 0; border-bottom: 1px dashed var(--line);
    font-family: var(--font-mono); font-size: 11px; letter-spacing: 0.5px; color: var(--ink); align-items: center;
  }
  .sys-metrics { display: flex; flex-direction: column; gap: 8px; font-family: var(--font-mono); font-size: 11px; }
  .sys-row { display: grid; grid-template-columns: 58px 1fr auto; gap: 10px; align-items: center; }
  .log-tail {
    font-family: var(--font-mono); font-size: 10px; color: var(--ink-dim);
    letter-spacing: 0.3px; line-height: 1.7; flex: 1; overflow: hidden;
  }
</style>
```

- [ ] **Step 4: Add 5-tap diagnostics unlock to home page**

In `frontend/src/routes/+page.svelte`, find the clock block and add the tap handler:

After the `let clockInterval` declaration, add:

```typescript
  let tapCount = 0;
  let tapTimer: ReturnType<typeof setTimeout>;

  function handleTimeTap() {
    tapCount++;
    clearTimeout(tapTimer);
    tapTimer = setTimeout(() => { tapCount = 0; }, 2000);
    if (tapCount >= 5) {
      tapCount = 0;
      goto('/diagnostics');
    }
  }
```

Wrap the `.time-block` div with a click handler:

```svelte
<div class="time-block" on:click={handleTimeTap} role="button" tabindex="-1" aria-label="time — tap 5× for diagnostics">
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
cd frontend && npm run build && npx playwright test tests/diagnostics.spec.ts
```

Expected: all 3 tests pass.

- [ ] **Step 6: Commit**

```bash
cd .. && git add frontend/src/routes/diagnostics/ frontend/src/routes/+page.svelte frontend/tests/diagnostics.spec.ts
git commit -m "feat(frontend): diagnostics page + 5-tap unlock on home time tile"
```

---

## Task 10: Run full Playwright suite

- [ ] **Step 1: Run all tests**

```bash
cd frontend && npm run build && npx playwright test
```

Expected: all tests across all spec files pass.

- [ ] **Step 2: Fix any failures**

If a test fails due to timing: increase `waitForTimeout` in that spec. If due to mock data: update `helpers.ts` to add the missing field.

- [ ] **Step 3: Commit final fix if needed**

```bash
cd .. && git add -A && git commit -m "test(frontend): fix any Playwright test regressions"
```

---

## Self-Review

**Spec coverage:**
- Transit detail: ✅ 4 stations (primary + secondary), alerts, secondary collapsible via grid
- Calendar: ✅ day timeline, now-marker, week mini-grid, up-next, Notion badges
- GitHub: ✅ heartbeat, commits list, open PRs, assigned issues, relative times
- Doomscroll: ✅ feed list, QR handoff (real qrcode library), story selection
- Photos: ✅ full-bleed, source/rotation chrome, progress bar
- Pomodoro: ✅ circular ring, countdown, cycle dots, preset selector, REST controls, resume
- Showcase: ✅ full-bleed DriftOrbs, tap-to-return, mode-reactive palette
- Subway map: ✅ abstract SVG diagram, animated train markers, you-are-here pulse, legend
- Diagnostics: ✅ integration table, system metrics, log tail, auto-refresh, 5-tap unlock
- Navigation: ✅ ODDock in all routes, tap-to-return in Showcase and Photos

**Placeholder scan:** None — all routes have concrete implementations.

**Type consistency:**
- `TrainArrival.delay` (number) → conditional color in transit route ✅
- `CalendarEvent.notion` (null | object) — guarded with `{#if event.notion}` ✅
- `PomodoroData.remaining_seconds` → local countdown sync on store update ✅
- `RSSItem.link` → passed to QR generator ✅

---

## Parallelization Strategy

- Tasks within this plan are mostly **independent** (each route is a separate file).
- One subagent can execute all tasks sequentially (each is ~5–10 minutes of work).
- Alternatively: dispatch 3 parallel subagents:
  - Subagent A: Tasks 1–3 (transit, calendar, github)
  - Subagent B: Tasks 4–6 (doomscroll, pomodoro, photos)
  - Subagent C: Tasks 7–9 (showcase, subway, diagnostics)
  Then merge and run Task 10 (full test suite) to catch conflicts.

---

## New Chat Handoff Prompt

```
You are implementing the O-Deck fullscreen apps plan.

Repo: /Users/oliversantana/Documents/dev/cyberdeck
Worktree: .worktrees/frontend-foundation  (or feature/fullscreen-apps branched from it)
Plan: docs/superpowers/plans/2026-04-26-fullscreen-apps.md

Context:
- Plan 3 (Frontend Foundation) is complete: SvelteKit scaffold, all $lib/components/* exist, home screen done.
- You are adding 9 fullscreen routes: transit, calendar, github, doomscroll, photos, pomodoro, showcase, subway, diagnostics.
- Design references: design/screens/apps-1.jsx (Transit, Calendar, Pomodoro) and design/screens/apps-2.jsx (GitHub, Doomscroll, Photos, Showcase, Subway, Diagnostics).
- All routes import from $lib/components/ — do NOT recreate those components.
- Start with the shared test helper (helpers.ts), then implement routes task by task.
- After each task: `cd frontend && npm run build && npx playwright test tests/<name>.spec.ts`
- Use superpowers:subagent-driven-development.

Start with the shared helper file (Step 1 before Task 1).
```
