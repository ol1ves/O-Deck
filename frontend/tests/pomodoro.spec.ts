import { expect, test } from '@playwright/test';
import { mockBackend } from './helpers';

test.beforeEach(async ({ page }) => {
  await mockBackend(page);
});

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
  await expect(page.locator('.pomo-main').getByText('IDLE', { exact: true })).toBeVisible();
});

test('pomodoro page shows preset selector', async ({ page }) => {
  await page.goto('/pomodoro');
  await expect(page.getByText('Classic')).toBeVisible();
});

test('pomodoro start button calls API', async ({ page }) => {
  let startCalled = false;
  await page.route('**/api/pomodoro/start', (r) => {
    startCalled = true;
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
    });
  });

  await page.goto('/pomodoro');
  await page.locator('button:has-text("Start")').click();
  await page.waitForTimeout(200);
  expect(startCalled).toBe(true);
});
