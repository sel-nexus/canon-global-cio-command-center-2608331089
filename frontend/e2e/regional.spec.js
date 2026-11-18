import { test, expect } from '@playwright/test';

test('signed-in executive views persisted regional data and investigates a warning', async ({ page }) => {
  const errors = [];
  page.on('pageerror', (error) => errors.push(error.message));
  page.on('console', (message) => { if (message.type() === 'error') errors.push(message.text()); });
  const username = `regional${Date.now()}${Math.floor(Math.random() * 10000)}`;
  await page.goto('/register');
  await page.getByLabel('Username').fill(username);
  await page.getByLabel('Email').fill(`${username}@example.com`);
  await page.getByLabel('Password').fill('password123');
  await page.getByRole('button', { name: 'Create account' }).click();
  await expect(page.getByRole('status')).toContainText('Account created');
  await page.getByRole('link', { name: 'Sign in' }).click();
  await page.getByLabel('Username').fill(username);
  await page.getByLabel('Password').fill('password123');
  await page.getByRole('button', { name: 'Sign in' }).click();
  const responsePromise = page.waitForResponse((response) => response.url().endsWith('/metrics/regional-performance') && response.status() === 200);
  await page.getByRole('link', { name: 'Executive Summary' }).click();
  const data = await (await responsePromise).json();
  await expect(page.getByRole('heading', { name: 'Executive Summary' })).toBeVisible();
  if (data.regions.length) {
    await expect(page.getByRole('img', { name: 'Regional health radar comparison' })).toBeVisible();
    await expect(page.getByRole('row', { name: new RegExp(data.regions[0].region) })).toContainText(data.regions[0].status);
    const warning = data.regions.find((row) => row.status === 'Warning');
    expect(warning, 'A source-provided Warning fixture is required for this journey').toBeTruthy();
    await page.getByRole('button', { name: `Investigate ${warning.region}` }).click();
    await expect(page.getByRole('heading', { name: `Investigate ${warning.region}` })).toBeVisible();
    await page.reload();
    await expect(page.getByRole('heading', { name: `Investigate ${warning.region}` })).toBeVisible();
  } else {
    throw new Error('A source-provided Warning fixture is required for this journey');
  }
  expect(errors).toEqual([]);
});
