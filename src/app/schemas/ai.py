from typing import Literal
from pydantic import BaseModel, Field


AIProvider = Literal["openai", "local"]


class AIGenerateRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=20000)
    system_prompt: str | None = Field(default=None, max_length=10000)
    provider: AIProvider | None = None
    model: str | None = Field(default=None, max_length=200)
    temperature: float = Field(default=0.2, ge=0, le=2)
    max_output_tokens: int = Field(default=2000, ge=1, le=16000)
    include_knowledge: bool = True
    knowledge_query: str | None = Field(default=None, max_length=1000)


class AIGenerateResponse(BaseModel):
    provider: str
    model: str
    content: str
    knowledge_used: int = 0


class AIArtifactRequest(BaseModel):
    artifact_type: Literal[
        "srs", "design", "database", "api", "test_plan",
        "user_manual", "installation", "maintenance", "release_notes",
        "changelog", "proposal", "requirements", "user_stories",
        "development_tasks", "code_review"
    ]
    instructions: str | None = Field(default=None, max_length=10000)
    provider: AIProvider | None = None
    model: str | None = Field(default=None, max_length=200)
    temperature: float = Field(default=0.2, ge=0, le=2)
    max_output_tokens: int = Field(default=4000, ge=1, le=20000)


class AIArtifactResponse(BaseModel):
    project_id: int
    artifact_type: str
    provider: str
    model: str
    content: str
    knowledge_used: int
