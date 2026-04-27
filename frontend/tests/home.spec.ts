import { expect, test } from '@playwright/test';

test.beforeEach(async ({ page }) => {
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

      send(_data: string) {}

      close() {
        this.readyState = MockWebSocket.CLOSED;
        this.dispatchEvent(new Event('close'));
      }
    }

    window.WebSocket = MockWebSocket as unknown as typeof WebSocket;
  });

  await page.route('**/api/state', (route) =>
    route.fulfill({
      status: 200,
      json: {
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
            { h: '2', t: 57 }
          ],
          alerts: []
        },
        transit: {
          stations: [
            {
              name: 'Jay St',
              stop_id: 'A41N',
              lines: ['A'],
              primary: true,
              trains: [{ line: 'A', mins: 3, dest: 'Inwood', status: 'on time', delay: 0 }]
            }
          ],
          secondary: [],
          alerts: []
        },
        spotify: {
          is_playing: false,
          track: null,
          artist: null,
          album: null,
          progress: 0,
          elapsed: '0:00',
          total: '0:00',
          art_url: null
        },
        calendar: { events: [], next_in: null },
        github: { commits: [], prs: [], issues: [] },
        rss: { items: [], headlines: [], ticker: ['HN - Test headline'] },
        photos: { source: 'local', url: null, index: 0, total: 0, rotation_seconds: 30 },
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
      }
    })
  );

  await page.route('**/api/config', (route) =>
    route.fulfill({
      status: 200,
      json: { device: { name: 'O-Deck', resolution: { width: 1024, height: 600 } }, home: {} }
    })
  );
});

test('home page loads without JS errors', async ({ page }) => {
  const errors: string[] = [];
  page.on('pageerror', (error) => errors.push(error.message));

  await page.goto('/');
  await page.waitForLoadState('networkidle');

  expect(errors).toHaveLength(0);
});

test('home page shows clock', async ({ page }) => {
  await page.goto('/');

  await expect(page.locator('.clock-hhmm')).toBeVisible();
});

test('home page shows O-DECK brand', async ({ page }) => {
  await page.goto('/');

  await expect(page.locator('.brand')).toContainText('O-DECK');
});

test('home page shows weather temperature', async ({ page }) => {
  await page.goto('/');

  await expect(page.locator('.temp-num')).toContainText('58');
});

test('home page shows transit train', async ({ page }) => {
  await page.goto('/');

  await expect(page.locator('.pill').first()).toContainText('A');
});

test('home page launcher dock is present', async ({ page }) => {
  await page.goto('/');

  await expect(page.locator('.dock-btn').first()).toBeVisible();
});
