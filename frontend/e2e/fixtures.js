import { expect } from '@playwright/test';

// E2E infrastructure: run migrated real backend(s) and PostgreSQL with Vite's
// /api proxy, plus Chromium. Never point fixtures at valuable data. Each journey
// registers a real user and leaves it in the disposable database.
// E2E_EMPTY_BASE_URL must point to a separate running app and database with no
// strategic_metrics or strategic_budgets in its current reporting window. Do
// not truncate or mutate the populated database used by the other journeys.
// The populated database must contain an operations incident and history row,
// innovation outcome and portfolio rows, and an XSS fixture incident among the
// newest 20: incident_number E2E-XSS, severity P1, status Open, resolved_at NULL,
// title exactly '<img src=x onerror="window.__e2eStoredXss=1">'. Insert it via
// an authorized test-data load into the real database, not a browser mock.
// Give the XSS incident a recent created_at and remove it after the test run.
// Parallel suites must not modify these fixtures while tests are running.

/** Register and sign in through the real user interface.
 *
 * Args:
 *   page: Browser page with access to the running application.
 *   prefix: Distinguishes this journey's generated account.
 *   origin: Optional separate application origin for isolated data.
 */
export async function registerAndLogin(page, prefix, origin = '') {
  const username = `${prefix}${Date.now()}${Math.floor(Math.random() * 10000)}`;
  await page.goto(`${origin}/register`);
  await page.getByLabel('Username').fill(username);
  await page.getByLabel('Email').fill(`${username}@example.com`);
  await page.getByLabel('Password').fill('password123');
  await page.getByRole('button', { name: 'Create account' }).click();
  await expect(page.getByRole('status')).toContainText('Account created');
  await page.getByRole('link', { name: 'Sign in' }).click();
  await page.getByLabel('Username').fill(username);
  await page.getByLabel('Password').fill('password123');
  await page.getByRole('button', { name: 'Sign in' }).click();
  await expect(page.getByRole('heading', { name: `Welcome, ${username}` })).toBeVisible();
}

/** Capture browser exceptions and console errors before navigation. */
export function captureErrors(page) {
  const errors = [];
  page.on('pageerror', (error) => errors.push(error.message));
  page.on('console', (message) => { if (message.type() === 'error') errors.push(message.text()); });
  return errors;
}
