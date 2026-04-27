import { expect, test } from '@playwright/test';
import { mockBackend } from './helpers';

test.beforeEach(async ({ page }) => {
  await mockBackend(page);
});

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
