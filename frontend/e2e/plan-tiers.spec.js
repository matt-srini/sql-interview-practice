/**
 * Plan-tier e2e tests.
 *
 * Runs against live dev servers (:8000 backend, :5173 frontend).
 * Users are provisioned once via globalSetup (e2e/global-setup.js) and
 * loaded from e2e/.test-users.json to avoid exhausting the rate limiter.
 */
import { test, expect } from '@playwright/test';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const USERS_FILE = path.join(path.dirname(fileURLToPath(import.meta.url)), '.test-users.json');
// A stable easy SQL question ID (confirmed from dev catalog)
const EASY_SQL_QUESTION_ID = 1003;

function getUsers() {
  return JSON.parse(fs.readFileSync(USERS_FILE, 'utf8'));
}

async function loginAs(page, email, password) {
  await page.goto('/auth');
  await page.getByLabel('Email address').fill(email);
  // Use the input id — getByLabel('Password') also matches the show/hide toggle button
  await page.locator('#auth-password').fill(password);
  await page.getByRole('button', { name: 'Sign in' }).click();
  await page.waitForURL('/');
}

// ---------------------------------------------------------------------------
// Dashboard: per-difficulty counts must render correctly
// ---------------------------------------------------------------------------

test.describe('Dashboard — per-difficulty counts', () => {
  test('elite user sees X/Y counts, not bare "/" separators', async ({ page }) => {
    const { elite } = getUsers();
    await loginAs(page, elite.email, elite.password);
    await page.goto('/dashboard');
    await page.waitForSelector('.dashboard-track-card');

    // At least one breakdown section must contain an X/Y pattern
    const body = await page.locator('.dashboard-diff-breakdown').first().textContent();
    expect(body).toMatch(/\d+\/\d+/);

    // No element whose entire text is just "/" (the broken rendering)
    const slashOnly = page.locator('.dashboard-diff-count', { hasText: /^\/$/ });
    await expect(slashOnly).toHaveCount(0);
  });

  test('pro user dashboard shows correct SQL total (95)', async ({ page }) => {
    const { pro } = getUsers();
    await loginAs(page, pro.email, pro.password);
    await page.goto('/dashboard');
    await page.waitForSelector('.dashboard-track-card');

    const sqlCard = page.locator('.dashboard-track-card').filter({ hasText: 'SQL' });
    await expect(sqlCard.locator('text=/\\d+ \\/ 95/')).toBeVisible();
  });
});

// ---------------------------------------------------------------------------
// Practice sidebar: lock state per plan
// ---------------------------------------------------------------------------

test.describe('Practice sidebar — lock state', () => {
  test('elite user sees no locked questions in SQL sidebar', async ({ page }) => {
    const { elite } = getUsers();
    await loginAs(page, elite.email, elite.password);
    await page.goto(`/practice/sql/questions/${EASY_SQL_QUESTION_ID}`);

    // Open the sidebar (first button is the ☰ Questions toggle)
    await page.locator('button').first().click();
    await page.waitForSelector('.sidebar-question');

    const locked = page.locator('.sidebar-question-locked');
    await expect(locked).toHaveCount(0);
  });

  test('free user sees locked questions in SQL sidebar', async ({ page }) => {
    const { free } = getUsers();
    await loginAs(page, free.email, free.password);
    await page.goto(`/practice/sql/questions/${EASY_SQL_QUESTION_ID}`);

    // Open the sidebar
    await page.locator('button').first().click();
    await page.waitForSelector('.sidebar-question');

    // Medium group is collapsed by default — expand it to reveal locked questions
    await page.getByRole('button', { name: /medium/i }).click();
    await page.waitForSelector('.sidebar-question-locked');

    // Free user with no solves: medium questions are locked
    const locked = page.locator('.sidebar-question-locked');
    await expect(locked).not.toHaveCount(0);
  });
});

// ---------------------------------------------------------------------------
// TrackHub: plan banner
// ---------------------------------------------------------------------------

test.describe('TrackHub — plan banner', () => {
  test('elite user sees full-access banner', async ({ page }) => {
    const { elite } = getUsers();
    await loginAs(page, elite.email, elite.password);
    await page.goto('/practice/sql');
    await expect(page.getByText(/Elite plan/i)).toBeVisible();
    await expect(page.getByText(/full practice access/i)).toBeVisible();
  });
});

// ---------------------------------------------------------------------------
// Mock hub: difficulty gating per plan
// ---------------------------------------------------------------------------

test.describe('Mock hub — difficulty buttons', () => {
  test('elite user: Hard difficulty pill is NOT aria-disabled', async ({ page }) => {
    const { elite } = getUsers();
    await loginAs(page, elite.email, elite.password);
    await page.goto('/mock');
    await page.waitForSelector('.mock-config-pill');

    const hardBtn = page.locator('.mock-config-pill', { hasText: 'Hard' });
    await expect(hardBtn).toBeVisible();
    await expect(hardBtn).not.toHaveAttribute('aria-disabled', 'true');
  });

  test('free user: Hard difficulty pill is aria-disabled', async ({ page }) => {
    const { free } = getUsers();
    await loginAs(page, free.email, free.password);
    await page.goto('/mock');
    await page.waitForSelector('.mock-config-pill');

    const hardBtn = page.locator('.mock-config-pill', { hasText: 'Hard' });
    await expect(hardBtn).toBeVisible();
    await expect(hardBtn).toHaveAttribute('aria-disabled', 'true');
  });
});
