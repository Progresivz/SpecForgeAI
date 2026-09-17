import json
import logging
import os
from logging.handlers import RotatingFileHandler


class RequestIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, "request_id"):
            record.request_id = "-"
        return True


class JsonFormatter(logging.Formatter):
    def format(self, record):
        payload = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": getattr(record, "request_id", "-"),
        }
        return json.dumps(payload, default=str, separators=(",", ":"))


def configure_logging() -> None:
    level = os.getenv("LOG_LEVEL", "INFO").upper()
    fmt = os.getenv("LOG_FORMAT", "text").lower()
    handlers = []
    stream = logging.StreamHandler()
    if fmt == "json":
        stream.setFormatter(JsonFormatter())
    else:
        stream.setFormatter(logging.Formatter(
            "%(asctime)s %(levelname)s %(name)s request_id=%(request_id)s %(message)s"
        ))
    stream.addFilter(RequestIdFilter())
    handlers.append(stream)
    log_file = os.getenv("LOG_FILE", "").strip()
    if log_file:
        fh = RotatingFileHandler(log_file, maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8")
        fh.addFilter(RequestIdFilter())
        fh.setFormatter(JsonFormatter() if fmt == "json" else logging.Formatter(
            "%(asctime)s %(levelname)s %(name)s request_id=%(request_id)s %(message)s"
        ))
        handlers.append(fh)
    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(getattr(logging, level, logging.INFO))
    for handler in handlers:
        root.addHandler(handler)
