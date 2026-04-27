import { expect, test } from '@playwright/test';
import { mockBackend } from './helpers';

test.beforeEach(async ({ page }) => {
  await mockBackend(page);
});

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
  const rows = page.locator('.integrations-col .table-row');
  await expect(rows.nth(0)).toContainText('weather');
  await expect(rows.nth(1)).toContainText('transit');
});

test('diagnostics page shows system metrics', async ({ page }) => {
  await page.goto('/diagnostics');
  await expect(page.getByText(/cpu/i)).toBeVisible();
});
