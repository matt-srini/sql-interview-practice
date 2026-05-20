/**
 * Mock hub plan-tier e2e flows.
 *
 * Covers the repeatable QA checks that matter most for the current mock rollout:
 * free/pro/elite surface differences on /mock, right/wrong mid-session submission
 * behavior, and summary follow-up actions for drill vs benchmark flows.
 */
import { test, expect } from '@playwright/test';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const ROOT = path.dirname(fileURLToPath(import.meta.url));
const USERS_FILE = path.join(ROOT, '.test-users.json');
const PYSPARK_CONTENT = path.join(ROOT, '..', '..', 'backend', 'content', 'pyspark_questions');

function readJson(filePath) {
  return JSON.parse(fs.readFileSync(filePath, 'utf8'));
}

function getUsers() {
  return readJson(USERS_FILE);
}

function buildPysparkIndex() {
  const files = ['easy.json', 'medium.json', 'hard.json'];
  return Object.fromEntries(
    files
      .flatMap((file) => readJson(path.join(PYSPARK_CONTENT, file)))
      .map((question) => [question.id, question])
  );
}

const PYSPARK_INDEX = buildPysparkIndex();

async function loginAs(page, email, password) {
  await page.goto('/auth');
  await page.getByLabel('Email address').fill(email);
  await page.locator('#auth-password').fill(password);
  await page.getByRole('button', { name: 'Sign in' }).click();
  await page.waitForURL('/');
}

async function api(page, pathName, { method = 'GET', body } = {}) {
  return page.evaluate(async ({ pathName, method, body }) => {
    const response = await fetch(pathName, {
      method,
      credentials: 'include',
      headers: body ? { 'Content-Type': 'application/json' } : undefined,
      body: body ? JSON.stringify(body) : undefined,
    });
    const text = await response.text();
    let parsed = null;
    try {
      parsed = text ? JSON.parse(text) : null;
    } catch {
      parsed = text;
    }
    return { status: response.status, body: parsed };
  }, { pathName, method, body });
}

function wrongOption(questionId) {
  const question = PYSPARK_INDEX[questionId];
  return (question.correct_option + 1) % question.options.length;
}

async function startAndFinishPyspark(page, { mode, difficulty }) {
  let start = await api(page, '/api/mock/start', {
    method: 'POST',
    body: { mode, track: 'pyspark', difficulty },
  });

  if (start.status === 409 && start.body?.session_id) {
    await api(page, `/api/mock/${start.body.session_id}/finish`, { method: 'POST' });
    start = await api(page, '/api/mock/start', {
      method: 'POST',
      body: { mode, track: 'pyspark', difficulty },
    });
  }

  expect(start.status).toBeGreaterThanOrEqual(200);
  expect(start.status).toBeLessThan(300);

  const sessionId = start.body.session_id;
  const [firstQuestion, secondQuestion] = start.body.questions;

  const firstSubmit = await api(page, `/api/mock/${sessionId}/submit`, {
    method: 'POST',
    body: {
      question_id: firstQuestion.id,
      track: 'pyspark',
      selected_option: wrongOption(firstQuestion.id),
    },
  });
  const secondSubmit = await api(page, `/api/mock/${sessionId}/submit`, {
    method: 'POST',
    body: {
      question_id: secondQuestion.id,
      track: 'pyspark',
      selected_option: PYSPARK_INDEX[secondQuestion.id].correct_option,
    },
  });
  const finish = await api(page, `/api/mock/${sessionId}/finish`, { method: 'POST' });

  return { sessionId, start, firstSubmit, secondSubmit, finish };
}

test.describe('Mock plan-tier flows', () => {
  test('free user gets drill-first follow-up framing without elite surfaces', async ({ page }) => {
    const { free } = getUsers();
    await loginAs(page, free.email, free.password);
    await page.goto('/mock');

    await expect(page.getByText('What Elite adds to every session')).toBeVisible();
    await expect(page.locator('.mock-config-pill', { hasText: 'Hard' })).toHaveAttribute('aria-disabled', 'true');

    const flow = await startAndFinishPyspark(page, { mode: '30min', difficulty: 'easy' });
    expect(flow.firstSubmit.status).toBe(200);
    expect(flow.firstSubmit.body.correct).toBe(false);
    expect(flow.firstSubmit.body.solution ?? null).toBeNull();
    expect(flow.secondSubmit.body.correct).toBe(true);

    await page.goto(`/mock/${flow.sessionId}`);
    await expect(page.getByText('Drill summary')).toBeVisible();
    await expect(page.getByRole('button', { name: 'Continue targeted drill' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Back to drill lobby' })).toBeVisible();
    await expect(page.getByText('Session debrief')).toHaveCount(0);
  });

  test('pro user gets drill weak-concept follow-up without elite analytics', async ({ page }) => {
    const { pro } = getUsers();
    await loginAs(page, pro.email, pro.password);
    await page.goto('/mock');

    await expect(page.getByText('One step from Elite')).toBeVisible();
    await expect(page.locator('.mock-config-pill', { hasText: 'Hard' })).not.toHaveAttribute('aria-disabled', 'true');

    const flow = await startAndFinishPyspark(page, { mode: '30min', difficulty: 'medium' });
    expect(flow.firstSubmit.body.correct).toBe(false);
    expect(flow.firstSubmit.body.solution ?? null).toBeNull();
    expect(flow.secondSubmit.body.correct).toBe(true);

    await page.goto(`/mock/${flow.sessionId}`);
    await expect(page.getByText('Drill summary')).toBeVisible();
    await expect(page.getByRole('link', { name: 'Drill weak concepts →' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Back to drill lobby' })).toBeVisible();
    await expect(page.getByText('Session debrief')).toHaveCount(0);
  });

  test('elite user gets benchmark debrief and drill handoff back into MockHub', async ({ page }) => {
    const { elite } = getUsers();
    await loginAs(page, elite.email, elite.password);
    await page.goto('/mock');

    await expect(page.getByText('Benchmark Analytics')).toBeVisible();
    await expect(page.locator('input[type="checkbox"]').first()).not.toBeDisabled();

    const flow = await startAndFinishPyspark(page, { mode: 'benchmark', difficulty: 'easy' });
    expect(flow.start.body.questions).toHaveLength(6);
    expect(flow.start.body.time_limit_s).toBe(2400);
    expect(flow.firstSubmit.body.correct).toBe(false);
    expect(flow.secondSubmit.body.correct).toBe(true);

    await page.goto(`/mock/${flow.sessionId}`);
    await expect(page.getByText('Benchmark summary')).toBeVisible();
    await expect(page.getByText('Session debrief')).toBeVisible();
    await expect(page.getByRole('button', { name: 'Review benchmarks' })).toBeVisible();
    await page.getByRole('button', { name: 'Plan follow-up drill' }).click();

    await expect(page.getByText('Recommended next step')).toBeVisible();
    await expect(page.getByText(/short targeted drill/i)).toBeVisible();
    await expect(page.getByRole('button', { name: 'Start drill session' })).toBeVisible();
  });
});