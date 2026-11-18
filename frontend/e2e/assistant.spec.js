import { test, expect } from '@playwright/test';

// Run with two real, separately configured deployments and disposable migrated
// PostgreSQL databases. E2E_BASE_URL (default http://127.0.0.1:5173) must
// proxy to a backend with AI_ENABLED=true and an owner-approved HTTPS
// AI_ENDPOINT, AI_MODEL and AI_API_KEY; the provider must return nonempty
// narrative, actions and confidence. Do not use the example placeholders.
// E2E_AI_UNAVAILABLE_BASE_URL must point to a different frontend proxying to
// a real backend started with AI_ENABLED=false and AI_MOCK_ENABLED=false. Both deployments need working
// registration and dashboard APIs. Playwright's configured Vite webServer
// starts only the default frontend; start the other servers separately. Use
// isolated test data approved for sharing with the provider. For example,
// start a second backend on 127.0.0.1:8001 with AI_ENABLED=false and its own
// DATABASE_URL/DB_NAME, then from frontend run
// VITE_DEV_PROXY_TARGET=http://127.0.0.1:8001 npm run dev -- --port 5174 --strictPort.
// Set E2E_AI_UNAVAILABLE_BASE_URL=http://127.0.0.1:5174 when running this spec.
// No browser routes or provider responses are mocked. Missing environments
// fail, not skip; provider approval and credentials must be supplied by owners.

/** Capture all browser errors and failed network requests before navigation. */
function captureErrors(page) {
  const consoleErrors = [];
  const pageErrors = [];
  const failedRequests = [];
  page.on('console', (message) => {
    if (message.type() === 'error') consoleErrors.push({ text: message.text(), url: message.location().url });
  });
  page.on('pageerror', (error) => pageErrors.push(error.message));
  page.on('requestfailed', (request) => failedRequests.push({ url: request.url(), error: request.failure()?.errorText }));
  return { consoleErrors, pageErrors, failedRequests };
}

/** Register a unique user and sign in through the real application. */
async function signIn(page, baseUrl) {
  const username = `assistant${Date.now()}${Math.floor(Math.random() * 10000)}`;
  await page.goto(new URL('/register', baseUrl).toString());
  await page.getByLabel('Username').fill(username);
  await page.getByLabel('Email').fill(`${username}@example.com`);
  await page.getByLabel('Password').fill('password123');
  await page.getByRole('button', { name: 'Create account' }).click();
  await expect(page.getByRole('status')).toContainText('Account created');
  await page.getByRole('link', { name: 'Sign in' }).click();
  await page.getByLabel('Username').fill(username);
  await page.getByLabel('Password').fill('password123');
  await page.getByRole('button', { name: 'Sign in' }).click();
}

/** Observe the real chat POST without accepting a particular status. */
function nextChat(page) {
  return page.waitForResponse((response) => new URL(response.url()).pathname === '/api/v1/ai/chat' && response.request().method() === 'POST');
}

/** Compare every displayed analysis field with the real provider response. */
async function expectAnalysis(page, response, query, contextTab) {
  expect(response.status()).toBe(200);
  expect(response.request().postDataJSON()).toEqual({ query, context_tab: contextTab });
  const data = await response.json();
  expect(data.source).toBe('provider');
  expect(typeof data.narrative).toBe('string');
  expect(data.narrative.trim()).not.toBe('');
  expect(Array.isArray(data.actions)).toBe(true);
  expect(data.actions.length).toBeGreaterThan(0);
  for (const action of data.actions) {
    expect(typeof action).toBe('string');
    expect(action.trim()).not.toBe('');
  }
  expect(typeof data.confidence).toBe('string');
  expect(data.confidence.trim()).not.toBe('');
  const dialog = page.getByRole('dialog');
  await expect(dialog).toContainText(`Context: ${contextTab}`);
  await expect(dialog.getByLabel('Your question')).toHaveValue(query);
  await expect(dialog.getByText('Source: AI provider', { exact: true })).toBeVisible();
  await expect(dialog.getByText(data.narrative, { exact: true })).toBeVisible();
  const actions = dialog.getByRole('heading', { name: 'Suggested actions' }).locator('xpath=following-sibling::*[1]');
  await expect(actions.locator('li')).toHaveText(data.actions);
  await expect(dialog.getByText(`Confidence: ${data.confidence}`, { exact: true })).toBeVisible();
}

test('approved provider answers strategic recommendation and partnership summary across tabs', async ({ page, baseURL }) => {
  test.setTimeout(90000);
  const errors = captureErrors(page);
  const recommendations = page.waitForResponse((response) => {
    const url = new URL(response.url());
    return url.pathname === '/api/v1/ai/recommendations' && url.searchParams.get('context_tab') === 'strategic';
  });
  await signIn(page, baseURL);
  const recommendationResponse = await recommendations;
  expect(recommendationResponse.status()).toBe(200);
  const suggestions = await recommendationResponse.json();
  expect(suggestions).toEqual(expect.arrayContaining([{
    label: 'Executive narrative',
    query: 'Summarize the available strategic observations and suggest priorities.',
    context_tab: 'strategic',
  }]));
  const suggestion = suggestions.find((item) => item.label === 'Executive narrative');
  const strategicChat = nextChat(page);
  await page.getByRole('region', { name: 'Suggested assistant questions' }).getByRole('button', { name: suggestion.label }).click();
  await expectAnalysis(page, await strategicChat, suggestion.query, 'strategic');
  await page.keyboard.press('Escape');
  await expect(page.getByRole('dialog')).toHaveCount(0);

  await page.getByRole('link', { name: 'Partnerships' }).click();
  const partnershipChat = nextChat(page);
  await page.getByRole('button', { name: 'Summarize partnerships' }).click();
  await expectAnalysis(page, await partnershipChat, 'Summarize partnership performance for contract review and negotiation preparation.', 'partnerships');
  await page.keyboard.press('Escape');
  await page.getByRole('link', { name: 'Operations' }).click();
  await page.getByRole('button', { name: 'Executive assistant' }).click();
  await expect(page.getByRole('dialog')).toContainText('Context: operations');
  const query = 'Review operational trends and identify priorities.';
  await page.getByLabel('Your question').fill(query);
  const operationsChat = nextChat(page);
  await page.getByRole('button', { name: 'Ask assistant' }).click();
  await expectAnalysis(page, await operationsChat, query, 'operations');
  expect(errors).toEqual({ consoleErrors: [], pageErrors: [], failedRequests: [] });
});

test('explicit mock deployment displays synthetic assistant output', async ({ page, baseURL }) => {
  const errors = captureErrors(page);
  const mockUrl = process.env.E2E_AI_MOCK_BASE_URL;
  expect(mockUrl, 'Set E2E_AI_MOCK_BASE_URL to a separate frontend backed by AI_MOCK_ENABLED=true').toBeTruthy();
  expect(new URL(mockUrl).origin).not.toBe(new URL(baseURL).origin);
  await signIn(page, mockUrl);
  const chat = nextChat(page);
  await page.getByRole('region', { name: 'Suggested assistant questions' }).getByRole('button', { name: 'Executive narrative' }).click();
  const response = await chat;
  expect(response.status()).toBe(200);
  const data = await response.json();
  expect(data.source).toBe('mock');
  expect(data.narrative).toContain('MOCK / synthetic');
  expect(data.actions[0]).toContain('MOCK / synthetic');
  expect(data.confidence).toContain('MOCK / synthetic');
  const dialog = page.getByRole('dialog');
  await expect(dialog).toContainText('MOCK / synthetic output — not an analysis of dashboard data.');
  await expect(dialog).toContainText(data.narrative);
  await expect(dialog).toContainText(data.actions[0]);
  await expect(dialog).toContainText(data.confidence);
  expect(errors).toEqual({ consoleErrors: [], pageErrors: [], failedRequests: [] });
});

test('unconfigured provider returns a specific 503 and shows the error', async ({ page, baseURL }) => {
  const errors = captureErrors(page);
  const unavailableUrl = process.env.E2E_AI_UNAVAILABLE_BASE_URL;
  expect(unavailableUrl, 'Set E2E_AI_UNAVAILABLE_BASE_URL to the separate frontend backed by AI_ENABLED=false').toBeTruthy();
  expect(new URL(unavailableUrl).origin).not.toBe(new URL(baseURL).origin);
  await signIn(page, unavailableUrl);
  await page.getByRole('link', { name: 'Partnerships' }).click();
  const chat = nextChat(page);
  await page.getByRole('button', { name: 'Summarize partnerships' }).click();
  const response = await chat;
  expect(response.request().postDataJSON()).toEqual({
    query: 'Summarize partnership performance for contract review and negotiation preparation.',
    context_tab: 'partnerships',
  });
  expect(response.status()).toBe(503);
  expect(await response.json()).toEqual({ detail: 'AI provider is not configured or approved.' });
  const dialog = page.getByRole('dialog');
  await expect(dialog).toContainText('Context: partnerships');
  await expect(dialog.getByRole('alert')).toHaveText('AI provider is not configured or approved.');
  await expect(dialog.getByRole('heading', { name: 'Analysis' })).toHaveCount(0);
  // Chromium emits one resource error for this exact 503; no other error is ignored.
  expect(errors.pageErrors).toEqual([]);
  expect(errors.failedRequests).toEqual([]);
  expect(errors.consoleErrors).toHaveLength(1);
  expect(errors.consoleErrors[0].url).toBe(response.url());
  expect(errors.consoleErrors[0].text).toMatch(/^Failed to load resource: the server responded with a status of 503 \(Service Unavailable\)$/);
});
