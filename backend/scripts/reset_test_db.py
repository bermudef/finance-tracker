"""Drop and recreate the schema for a TEST database, then apply migrations.

Guardrail: this script refuses to run against a database whose name does not
contain "test". It exists so destructive resets are always explicit and can
never accidentally target a development or production database.

Usage:

    DATABASE_URL=postgresql+asyncpg://finance:...@localhost:5432/finance_test_db \
        ./venv/bin/python scripts/reset_test_db.py
"""
from __future__ import annotations

import asyncio
import os
import sys

from sqlalchemy import text


def _database_name(url: str) -> str:
    return url.rsplit("/", 1)[-1].split("?")[0]


async def main() -> None:
    url = os.environ.get("DATABASE_URL")
    if not url:
        sys.exit("DATABASE_URL must be set explicitly. Refusing to guess.")
    db_name = _database_name(url)
    if "test" not in db_name:
        sys.exit(
            f"Refusing to reset '{db_name}' — only databases whose name "
            "contains 'test' can be reset by this script."
        )

    from sqlalchemy.ext.asyncio import create_async_engine

    engine = create_async_engine(url)
    async with engine.begin() as conn:
        await conn.execute(text("DROP SCHEMA public CASCADE"))
        await conn.execute(text("CREATE SCHEMA public"))
    await engine.dispose()
    print(f"Reset schema on '{db_name}'")


if __name__ == "__main__":
    asyncio.run(main())
