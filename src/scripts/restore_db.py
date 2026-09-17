"""Restore a SpecForge database backup.

Usage: python scripts/restore_db.py <backup-file>
SQLite restores by replacing the configured DB file.
PostgreSQL restores a custom pg_dump archive with pg_restore --clean --if-exists.
"""
import os
import shutil
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: python scripts/restore_db.py <backup-file>", file=sys.stderr)
        return 2
    backup = Path(sys.argv[1]).resolve()
    if not backup.exists():
        print(f"Backup not found: {backup}", file=sys.stderr)
        return 2
    database_url = os.getenv("DATABASE_URL", "sqlite:///./specforge.db")
    parsed = urlparse(database_url)
    if parsed.scheme.startswith("sqlite"):
        target = Path(database_url.split("///", 1)[-1]).resolve()
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(backup, target)
        print(target)
        return 0
    if parsed.scheme.startswith("postgresql"):
        subprocess.run(["pg_restore", "--clean", "--if-exists", "--dbname", database_url, str(backup)], check=True)
        print("PostgreSQL restore completed")
        return 0
    print(f"Unsupported DATABASE_URL scheme: {parsed.scheme}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
