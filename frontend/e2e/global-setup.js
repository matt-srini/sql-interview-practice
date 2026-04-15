/**
 * Playwright globalSetup — runs once before the entire test suite.
 *
 * Creates one user per plan tier (elite, pro, free) and stores credentials
 * in e2e/.test-users.json so individual tests can reuse them without
 * making further registration requests and exhausting the dev rate limiter.
 */
import { request } from '@playwright/test';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const API = 'http://localhost:8000';
const OUT = path.join(path.dirname(fileURLToPath(import.meta.url)), '.test-users.json');

async function createUser(apiCtx, plan) {
  const ts = Date.now();
  const email = `e2e-${plan}-setup-${ts}@internal.test`;
  const password = 'E2eTest123!';

  await apiCtx.get('/api/catalog'); // seed anon session
  const reg = await apiCtx.post('/api/auth/register', {
    data: { email, name: `E2E ${plan}`, password },
  });
  const body = await reg.json();
  if (!body.user?.id) throw new Error(`Registration failed for ${plan}: ${JSON.stringify(body)}`);

  if (plan !== 'free') {
    const up = await apiCtx.post('/api/user/plan', {
      data: { user_id: body.user.id, new_plan: plan, context: 'e2e-global-setup' },
    });
    if (!up.ok()) throw new Error(`Plan upgrade to ${plan} failed: ${await up.text()}`);
  }

  return { email, password, plan, id: body.user.id };
}

export default async function globalSetup() {
  // Each user gets its own context so session cookies don't bleed between registrations
  const ctxElite = await request.newContext({ baseURL: API });
  const ctxPro   = await request.newContext({ baseURL: API });
  const ctxFree  = await request.newContext({ baseURL: API });

  try {
    // Create users sequentially to avoid parallel rate-limit bursts
    const elite = await createUser(ctxElite, 'elite');
    const pro   = await createUser(ctxPro,   'pro');
    const free  = await createUser(ctxFree,  'free');

    fs.writeFileSync(OUT, JSON.stringify({ elite, pro, free }, null, 2));
    console.log(`\n[globalSetup] Test users written to ${OUT}`);
  } finally {
    await ctxElite.dispose();
    await ctxPro.dispose();
    await ctxFree.dispose();
  }
}
