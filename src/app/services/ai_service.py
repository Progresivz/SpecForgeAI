import json
import urllib.error
import urllib.request
from dataclasses import dataclass

from app.core.config import settings
from app.models.project import Project
from app.services.knowledge_service import search_entries


@dataclass
class AIResult:
    provider: str
    model: str
    content: str
    knowledge_used: int = 0


ARTIFACT_INSTRUCTIONS = {
    "proposal": "Create a concise professional project proposal with overview, objectives, scope, stakeholders, milestones, risks, and success criteria.",
    "srs": "Create a Software Requirements Specification with business requirements, functional and non-functional requirements, user stories, use cases, acceptance criteria, and traceability considerations.",
    "requirements": "Derive clear, testable functional and non-functional requirements from the project context. Avoid inventing unsupported business facts; mark assumptions explicitly.",
    "user_stories": "Create implementation-ready user stories with roles, goals, benefits, acceptance criteria, and dependencies.",
    "design": "Create a software design document covering architecture, components, data flow, security considerations, interfaces, and deployment context.",
    "database": "Create a database design narrative covering entities, tables, columns, relationships, keys, constraints, and indexing considerations.",
    "api": "Create API documentation covering resources, endpoints, authentication, request/response expectations, errors, and examples where supported by the context.",
    "test_plan": "Create a practical test plan covering functional, integration, security, regression, performance, and acceptance testing.",
    "user_manual": "Create a user manual organized around the actual project workflow and known features.",
    "installation": "Create an installation and setup guide covering prerequisites, configuration, database initialization, and application startup.",
    "maintenance": "Create a maintenance guide covering known maintenance items, operational checks, security updates, dependencies, and technical debt.",
    "release_notes": "Create release notes summarizing the supplied project changes, improvements, fixes, risks, and upgrade notes.",
    "changelog": "Create a structured changelog from the supplied project and Git context. Do not claim changes that are not supported by the context.",
    "development_tasks": "Turn the supplied project context into prioritized, actionable development tasks with dependencies and acceptance criteria.",
    "code_review": "Review the supplied project/Git context for correctness, maintainability, security, and regression risks. Give prioritized findings and recommendations.",
}


def _project_context(project: Project, knowledge_results) -> str:
    lines = [
        f"Project: {project.name}",
        f"Description: {project.description or ''}",
        f"Status: {project.status}",
        f"Target date: {project.target_date or ''}",
    ]
    for result in knowledge_results:
        entry = result[2] if isinstance(result, tuple) else result
        lines.append(f"\n[{entry.source_type}] {entry.title}\n{entry.content}")
    return "\n".join(lines)


def _openai_generate(
    prompt: str,
    system_prompt: str,
    model: str,
    temperature: float,
    max_output_tokens: int,
) -> str:
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise RuntimeError(
            "OpenAI provider requires the 'openai' package. Install requirements.txt."
        ) from exc

    if not settings.OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY is not configured.")

    client = OpenAI(
        api_key=settings.OPENAI_API_KEY,
        base_url=settings.OPENAI_BASE_URL or None,
    )

    response = client.responses.create(
        model=model,
        instructions=system_prompt,
        input=prompt,
        max_output_tokens=max_output_tokens,
    )

    text = getattr(response, "output_text", None)
    if text:
        return text

    # Defensive fallback for SDK response-shape changes.
    output = getattr(response, "output", []) or []
    parts = []

    for item in output:
        for content in getattr(item, "content", []) or []:
            value = getattr(content, "text", None)
            if value:
                parts.append(value)

    return "\n".join(parts).strip()


def _local_generate(prompt: str, system_prompt: str, model: str, temperature: float, max_output_tokens: int) -> str:
    if not settings.LOCAL_LLM_URL:
        raise RuntimeError("LOCAL_LLM_URL is not configured.")
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ],
        "temperature": temperature,
        "max_tokens": max_output_tokens,
    }
    request = urllib.request.Request(
        settings.LOCAL_LLM_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=settings.LOCAL_LLM_TIMEOUT_SECONDS) as response:
            data = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as exc:
        raise RuntimeError(f"Local LLM request failed: {exc}") from exc
    # OpenAI-compatible local servers normally return choices[0].message.content.
    try:
        return data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        if isinstance(data.get("response"), str):
            return data["response"]
        raise RuntimeError("Local LLM returned an unsupported response format.")


def generate(db, project: Project, prompt: str, system_prompt: str | None = None,
             provider: str | None = None, model: str | None = None,
             temperature: float = 0.2, max_output_tokens: int = 2000,
             include_knowledge: bool = True, knowledge_query: str | None = None) -> AIResult:
    provider = provider or settings.AI_PROVIDER
    model = model or (settings.OPENAI_MODEL if provider == "openai" else settings.LOCAL_LLM_MODEL)
    system_prompt = system_prompt or (
        "You are SpecForge AI, an SDLC assistant. Use only the supplied project context. "
        "Distinguish facts from assumptions. Prefer structured, actionable output."
    )
    results = []
    if include_knowledge:
        entries = list(project.knowledge_entries or [])
        if knowledge_query:
            results = search_entries(entries, knowledge_query, limit=settings.AI_KNOWLEDGE_LIMIT)
        else:
            results = [(0, [], e) for e in entries[: settings.AI_KNOWLEDGE_LIMIT]]
    context = _project_context(project, results)
    full_prompt = f"PROJECT CONTEXT:\n{context}\n\nUSER REQUEST:\n{prompt}"
    if provider == "openai":
        content = _openai_generate(full_prompt, system_prompt, model, temperature, max_output_tokens)
    elif provider == "local":
        content = _local_generate(full_prompt, system_prompt, model, temperature, max_output_tokens)
    else:
        raise RuntimeError(f"Unsupported AI provider: {provider}")
    return AIResult(provider=provider, model=model, content=content, knowledge_used=len(results))


def generate_artifact(db, project: Project, artifact_type: str, instructions: str | None = None,
                      **kwargs) -> AIResult:
    base = ARTIFACT_INSTRUCTIONS[artifact_type]
    prompt = base
    if instructions:
        prompt += f"\n\nAdditional instructions:\n{instructions}"
    return generate(db, project, prompt, knowledge_query=artifact_type, **kwargs)
