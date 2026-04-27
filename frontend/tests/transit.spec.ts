import { expect, test } from '@playwright/test';
import { mockBackend } from './helpers';

test.beforeEach(async ({ page }) => {
  await mockBackend(page);
});

test('transit page loads without JS errors', async ({ page }) => {
  const errors: string[] = [];
  page.on('pageerror', (e) => errors.push(e.message));
  await page.goto('/transit');
  await page.waitForLoadState('networkidle');
  expect(errors).toHaveLength(0);
});

test('transit page shows all 4 station names', async ({ page }) => {
  await page.goto('/transit');
  await page.waitForTimeout(300);
  await expect(page.getByText('Jay St–MetroTech')).toBeVisible();
  await expect(page.getByText('DeKalb Av')).toBeVisible();
  await expect(page.getByText('14 St–Union Sq')).toBeVisible();
  await expect(page.getByText('W 4 St–Wash Sq')).toBeVisible();
});

test('transit page shows alert banner', async ({ page }) => {
  await page.goto('/transit');
  await page.waitForTimeout(300);
  await expect(page.getByText(/signal delays/i)).toBeVisible();
});

test('transit page dock HOME tap navigates home', async ({ page }) => {
  await page.goto('/transit');
  await page.locator('.dock-btn').first().click();
  await expect(page).toHaveURL('/');
});
