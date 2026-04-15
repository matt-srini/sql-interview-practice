// @ts-check
import { defineConfig, devices } from '@playwright/test';

/**
 * Playwright e2e test config.
 *
 * Tests run against the live dev servers (backend :8000, frontend :5173).
 * Make sure both are running before executing: `npx playwright test`
 *
 * The plan-upgrade endpoint (POST /api/user/plan) is used in beforeEach hooks
 * to provision test users — it only works when IS_PROD is false (dev mode).
 */
export default defineConfig({
  testDir: './e2e',
  globalSetup: './e2e/global-setup.js',
  fullyParallel: false, // tests share a DB — run sequentially to avoid interference
  retries: 0,
  reporter: 'list',
  timeout: 15_000,

  use: {
    baseURL: 'http://localhost:5173',
    // Each test file gets its own browser context (fresh cookies/session)
    browserName: 'chromium',
    headless: true,
    trace: 'retain-on-failure',
  },

  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'] } },
  ],
});
