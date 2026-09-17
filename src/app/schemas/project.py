from datetime import date

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: str = Field(default="", max_length=500)
    start_date: date
    target_date: date

    @model_validator(mode="after")
    def validate_dates(self):
        if self.target_date < self.start_date:
            raise ValueError("target_date cannot be before start_date")
        return self


class ProjectUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=500)
    start_date: date | None = None
    target_date: date | None = None
    status: str | None = Field(default=None, max_length=20)


class ProjectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str
    start_date: date
    target_date: date
    status: str
