import { test, expect } from '@playwright/test';
import { captureErrors, registerAndLogin } from './fixtures.js';

test('innovation journey displays persisted outcomes and portfolio after reload', async ({ page }) => {
  const errors = captureErrors(page);
  await registerAndLogin(page, 'innovation');
  const responsePromise = page.waitForResponse((response) => response.url().endsWith('/governance/innovation') && response.request().method() === 'GET');
  await page.getByRole('link', { name: 'Innovation' }).click();
  const response = await responsePromise;
  expect(response.status()).toBe(200);
  const data = await response.json();
  expect(data.latest, 'A persisted innovation outcome is required').not.toBeNull();
  expect(data.portfolio.length, 'A persisted portfolio row is required').toBeGreaterThan(0);
  await expect(page.getByRole('heading', { name: 'Innovation', exact: true })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'AI models deployed to production' }).locator('..')).toContainText(String(data.latest.deployed_models ?? 'Not provided'));
  await expect(page.getByRole('heading', { name: 'Patent disclosures filed' }).locator('..')).toContainText(String(data.latest.patent_disclosures ?? 'Not provided'));
  await expect(page.getByRole('heading', { name: 'Quarterly innovation index' }).locator('..')).toContainText(String(data.latest.innovation_index ?? 'Not provided'));
  await expect(page.getByText(`Reporting period: Q${data.latest.quarter} ${data.latest.year}`, { exact: false })).toBeVisible();
  const item = data.portfolio[0];
  const row = page.getByRole('row').filter({ hasText: item.category });
  await expect(row).toContainText(String(item.amount));
  await expect(row).toContainText(item.unit);
  const reloaded = page.waitForResponse((res) => res.url().endsWith('/governance/innovation') && res.request().method() === 'GET');
  await page.reload();
  expect((await reloaded).status()).toBe(200);
  await expect(row).toContainText(String(item.amount));
  await expect(row).toContainText(item.unit);
  expect(errors).toEqual([]);
});
