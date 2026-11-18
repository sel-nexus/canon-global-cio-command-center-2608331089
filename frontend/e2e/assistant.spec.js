import { test, expect } from '@playwright/test';

test('assistant is available across tabs and reports provider status honestly', async ({ page }) => {
  const errors = [];
  page.on('pageerror', (error) => errors.push(error.message));
  page.on('console', (message) => { if (message.type() === 'error' && !message.text().includes('503')) errors.push(message.text()); });
  const username = `assistant${Date.now()}`;
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
  await page.getByRole('link', { name: 'Partnerships' }).click();
  const chat = page.waitForResponse((response) => response.url().includes('/api/v1/ai/chat'));
  await page.getByRole('button', { name: 'Summarize partnerships' }).click();
  const response = await chat;
  expect(response.request().postDataJSON().context_tab).toBe('partnerships');
  if (response.status() === 503) await expect(page.getByRole('alert')).toContainText('not configured');
  else { expect(response.status()).toBe(200); await expect(page.getByText((await response.json()).narrative)).toBeVisible(); }
  await page.keyboard.press('Escape');
  await page.getByRole('link', { name: 'Operations' }).click();
  await page.getByRole('button', { name: 'Executive assistant' }).click();
  await expect(page.getByRole('dialog')).toContainText('Context: operations');
  expect(errors).toEqual([]);
});
