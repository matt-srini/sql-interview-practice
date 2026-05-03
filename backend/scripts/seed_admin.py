from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

# Allow running as `python scripts/seed_admin.py` from backend/
sys.path.insert(0, str(Path(__file__).parent.parent))

# Load backend/.env if present (supports DATABASE_URL, ADMIN_EMAIL, ADMIN_PASSWORD, QA_SEED_PASSWORD, etc.)
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent / ".env")
except ImportError:
    pass

from sqlalchemy import text

from db import _hash_password, close_pool, init_pool, _session_factory_or_raise

_VALID_PLANS = ["free", "pro", "elite", "lifetime_pro", "lifetime_elite"]


async def _upsert_user(email: str, name: str, password: str, plan: str) -> dict:
    pwd_hash, pwd_salt = _hash_password(password)
    session_factory = _session_factory_or_raise()
    async with session_factory() as session:
        result = await session.execute(
            text(
                """
                INSERT INTO users (email, name, pwd_hash, pwd_salt, plan, upgraded_at, email_verified)
                VALUES (:email, :name, :pwd_hash, :pwd_salt, :plan, now(), true)
                ON CONFLICT (email) DO UPDATE
                  SET plan           = EXCLUDED.plan,
                      name           = EXCLUDED.name,
                      pwd_hash       = EXCLUDED.pwd_hash,
                      pwd_salt       = EXCLUDED.pwd_salt,
                      upgraded_at    = now(),
                      email_verified = true
                RETURNING id, email, name, plan
                """
            ),
            {"email": email, "name": name, "pwd_hash": pwd_hash, "pwd_salt": pwd_salt, "plan": plan},
        )
        await session.commit()
        row = result.mappings().one()
        return {"id": str(row["id"]), "email": row["email"], "name": row["name"], "plan": row["plan"]}


async def _run(email: str, name: str, password: str, plan: str) -> dict:
    await init_pool()
    try:
        return await _upsert_user(email, name, password, plan)
    finally:
        await close_pool()


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed or update a user with a given plan (bypasses registration API).")
    parser.add_argument("--email", default=os.getenv("ADMIN_EMAIL"), help="User email (or ADMIN_EMAIL env var)")
    parser.add_argument("--name", default=os.getenv("ADMIN_NAME", "Admin"), help="Display name (default: Admin)")
    parser.add_argument(
        "--password",
        default=os.getenv("ADMIN_PASSWORD") or os.getenv("QA_SEED_PASSWORD"),
        help="Password (or ADMIN_PASSWORD / QA_SEED_PASSWORD env var)",
    )
    parser.add_argument(
        "--plan",
        default="elite",
        choices=_VALID_PLANS,
        help="Plan tier to assign (default: elite)",
    )
    args = parser.parse_args()

    if not args.email:
        print("Error: --email or ADMIN_EMAIL is required", file=sys.stderr)
        sys.exit(1)
    if not args.password:
        print("Error: --password, ADMIN_PASSWORD, or QA_SEED_PASSWORD is required", file=sys.stderr)
        sys.exit(1)
    if len(args.password) < 8:
        print("Error: password must be at least 8 characters", file=sys.stderr)
        sys.exit(1)

    user = asyncio.run(_run(args.email, args.name, args.password, args.plan))
    print(json.dumps(user, indent=2))


if __name__ == "__main__":
    main()
