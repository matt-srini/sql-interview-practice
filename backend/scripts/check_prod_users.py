#!/usr/bin/env python3
"""Prod user / login snapshot — read-only.

On-demand answer to "how many users have registered / logged in on the live site?"
Connects to the live Railway Postgres using the prod DATABASE_URL that lives
(commented out) in backend/.env line 4 — read at runtime, never hardcoded.

Run:  .venv/bin/python backend/scripts/check_prod_users.py
Read-only: SELECT statements only. Safe to run anytime.

Identity model is anonymous-first: every visitor gets a `users` row; `email`
is populated only when they actually register. So real registrations = rows
with a non-null email, minus internal/test accounts (see INTERNAL below).
A `sessions` row is created per login, so `sessions.created_at` = a login event
and a non-expired session ≈ a currently-valid login.
"""
import asyncio
import pathlib
import re
from collections import Counter

import asyncpg

# Internal / test accounts to exclude from "real signup" counts. Any @datathink.co
# address is internal by definition (company domain); the rest are the known dev
# accounts (CLAUDE.md § Local dev accounts) plus the founder's brand gmail.
INTERNAL_EMAILS = {
    "matt.srini@gmail.com",
    "srinivas.assampally@gmail.com",
    "admin@datathink.co",
    "test@datathink.co",
    "datathinkdt@gmail.com",
}


def is_internal(email: str) -> bool:
    return email in INTERNAL_EMAILS or email.endswith("@datathink.co")


def load_prod_url() -> str:
    env = (pathlib.Path(__file__).resolve().parent.parent / ".env").read_text().splitlines()
    line = next(l for l in env if "shuttle.proxy.rlwy.net" in l)  # the prod Railway proxy
    return re.sub(r"^\s*#\s*", "", line).split("DATABASE_URL=", 1)[1].strip()


async def main() -> None:
    url = load_prod_url()
    conn = await asyncpg.connect(url, timeout=15)
    try:
        now = await conn.fetchval("SELECT now() AT TIME ZONE 'UTC'")

        total = await conn.fetchval("SELECT count(*) FROM users")
        registered = await conn.fetchval("SELECT count(*) FROM users WHERE email IS NOT NULL")
        anon = total - registered
        submitters = await conn.fetchval("SELECT count(DISTINCT user_id) FROM submissions")

        # Sessions = login events. Non-expired ≈ currently-valid login. Split by
        # registered vs anonymous — anonymous-first visitors also hold session tokens,
        # so the registered count is the meaningful "signed-in real users" figure.
        active_reg = await conn.fetchval(
            """SELECT count(DISTINCT s.user_id) FROM sessions s JOIN users u ON u.id = s.user_id
               WHERE s.expires_at > now() AND u.email IS NOT NULL""")
        active_anon = await conn.fetchval(
            """SELECT count(DISTINCT s.user_id) FROM sessions s JOIN users u ON u.id = s.user_id
               WHERE s.expires_at > now() AND u.email IS NULL""")
        logins_24h = await conn.fetchval(
            """SELECT count(DISTINCT s.user_id) FROM sessions s JOIN users u ON u.id = s.user_id
               WHERE u.email IS NOT NULL AND s.created_at > now() - interval '24 hours'""")
        logins_7d = await conn.fetchval(
            """SELECT count(DISTINCT s.user_id) FROM sessions s JOIN users u ON u.id = s.user_id
               WHERE u.email IS NOT NULL AND s.created_at > now() - interval '7 days'""")

        regs = await conn.fetch(
            """SELECT u.email, u.name, u.plan, u.email_verified, u.created_at,
                      max(s.created_at) AS last_login
               FROM users u LEFT JOIN sessions s ON s.user_id = u.id
               WHERE u.email IS NOT NULL
               GROUP BY u.id, u.email, u.name, u.plan, u.email_verified, u.created_at
               ORDER BY u.created_at DESC""")

        real = [r for r in regs if not is_internal(r["email"])]

        def line(r):
            ca = r["created_at"].strftime("%Y-%m-%d")
            ll = r["last_login"].strftime("%Y-%m-%d %H:%M") if r["last_login"] else "never"
            ver = "✓" if r["email_verified"] else "·"
            return f"  {ca}  {r['plan']:<6} {ver}  {(r['email'] or ''):<34} login:{ll:<16} {r['name'] or ''}"

        print(f"datathink · prod user snapshot   (as of {now:%Y-%m-%d %H:%M} UTC)")
        print(f"DB: {url.split('@')[1]}")
        print()
        print("USERS")
        print(f"  total identities ...... {total:>4}   (anonymous-first: a row per visitor)")
        print(f"  registered (email) .... {registered:>4}")
        print(f"    real signups ........ {len(real):>4}")
        print(f"    internal / test ..... {registered - len(real):>4}")
        print(f"  anonymous (no email) .. {anon:>4}")
        print()
        print("LOGINS / SESSIONS   (a session row = one login; non-expired = still signed in)")
        print(f"  signed-in real users .. {active_reg:>4}   (registered, valid session)")
        print(f"  signed-in anon visitors {active_anon:>4}   (anonymous-first, valid session)")
        print(f"  registered logins 24h . {logins_24h:>4}")
        print(f"  registered logins 7d .. {logins_7d:>4}")
        print()
        print(f"ENGAGEMENT")
        print(f"  users w/ >=1 submission {submitters:>4}")
        print()
        print(f"REAL SIGNUPS  ({len(real)}, newest first)")
        print("\n".join(line(r) for r in real) or "  (none)")
        print()
        print(f"INTERNAL / TEST  ({registered - len(real)})")
        print("\n".join(line(r) for r in regs if is_internal(r["email"])) or "  (none)")
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
