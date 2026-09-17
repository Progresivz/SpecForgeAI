from datetime import datetime
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field

AIArtifactStatus = Literal["draft", "applied", "archived"]

class AIArtifactResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    project_id: int
    artifact_type: str
    title: str
    content: str
    provider: str
    model: str
    status: str
    target_type: str | None = None
    target_id: str | None = None
    created_at: datetime
    updated_at: datetime

class AIArtifactUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=300)
    content: str | None = None
    status: AIArtifactStatus | None = None

class AIArtifactApplyRequest(BaseModel):
    target_type: Literal[
        "knowledge", "documentation", "requirements", "maintenance", "database", "prototype"
    ]
    target_id: str | None = None
    title: str | None = Field(default=None, max_length=300)
