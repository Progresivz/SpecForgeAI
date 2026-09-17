"""Non-destructive SpecForge AI production preflight.

Use --strict to return a non-zero exit code on any failed check.
Use --no-tools to skip PATH checks for Git/PostgreSQL client utilities.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.production_validation_service import summarize, validate_environment


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--no-tools", action="store_true")
    args = parser.parse_args()

    result = summarize(validate_environment(include_tools=not args.no_tools))
    print(json.dumps(result, indent=2))
    if args.strict and result["failed"]:
        return 1
    if result["critical_failures"]:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
