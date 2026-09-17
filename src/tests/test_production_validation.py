from pathlib import Path

from app.services.production_validation_service import summarize, validate_environment


def test_validation_summary_is_structured():
    checks = validate_environment(include_tools=False)
    result = summarize(checks)
    assert isinstance(result["checks"], list)
    assert "ready" in result
    assert all({"name", "status", "message", "critical"} <= set(item) for item in result["checks"])


def test_backup_directory_check_uses_configured_path(tmp_path, monkeypatch):
    monkeypatch.setattr("app.services.production_validation_service.settings.BACKUP_DIR", str(tmp_path))
    checks = validate_environment(include_tools=False)
    backup = next(c for c in checks if c.name == "backup.directory")
    assert backup.status == "pass"
    assert Path(tmp_path).exists()
