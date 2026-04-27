import { expect, test } from '@playwright/test';
import { mockBackend } from './helpers';

test.beforeEach(async ({ page }) => {
  await mockBackend(page);
});

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
  await expect(page.getByText('Lunch w/ Maya').first()).toBeVisible();
  await expect(page.getByText('O-Deck install on Pi').first()).toBeVisible();
});

test('calendar page shows Notion badge on linked event', async ({ page }) => {
  await page.goto('/calendar');
  await page.waitForTimeout(300);
  await expect(page.getByText(/notion\/cyberdeck/).first()).toBeVisible();
});
