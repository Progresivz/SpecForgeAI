import argparse
import os
import subprocess
import sys
import uuid

from sqlalchemy.engine import make_url


def run(command, env=None):
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


def main():
    parser = argparse.ArgumentParser(
        description="Restore a PostgreSQL backup into a temporary database and verify it."
    )
    parser.add_argument("backup", help="Path to a PostgreSQL custom-format backup")
    args = parser.parse_args()

    from app.core.config import settings

    source = make_url(settings.DATABASE_URL)

    if source.get_backend_name() != "postgresql":
        raise RuntimeError("restore verification requires PostgreSQL")

    if not source.host or not source.username:
        raise RuntimeError("DATABASE_URL is missing PostgreSQL connection details")

    database_name = f"specforge_restore_test_{uuid.uuid4().hex[:10]}"

    env = os.environ.copy()
    env["PGPASSWORD"] = source.password or ""

    common = [
        "--host", source.host,
        "--port", str(source.port or 5432),
        "--username", source.username,
    ]

    try:
        print(f"Creating temporary database: {database_name}")

        run(
            [
                "createdb",
                *common,
                database_name,
            ],
            env=env,
        )

        print("Restoring backup...")

        run(
            [
                "pg_restore",
                "--no-owner",
                "--no-privileges",
                "--exit-on-error",
                "--dbname", database_name,
                args.backup,
            ],
            env=env,
        )

        output = run(
            [
                "psql",
                *common,
                "--dbname", database_name,
                "--tuples-only",
                "--no-align",
                "--command",
                "SELECT count(*) FROM information_schema.tables "
                "WHERE table_schema='public';",
            ],
            env=env,
        )

        table_count = int(output.strip())

        if table_count <= 0:
            raise RuntimeError("Restore completed but no public tables were found")

        print(f"RESTORE VERIFIED: {table_count} public tables restored")
        print("STATUS: success")

    finally:
        print(f"Dropping temporary database: {database_name}")
        cleanup = subprocess.run(
            [
                "dropdb",
                "--if-exists",
                *common,
                database_name,
            ],
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )

        if cleanup.returncode != 0:
            print(
                "WARNING: temporary database cleanup failed:",
                cleanup.stderr.strip(),
                file=sys.stderr,
            )


if __name__ == "__main__":
    main()

