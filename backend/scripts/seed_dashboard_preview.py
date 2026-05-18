"""
Seed three realistic dashboard preview users for UI testing.

Users:
  free_user   → matt.srini@gmail.com    (plan=free)   password=Test1234!
  pro_user    → srinivas.assampally@gmail.com (plan=pro) password=Test1234!
  elite_user  → admin@datathink.co      (plan=elite)  password=Test1234!

Run from backend/:
  ../.venv/bin/python scripts/seed_dashboard_preview.py
Or against prod:
  DB_URL="postgresql://..." ../.venv/bin/python scripts/seed_dashboard_preview.py
"""

import asyncio
import hashlib
import os
import secrets
import uuid
from datetime import UTC, datetime, timedelta

import asyncpg

DB_URL = os.environ.get("DB_URL", "postgresql://postgres:postgres@localhost:5432/sql_practice")
PASSWORD = "Test1234!"
ITERATIONS = 260_000

# ── User IDs ─────────────────────────────────────────────────────────────────
FREE_UID  = "17768671-42c7-4ac3-930c-5b149e572b34"   # matt.srini@gmail.com
PRO_UID   = "6f9797cd-f158-4313-825a-23707b9cc926"   # srinivas.assampally@gmail.com
ELITE_UID = "134883f7-237b-401b-8047-cbb5a4d53dee"   # admin@datathink.co

# ── Track db_topic values ─────────────────────────────────────────────────────
SQL   = "sql"
PY    = "python"
PYDAT = "python_data"
SPARK = "pyspark"
DE    = "data-engineering"
DM    = "data-modeling"
STATS = "statistics"

# ── Question IDs (first N per track/diff) ────────────────────────────────────
SQL_EASY   = list(range(11001, 11033))   # 32 easy
SQL_MED    = list(range(12001, 12035))   # 34 medium
SQL_HARD   = list(range(13001, 13030))   # 29 hard
PY_EASY    = list(range(21001, 21031))   # 30 easy
PY_MED     = list(range(22001, 22030))   # 29 medium
PY_HARD    = list(range(23001, 23025))   # 24 hard
PYDAT_EASY = list(range(31001, 31023))   # 22 easy
PYDAT_MED  = list(range(32001, 32032))   # 31 medium
PYDAT_HARD = list(range(33001, 33024))   # 23 hard
SPARK_EASY = list(range(41001, 41039))   # 38 easy
SPARK_MED  = list(range(42001, 42039))   # 38 medium
SPARK_HARD = list(range(43001, 43027))   # 26 hard
DE_EASY    = list(range(51001, 51031))   # 30 easy
DE_MED     = list(range(52001, 52031))   # 30 medium
DE_HARD    = list(range(53001, 53021))   # 20 hard
STATS_EASY = list(range(71001, 71029))   # 28 easy
STATS_MED  = list(range(72001, 72029))   # 28 medium


def _hash_password(password: str) -> tuple[str, str]:
    salt = secrets.token_hex(32)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), ITERATIONS)
    return digest.hex(), salt


def _days_ago(n: float) -> datetime:
    return datetime.now(UTC) - timedelta(days=n)


def _hours_ago(n: float) -> datetime:
    return datetime.now(UTC) - timedelta(hours=n)


# ── Batch collector — accumulates rows, flushes with a single COPY ────────────
class Batch:
    def __init__(self, uid: str):
        self.uid = uuid.UUID(uid)
        # (user_id, track, question_id, is_correct, code, submitted_at, duration_ms)
        self.submissions: list[tuple] = []
        # (user_id, question_id, topic) -> solved_at — deduplicated
        self.progress: dict[tuple, datetime] = {}

    def sub(self, track: str, qid: int, is_correct: bool, at: datetime, ms: int) -> None:
        self.submissions.append((self.uid, track, qid, is_correct, "", at, ms))

    def prog(self, qid: int, topic: str, at: datetime) -> None:
        key = (self.uid, qid, topic)
        # keep the most-recent solved_at
        if key not in self.progress or self.progress[key] < at:
            self.progress[key] = at

    def seed_solved(self, track: str, topic: str, qids: list[int],
                    wrong_before: int, avg_ms: int, spread_days: float,
                    accuracy_override: dict[int, bool] | None = None) -> None:
        ao = accuracy_override or {}
        n = len(qids)
        for i, qid in enumerate(qids):
            t = _days_ago(spread_days * (1 - i / max(n - 1, 1)))
            for j in range(wrong_before):
                ms = int(avg_ms * (0.6 + 0.8 * (j / max(wrong_before, 1))))
                self.sub(track, qid, False, t - timedelta(minutes=20 * (wrong_before - j)), ms)
            if ao.get(qid) is not False:
                self.sub(track, qid, True, t, avg_ms)
                self.prog(qid, topic, t)
            else:
                self.sub(track, qid, False, t, int(avg_ms * 0.9))

    async def flush(self, conn) -> None:
        print(f"  Flushing {len(self.submissions)} submissions + {len(self.progress)} progress rows…")
        # Bulk insert submissions via COPY
        await conn.copy_records_to_table(
            "submissions",
            records=self.submissions,
            columns=["user_id", "track", "question_id", "is_correct", "code", "submitted_at", "duration_ms"],
        )
        # Bulk upsert progress
        if self.progress:
            prog_rows = [(uid, qid, topic, at) for (uid, qid, topic), at in self.progress.items()]
            await conn.executemany(
                """INSERT INTO user_progress (user_id, question_id, topic, solved_at)
                   VALUES ($1, $2, $3, $4)
                   ON CONFLICT (user_id, question_id, topic) DO UPDATE SET solved_at=EXCLUDED.solved_at""",
                prog_rows,
            )


async def ensure_user(conn, uid: str, email: str, name: str, plan: str) -> str:
    """Create/update user; returns the actual UUID string used in DB."""
    pwd_hash, pwd_salt = _hash_password(PASSWORD)
    existing_id = await conn.fetchval("SELECT id FROM users WHERE email=$1", email)
    if existing_id:
        await conn.execute(
            "UPDATE users SET pwd_hash=$1, pwd_salt=$2, plan=$3, email_verified=TRUE WHERE email=$4",
            pwd_hash, pwd_salt, plan, email,
        )
        return str(existing_id)
    else:
        await conn.execute(
            """INSERT INTO users (id, email, name, pwd_hash, pwd_salt, plan, email_verified)
               VALUES ($1::uuid, $2, $3, $4, $5, $6, TRUE)""",
            uid, email, name, pwd_hash, pwd_salt, plan,
        )
        return uid


async def wipe_user(conn, uid: str) -> None:
    await conn.execute("DELETE FROM submissions WHERE user_id=$1::uuid", uid)
    await conn.execute("DELETE FROM user_progress WHERE user_id=$1::uuid", uid)
    await conn.execute(
        "DELETE FROM mock_session_questions WHERE session_id IN (SELECT id FROM mock_sessions WHERE user_id=$1::uuid)", uid
    )
    await conn.execute("DELETE FROM mock_sessions WHERE user_id=$1::uuid", uid)


# ─────────────────────────────────────────────────────────────────────────────
# FREE USER
# ─────────────────────────────────────────────────────────────────────────────
async def seed_free(conn) -> None:
    print("Seeding FREE user (matt.srini)…")
    uid = await ensure_user(conn, FREE_UID, "matt.srini@gmail.com", "Matt", "free")
    await wipe_user(conn, uid)
    b = Batch(uid)

    for i, qid in enumerate(SQL_EASY[:7]):
        t = _days_ago(4 - i * 0.4)
        b.sub(SQL, qid, True, t, 180_000 + i * 20_000)
        b.prog(qid, SQL, t)

    for i, qid in enumerate(SQL_EASY[7:10]):
        t = _days_ago(1.5 - i * 0.3)
        b.sub(SQL, qid, False, t - timedelta(minutes=25), 210_000)
        b.sub(SQL, qid, True, t, 350_000)
        b.prog(qid, SQL, t)

    b.sub(SQL, SQL_EASY[10], False, _hours_ago(2), 240_000)
    b.sub(SQL, SQL_EASY[11], True, _hours_ago(3), 195_000)
    b.prog(SQL_EASY[11], SQL, _hours_ago(3))

    await b.flush(conn)
    print("  FREE: 12 SQL easy solved, streak 2 days, 1 unsolved attempt")


# ─────────────────────────────────────────────────────────────────────────────
# PRO USER
# ─────────────────────────────────────────────────────────────────────────────
async def seed_pro(conn) -> None:
    print("Seeding PRO user (srinivas)…")
    uid = await ensure_user(conn, PRO_UID, "srinivas.assampally@gmail.com", "Srinivas", "pro")
    await wipe_user(conn, uid)
    b = Batch(uid)

    b.seed_solved(SQL, SQL, SQL_EASY[:32], wrong_before=0, avg_ms=190_000, spread_days=20)
    b.seed_solved(SQL, SQL, SQL_MED[:18],  wrong_before=1, avg_ms=290_000, spread_days=14)
    b.seed_solved(SQL, SQL, SQL_HARD[:4],  wrong_before=2, avg_ms=480_000, spread_days=6)
    for qid in SQL_HARD[4:7]:
        b.sub(SQL, qid, False, _days_ago(1.5), 380_000)
        b.sub(SQL, qid, False, _days_ago(1.5), 380_000)

    b.seed_solved(PY, PY, PY_EASY[:22], wrong_before=0, avg_ms=230_000, spread_days=16)
    b.seed_solved(PY, PY, PY_MED[:12],  wrong_before=1, avg_ms=380_000, spread_days=10)

    b.seed_solved(PYDAT, PYDAT, PYDAT_EASY[:10], wrong_before=1, avg_ms=260_000, spread_days=8)
    b.seed_solved(PYDAT, PYDAT, PYDAT_MED[:6],   wrong_before=2, avg_ms=420_000, spread_days=5)
    for qid in PYDAT_MED[6:10]:
        b.sub(PYDAT, qid, False, _days_ago(2), 400_000)

    b.sub(SQL, SQL_EASY[31], False, _hours_ago(5), 210_000)
    today_qid = PY_EASY[22]
    b.sub(PY, today_qid, True, _hours_ago(4), 260_000)
    b.prog(today_qid, PY, _hours_ago(4))

    await b.flush(conn)
    print("  PRO: SQL 32e/18m/4h · Python 22e/12m · Pandas 10e/6m, streak ~6 days")


# ─────────────────────────────────────────────────────────────────────────────
# ELITE USER
# ─────────────────────────────────────────────────────────────────────────────
async def seed_elite(conn) -> None:
    print("Seeding ELITE user (admin)…")
    uid = await ensure_user(conn, ELITE_UID, "admin@datathink.co", "Admin", "elite")
    await wipe_user(conn, uid)
    b = Batch(uid)

    b.seed_solved(SQL, SQL, SQL_EASY[:32], wrong_before=0, avg_ms=140_000, spread_days=30)
    b.seed_solved(SQL, SQL, SQL_MED[:28],  wrong_before=1, avg_ms=220_000, spread_days=25)
    b.seed_solved(SQL, SQL, SQL_HARD[:18], wrong_before=1, avg_ms=380_000, spread_days=18)
    for qid in SQL_HARD[18:22]:
        for _ in range(3):
            b.sub(SQL, qid, False, _days_ago(3), 420_000)

    b.seed_solved(PY, PY, PY_EASY[:28], wrong_before=0, avg_ms=160_000, spread_days=28)
    b.seed_solved(PY, PY, PY_MED[:20],  wrong_before=1, avg_ms=280_000, spread_days=22)
    b.seed_solved(PY, PY, PY_HARD[:10], wrong_before=2, avg_ms=450_000, spread_days=15)

    b.seed_solved(PYDAT, PYDAT, PYDAT_EASY[:20], wrong_before=0, avg_ms=180_000, spread_days=25)
    b.seed_solved(PYDAT, PYDAT, PYDAT_MED[:18],  wrong_before=1, avg_ms=310_000, spread_days=18)
    b.seed_solved(PYDAT, PYDAT, PYDAT_HARD[:8],  wrong_before=2, avg_ms=520_000, spread_days=10)
    for qid in PYDAT_MED[18:22]:
        for _ in range(4):
            b.sub(PYDAT, qid, False, _days_ago(5), 380_000)

    b.seed_solved(SPARK, SPARK, SPARK_EASY[:30], wrong_before=0, avg_ms=120_000, spread_days=20)
    b.seed_solved(SPARK, SPARK, SPARK_MED[:18],  wrong_before=1, avg_ms=190_000, spread_days=14)
    b.seed_solved(SPARK, SPARK, SPARK_HARD[:8],  wrong_before=2, avg_ms=280_000, spread_days=8)

    b.seed_solved(DE, DE, DE_EASY[:20], wrong_before=0, avg_ms=100_000, spread_days=18)
    b.seed_solved(DE, DE, DE_MED[:10],  wrong_before=1, avg_ms=160_000, spread_days=10)
    for qid in DE_MED[10:15]:
        for _ in range(2):
            b.sub(DE, qid, False, _days_ago(4), 200_000)

    b.seed_solved(STATS, STATS, STATS_EASY[:15], wrong_before=1, avg_ms=200_000, spread_days=10)
    b.seed_solved(STATS, STATS, STATS_MED[:8],   wrong_before=2, avg_ms=340_000, spread_days=6)

    # Ensure 12-day streak — one correct SQL solve per calendar day
    for d in range(12):
        qid = SQL_EASY[d]
        streak_t = datetime.now(UTC).replace(hour=10, minute=0, second=0, microsecond=0) - timedelta(days=d)
        b.sub(SQL, qid, True, streak_t, 130_000)
        b.prog(qid, SQL, streak_t)

    await b.flush(conn)

    # Mock sessions (few rows — execute individually)
    mock1_id = await conn.fetchval(
        """INSERT INTO mock_sessions (user_id, mode, track, difficulty, status, started_at, ended_at, time_limit_s)
           VALUES ($1::uuid, 'solo', 'sql', 'hard', 'completed', $2, $3, 1800) RETURNING id""",
        uid, _days_ago(8), _days_ago(8) + timedelta(minutes=28),
    )
    mock2_id = await conn.fetchval(
        """INSERT INTO mock_sessions (user_id, mode, track, difficulty, status, started_at, ended_at, time_limit_s)
           VALUES ($1::uuid, 'solo', 'python', 'medium', 'completed', $2, $3, 1800) RETURNING id""",
        uid, _days_ago(5), _days_ago(5) + timedelta(minutes=22),
    )
    mock3_id = await conn.fetchval(
        """INSERT INTO mock_sessions (user_id, mode, track, difficulty, status, started_at, ended_at, time_limit_s)
           VALUES ($1::uuid, 'solo', 'sql', 'medium', 'completed', $2, $3, 1800) RETURNING id""",
        uid, _days_ago(2), _days_ago(2) + timedelta(minutes=18),
    )

    mock_q_rows = []
    for pos, (qid, solved) in enumerate([(SQL_HARD[i], i < 5) for i in range(7)]):
        mock_q_rows.append((mock1_id, qid, "sql", solved, pos,
                            _days_ago(8) + timedelta(minutes=4 * (pos + 1)), 220 + pos * 30))
    for pos, (qid, solved) in enumerate([(PY_MED[i], i < 6) for i in range(7)]):
        mock_q_rows.append((mock2_id, qid, "python", solved, pos,
                            _days_ago(5) + timedelta(minutes=3 * (pos + 1)), 190 + pos * 20))
    for pos, (qid, solved) in enumerate([(SQL_MED[i], True) for i in range(7)]):
        mock_q_rows.append((mock3_id, qid, "sql", solved, pos,
                            _days_ago(2) + timedelta(minutes=2 * (pos + 1)), 155 + pos * 15))

    await conn.executemany(
        """INSERT INTO mock_session_questions
           (session_id, question_id, track, is_solved, position, submitted_at, time_spent_s)
           VALUES ($1, $2, $3, $4, $5, $6, $7)""",
        mock_q_rows,
    )

    print("  ELITE: SQL 32e/28m/18h · Python 28e/20m/10h · Pandas 20e/18m/8h")
    print("         PySpark 30e/18m/8h · DE 20e/10m · Stats 15e/8m")
    print("         3 mock sessions · 12-day streak")


async def main() -> None:
    print(f"Connecting to {DB_URL}…")
    conn = await asyncpg.connect(DB_URL)
    try:
        await seed_free(conn)
        await seed_pro(conn)
        await seed_elite(conn)
        print("\n✓ Done. Login credentials:")
        print("  FREE  — matt.srini@gmail.com / Test1234!")
        print("  PRO   — srinivas.assampally@gmail.com / Test1234!")
        print("  ELITE — admin@datathink.co / Test1234!")
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())


import asyncio
import hashlib
import os
import secrets
import sys
from datetime import UTC, datetime, timedelta

import asyncpg

DB_URL = os.environ.get("DB_URL", "postgresql://postgres:postgres@localhost:5432/sql_practice")
PASSWORD = "Test1234!"
ITERATIONS = 260_000

# ── User IDs ─────────────────────────────────────────────────────────────────
FREE_UID  = "17768671-42c7-4ac3-930c-5b149e572b34"   # matt.srini@gmail.com
PRO_UID   = "6f9797cd-f158-4313-825a-23707b9cc926"   # srinivas.assampally@gmail.com
ELITE_UID = "134883f7-237b-401b-8047-cbb5a4d53dee"   # admin@datathink.co

# ── Track db_topic values ─────────────────────────────────────────────────────
SQL   = "sql"
PY    = "python"
PYDAT = "python_data"
SPARK = "pyspark"
DE    = "data-engineering"
DM    = "data-modeling"
STATS = "statistics"

# ── Question IDs (first N per track/diff) ────────────────────────────────────
SQL_EASY   = list(range(11001, 11033))   # 32 easy
SQL_MED    = list(range(12001, 12035))   # 34 medium
SQL_HARD   = list(range(13001, 13030))   # 29 hard
PY_EASY    = list(range(21001, 21031))   # 30 easy
PY_MED     = list(range(22001, 22030))   # 29 medium
PY_HARD    = list(range(23001, 23025))   # 24 hard
PYDAT_EASY = list(range(31001, 31023))   # 22 easy
PYDAT_MED  = list(range(32001, 32032))   # 31 medium
PYDAT_HARD = list(range(33001, 33024))   # 23 hard
SPARK_EASY = list(range(41001, 41039))   # 38 easy
SPARK_MED  = list(range(42001, 42039))   # 38 medium
SPARK_HARD = list(range(43001, 43027))   # 26 hard
DE_EASY    = list(range(51001, 51031))   # 30 easy
DE_MED     = list(range(52001, 52031))   # 30 medium
DE_HARD    = list(range(53001, 53021))   # 20 hard
STATS_EASY = list(range(71001, 71029))   # 28 easy
STATS_MED  = list(range(72001, 72029))   # 28 medium


def _hash_password(password: str) -> tuple[str, str]:
    salt = secrets.token_hex(32)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        ITERATIONS,
    )
    return digest.hex(), salt


def _days_ago(n: float) -> datetime:
    return datetime.now(UTC) - timedelta(days=n)


def _hours_ago(n: float) -> datetime:
    return datetime.now(UTC) - timedelta(hours=n)


async def wipe_user(conn, uid: str) -> None:
    await conn.execute("DELETE FROM submissions WHERE user_id=$1::uuid", uid)
    await conn.execute("DELETE FROM user_progress WHERE user_id=$1::uuid", uid)
    await conn.execute("DELETE FROM mock_session_questions WHERE session_id IN (SELECT id FROM mock_sessions WHERE user_id=$1::uuid)", uid)
    await conn.execute("DELETE FROM mock_sessions WHERE user_id=$1::uuid", uid)


async def set_password(conn, uid: str) -> None:
    pwd_hash, pwd_salt = _hash_password(PASSWORD)
    await conn.execute(
        "UPDATE users SET pwd_hash=$1, pwd_salt=$2, email_verified=TRUE WHERE id=$3::uuid",
        pwd_hash, pwd_salt, uid
    )


async def set_plan(conn, uid: str, plan: str) -> None:
    await conn.execute("UPDATE users SET plan=$1 WHERE id=$2::uuid", plan, uid)


async def ensure_user(conn, uid: str, email: str, name: str, plan: str) -> None:
    """Create user with fixed UUID if not exists; set password + plan regardless."""
    pwd_hash, pwd_salt = _hash_password(PASSWORD)
    # Check if email already exists (may have a different UUID)
    existing_id = await conn.fetchval("SELECT id FROM users WHERE email=$1", email)
    if existing_id:
        # Email already in DB — just update password + plan on that row
        await conn.execute(
            "UPDATE users SET pwd_hash=$1, pwd_salt=$2, plan=$3, email_verified=TRUE, name=COALESCE(name, $4) WHERE email=$5",
            pwd_hash, pwd_salt, plan, name, email
        )
    else:
        await conn.execute(
            """INSERT INTO users (id, email, name, pwd_hash, pwd_salt, plan, email_verified)
               VALUES ($1::uuid, $2, $3, $4, $5, $6, TRUE)""",
            uid, email, name, pwd_hash, pwd_salt, plan
        )


async def add_submission(conn, uid: str, track: str, qid: int, is_correct: bool,
                         at: datetime, duration_ms: int) -> None:
    await conn.execute(
        """INSERT INTO submissions (user_id, track, question_id, is_correct, code, submitted_at, duration_ms)
           VALUES ($1::uuid, $2, $3, $4, '', $5, $6)""",
        uid, track, qid, is_correct, at, duration_ms
    )


async def add_progress(conn, uid: str, qid: int, topic: str, at: datetime) -> None:
    await conn.execute(
        """INSERT INTO user_progress (user_id, question_id, topic, solved_at)
           VALUES ($1::uuid, $2, $3, $4)
           ON CONFLICT (user_id, question_id, topic) DO UPDATE SET solved_at=EXCLUDED.solved_at""",
        uid, qid, topic, at
    )


async def seed_solved(conn, uid: str, track: str, topic: str, qids: list[int],
                      wrong_before: int, avg_ms: int, spread_days: float,
                      accuracy_override: dict[int, bool] | None = None) -> None:
    """
    Seed N correct solves, each optionally preceded by `wrong_before` wrong attempts.
    Times are spread over the last `spread_days` days.
    accuracy_override: {qid: False} to force a question to never be solved (still has wrong attempts).
    """
    ao = accuracy_override or {}
    n = len(qids)
    for i, qid in enumerate(qids):
        # Spread time across the period
        t = _days_ago(spread_days * (1 - i / max(n - 1, 1)))
        # Wrong attempts first
        for j in range(wrong_before):
            ms = int(avg_ms * (0.6 + 0.8 * (j / max(wrong_before, 1))))
            await add_submission(conn, uid, track, qid, False,
                                 t - timedelta(minutes=20 * (wrong_before - j)), ms)
        # Correct solve (unless overridden)
        if ao.get(qid) is not False:
            await add_submission(conn, uid, track, qid, True, t, avg_ms)
            await add_progress(conn, uid, qid, topic, t)
        else:
            # Only wrong — leave as attempted but unsolved
            ms = int(avg_ms * 0.9)
            await add_submission(conn, uid, track, qid, False, t, ms)


# ─────────────────────────────────────────────────────────────────────────────
# FREE USER — small number of SQL easy solves, 2-day streak
# Representative of a new user who's just getting started
# ─────────────────────────────────────────────────────────────────────────────
async def seed_free(conn) -> None:
    uid = FREE_UID
    print("Seeding FREE user (matt.srini)…")
    await ensure_user(conn, uid, "matt.srini@gmail.com", "Matt", "free")
    # If email existed with a different UUID, look up the real UID
    real_uid = await conn.fetchval("SELECT id FROM users WHERE email='matt.srini@gmail.com'") or uid
    uid = str(real_uid)
    await wipe_user(conn, uid)

    # 10 SQL easy solved — 7 on first try, 3 needed 1 wrong attempt first
    for i, qid in enumerate(SQL_EASY[:7]):
        t = _days_ago(4 - i * 0.4)
        await add_submission(conn, uid, SQL, qid, True, t, 180_000 + i * 20_000)
        await add_progress(conn, uid, qid, SQL, t)

    for i, qid in enumerate(SQL_EASY[7:10]):
        t = _days_ago(1.5 - i * 0.3)
        await add_submission(conn, uid, SQL, qid, False, t - timedelta(minutes=25), 210_000)
        await add_submission(conn, uid, SQL, qid, True, t, 350_000)
        await add_progress(conn, uid, qid, SQL, t)

    # 1 wrong attempt on a question not solved yet — shows partial effort
    await add_submission(conn, uid, SQL, SQL_EASY[10], False, _hours_ago(2), 240_000)

    # Streak: solved today + yesterday → 2 days
    await add_submission(conn, uid, SQL, SQL_EASY[11], True, _hours_ago(3), 195_000)
    await add_progress(conn, uid, SQL_EASY[11], SQL, _hours_ago(3))
    # already solved SQL_EASY[0..9] covers yesterday via _days_ago(0.5..1.5)

    print("  FREE: 12 SQL easy solved, streak 2 days, 1 unsolved attempt")


# ─────────────────────────────────────────────────────────────────────────────
# PRO USER — multi-track, good SQL + Python progress, 6-day streak
# Representative of a committed user mid-way through prep
# ─────────────────────────────────────────────────────────────────────────────
async def seed_pro(conn) -> None:
    uid = PRO_UID
    print("Seeding PRO user (srinivas)…")
    await ensure_user(conn, uid, "srinivas.assampally@gmail.com", "Srinivas", "pro")
    real_uid = await conn.fetchval("SELECT id FROM users WHERE email='srinivas.assampally@gmail.com'") or uid
    uid = str(real_uid)
    await wipe_user(conn, uid)

    # SQL: all 32 easy + 18 medium + 4 hard
    await seed_solved(conn, uid, SQL, SQL, SQL_EASY[:32], wrong_before=0, avg_ms=190_000, spread_days=20)
    await seed_solved(conn, uid, SQL, SQL, SQL_MED[:18],  wrong_before=1, avg_ms=290_000, spread_days=14)
    # 4 hard — struggled more (2 wrong before each)
    await seed_solved(conn, uid, SQL, SQL, SQL_HARD[:4],  wrong_before=2, avg_ms=480_000, spread_days=6)
    # A few hard that were only attempted wrongly
    for qid in SQL_HARD[4:7]:
        for _ in range(2):
            await add_submission(conn, uid, SQL, qid, False, _days_ago(1.5), 380_000)

    # Python: 22 easy + 12 medium
    await seed_solved(conn, uid, PY, PY, PY_EASY[:22], wrong_before=0, avg_ms=230_000, spread_days=16)
    await seed_solved(conn, uid, PY, PY, PY_MED[:12],  wrong_before=1, avg_ms=380_000, spread_days=10)

    # Pandas: 10 easy + 6 medium — slower progress
    await seed_solved(conn, uid, PYDAT, PYDAT, PYDAT_EASY[:10], wrong_before=1, avg_ms=260_000, spread_days=8)
    await seed_solved(conn, uid, PYDAT, PYDAT, PYDAT_MED[:6],   wrong_before=2, avg_ms=420_000, spread_days=5)
    # A few more wrong attempts on Pandas medium (concept weakness)
    for qid in PYDAT_MED[6:10]:
        await add_submission(conn, uid, PYDAT, qid, False, _days_ago(2), 400_000)

    # Streak: must have solves on today + 5 consecutive days
    # The spread above covers multiple days; add explicit today/yesterday solves
    await add_submission(conn, uid, SQL, SQL_EASY[31], False, _hours_ago(5), 210_000)
    # Ensure today is covered by recent data from spread — add a Python solve today
    today_qid = PY_EASY[22]
    await add_submission(conn, uid, PY, today_qid, True, _hours_ago(4), 260_000)
    await add_progress(conn, uid, today_qid, PY, _hours_ago(4))

    print("  PRO: SQL 32e/18m/4h · Python 22e/12m · Pandas 10e/6m, streak ~6 days")


# ─────────────────────────────────────────────────────────────────────────────
# ELITE USER — heavy cross-track history, mock sessions, 12-day streak
# Representative of a power user close to interview-ready
# ─────────────────────────────────────────────────────────────────────────────
async def seed_elite(conn) -> None:
    uid = ELITE_UID
    print("Seeding ELITE user (admin)…")
    await ensure_user(conn, uid, "admin@datathink.co", "Admin", "elite")
    real_uid = await conn.fetchval("SELECT id FROM users WHERE email='admin@datathink.co'") or uid
    uid = str(real_uid)
    await wipe_user(conn, uid)

    # SQL: all easy, most medium, good hard coverage
    await seed_solved(conn, uid, SQL, SQL, SQL_EASY[:32], wrong_before=0, avg_ms=140_000, spread_days=30)
    await seed_solved(conn, uid, SQL, SQL, SQL_MED[:28],  wrong_before=1, avg_ms=220_000, spread_days=25)
    await seed_solved(conn, uid, SQL, SQL, SQL_HARD[:18], wrong_before=1, avg_ms=380_000, spread_days=18)
    # A handful of hard SQL still struggling with
    for qid in SQL_HARD[18:22]:
        for _ in range(3):
            await add_submission(conn, uid, SQL, qid, False, _days_ago(3), 420_000)

    # Python: strong
    await seed_solved(conn, uid, PY, PY, PY_EASY[:28], wrong_before=0, avg_ms=160_000, spread_days=28)
    await seed_solved(conn, uid, PY, PY, PY_MED[:20],  wrong_before=1, avg_ms=280_000, spread_days=22)
    await seed_solved(conn, uid, PY, PY, PY_HARD[:10], wrong_before=2, avg_ms=450_000, spread_days=15)

    # Pandas: good but weak on certain medium
    await seed_solved(conn, uid, PYDAT, PYDAT, PYDAT_EASY[:20], wrong_before=0, avg_ms=180_000, spread_days=25)
    await seed_solved(conn, uid, PYDAT, PYDAT, PYDAT_MED[:18],  wrong_before=1, avg_ms=310_000, spread_days=18)
    await seed_solved(conn, uid, PYDAT, PYDAT, PYDAT_HARD[:8],  wrong_before=2, avg_ms=520_000, spread_days=10)
    # Pandas weak area — many wrong on a few
    for qid in PYDAT_MED[18:22]:
        for _ in range(4):
            await add_submission(conn, uid, PYDAT, qid, False, _days_ago(5), 380_000)

    # PySpark: decent progress
    await seed_solved(conn, uid, SPARK, SPARK, SPARK_EASY[:30], wrong_before=0, avg_ms=120_000, spread_days=20)
    await seed_solved(conn, uid, SPARK, SPARK, SPARK_MED[:18],  wrong_before=1, avg_ms=190_000, spread_days=14)
    await seed_solved(conn, uid, SPARK, SPARK, SPARK_HARD[:8],  wrong_before=2, avg_ms=280_000, spread_days=8)

    # Data Engineering: decent easy, some medium
    await seed_solved(conn, uid, DE, DE, DE_EASY[:20], wrong_before=0, avg_ms=100_000, spread_days=18)
    await seed_solved(conn, uid, DE, DE, DE_MED[:10],  wrong_before=1, avg_ms=160_000, spread_days=10)
    # Weak concepts in DE medium
    for qid in DE_MED[10:15]:
        for _ in range(2):
            await add_submission(conn, uid, DE, qid, False, _days_ago(4), 200_000)

    # Statistics: started recently
    await seed_solved(conn, uid, STATS, STATS, STATS_EASY[:15], wrong_before=1, avg_ms=200_000, spread_days=10)
    await seed_solved(conn, uid, STATS, STATS, STATS_MED[:8],   wrong_before=2, avg_ms=340_000, spread_days=6)

    # Ensure solid 12-day streak: add explicit solves across today through 11 days back
    for d in range(12):
        qid = SQL_EASY[d % 32]
        streak_t = _days_ago(d) - timedelta(hours=2)
        # Don't add duplicate progress rows — just add a submission for each day
        # (mark_solved uses ON CONFLICT so re-inserting is safe; but progress already
        #  exists for these qids. The insights query checks submission dates for streak.)
        await add_submission(conn, uid, SQL, 11098 + d, True, streak_t, 150_000 + d * 5000)
        # Use high IDs that may not exist in the catalog — that's OK, streak
        # only cares about submission dates, not question validity.
        # Actually, let's use real IDs from the already-seeded pool above.

    # Better: ensure each of the last 12 calendar days has at least one correct submission
    # by inserting a small SQL easy solve per day using IDs we definitely seeded above
    for d in range(12):
        # pick a unique qid offset per day
        qid = SQL_EASY[d]  # 11001..11012 — already seeded as correct, just add one more submission
        streak_t = datetime.now(UTC).replace(hour=10, minute=0, second=0, microsecond=0) - timedelta(days=d)
        await add_submission(conn, uid, SQL, qid, True, streak_t, 130_000)
        # update progress timestamp to reflect this day
        await add_progress(conn, uid, qid, SQL, streak_t)

    # Mock sessions — 3 completed
    mock1_id = await conn.fetchval(
        """INSERT INTO mock_sessions (user_id, mode, track, difficulty, status, started_at, ended_at, time_limit_s)
           VALUES ($1::uuid, 'solo', 'sql', 'hard', 'completed', $2, $3, 1800) RETURNING id""",
        uid, _days_ago(8), _days_ago(8) + timedelta(minutes=28)
    )
    mock2_id = await conn.fetchval(
        """INSERT INTO mock_sessions (user_id, mode, track, difficulty, status, started_at, ended_at, time_limit_s)
           VALUES ($1::uuid, 'solo', 'python', 'medium', 'completed', $2, $3, 1800) RETURNING id""",
        uid, _days_ago(5), _days_ago(5) + timedelta(minutes=22)
    )
    mock3_id = await conn.fetchval(
        """INSERT INTO mock_sessions (user_id, mode, track, difficulty, status, started_at, ended_at, time_limit_s)
           VALUES ($1::uuid, 'solo', 'sql', 'medium', 'completed', $2, $3, 1800) RETURNING id""",
        uid, _days_ago(2), _days_ago(2) + timedelta(minutes=18)
    )

    # Mock session questions for mock1 (SQL hard) — 7 questions, 5 solved
    mock_q_ids = [(SQL_HARD[i], i < 5) for i in range(7)]
    for pos, (qid, solved) in enumerate(mock_q_ids):
        await conn.execute(
            """INSERT INTO mock_session_questions (session_id, question_id, track, is_solved, position, submitted_at, time_spent_s)
               VALUES ($1, $2, 'sql', $3, $4, $5, $6)""",
            mock1_id, qid, solved, pos,
            _days_ago(8) + timedelta(minutes=4 * (pos + 1)),
            220 + pos * 30
        )

    # Mock session questions for mock2 (Python medium) — 7 questions, 6 solved
    mock2_q_ids = [(PY_MED[i], i < 6) for i in range(7)]
    for pos, (qid, solved) in enumerate(mock2_q_ids):
        await conn.execute(
            """INSERT INTO mock_session_questions (session_id, question_id, track, is_solved, position, submitted_at, time_spent_s)
               VALUES ($1, $2, 'python', $3, $4, $5, $6)""",
            mock2_id, qid, solved, pos,
            _days_ago(5) + timedelta(minutes=3 * (pos + 1)),
            190 + pos * 20
        )

    # Mock session questions for mock3 (SQL medium) — 7 questions, 7 solved
    mock3_q_ids = [(SQL_MED[i], True) for i in range(7)]
    for pos, (qid, solved) in enumerate(mock3_q_ids):
        await conn.execute(
            """INSERT INTO mock_session_questions (session_id, question_id, track, is_solved, position, submitted_at, time_spent_s)
               VALUES ($1, $2, 'sql', $3, $4, $5, $6)""",
            mock3_id, qid, solved, pos,
            _days_ago(2) + timedelta(minutes=2 * (pos + 1)),
            155 + pos * 15
        )

    print("  ELITE: SQL 32e/28m/18h · Python 28e/20m/10h · Pandas 20e/18m/8h")
    print("         PySpark 30e/18m/8h · DE 20e/10m · Stats 15e/8m")
    print("         3 mock sessions · 12-day streak")


async def main() -> None:
    print(f"Connecting to {DB_URL}…")
    conn = await asyncpg.connect(DB_URL)
    try:
        await seed_free(conn)
        await seed_pro(conn)
        await seed_elite(conn)

        print("\n✓ Done. Login credentials:")
        print("  FREE  — matt.srini@gmail.com / Test1234!")
        print("  PRO   — srinivas.assampally@gmail.com / Test1234!")
        print("  ELITE — admin@datathink.co / Test1234!")
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
