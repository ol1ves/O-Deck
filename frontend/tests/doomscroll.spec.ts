import { expect, test } from '@playwright/test';
import { mockBackend } from './helpers';

test.beforeEach(async ({ page }) => {
  await mockBackend(page);
});

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
  await expect(page.getByText('Apple unveils on-device LLM runtime').first()).toBeVisible();
});

test('doomscroll page shows QR section', async ({ page }) => {
  await page.goto('/doomscroll');
  await expect(page.getByText(/READ ON PHONE/i)).toBeVisible();
});

test('doomscroll clicking story updates QR panel', async ({ page }) => {
  await page.goto('/doomscroll');
  await page.waitForTimeout(300);
  const items = page.locator('.feed-item');
  await items.nth(1).click();
  await expect(page.locator('.qr-title')).toContainText('50-line distributed lock manager');
});
