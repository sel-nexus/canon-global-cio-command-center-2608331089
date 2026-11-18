import { test, expect } from '@playwright/test';

test('register, authenticate, restore and revoke a session', async ({ page }) => {
  const errors = [];
  page.on('pageerror', (error) => errors.push(error.message));
  page.on('console', (message) => { if (message.type() === 'error') errors.push(message.text()); });
  const username = `user${Date.now()}${Math.floor(Math.random() * 10000)}`;
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
  await expect(page.getByRole('heading', { name: `Welcome, ${username}` })).toBeVisible();
  const token = await page.evaluate(() => sessionStorage.getItem('cio_access_token'));
  await page.reload();
  await expect(page.getByText(`${username}@example.com · executive`)).toBeVisible();
  await page.getByRole('button', { name: 'Sign out' }).click();
  await expect(page.getByRole('heading', { name: 'Sign in' })).toBeVisible();
  const revoked = await page.request.get('/api/v1/auth/me', { headers: { Authorization: `Bearer ${token}` } });
  expect(revoked.status()).toBe(401);
  expect(errors).toEqual([]);
});

test('an unauthenticated visitor cannot enter a protected dashboard', async ({ page }) => {
  const errors = [];
  page.on('pageerror', (error) => errors.push(error.message));
  page.on('console', (message) => { if (message.type() === 'error') errors.push(message.text()); });
  await page.goto('/dashboard/operations');
  await expect(page).toHaveURL(/\/login$/);
  await expect(page.getByRole('heading', { name: 'Sign in' })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Operations' })).toHaveCount(0);
  const response = await page.request.get('/api/v1/operations/summary');
  expect(response.status()).toBe(401);
  expect(errors).toEqual([]);
});

test('invalid credentials are rejected without creating a session', async ({ page }, testInfo) => {
  const pageErrors = [];
  const consoleErrors = [];
  page.on('pageerror', (error) => pageErrors.push(error.message));
  page.on('console', (message) => {
    if (message.type() === 'error') consoleErrors.push({ text: message.text(), url: message.location().url });
  });
  await page.goto('/login');
  await page.getByLabel('Username').fill(`missing${Date.now()}${Math.floor(Math.random() * 10000)}`);
  await page.getByLabel('Password').fill('incorrect-password');
  const responsePromise = page.waitForResponse((response) => response.url().endsWith('/auth/login') && response.request().method() === 'POST');
  await page.getByRole('button', { name: 'Sign in' }).click();
  const response = await responsePromise;
  expect(response.status()).toBe(401);
  await expect(page.getByRole('alert')).toHaveText('Invalid username or password.');
  await expect(page).toHaveURL(/\/login$/);
  expect(await page.evaluate(() => sessionStorage.getItem('cio_access_token'))).toBeNull();
  await page.screenshot({ path: testInfo.outputPath('login-error.png'), fullPage: true });
  // Chromium reports the failed login resource as a console error; no other errors are allowed.
  const isExpectedLoginError = (error) => error.url === response.url()
    && /^Failed to load resource: the server responded with a status of 401(?: \(Unauthorized\))?$/.test(error.text);
  expect(consoleErrors.filter(isExpectedLoginError)).toHaveLength(1);
  expect(consoleErrors.filter((error) => !isExpectedLoginError(error))).toEqual([]);
  expect(pageErrors).toEqual([]);
});
