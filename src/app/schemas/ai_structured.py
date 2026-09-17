from datetime import date
from typing import Literal
from pydantic import BaseModel, Field, ConfigDict

StructuredType = Literal["requirements", "user_stories", "database", "prototype", "maintenance", "development_tasks"]

class StructuredAIRequest(BaseModel):
    artifact_type: StructuredType
    instructions: str | None = Field(default=None, max_length=10000)
    provider: Literal["openai", "local"] | None = None
    model: str | None = Field(default=None, max_length=200)
    temperature: float = Field(default=0.1, ge=0, le=1)
    max_output_tokens: int = Field(default=6000, ge=1, le=20000)
    include_knowledge: bool = True

class AcceptanceCriterionInput(BaseModel):
    criterion: str = Field(min_length=1, max_length=2000)

class RequirementInput(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1, max_length=10000)
    requirement_type: Literal["functional", "nonfunctional"] = "functional"
    priority: Literal["low", "medium", "high", "critical"] = "medium"
    status: Literal["draft", "approved", "implemented", "verified"] = "draft"
    rationale: str | None = None
    source: str | None = Field(default=None, max_length=200)
    acceptance_criteria: list[AcceptanceCriterionInput] = Field(default_factory=list)

class UserStoryInput(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    as_a: str = Field(min_length=1, max_length=100)
    i_want: str = Field(min_length=1, max_length=5000)
    so_that: str = Field(min_length=1, max_length=5000)
    priority: Literal["low", "medium", "high", "critical"] = "medium"
    status: Literal["draft", "ready", "in_progress", "done"] = "draft"

class DatabaseColumnInput(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    data_type: str = Field(min_length=1, max_length=50)
    nullable: bool = True
    primary_key: bool = False
    unique: bool = False
    default_value: str | None = Field(default=None, max_length=200)
    description: str | None = None

class DatabaseTableInput(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: str | None = None
    columns: list[DatabaseColumnInput] = Field(default_factory=list)

class DatabaseRelationshipInput(BaseModel):
    from_table: str = Field(min_length=1, max_length=100)
    from_column: str = Field(min_length=1, max_length=100)
    to_table: str = Field(min_length=1, max_length=100)
    to_column: str = Field(min_length=1, max_length=100)
    cardinality: Literal["one-to-one", "one-to-many", "many-to-one", "many-to-many"] = "many-to-one"
    on_delete: Literal["CASCADE", "SET NULL", "RESTRICT", "NO ACTION"] = "CASCADE"
    notes: str | None = None

class DatabaseInput(BaseModel):
    name: str = Field(default="AI Generated Database Design", max_length=200)
    target_dialect: Literal["postgresql", "mysql", "sqlite", "sqlserver"] = "postgresql"
    notes: str | None = None
    tables: list[DatabaseTableInput] = Field(default_factory=list)
    relationships: list[DatabaseRelationshipInput] = Field(default_factory=list)

class PrototypeComponentInput(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    component_type: str = Field(min_length=1, max_length=50)
    description: str = ""
    interaction: str = ""

class PrototypeScreenInput(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    route: str = Field(default="/", max_length=200)
    purpose: str = ""
    layout: str = Field(default="standard", max_length=100)
    components: list[PrototypeComponentInput] = Field(default_factory=list)

class PrototypeFlowInput(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    from_screen: str = Field(min_length=1, max_length=150)
    to_screen: str = Field(min_length=1, max_length=150)
    trigger: str = ""
    notes: str = ""

class PrototypeInput(BaseModel):
    name: str = Field(default="AI Generated Prototype", max_length=150)
    description: str = ""
    style_notes: str = ""
    screens: list[PrototypeScreenInput] = Field(default_factory=list)
    flows: list[PrototypeFlowInput] = Field(default_factory=list)

class MaintenanceInput(BaseModel):
    item_type: Literal["bug", "feature_request", "technical_debt", "security", "dependency_update", "refactoring"] = "bug"
    title: str = Field(min_length=1, max_length=200)
    description: str = ""
    severity: Literal["low", "medium", "high", "critical"] = "medium"
    priority: Literal["low", "medium", "high", "urgent"] = "medium"
    status: Literal["open", "in_progress", "resolved", "closed", "deferred"] = "open"
    affected_area: str | None = Field(default=None, max_length=200)
    source: str | None = Field(default="AI analysis", max_length=200)
    effort: str | None = Field(default=None, max_length=20)
    due_date: date | None = None

class DevelopmentTaskInput(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str = ""
    task_type: Literal["development", "design", "testing", "documentation", "devops", "research", "maintenance"] = "development"
    priority: Literal["low", "medium", "high", "critical"] = "medium"
    status: Literal["todo", "in_progress", "blocked", "done", "cancelled"] = "todo"
    estimate_hours: int | None = Field(default=None, ge=1, le=10000)
    due_date: date | None = None
    milestone_id: int | None = None
    requirement_id: int | None = None
    user_story_id: int | None = None
    maintenance_item_id: int | None = None
    depends_on_task_id: int | None = None
    notes: str | None = None
    completed: bool = False

class StructuredAIResponse(BaseModel):
    project_id: int
    artifact_type: str
    provider: str
    model: str
    validation_passed: bool
    item_count: int
    data: dict
    assumptions: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

class StructuredApplyRequest(BaseModel):
    artifact_type: StructuredType
    data: dict
    replace_existing: bool = False

class StructuredApplyResponse(BaseModel):
    project_id: int
    artifact_type: str
    created_count: int
    replaced_existing: bool
    warnings: list[str] = Field(default_factory=list)
