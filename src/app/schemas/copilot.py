from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


CopilotMode = Literal[
    "auto",
    "general",
    "health",
    "requirements",
    "planning",
    "tasks",
    "deadlines",
    "maintenance",
    "architecture",
    "testing",
    "release",
]


class CopilotChatRequest(BaseModel):
    project_id: int
    message: str = Field(min_length=1, max_length=10000)
    mode: CopilotMode = "auto"
    include_context: bool = True
    conversation_id: int | None = None


class CopilotAction(BaseModel):
    title: str
    reason: str
    priority: Literal["critical", "high", "medium", "low"] = "medium"
    area: str


class CopilotMessageResponse(BaseModel):
    id: int
    role: Literal["user", "assistant"]
    content: str
    mode: CopilotMode
    created_at: datetime


class CopilotConversationResponse(BaseModel):
    id: int
    project_id: int
    title: str
    created_at: datetime
    updated_at: datetime
    messages: list[CopilotMessageResponse] = Field(default_factory=list)


class CopilotChatResponse(BaseModel):
    project_id: int
    message: str
    response: str
    mode: CopilotMode
    conversation_id: int
    context: dict[str, Any] = Field(default_factory=dict)
    suggested_actions: list[CopilotAction] = Field(default_factory=list)