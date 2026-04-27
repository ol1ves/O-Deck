import { expect, test } from '@playwright/test';
import { mockBackend } from './helpers';

test.beforeEach(async ({ page }) => {
  await mockBackend(page);
});

test('subway page loads without JS errors', async ({ page }) => {
  const errors: string[] = [];
  page.on('pageerror', (e) => errors.push(e.message));
  await page.goto('/subway');
  await page.waitForLoadState('networkidle');
  expect(errors).toHaveLength(0);
});

test('subway page shows line labels', async ({ page }) => {
  await page.goto('/subway');
  const diagram = page.locator('main svg');
  await expect(diagram.getByText('A/C', { exact: true })).toBeVisible();
  await expect(diagram.getByText('F', { exact: true })).toBeVisible();
  await expect(diagram.getByText('Q/R', { exact: true })).toBeVisible();
});

test('subway page shows Jay St marker', async ({ page }) => {
  await page.goto('/subway');
  await expect(page.getByText('YOU · JAY ST')).toBeVisible();
});
