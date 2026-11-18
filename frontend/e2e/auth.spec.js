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
