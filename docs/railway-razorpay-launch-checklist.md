# Railway + Razorpay Launch Checklist

> **Navigation:** [Docs index](./README.md) · [Deployment](./deployment.md) · [Backend](./backend.md)

This checklist is the step-by-step launch playbook for taking the project from a purely local app to a Railway deployment using **Razorpay test mode first**, then switching to **Razorpay live mode** after website verification is approved.

Use this file as the operational source of truth. Tick items off one by one as you complete them.

---

## How to use this checklist

- Work **top to bottom**. Do not skip ahead to live keys.
- Keep **test mode** and **live mode** credentials completely separate.
- Do not paste Razorpay secrets into frontend files. This app reads Razorpay credentials from the **backend environment only**.
- For this codebase, checkout is blocked until the user account is **email verified**. Plan that dependency before testing payments.
- Prefer the free Railway-generated domain first. Buy and attach a custom domain later if needed.

---

## Phase 0: Accounts and prerequisites

### 0.1 Create or confirm the required accounts

- [ ] Razorpay account exists and you can log in at https://dashboard.razorpay.com
- [x] Railway account exists at https://railway.com
- [x] GitHub repo is available and current code is pushed
- [x] Resend account exists at https://resend.com if you want real verification emails during checkout testing
- [x] Sentry account exists at https://sentry.io if you want production error capture from the first deploy
- [ ] PostHog account exists at https://posthog.com if you want product analytics from the first deploy

### 0.2 Confirm the current project state locally

- [x] Backend runs locally from `backend/`
- [x] Frontend runs locally from `frontend/`
- [x] Backend tests are green enough for deploy confidence
- [x] You can log in locally and reach the pricing or upgrade UI

Notes recorded from current setup:

- Sentry is already configured at the account level for both frontend and backend local error tracking.
- Railway account exists and is ready for project creation/deploy steps.

### 0.3 Know the environment variables this app expects

The Razorpay-related backend variables in this repo are:

```env
RAZORPAY_KEY_ID=
RAZORPAY_KEY_SECRET=
RAZORPAY_WEBHOOK_SECRET=
RAZORPAY_PLAN_PRO=
RAZORPAY_PLAN_ELITE=
RAZORPAY_AMOUNT_LIFETIME_PRO=799900
RAZORPAY_AMOUNT_LIFETIME_ELITE=1499900
RAZORPAY_CURRENCY=INR
```

The optional email variables are:

```env
RESEND_API_KEY=
EMAIL_FROM=datathink <noreply@yourdomain.com>
```

The core deployment variables are:

```env
ENV=production
DATABASE_URL=
REDIS_URL=
SECURE_COOKIES=true
APP_BASE_URL=
FRONTEND_BASE_URL=
ALLOWED_ORIGINS=
```

The optional observability variables are:

```env
SENTRY_DSN=
VITE_SENTRY_DSN=
VITE_POSTHOG_KEY=
VITE_POSTHOG_HOST=https://us.i.posthog.com
```

---

## Phase 1: Local Razorpay test-mode setup

This phase keeps everything local. It proves your app can create orders and subscriptions with **test** credentials before Railway exists.

### 1.1 Confirm Razorpay test keys

- [x] In Razorpay dashboard, click **Switch to Test Mode** in the top bar or key area
- [x] Go to **Account & Settings**
- [x] Open **Website and app details** if prompted by the dashboard flow
- [x] Go to the **Websites & API keys** area
- [x] Confirm you already have a **Test Key Id** and **Test Key Secret**
- [x] Store them temporarily in a password manager or secure notes, not in source control

Useful entry points:

- Razorpay dashboard home: https://dashboard.razorpay.com
- Razorpay integration docs: https://razorpay.com/docs/payments/payment-gateway/web-integration/standard/
- Razorpay subscriptions docs: https://razorpay.com/docs/payments/subscriptions/
- Razorpay webhooks docs: https://razorpay.com/docs/webhooks/

### 1.2 Create local backend env values

- [x] Open the local file `backend/.env`
- [x] Insert your current local database value
- [x] Insert your Razorpay **test** key id and secret
- [x] Leave live values out of local files for now

Use this template:

```env
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/sql_practice
REDIS_URL=redis://localhost:6379/0

RAZORPAY_KEY_ID=rzp_test_replace_me
RAZORPAY_KEY_SECRET=replace_me
RAZORPAY_WEBHOOK_SECRET=replace_after_webhook_creation
RAZORPAY_PLAN_PRO=replace_after_test_plan_creation
RAZORPAY_PLAN_ELITE=replace_after_test_plan_creation
RAZORPAY_AMOUNT_LIFETIME_PRO=799900
RAZORPAY_AMOUNT_LIFETIME_ELITE=1499900
RAZORPAY_CURRENCY=INR
```

Notes:

- `backend/.env` is local-only and should stay ignored.
- There is **no frontend Razorpay secret** to add. Checkout receives only the public key id returned by the backend.

### 1.3 Create Razorpay test subscription plans

This app uses:

- `pro` and `elite` as **subscriptions**
- `lifetime_pro` and `lifetime_elite` as **one-time orders** created directly by the backend

Steps in Razorpay:

- [x] Stay in **Test Mode**
- [x] Open **Subscriptions** in the left navigation
- [x] Go to the **Plans** section
- [x] Create a plan for **Pro monthly**
- [x] Create a plan for **Elite monthly**

Recommended values:

- Pro monthly
  - Plan name: `datathink Pro Monthly`
  - Billing period: `Monthly`
  - Interval: `1`
  - Amount: `79900` paise if Razorpay asks for subunits, or `799` if it asks for rupees in the UI
- Elite monthly
  - Plan name: `datathink Elite Monthly`
  - Billing period: `Monthly`
  - Interval: `1`
  - Amount: `159900` paise or `1599` rupees depending on the UI field

- [x] Copy the test plan id for Pro into `RAZORPAY_PLAN_PRO`
- [x] Copy the test plan id for Elite into `RAZORPAY_PLAN_ELITE`

### 1.4 Understand what does not need a Razorpay Plan

- [x] Confirm that **Lifetime Pro** does not need a Razorpay Plan object
- [x] Confirm that **Lifetime Elite** does not need a Razorpay Plan object
- [x] Keep these values in env only:

```env
RAZORPAY_AMOUNT_LIFETIME_PRO=799900
RAZORPAY_AMOUNT_LIFETIME_ELITE=1499900
```

Those amounts are used by the backend when it creates a one-time Razorpay Order.

### 1.5 Handle email verification before testing checkout

This codebase blocks checkout for users whose `email_verified` flag is false.

Choose one path:

- [x] **Preferred:** Set up Resend so the app can send verification emails
- [ ] **Temporary local-only fallback:** Manually mark your test user as verified in Postgres

If using Resend:

- [x] Log in at https://resend.com
- [x] Create an API key
- [x] Add it to `backend/.env` as `RESEND_API_KEY`
- [x] Set `EMAIL_FROM` to a valid sender identity
- [x] Register a test account in your app and verify the email through the app flow

If using the manual fallback locally:

- [ ] Open Postgres for your local database
- [ ] Run an update against your own test account only

Example SQL:

```sql
UPDATE users
SET email_verified = true
WHERE email = 'your-test-email@example.com';
```

### 1.6 Run the local app and smoke-test checkout initialization

- [x] Start Postgres and Redis locally
- [x] Start the backend from `backend/`
- [x] Start the frontend from `frontend/`
- [x] Log in with a verified account
- [x] Click an upgrade button for a lifetime plan
- [x] Confirm no immediate backend error appears when the app tries to call `/api/razorpay/create-order`

### Phase 1 status

- [x] Phase 1 complete: local Razorpay test-mode setup and checkout smoke test finished
- [x] Razorpay test card flow validated end-to-end, including upgrade success

If checkout fails immediately, verify:

- [ ] `RAZORPAY_KEY_ID` is set
- [ ] `RAZORPAY_KEY_SECRET` is set
- [ ] `RAZORPAY_PLAN_PRO` and `RAZORPAY_PLAN_ELITE` exist for subscription flows
- [ ] The account is verified

---

## Phase 2: Prepare the future production identity

You do **not** need a purchased domain before the first deployment. Use Railway's generated domain first, then optionally attach a custom domain later.

### 2.1 Decide the first public URL

- [x] Use the Railway-generated domain as the initial public app URL
- [x] Plan to use that same URL in:
  - `APP_BASE_URL`
  - `FRONTEND_BASE_URL`
  - `ALLOWED_ORIGINS`
  - Razorpay webhook URL
  - Razorpay website verification form

Current launch host:

- [x] Public app URL fixed to `https://datathink.co`
- [x] Cloudflare domain already purchased and configured
- [x] Backend environment already reflects the chosen public host

### 2.2 Prepare the site details you will submit to Razorpay later

Before you can generate **live** keys, Razorpay may require website verification.

Prepare these details now so you can paste them later:

- [x] Public app name: `datathink`
- [x] Short site description: `Data interview practice platform for SQL, Python, Pandas, and PySpark`
- [x] Support email address
- [x] Public website URL placeholder for now
- [x] Pricing description for Pro, Elite, Lifetime Pro, Lifetime Elite
- [x] Refund/cancellation wording if required by Razorpay review
- [x] Privacy policy and terms links if you plan to add them before live review

### Phase 2 status

- [x] Phase 2 complete: production identity is fixed to `https://datathink.co` and supporting site details/docs are prepared for Railway + Razorpay setup

Razorpay area to revisit later:

- Dashboard: https://dashboard.razorpay.com
- Navigation: **Account & Settings** → **Business website details** → **Websites & API keys**

---

## Phase 3: Create the Railway project

This is the first public deployment phase.

### 3.1 Create a Railway account and project

- [ ] Go to https://railway.com
- [ ] Sign in with GitHub
- [ ] Click **New Project**
- [ ] Choose **Deploy from GitHub repo** if available for your account flow
- [ ] Select the `sql-interview-practice` repository
- [ ] Confirm Railway detects the root `Dockerfile`

Useful pages:

- Railway home: https://railway.com
- Railway dashboard: https://railway.com/dashboard
- Railway docs: https://docs.railway.com

### 3.2 Add the backing services

- [ ] In the Railway project, click **New** or **Add Service**
- [ ] Add a **PostgreSQL** service
- [ ] Add a **Redis** service
- [ ] Keep the existing app service that builds your repository

### 3.3 Generate the first public domain

- [ ] Open the app service in Railway
- [ ] Go to the **Settings** tab
- [ ] Find the **Domains** section
- [ ] Click **Generate Domain** or the equivalent domain action
- [ ] Copy the generated public URL

This generated Railway URL is enough for test deployments and Razorpay website verification submission later.

---

## Phase 4: Configure Railway environment variables

### 4.1 Open the app service variables page

- [ ] In Railway, open your **app service**, not the Postgres or Redis service
- [ ] Go to the **Variables** tab
- [ ] Paste variables into the app service only

### 4.2 Insert the core deployment values

- [ ] Add the generated Railway domain everywhere the app expects a public origin

Template:

```env
ENV=production
SECURE_COOKIES=true

APP_BASE_URL=https://replace-with-your-railway-domain.up.railway.app
FRONTEND_BASE_URL=https://replace-with-your-railway-domain.up.railway.app
ALLOWED_ORIGINS=https://replace-with-your-railway-domain.up.railway.app
```

### 4.3 Insert the database and Redis values

Railway usually exposes connection values from the Postgres and Redis services. Depending on the UI, you may either:

- paste the full connection strings manually, or
- reference service-provided variables from the app service

- [ ] Copy the Postgres connection string into `DATABASE_URL`
- [ ] Copy the Redis connection string into `REDIS_URL`

### 4.4 Insert Razorpay **test** variables into Railway

Important: your first production deployment should still use **test** mode Razorpay values.

- [ ] Add your test key id to `RAZORPAY_KEY_ID`
- [ ] Add your test key secret to `RAZORPAY_KEY_SECRET`
- [ ] Add your test Pro plan id to `RAZORPAY_PLAN_PRO`
- [ ] Add your test Elite plan id to `RAZORPAY_PLAN_ELITE`
- [ ] Add lifetime amounts
- [ ] Leave live values out for now

Template:

```env
RAZORPAY_KEY_ID=rzp_test_replace_me
RAZORPAY_KEY_SECRET=replace_me
RAZORPAY_PLAN_PRO=plan_replace_me
RAZORPAY_PLAN_ELITE=plan_replace_me
RAZORPAY_AMOUNT_LIFETIME_PRO=799900
RAZORPAY_AMOUNT_LIFETIME_ELITE=1499900
RAZORPAY_CURRENCY=INR
```

### 4.5 Insert email variables if you want a real signup-to-payment flow

- [ ] Add `RESEND_API_KEY`
- [ ] Add `EMAIL_FROM`

If you skip this, registration still works, but verification emails are not sent automatically. That makes payment testing harder because checkout requires verified accounts.

### 4.6 Insert observability variables if you want production debugging

- [ ] Add `SENTRY_DSN`
- [ ] Add `VITE_SENTRY_DSN`
- [ ] Add `VITE_POSTHOG_KEY`
- [ ] Optionally change `VITE_POSTHOG_HOST` if your project uses another region

---

## Phase 5: Run database migrations on Railway

### 5.1 Apply Alembic migrations against the Railway Postgres database

- [ ] Retrieve the production `DATABASE_URL`
- [ ] Run Alembic from your local machine against that database

Command template:

```bash
cd backend
DATABASE_URL="postgresql+asyncpg://replace-me" ../.venv/bin/alembic upgrade head
```

If Railway gives you a `postgresql://` URL, convert it to `postgresql+asyncpg://` for the Alembic command.

### 5.2 Confirm schema readiness

- [ ] No migration errors occurred
- [ ] App startup no longer depends on schema bootstrapping for the new environment

---

## Phase 6: First Railway deploy with Razorpay test mode

### 6.1 Trigger the first app deploy

- [ ] In Railway, deploy the current `main` branch
- [ ] Wait for the Docker build and runtime start to finish
- [ ] Open the generated public URL

### 6.2 Smoke-test the deployed app

- [ ] Visit `https://YOUR-RAILWAY-DOMAIN/health`
- [ ] Confirm the app responds successfully
- [ ] Visit the main app URL in a browser
- [ ] Confirm the SPA loads correctly
- [ ] Register or log in

### 6.3 Verify email flow on the deployed app

Choose one:

- [ ] Preferred: complete email verification through Resend
- [ ] Temporary fallback: manually mark your own deployed test account as verified in production Postgres

Production-only SQL for your own test account:

```sql
UPDATE users
SET email_verified = true
WHERE email = 'your-test-email@example.com';
```

Do this only for controlled testing while Resend is not configured.

---

## Phase 7: Configure the Razorpay **test** webhook for Railway

### 7.1 Create the webhook in Razorpay test mode

- [ ] Return to https://dashboard.razorpay.com
- [ ] Ensure **Test Mode** is enabled
- [ ] Go to **Account & Settings**
- [ ] Open **Webhooks**
- [ ] Click **Add New Webhook** or equivalent
- [ ] Set the webhook URL to:

```text
https://YOUR-RAILWAY-DOMAIN/api/razorpay/webhook
```

- [ ] Select these events:
  - `payment.captured`
  - `payment.failed`
  - `subscription.activated`
  - `subscription.charged`
  - `subscription.cancelled`
  - `subscription.halted`
- [ ] Save the webhook
- [ ] Copy the generated webhook secret
- [ ] Paste it into Railway app variables as `RAZORPAY_WEBHOOK_SECRET`
- [ ] Redeploy if Railway does not hot-apply variables automatically for your service

### 7.2 Confirm webhook delivery visibility

- [ ] In Razorpay dashboard, open the webhook details page
- [ ] Learn where delivery attempts are shown
- [ ] Be ready to compare Razorpay delivery status with your app logs after each payment test

---

## Phase 8: End-to-end payment testing in Razorpay test mode

### 8.1 Test a lifetime purchase flow

- [ ] Log in to the deployed app with a verified account
- [ ] Click a **Lifetime Pro** or **Lifetime Elite** upgrade button
- [ ] Confirm the Razorpay modal opens

Razorpay test payment values:

- Card number: `4111 1111 1111 1111`
- Expiry: any future date
- CVV: any 3 digits
- OTP: `1234`

- [ ] Complete the payment
- [ ] Confirm the app redirects or returns to the practice flow without an error
- [ ] Confirm the user's plan changed in the app

### 8.2 Test a monthly subscription flow

- [ ] Start a **Pro** monthly checkout
- [ ] Start an **Elite** monthly checkout
- [ ] Confirm the Razorpay modal opens for each
- [ ] Confirm the correct subscription path is used
- [ ] Confirm the plan upgrades correctly after success

### 8.3 Confirm webhook behavior after test payments

- [ ] Open the Razorpay webhook delivery log for the test webhook
- [ ] Confirm successful delivery to your Railway URL
- [ ] Check Railway logs if a webhook attempt fails
- [ ] Confirm the app records the plan state you expect

### 8.4 Test negative scenarios

- [ ] Dismiss the modal and confirm the UI handles it cleanly
- [ ] Trigger a payment failure and confirm the UI shows a clear message
- [ ] Confirm invalid or missing webhook secret causes expected webhook rejection rather than silent success

---

## Phase 9: Submit the deployed site for Razorpay website verification

You cannot complete live-mode payment setup until Razorpay approves the website/app details.

### 9.1 Submit the currently deployed public site

- [ ] Go to https://dashboard.razorpay.com
- [ ] Open **Account & Settings**
- [ ] Go to **Business website details**
- [ ] Open the **Websites & API keys** tab
- [ ] Click **Add website/app**
- [ ] Submit the current Railway URL if no custom domain exists yet
- [ ] Fill in the requested business and website details accurately
- [ ] Submit for review

Typical content to prepare:

- public website URL
- business description
- what the customer is paying for
- support contact details
- cancellation/refund wording if asked

### 9.2 Wait for approval

- [ ] Watch for Razorpay review updates in email or dashboard
- [ ] Do not attempt live key generation until the website is approved
- [ ] Continue testing with test keys while waiting

---

## Phase 10: Optional custom domain attachment before going live

This is optional. You can launch first on the Railway domain and move to a custom domain later.

### 10.1 Buy a domain if desired

- [ ] Purchase a domain from your registrar of choice
- [ ] Decide whether the app will live on the root domain or a subdomain such as `app.yourdomain.com`

### 10.2 Attach it in Railway

- [ ] In Railway, open the app service
- [ ] Go to **Settings** → **Domains**
- [ ] Add the custom domain
- [ ] Copy the DNS records Railway tells you to create
- [ ] Create those DNS records in your domain registrar
- [ ] Wait for Railway to show the custom domain as active

### 10.3 Update origin variables if you switch domains before live keys

- [ ] Update `APP_BASE_URL`
- [ ] Update `FRONTEND_BASE_URL`
- [ ] Update `ALLOWED_ORIGINS`
- [ ] Update the Razorpay webhook URL if the host changed
- [ ] Update the Razorpay website details if the public site URL changed

---

## Phase 11: Prepare the live-mode cutover

Do this only after Razorpay approves the site.

### 11.1 Generate live keys in Razorpay

- [ ] Go to https://dashboard.razorpay.com
- [ ] Switch from **Test Mode** to **Live Mode**
- [ ] Return to **Account & Settings**
- [ ] Open the API key area
- [ ] Generate a **Live Key Id** and **Live Key Secret**
- [ ] Store them securely

### 11.2 Create live subscription plans

Live mode needs a fresh set of subscription plans. Test plan ids do not carry over.

- [ ] In **Live Mode**, go to **Subscriptions** → **Plans**
- [ ] Create `datathink Pro Monthly`
- [ ] Create `datathink Elite Monthly`
- [ ] Copy the live plan ids

### 11.3 Create the live webhook

- [ ] In **Live Mode**, go to **Account & Settings** → **Webhooks**
- [ ] Create a webhook pointing to:

```text
https://YOUR-PUBLIC-DOMAIN/api/razorpay/webhook
```

- [ ] Select the same six events used in test mode
- [ ] Save the webhook
- [ ] Copy the new **live** webhook secret

Important:

- [ ] Do not reuse the test webhook secret
- [ ] Do not reuse the test plan ids
- [ ] Do not mix a live key with test plan ids or vice versa

---

## Phase 12: Replace Railway test variables with live variables

### 12.1 Update only the values that must change

- [ ] In Railway app service → **Variables**
- [ ] Replace `RAZORPAY_KEY_ID` with the live key id
- [ ] Replace `RAZORPAY_KEY_SECRET` with the live key secret
- [ ] Replace `RAZORPAY_WEBHOOK_SECRET` with the live webhook secret
- [ ] Replace `RAZORPAY_PLAN_PRO` with the live Pro plan id
- [ ] Replace `RAZORPAY_PLAN_ELITE` with the live Elite plan id

Keep these unless your pricing changed:

- [ ] `RAZORPAY_AMOUNT_LIFETIME_PRO`
- [ ] `RAZORPAY_AMOUNT_LIFETIME_ELITE`
- [ ] `RAZORPAY_CURRENCY`

### 12.2 Redeploy and verify the host values one last time

- [ ] Redeploy the app
- [ ] Confirm the domain in `APP_BASE_URL` matches the real public site
- [ ] Confirm `FRONTEND_BASE_URL` matches the same public site in single-service deployment
- [ ] Confirm `ALLOWED_ORIGINS` exactly matches the browser origin users will hit

---

## Phase 13: Live payment verification

### 13.1 Run a controlled real transaction

- [ ] Use a real verified account you control
- [ ] Make one small real payment or the safest real upgrade you are comfortable testing
- [ ] Confirm the payment succeeds in the app
- [ ] Confirm the webhook delivers successfully in Razorpay live-mode logs
- [ ] Confirm the user plan changed correctly in the app and in the database

### 13.2 Verify operational visibility

- [ ] Check Railway logs for any backend errors
- [ ] Check Sentry for any frontend or backend exceptions
- [ ] Check PostHog for payment funnel events if enabled
- [ ] Confirm there are no CSRF, origin, or cookie issues on the live domain

---

## Phase 14: Post-launch guardrails

- [ ] Store all live secrets in Railway only, not in repo files
- [ ] Rotate any secret immediately if it was pasted somewhere unsafe
- [ ] Keep a copy of both test and live plan ids in a secure internal note
- [ ] Record the webhook URL and event list for future reference
- [ ] Keep at least one test account and one live admin account documented privately

---

## Fast rollback plan

If live Razorpay breaks after cutover:

- [ ] Stop further payment testing immediately
- [ ] Check Railway app logs
- [ ] Check Razorpay webhook delivery logs
- [ ] Check whether test and live values were mixed accidentally
- [ ] If necessary, temporarily replace live values with the last-known-good set while you diagnose
- [ ] Re-test with one controlled transaction after the fix

---

## Copy-paste blocks

### Local backend `.env` with test mode

```env
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/sql_practice
REDIS_URL=redis://localhost:6379/0

RAZORPAY_KEY_ID=rzp_test_replace_me
RAZORPAY_KEY_SECRET=replace_me
RAZORPAY_WEBHOOK_SECRET=replace_after_webhook_creation
RAZORPAY_PLAN_PRO=plan_replace_me
RAZORPAY_PLAN_ELITE=plan_replace_me
RAZORPAY_AMOUNT_LIFETIME_PRO=799900
RAZORPAY_AMOUNT_LIFETIME_ELITE=1499900
RAZORPAY_CURRENCY=INR

RESEND_API_KEY=replace_if_using_resend
EMAIL_FROM=datathink <noreply@yourdomain.com>
```

### Railway app service variables with test mode

```env
ENV=production
SECURE_COOKIES=true

APP_BASE_URL=https://replace-with-your-railway-domain.up.railway.app
FRONTEND_BASE_URL=https://replace-with-your-railway-domain.up.railway.app
ALLOWED_ORIGINS=https://replace-with-your-railway-domain.up.railway.app

DATABASE_URL=replace-me
REDIS_URL=replace-me

RAZORPAY_KEY_ID=rzp_test_replace_me
RAZORPAY_KEY_SECRET=replace_me
RAZORPAY_WEBHOOK_SECRET=replace_after_test_webhook_creation
RAZORPAY_PLAN_PRO=plan_replace_me
RAZORPAY_PLAN_ELITE=plan_replace_me
RAZORPAY_AMOUNT_LIFETIME_PRO=799900
RAZORPAY_AMOUNT_LIFETIME_ELITE=1499900
RAZORPAY_CURRENCY=INR

RESEND_API_KEY=replace_if_using_resend
EMAIL_FROM=datathink <noreply@yourdomain.com>

SENTRY_DSN=replace_if_using_sentry
VITE_SENTRY_DSN=replace_if_using_sentry
VITE_POSTHOG_KEY=replace_if_using_posthog
VITE_POSTHOG_HOST=https://us.i.posthog.com
```

### Railway app service variables after live cutover

```env
ENV=production
SECURE_COOKIES=true

APP_BASE_URL=https://your-public-domain
FRONTEND_BASE_URL=https://your-public-domain
ALLOWED_ORIGINS=https://your-public-domain

DATABASE_URL=replace-me
REDIS_URL=replace-me

RAZORPAY_KEY_ID=rzp_live_replace_me
RAZORPAY_KEY_SECRET=replace_me
RAZORPAY_WEBHOOK_SECRET=replace_after_live_webhook_creation
RAZORPAY_PLAN_PRO=plan_live_replace_me
RAZORPAY_PLAN_ELITE=plan_live_replace_me
RAZORPAY_AMOUNT_LIFETIME_PRO=799900
RAZORPAY_AMOUNT_LIFETIME_ELITE=1499900
RAZORPAY_CURRENCY=INR

RESEND_API_KEY=replace_if_using_resend
EMAIL_FROM=datathink <noreply@yourdomain.com>

SENTRY_DSN=replace_if_using_sentry
VITE_SENTRY_DSN=replace_if_using_sentry
VITE_POSTHOG_KEY=replace_if_using_posthog
VITE_POSTHOG_HOST=https://us.i.posthog.com
```