"""Verify that a SpecForge backup file exists and is readable."""
import argparse
import gzip
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("backup")
    args = parser.parse_args()
    path = Path(args.backup)
    if not path.is_file() or path.stat().st_size == 0:
        raise SystemExit("Backup missing or empty")
    if path.suffix == ".gz":
        with gzip.open(path, "rb") as fh:
            fh.read(16)
    elif path.suffix == ".json":
        json.loads(path.read_text(encoding="utf-8"))
    else:
        with path.open("rb") as fh:
            fh.read(16)
    print(f"Backup verification passed: {path} ({path.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
