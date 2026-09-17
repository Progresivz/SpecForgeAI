from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class TraceLinkCreate(BaseModel):
    source_type: str = Field(min_length=1, max_length=50)
    source_id: int | None = None
    target_type: str = Field(min_length=1, max_length=50)
    target_id: int | None = None
    relation: str = Field(default="implements", max_length=40)
    confidence: int = Field(default=100, ge=0, le=100)
    notes: str | None = None


class TraceLinkResponse(TraceLinkCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    created_at: datetime


class ReleaseCreate(BaseModel):
    version: str = Field(min_length=1, max_length=50)
    name: str = Field(min_length=1, max_length=200)
    description: str = ""
    target_date: datetime | None = None


class ReleaseUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    status: str | None = None
    target_date: datetime | None = None


class ReleaseResponse(ReleaseCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    status: str
    readiness_score: int
    gate_status: str
    gate_report: str
    created_at: datetime
    updated_at: datetime