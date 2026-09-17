"""AI integration smoke test.

Default mode is configuration-only and never calls a paid AI provider.
Use --live to make one real provider request. This can incur provider cost.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import settings
from app.services.production_validation_service import _ai_config_check


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--live", action="store_true", help="make one real AI request")
    args = parser.parse_args()

    configured, message = _ai_config_check()
    result = {"provider": settings.AI_PROVIDER, "model": settings.OPENAI_MODEL if settings.AI_PROVIDER == "openai" else settings.LOCAL_LLM_MODEL, "configured": configured, "message": message}
    if not configured:
        print(json.dumps(result, indent=2))
        return 1

    if args.live:
        from app.services.ai_service import _openai_generate, _local_generate
        prompt = "Reply with exactly: SpecForge AI operational smoke test passed."
        system = "You are performing a connectivity smoke test. Do not add commentary."
        if settings.AI_PROVIDER.lower() == "openai":
            text = _openai_generate(prompt, system, settings.OPENAI_MODEL, 0, 32)
        elif settings.AI_PROVIDER.lower() == "local":
            text = _local_generate(prompt, system, settings.LOCAL_LLM_MODEL, 0, 32)
        else:
            raise RuntimeError(f"Unsupported provider: {settings.AI_PROVIDER}")
        result["live_test"] = {"passed": bool(text.strip()), "response": text[:500]}
        print(json.dumps(result, indent=2))
        return 0 if text.strip() else 2

    result["live_test"] = "not run; use --live for one real provider request"
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
