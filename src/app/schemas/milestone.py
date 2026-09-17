from datetime import date

from pydantic import BaseModel, ConfigDict, Field


class MilestoneCreate(BaseModel):
    title: str = Field(min_length=1, max_length=100)
    description: str = Field(default="", max_length=300)
    due_date: date


class MilestoneUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=300)
    due_date: date | None = None
    completed: bool | None = None


class MilestoneResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str
    due_date: date
    completed: bool
