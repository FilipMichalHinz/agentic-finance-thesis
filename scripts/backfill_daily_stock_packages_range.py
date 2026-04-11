#!/usr/bin/env python3
import os
import subprocess
import sys
from pathlib import Path

from dotenv import load_dotenv

sys.path.append("/tmp/psycopg_tmp")
import psycopg  # type: ignore


def main() -> int:
    repo = Path(__file__).resolve().parents[1]
    load_dotenv(repo / ".env")

    project_ref = (repo / "supabase/.temp/project-ref").read_text().strip()
    password = os.environ["SUPABASE_DB_PASSWORD"]
    user = f"postgres.{project_ref}"
    host = "aws-1-eu-west-1.pooler.supabase.com"
    conninfo = f"postgresql://{user}:{password}@{host}:5432/postgres?sslmode=require"

    with psycopg.connect(conninfo) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                select distinct event_timestamp::date
                from public.market_prices_daily
                where event_timestamp::date between date '2025-04-11' and date '2026-04-08'
                order by 1
                """
            )
            dates = [row[0].isoformat() for row in cur.fetchall()]

    print(f"Backfilling {len(dates)} trading dates...")
    for idx, day in enumerate(dates, start=1):
        result = subprocess.run(
            [sys.executable, "scripts/build_daily_stock_packages.py", "--package-date", day],
            cwd=repo,
            text=True,
            capture_output=True,
        )
        if result.returncode != 0:
            print(f"FAILED {day}")
            if result.stdout:
                print(result.stdout)
            if result.stderr:
                print(result.stderr)
            return result.returncode

        if idx % 10 == 0 or idx == 1 or idx == len(dates):
            print(f"Completed {idx}/{len(dates)} through {day}")

    print("Backfill complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
