import { test, expect } from '@playwright/test';
import { captureErrors, registerAndLogin } from './fixtures.js';

test('authenticated strategic dashboard renders real API content and exports', async ({ page }, testInfo) => {
  const errors = [];
  page.on('pageerror', (error) => errors.push(error.message));
  page.on('console', (message) => { if (message.type() === 'error') errors.push(message.text()); });
  const username = `strategic${Date.now()}${Math.floor(Math.random() * 10000)}`;
  await page.goto('/register');
  await page.getByLabel('Username').fill(username);
  await page.getByLabel('Email').fill(`${username}@example.com`);
  await page.getByLabel('Password').fill('password123');
  await page.getByRole('button', { name: 'Create account' }).click();
  await expect(page.getByRole('status')).toContainText('Account created');
  await page.getByRole('link', { name: 'Sign in' }).click();
  await page.getByLabel('Username').fill(username);
  await page.getByLabel('Password').fill('password123');
  const responsePromise = page.waitForResponse((response) => response.url().endsWith('/dashboard/strategic-metrics') && response.status() === 200);
  await page.getByRole('button', { name: 'Sign in' }).click();
  const response = await responsePromise;
  const data = await response.json();
  await expect(page.getByRole('heading', { name: 'Strategic Command' })).toBeVisible();
  if (data.metrics.length) {
    await expect(page.getByRole('heading', { name: data.metrics[0].metric_name }).first()).toBeVisible();
    await expect(page.getByRole('img', { name: `${data.metrics[0].metric_name} performance chart` })).toBeVisible();
  } else if (!data.budgets.length) {
    await expect(page.getByText('No strategic data available for this period.')).toBeVisible();
  }
  await page.screenshot({ path: testInfo.outputPath('strategic-desktop.png'), fullPage: true });
  const download = page.waitForEvent('download');
  await page.getByRole('button', { name: 'Export CSV' }).click();
  expect((await download).suggestedFilename()).toBe('strategic-metrics.csv');
  await page.reload();
  await expect(page.getByRole('heading', { name: 'Strategic Command' })).toBeVisible();
  expect(errors).toEqual([]);
});

test('a separate empty database renders the strategic empty state', async ({ page }, testInfo) => {
  const emptyOrigin = process.env.E2E_EMPTY_BASE_URL;
  expect(emptyOrigin, 'Set E2E_EMPTY_BASE_URL to the isolated empty application described in e2e/fixtures.js').toBeTruthy();
  expect(new URL(emptyOrigin).origin, 'Empty and populated apps must use distinct origins and databases').not.toBe(new URL(testInfo.project.use.baseURL).origin);
  const errors = captureErrors(page);
  await registerAndLogin(page, 'empty', emptyOrigin);
  const responsePromise = page.waitForResponse((response) => response.url().endsWith('/dashboard/strategic-metrics') && response.request().method() === 'GET');
  await page.reload();
  const response = await responsePromise;
  expect(response.status()).toBe(200);
  const data = await response.json();
  expect(data.metrics).toEqual([]);
  expect(data.budgets).toEqual([]);
  await expect(page.getByText('No strategic data available for this period.')).toBeVisible();
  await page.screenshot({ path: testInfo.outputPath('strategic-empty.png'), fullPage: true });
  expect(errors).toEqual([]);
});

test('strategic loading remains visible until the real request is released', async ({ page }) => {
  const errors = captureErrors(page);
  await registerAndLogin(page, 'loading');
  await page.getByRole('link', { name: 'Operations' }).click();
  await expect(page.getByRole('heading', { name: 'Operations', exact: true })).toBeVisible();
  let release;
  let requestArrived;
  const gate = new Promise((resolve) => { release = resolve; });
  const intercepted = new Promise((resolve) => { requestArrived = resolve; });
  // Hold the actual request, then continue it unchanged to the real backend.
  await page.route('**/api/v1/dashboard/strategic-metrics', async (route) => {
    requestArrived();
    await gate;
    await route.continue();
  });
  const responsePromise = page.waitForResponse((response) => response.url().endsWith('/dashboard/strategic-metrics') && response.request().method() === 'GET');
  try {
    await page.getByRole('link', { name: 'Strategic Command' }).click();
    await intercepted;
    await expect(page.getByRole('status')).toHaveText('Loading strategic data…');
    await expect(page.getByRole('button', { name: 'Export CSV' })).toBeDisabled();
  } finally {
    release();
  }
  const response = await responsePromise;
  expect(response.status()).toBe(200);
  const data = await response.json();
  await expect(page.getByRole('status')).toHaveCount(0);
  await expect(page.getByText(`Reporting window: ${data.window_start} to ${data.window_end}`)).toBeVisible();
  await expect(page.getByRole('button', { name: 'Export CSV' })).toBeEnabled();
  expect(errors).toEqual([]);
});
