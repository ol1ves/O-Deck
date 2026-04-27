import type { Page, Route } from '@playwright/test';

export const MOCK_STATE = {
  weather: {
    tempF: 58,
    feelsLikeF: 56,
    highF: 64,
    lowF: 49,
    cond: 'Partly cloudy',
    code: 2,
    hourly: [
      { h: '0', t: 58 },
      { h: '1', t: 60 },
      { h: '2', t: 62 },
      { h: '3', t: 63 },
      { h: '4', t: 61 },
      { h: '5', t: 58 }
    ],
    alerts: []
  },
  transit: {
    stations: [
      {
        name: 'Jay St–MetroTech',
        stop_id: 'A41N',
        lines: ['A', 'C', 'F', 'R'],
        primary: true,
        trains: [
          { line: 'A', mins: 2, dest: 'Inwood', status: 'on time', delay: 0 },
          { line: 'C', mins: 6, dest: '168 St', status: '+2m delay', delay: 2 },
          { line: 'F', mins: 9, dest: 'Forest Hills', status: 'slow · signals', delay: 4 },
          { line: 'R', mins: 14, dest: 'Forest Hills', status: 'on time', delay: 0 }
        ]
      },
      {
        name: 'DeKalb Av',
        stop_id: 'R30N',
        lines: ['Q'],
        primary: true,
        trains: [{ line: 'Q', mins: 4, dest: '96 St', status: 'on time', delay: 0 }]
      }
    ],
    secondary: [
      {
        name: '14 St–Union Sq',
        stop_id: '635S',
        lines: ['4', '5', '6'],
        primary: false,
        trains: [
          { line: '4', mins: 3, dest: 'Bowling Green', status: 'on time', delay: 0 },
          { line: '5', mins: 7, dest: 'Brooklyn', status: 'on time', delay: 0 }
        ]
      },
      {
        name: 'W 4 St–Wash Sq',
        stop_id: 'A32S',
        lines: ['F', 'A', 'C'],
        primary: false,
        trains: [{ line: 'F', mins: 4, dest: 'Coney Is', status: 'slow · signals', delay: 5 }]
      }
    ],
    alerts: ['F: signal delays at Bergen St']
  },
  spotify: {
    is_playing: true,
    track: 'Pyramid Song',
    artist: 'Radiohead',
    album: 'Amnesiac',
    progress: 0.34,
    elapsed: '1:54',
    total: '4:50',
    art_url: null
  },
  calendar: {
    events: [
      { id: '1', title: 'Lunch w/ Maya', time: '12:30', duration: '30m', location: 'Devoción', color: '#9bb38b', notion: null },
      {
        id: '2',
        title: 'O-Deck install on Pi',
        time: '14:00',
        duration: '1h',
        location: 'Desk',
        color: '#c9a26f',
        notion: { page_id: 'abc', status: 'In Progress', project: 'cyberdeck' }
      }
    ],
    next_in: '43 min'
  },
  github: {
    commits: [
      {
        sha: 'a3f2c1',
        msg: 'transit: handle GTFS feed reconnect',
        repo: 'oliversantana/cyberdeck',
        time: '2026-04-26T10:00:00Z'
      },
      {
        sha: 'b81e4d',
        msg: 'pomodoro: persist preset across reload',
        repo: 'oliversantana/cyberdeck',
        time: '2026-04-26T09:00:00Z'
      }
    ],
    prs: [
      {
        number: 42,
        title: 'feat: notion ↔ google calendar join',
        repo: 'oliversantana/cyberdeck',
        status: 'open',
        age: '2026-04-24T10:00:00Z'
      }
    ],
    issues: [
      {
        number: 12,
        title: 'F train delay banner overflows on 800×480',
        repo: 'oliversantana/cyberdeck',
        label: 'bug',
        age: '2026-04-25T10:00:00Z'
      }
    ]
  },
  rss: {
    items: [
      {
        id: '1',
        src: 'TLDR',
        title: 'Apple unveils on-device LLM runtime',
        link: 'https://example.com/1',
        summary: 'New CoreML primitives.',
        age: '12m'
      },
      {
        id: '2',
        src: 'HN',
        title: 'Show HN: A 50-line distributed lock manager',
        link: 'https://example.com/2',
        summary: 'Built on Postgres.',
        age: '38m'
      }
    ],
    headlines: [{ src: 'TLDR', title: 'Apple unveils on-device LLM runtime', age: '12m' }],
    ticker: ['TLDR · Apple LLM runtime', 'HN · 50-line lock manager']
  },
  photos: { source: 'local', url: '/api/photos/file/img1.jpg', index: 0, total: 5, rotation_seconds: 30 },
  pomodoro: {
    running: false,
    phase: 'idle',
    remaining_seconds: 0,
    cycle: 0,
    cycles_total: 4,
    work_min: 25,
    break_min: 5,
    preset_name: ''
  }
};

export async function installPlaywrightMocks(page: Page) {
  await page.addInitScript(() => {
    class MockWebSocket extends EventTarget {
      static CONNECTING = 0;
      static OPEN = 1;
      static CLOSED = 3;
      readyState = MockWebSocket.CONNECTING;
      constructor(_url: string) {
        super();
        queueMicrotask(() => {
          this.readyState = MockWebSocket.OPEN;
          this.dispatchEvent(new Event('open'));
        });
      }
      send() {}
      close() {
        this.readyState = MockWebSocket.CLOSED;
        this.dispatchEvent(new Event('close'));
      }
    }
    window.WebSocket = MockWebSocket as unknown as typeof WebSocket;
  });
}

const idlePomodoro = {
  running: false,
  phase: 'idle',
  remaining_seconds: 0,
  cycle: 0,
  cycles_total: 4,
  work_min: 25,
  break_min: 5,
  preset_name: ''
};

export async function mockBackend(page: Page) {
  await installPlaywrightMocks(page);
  await page.route('**/api/state', (r: Route) => r.fulfill({ status: 200, json: MOCK_STATE }));
  await page.route('**/api/config', (r: Route) =>
    r.fulfill({
      status: 200,
      json: {
        device: { name: 'O-Deck', resolution: { width: 1024, height: 600 }, timezone: 'America/New_York' },
        home: { hero_tiles: ['now_playing'], core_tiles: ['time', 'weather', 'transit', 'calendar', 'rss'] },
        pomodoro: { presets: [{ name: 'Classic', work_min: 25, break_min: 5, cycles: 4, long_break_min: 15 }] }
      }
    })
  );
  await page.route('**/api/status', (r: Route) =>
    r.fulfill({
      status: 200,
      json: {
        ws_clients: 1,
        integrations: [
          { name: 'weather', error_count: 0, last_success: Date.now() / 1000 },
          { name: 'transit', error_count: 0, last_success: Date.now() / 1000 }
        ]
      }
    })
  );
  await page.route('**/api/pomodoro/start', (r: Route) =>
    r.fulfill({
      status: 200,
      json: {
        running: true,
        phase: 'work',
        remaining_seconds: 1500,
        cycle: 1,
        cycles_total: 4,
        work_min: 25,
        break_min: 5,
        preset_name: 'Classic'
      }
    })
  );
  await page.route('**/api/pomodoro/**', (r: Route) => r.fulfill({ status: 200, json: idlePomodoro }));
}
