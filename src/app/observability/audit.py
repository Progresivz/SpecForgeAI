import json
import logging
from datetime import datetime, timezone

logger = logging.getLogger("specforge.audit")


def audit_event(event: str, *, request_id: str = "-", user_id=None, project_id=None, **details):
    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event": event,
        "request_id": request_id,
        "user_id": user_id,
        "project_id": project_id,
        **details,
    }
    logger.info(json.dumps(payload, default=str, separators=(",", ":")))
