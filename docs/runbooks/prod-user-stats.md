# Prod user / login stats runbook

On-demand answer to **"how many users have registered / logged in on the live
site so far?"** — a read-only snapshot of the live Railway Postgres.

Canonical tool: [`backend/scripts/check_prod_users.py`](../../backend/scripts/check_prod_users.py).

## Run it

```bash
.venv/bin/python backend/scripts/check_prod_users.py
```

Read-only (SELECTs only) — safe to run anytime. The script reads the prod
`DATABASE_URL` from `backend/.env` line 4 (the commented-out Railway proxy URL)
at runtime; the credential is never hardcoded. No arguments.

## How to read the output

Identity is **anonymous-first**: every visitor gets a `users` row, and `email`
is populated only on real registration. So the figures mean:

| Line | Meaning |
|---|---|
| `total identities` | Every `users` row — mostly anonymous visitors, not signups. |
| `registered (email)` | Rows with a non-null email = actual registrations. |
| ↳ `real signups` | Registrations excluding internal/test accounts (see below). **This is the "how many real users" number.** |
| ↳ `internal / test` | Any `@datathink.co` address + the known dev accounts + founder brand gmail. |
| `anonymous (no email)` | Visitors who never registered. |
| `signed-in real users` | Registered users with a non-expired session (`sessions` row per login). |
| `signed-in anon visitors` | Anonymous-first identities with a valid session — usually the bulk; not signups. |
| `registered logins 24h / 7d` | Distinct registered users who logged in recently (a `sessions` row = one login). |
| `users w/ >=1 submission` | Activation proxy — how many identities ever submitted an answer. |

Internal/test accounts excluded from "real signups" are configured in
`INTERNAL_EMAILS` + the `@datathink.co` domain rule at the top of the script.
Adjust there if a new staff account appears.

## Related

- Registration/session schema: `users` + `sessions` tables in [`backend/db.py`](../../backend/db.py) `_SCHEMA_SQL`.
- Channel attribution / funnel (sample→signup→activation) lives in PostHog, not the DB — see the GTM funnel in [`../growth/gtm-strategy.md`](../growth/gtm-strategy.md) §§ 5–6.
