import json
import logging

from app.observability.audit import audit_event
from app.observability.metrics import Metrics
from app.observability import scheduler


def test_metrics_prometheus_output():
    m = Metrics()
    m.observe_request("GET", "/health", 200, 0.01)
    m.observe_request("GET", "/health", 500, 0.02)

    text = m.prometheus()

    assert "specforge_http_requests_total" in text
    assert 'method="GET",path="/health",status="200"' in text
    assert 'method="GET",path="/health",status="500"' in text
    assert "specforge_http_errors_total" in text
    assert 'method="GET",path="/health"' in text


def test_metrics_count_5xx_errors_only():
    m = Metrics()

    m.observe_request("GET", "/health", 200, 0.01)
    m.observe_request("GET", "/api/test", 404, 0.01)
    m.observe_request("POST", "/api/test", 500, 0.02)
    m.observe_request("GET", "/api/test", 503, 0.03)

    text = m.prometheus()

    assert 'method="POST",path="/api/test"} 1' in text
    assert 'method="GET",path="/api/test"} 1' in text


def test_audit_event_redacts_sensitive_values(caplog):
    secret = "super-secret-api-key-123"

    with caplog.at_level(logging.INFO, logger="specforge.audit"):
        audit_event(
            "security_test",
            request_id="req-123",
            user_id=42,
            password="password-value",
            api_key=secret,
            access_token="access-token-value",
            nested={
                "client_secret": "nested-secret",
                "safe_value": "visible",
            },
        )

    assert caplog.records

    payload = json.loads(caplog.records[-1].message)

    assert payload["event"] == "security_test"
    assert payload["request_id"] == "req-123"
    assert payload["user_id"] == 42
    assert payload["password"] == "[REDACTED]"
    assert payload["api_key"] == "[REDACTED]"
    assert payload["access_token"] == "[REDACTED]"
    assert payload["nested"]["client_secret"] == "[REDACTED]"
    assert payload["nested"]["safe_value"] == "visible"

    serialized = caplog.records[-1].message
    assert secret not in serialized
    assert "password-value" not in serialized
    assert "access-token-value" not in serialized


def test_scheduler_disabled_does_not_start():
    scheduler.stop_scheduler()

    scheduler.start_scheduler(enabled=False)

    assert scheduler._scheduler is None


def test_scheduler_registers_health_check_job():
    scheduler.stop_scheduler()

    scheduler.start_scheduler(
        enabled=True,
        interval_minutes=15,
        backup_enabled=False,
    )

    try:
        assert scheduler._scheduler is not None

        jobs = scheduler._scheduler.get_jobs()
        job_ids = {job.id for job in jobs}

        assert "health-check" in job_ids
        assert "database-backup" not in job_ids
    finally:
        scheduler.stop_scheduler()


def test_scheduler_registers_backup_job():
    scheduler.stop_scheduler()

    scheduler.start_scheduler(
        enabled=True,
        interval_minutes=15,
        backup_enabled=True,
        backup_interval_hours=24,
    )

    try:
        assert scheduler._scheduler is not None

        jobs = scheduler._scheduler.get_jobs()
        job_ids = {job.id for job in jobs}

        assert "health-check" in job_ids
        assert "database-backup" in job_ids
    finally:
        scheduler.stop_scheduler()


def test_scheduler_stop_is_safe():
    scheduler.stop_scheduler()
    scheduler.stop_scheduler()

    assert scheduler._scheduler is None


def test_maintenance_job_records_success(monkeypatch):
    class FakeSession:
        def __init__(self):
            self.closed = False

        def execute(self, statement):
            assert "SELECT 1" in str(statement)

        def close(self):
            self.closed = True

    fake_session = FakeSession()

    class FakeSessionFactory:
        def __call__(self):
            return fake_session

    events = []

    monkeypatch.setattr(
        scheduler.database_session,
        "SessionLocal",
        FakeSessionFactory(),
    )

    monkeypatch.setattr(
        scheduler,
        "audit_event",
        lambda event, **details: events.append((event, details)),
    )

    scheduler._maintenance_job()

    assert fake_session.closed is True
    assert events
    assert events[0][0] == "scheduled_health_check"
    assert events[0][1]["status"] == "ok"


def test_prometheus_metrics_endpoint_requires_authentication():
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)

    response = client.get("/observability/metrics")

    assert response.status_code == 401


def test_prometheus_metrics_endpoint_returns_metrics(monkeypatch):
    from fastapi.testclient import TestClient
    from app.main import app
    from app.api import observability
    from app.auth.security import get_current_user

    monkeypatch.setattr(
        observability.metrics,
        "prometheus",
        lambda: (
            "# HELP specforge_test_metric Test metric\n"
            "# TYPE specforge_test_metric counter\n"
            "specforge_test_metric 1\n"
        ),
    )

    app.dependency_overrides[get_current_user] = lambda: {"id": 1}

    try:
        client = TestClient(app)

        response = client.get(
            "/observability/metrics",
            headers={"Authorization": "Bearer test-token"},
        )

        assert response.status_code == 200
        assert response.headers["content-type"].startswith(
            "text/plain; version=0.0.4"
        )
        assert "specforge_test_metric 1" in response.text
    finally:
        app.dependency_overrides.clear()


def test_request_id_filter_adds_default_request_id():
    import logging
    from app.core.logging_config import RequestIdFilter

    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="hello",
        args=(),
        exc_info=None,
    )

    assert not hasattr(record, "request_id")

    RequestIdFilter().filter(record)

    assert record.request_id == "-"


def test_request_id_filter_preserves_existing_request_id():
    import logging
    from app.core.logging_config import RequestIdFilter

    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="hello",
        args=(),
        exc_info=None,
    )
    record.request_id = "req-123"

    RequestIdFilter().filter(record)

    assert record.request_id == "req-123"


def test_json_formatter_includes_request_context():
    import json
    import logging
    from app.core.logging_config import JsonFormatter

    record = logging.LogRecord(
        name="specforge.test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="test message",
        args=(),
        exc_info=None,
    )
    record.request_id = "req-456"

    payload = json.loads(JsonFormatter().format(record))

    assert payload["level"] == "INFO"
    assert payload["logger"] == "specforge.test"
    assert payload["message"] == "test message"
    assert payload["request_id"] == "req-456"
    assert "timestamp" in payload


def test_configure_logging_json_mode(monkeypatch):
    import logging
    from app.core.logging_config import configure_logging

    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("LOG_FORMAT", "json")
    monkeypatch.delenv("LOG_FILE", raising=False)

    configure_logging()

    root = logging.getLogger()

    assert root.level == logging.DEBUG
    assert len(root.handlers) == 1

    handler = root.handlers[0]

    assert handler.formatter is not None

    try:
        assert handler.formatter.__class__.__name__ == "JsonFormatter"
    finally:
        for handler in root.handlers[:]:
            root.removeHandler(handler)
            handler.close()


def test_configure_logging_text_mode(monkeypatch):
    import logging
    from app.core.logging_config import configure_logging

    monkeypatch.setenv("LOG_LEVEL", "WARNING")
    monkeypatch.setenv("LOG_FORMAT", "text")
    monkeypatch.delenv("LOG_FILE", raising=False)

    configure_logging()

    root = logging.getLogger()

    assert root.level == logging.WARNING
    assert len(root.handlers) == 1

    handler = root.handlers[0]

    assert handler.formatter is not None

    try:
        assert handler.formatter.__class__.__name__ == "Formatter"
    finally:
        for handler in root.handlers[:]:
            root.removeHandler(handler)
            handler.close()
