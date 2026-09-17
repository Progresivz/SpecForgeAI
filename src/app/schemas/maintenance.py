from datetime import date
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field

ItemType = Literal["bug", "feature_request", "technical_debt", "security", "dependency_update", "refactoring"]
Severity = Literal["low", "medium", "high", "critical"]
Priority = Literal["low", "medium", "high", "urgent"]
Status = Literal["open", "in_progress", "resolved", "closed", "deferred"]

class MaintenanceItemCreate(BaseModel):
    item_type: ItemType = "bug"
    title: str = Field(min_length=1, max_length=200)
    description: str = ""
    severity: Severity = "medium"
    priority: Priority = "medium"
    status: Status = "open"
    affected_area: str | None = Field(default=None, max_length=200)
    source: str | None = Field(default=None, max_length=200)
    effort: str | None = Field(default=None, max_length=20)
    resolution: str | None = None
    due_date: date | None = None

class MaintenanceItemUpdate(BaseModel):
    item_type: ItemType | None = None
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    severity: Severity | None = None
    priority: Priority | None = None
    status: Status | None = None
    affected_area: str | None = Field(default=None, max_length=200)
    source: str | None = Field(default=None, max_length=200)
    effort: str | None = Field(default=None, max_length=20)
    resolution: str | None = None
    due_date: date | None = None

class MaintenanceItemResponse(MaintenanceItemCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    project_id: int

class MaintenanceSummary(BaseModel):
    total: int
    open: int
    in_progress: int
    resolved: int
    critical: int
    high: int
    bugs: int
    feature_requests: int
    technical_debt: int
    security_items: int
    dependency_updates: int
    refactoring_items: int

class MaintenanceReportResponse(BaseModel):
    project_id: int
    project_name: str
    summary: MaintenanceSummary
    priorities: list[MaintenanceItemResponse]
    recommendations: list[str]

class RefactoringRecommendation(BaseModel):
    priority: Priority
    area: str
    reason: str
    recommendation: str
    expected_benefit: str
