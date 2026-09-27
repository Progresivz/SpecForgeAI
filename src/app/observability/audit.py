import json
import logging
from datetime import datetime, timezone

logger = logging.getLogger("specforge.audit")
logger.setLevel(logging.INFO)

_SENSITIVE_KEYS = {
    "password",
    "passwd",
    "secret",
    "secret_key",
    "api_key",
    "apikey",
    "access_token",
    "refresh_token",
    "authorization",
    "cookie",
    "set_cookie",
    "token",
    "private_key",
}


def _is_sensitive_key(key: str) -> bool:
    normalized = key.lower().replace("-", "_")
    return (
        normalized in _SENSITIVE_KEYS
        or normalized.endswith("_token")
        or normalized.endswith("_secret")
        or normalized.endswith("_api_key")
    )


def _redact(value, *, key: str | None = None):
    if key is not None and _is_sensitive_key(key):
        return "[REDACTED]"

    if isinstance(value, dict):
        return {
            str(k): _redact(v, key=str(k))
            for k, v in value.items()
        }

    if isinstance(value, (list, tuple)):
        return [_redact(item) for item in value]

    return value


def audit_event(
    event: str,
    *,
    request_id: str = "-",
    user_id=None,
    project_id=None,
    **details,
):
    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event": event,
        "request_id": request_id,
        "user_id": user_id,
        "project_id": project_id,
        **details,
    }

    safe_payload = _redact(payload)
    logger.info(
        json.dumps(
            safe_payload,
            default=str,
            separators=(",", ":"),
        )
    )

