"""Create a timestamped database backup.

SQLite: copies the database safely using SQLite's online backup API.
PostgreSQL: invokes pg_dump; pg_dump must be installed and available on PATH.
"""
import os
import shutil
import sqlite3
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse


def main() -> int:
    database_url = os.getenv("DATABASE_URL", "sqlite:///./specforge.db")
    out_dir = Path(os.getenv("BACKUP_DIR", "./backups"))
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    parsed = urlparse(database_url)
    if parsed.scheme.startswith("sqlite"):
        raw = database_url.split("///", 1)[-1]
        source = Path(raw).resolve()
        destination = out_dir / f"specforge-{stamp}.db"
        if not source.exists():
            print(f"SQLite database not found: {source}", file=sys.stderr)
            return 2
        src = sqlite3.connect(source)
        dst = sqlite3.connect(destination)
        try:
            src.backup(dst)
        finally:
            dst.close()
            src.close()
        print(destination)
        return 0

    if parsed.scheme.startswith("postgresql"):
        destination = out_dir / f"specforge-{stamp}.dump"
        command = ["pg_dump", "--format=custom", "--file", str(destination), database_url]
        try:
            subprocess.run(command, check=True)
        except FileNotFoundError:
            print("pg_dump was not found on PATH.", file=sys.stderr)
            return 2
        print(destination)
        return 0

    print(f"Unsupported DATABASE_URL scheme: {parsed.scheme}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
