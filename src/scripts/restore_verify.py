from pathlib import Path
import argparse
import os
import subprocess
import sys
import uuid


APP_ROOT = Path(__file__).resolve().parents[1]
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))


def run(command: list[str], env: dict[str, str]) -> str:
    result = subprocess.run(
        command,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    if result.returncode != 0:
        raise RuntimeError(
            result.stderr.strip()
            or result.stdout.strip()
            or f"Command failed with exit code {result.returncode}"
        )

    return result.stdout.strip()


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Restore a PostgreSQL custom-format backup into a "
            "temporary database and verify the restored schema."
        )
    )
    parser.add_argument(
        "backup",
        help="Path to the PostgreSQL custom-format backup",
    )
    args = parser.parse_args()

    from app.core.config import settings
    from sqlalchemy.engine import make_url

    source = make_url(settings.DATABASE_URL)

    if source.get_backend_name() != "postgresql":
        raise RuntimeError(
            f"restore verification requires PostgreSQL, got {source.get_backend_name()!r}"
        )

    if not source.host:
        raise RuntimeError("DATABASE_URL is missing the PostgreSQL host")

    if not source.username:
        raise RuntimeError("DATABASE_URL is missing the PostgreSQL username")

    backup = Path(args.backup)

    if not backup.is_file():
        raise RuntimeError(f"Backup file not found: {backup}")

    if backup.stat().st_size == 0:
        raise RuntimeError(f"Backup file is empty: {backup}")

    temporary_database = (
        f"specforge_restore_test_{uuid.uuid4().hex[:10]}"
    )

    env = os.environ.copy()
    env["PGPASSWORD"] = source.password or ""

    host = source.host
    port = str(source.port or 5432)
    username = source.username

    connection_args = [
        "--host",
        host,
        "--port",
        port,
        "--username",
        username,
    ]

    try:
        print(f"Creating temporary database: {temporary_database}")

        run(
            [
                "createdb",
                *connection_args,
                temporary_database,
            ],
            env,
        )

        print("Restoring backup...")

        run(
            [
                "pg_restore",
                "--no-owner",
                "--no-privileges",
                "--exit-on-error",
                *connection_args,
                "--dbname",
                temporary_database,
                str(backup),
            ],
            env,
        )

        table_count_output = run(
            [
                "psql",
                *connection_args,
                "--dbname",
                temporary_database,
                "--tuples-only",
                "--no-align",
                "--command",
                (
                    "SELECT count(*) "
                    "FROM information_schema.tables "
                    "WHERE table_schema = 'public';"
                ),
            ],
            env,
        )

        table_count = int(table_count_output.strip())

        if table_count <= 0:
            raise RuntimeError(
                "Restore completed but no public tables were found"
            )

        print(
            f"RESTORE VERIFIED: {table_count} public tables restored"
        )
        print("STATUS: success")

    finally:
        print(
            f"Dropping temporary database: {temporary_database}"
        )

        cleanup = subprocess.run(
            [
                "dropdb",
                "--if-exists",
                *connection_args,
                temporary_database,
            ],
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )

        if cleanup.returncode != 0:
            print(
                "WARNING: temporary database cleanup failed: "
                + (
                    cleanup.stderr.strip()
                    or cleanup.stdout.strip()
                    or "unknown error"
                ),
                file=sys.stderr,
            )


if __name__ == "__main__":
    main()
