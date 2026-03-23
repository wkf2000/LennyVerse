from __future__ import annotations

from pathlib import Path

from data_pipeline.config import Settings
from data_pipeline.db import Database

MIGRATIONS_DIR = Path("data-pipeline/sql/migrations")


def main() -> None:
    settings = Settings()
    db = Database(settings.require_db_url())

    migration_files = sorted(MIGRATIONS_DIR.glob("*.sql"))
    if not migration_files:
        raise FileNotFoundError(f"No migrations found in {MIGRATIONS_DIR}")

    for migration_file in migration_files:
        db.execute_sql_file(migration_file)
        print(f"[ok] applied migration: {migration_file.name}")


if __name__ == "__main__":
    main()
