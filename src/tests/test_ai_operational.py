from types import SimpleNamespace

from app.services import ai_service


def test_ai_service_pipeline_with_mocked_openai(monkeypatch):
    monkeypatch.setattr(ai_service.settings, "AI_PROVIDER", "openai")
    monkeypatch.setattr(ai_service.settings, "OPENAI_MODEL", "gpt-5.6-luna")
    monkeypatch.setattr(ai_service, "_openai_generate", lambda *args, **kwargs: "AI smoke response")
    project = SimpleNamespace(
        name="Operational Test",
        description="Validate AI pipeline",
        status="active",
        target_date=None,
        knowledge_entries=[],
    )
    result = ai_service.generate(None, project, "Return a concise validation response.", include_knowledge=False)
    assert result.provider == "openai"
    assert result.model == "gpt-5.6-luna"
    assert result.content == "AI smoke response"
    assert result.knowledge_used == 0
