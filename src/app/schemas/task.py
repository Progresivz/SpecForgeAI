from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


TaskType = Literal["development", "design", "testing", "documentation", "devops", "research", "maintenance"]
TaskPriority = Literal["low", "medium", "high", "critical"]
TaskStatus = Literal["todo", "in_progress", "blocked", "done", "cancelled"]


class DevelopmentTaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(default="")
    task_type: TaskType = "development"
    priority: TaskPriority = "medium"
    status: TaskStatus = "todo"
    estimate_hours: int | None = Field(default=None, ge=1, le=10000)
    due_date: date | None = None
    milestone_id: int | None = None
    requirement_id: int | None = None
    user_story_id: int | None = None
    maintenance_item_id: int | None = None
    depends_on_task_id: int | None = None
    notes: str | None = None
    completed: bool = False

    @model_validator(mode="after")
    def sync_status(self):
        if self.completed:
            self.status = "done"
        elif self.status == "done":
            self.completed = True
        return self


class DevelopmentTaskUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    task_type: TaskType | None = None
    priority: TaskPriority | None = None
    status: TaskStatus | None = None
    estimate_hours: int | None = Field(default=None, ge=1, le=10000)
    due_date: date | None = None
    milestone_id: int | None = None
    requirement_id: int | None = None
    user_story_id: int | None = None
    maintenance_item_id: int | None = None
    depends_on_task_id: int | None = None
    notes: str | None = None
    completed: bool | None = None


class DevelopmentTaskResponse(DevelopmentTaskCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    project_id: int
    task_key: str


class TaskDependency(BaseModel):
    task_id: int
    task_key: str
    title: str
    status: str


class TaskPlanResponse(BaseModel):
    project_id: int
    project_name: str
    generated_at: date
    total_tasks: int
    completed_tasks: int
    blocked_tasks: int
    total_estimate_hours: int
    remaining_estimate_hours: int
    critical_path_hours: int
    recommended_tasks: list[DevelopmentTaskResponse]
    dependencies: list[TaskDependency]


class TaskApplyResponse(BaseModel):
    project_id: int
    created_count: int
    skipped_count: int
    warnings: list[str] = Field(default_factory=list)
