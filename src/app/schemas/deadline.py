from datetime import date

from pydantic import BaseModel, ConfigDict, Field, model_validator


class DeadlineCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=2000)
    deadline_type: str = Field(default="milestone", min_length=1, max_length=30)
    due_date: date
    estimated_work_days: int = Field(default=1, ge=1, le=3650)
    completed: bool = False
    alert_days_before: int = Field(default=3, ge=0, le=365)

    @model_validator(mode="after")
    def validate_completed_date(self):
        return self


class DeadlineUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    deadline_type: str | None = Field(default=None, min_length=1, max_length=30)
    due_date: date | None = None
    estimated_work_days: int | None = Field(default=None, ge=1, le=3650)
    completed: bool | None = None
    alert_days_before: int | None = Field(default=None, ge=0, le=365)


class DeadlineResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str
    deadline_type: str
    due_date: date
    estimated_work_days: int
    completed: bool
    alert_days_before: int


class DeadlineCalendarItem(BaseModel):
    id: int | None
    title: str
    deadline_type: str
    due_date: date
    completed: bool
    days_remaining: int
    overdue: bool
    alert: bool


class DeadlineAlert(BaseModel):
    deadline_id: int
    title: str
    due_date: date
    days_remaining: int
    severity: str
    message: str


class DeadlineReportResponse(BaseModel):
    project_id: int
    project_name: str
    as_of: date
    target_date: date
    project_days_remaining: int
    project_overdue: bool
    completion_percent: float
    remaining_work_days: int
    estimated_finish: date
    predicted_delay_days: int
    likely_to_meet_deadline: bool
    active_deadlines: int
    overdue_deadlines: int
    upcoming_deadlines: list[DeadlineCalendarItem]
    alerts: list[DeadlineAlert]
