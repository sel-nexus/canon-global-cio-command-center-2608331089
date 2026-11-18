import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './e2e',
  // Save screenshots in Playwright's per-test output directory for human review.
  use: { baseURL: process.env.E2E_BASE_URL || 'http://127.0.0.1:5173', browserName: 'chromium', screenshot: 'on' },
  webServer: { command: 'node node_modules/vite/bin/vite.js --host 127.0.0.1', url: 'http://127.0.0.1:5173', reuseExistingServer: true, timeout: 30000 },
});
