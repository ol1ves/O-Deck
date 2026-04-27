import { expect, test } from '@playwright/test';
import { mockBackend } from './helpers';

test.beforeEach(async ({ page }) => {
  await mockBackend(page);
});

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
