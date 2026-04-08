from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

# Allow running as `python scripts/seed_admin.py` from backend/
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text

from db import _hash_password, close_pool, init_pool, _session_factory_or_raise


async def _upsert_admin(email: str, name: str, password: str) -> dict:
    pwd_hash, pwd_salt = _hash_password(password)
    session_factory = _session_factory_or_raise()
    async with session_factory() as session:
        result = await session.execute(
            text(
                """
                INSERT INTO users (email, name, pwd_hash, pwd_salt, plan, upgraded_at)
                VALUES (:email, :name, :pwd_hash, :pwd_salt, 'elite', now())
                ON CONFLICT (email) DO UPDATE
                  SET plan        = 'elite',
                      name        = EXCLUDED.name,
                      pwd_hash    = EXCLUDED.pwd_hash,
                      pwd_salt    = EXCLUDED.pwd_salt,
                      upgraded_at = now()
                RETURNING id, email, name, plan
                """
            ),
            {"email": email, "name": name, "pwd_hash": pwd_hash, "pwd_salt": pwd_salt},
        )
        await session.commit()
        row = result.mappings().one()
        return {"id": str(row["id"]), "email": row["email"], "name": row["name"], "plan": row["plan"]}


async def _run(email: str, name: str, password: str) -> dict:
    await init_pool()
    try:
        return await _upsert_admin(email, name, password)
    finally:
        await close_pool()


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed or update an admin user with elite plan.")
    parser.add_argument("--email", default=os.getenv("ADMIN_EMAIL"), help="Admin email (or set ADMIN_EMAIL env var)")
    parser.add_argument("--name", default=os.getenv("ADMIN_NAME", "Admin"), help="Display name (default: Admin)")
    parser.add_argument("--password", default=os.getenv("ADMIN_PASSWORD"), help="Password (or set ADMIN_PASSWORD env var)")
    args = parser.parse_args()

    if not args.email:
        print("Error: --email or ADMIN_EMAIL is required", file=sys.stderr)
        sys.exit(1)
    if not args.password:
        print("Error: --password or ADMIN_PASSWORD is required", file=sys.stderr)
        sys.exit(1)
    if len(args.password) < 8:
        print("Error: password must be at least 8 characters", file=sys.stderr)
        sys.exit(1)

    user = asyncio.run(_run(args.email, args.name, args.password))
    print(json.dumps(user, indent=2))


if __name__ == "__main__":
    main()
