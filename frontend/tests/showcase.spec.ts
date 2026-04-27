import { expect, test } from '@playwright/test';
import { mockBackend } from './helpers';

test.beforeEach(async ({ page }) => {
  await mockBackend(page);
});

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
  await page.locator('.showcase-screen').click();
  await expect(page).toHaveURL('/');
});

test('showcase shows mode identifier', async ({ page }) => {
  await page.goto('/showcase');
  await expect(page.getByText(/SHOWCASE/)).toBeVisible();
});
