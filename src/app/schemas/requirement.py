from pydantic import BaseModel, ConfigDict, Field, model_validator


class AcceptanceCriterionBase(BaseModel):
    criterion: str = Field(min_length=1, max_length=2000)
    is_met: bool = False


class AcceptanceCriterionCreate(AcceptanceCriterionBase):
    pass


class AcceptanceCriterionResponse(AcceptanceCriterionBase):
    model_config = ConfigDict(from_attributes=True)
    id: int


class RequirementBase(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1)
    requirement_type: str = Field(default="functional", max_length=30)
    priority: str = Field(default="medium", max_length=20)
    status: str = Field(default="draft", max_length=20)
    rationale: str | None = None
    source: str | None = Field(default=None, max_length=200)


class RequirementCreate(RequirementBase):
    acceptance_criteria: list[AcceptanceCriterionCreate] = Field(default_factory=list)


class RequirementUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, min_length=1)
    requirement_type: str | None = Field(default=None, max_length=30)
    priority: str | None = Field(default=None, max_length=20)
    status: str | None = Field(default=None, max_length=20)
    rationale: str | None = None
    source: str | None = Field(default=None, max_length=200)


class RequirementResponse(RequirementBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    requirement_id: str
    acceptance_criteria: list[AcceptanceCriterionResponse] = Field(default_factory=list)


class UserStoryCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    as_a: str = Field(min_length=1, max_length=100)
    i_want: str = Field(min_length=1)
    so_that: str = Field(min_length=1)
    priority: str = Field(default="medium", max_length=20)
    status: str = Field(default="draft", max_length=20)


class UserStoryUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    as_a: str | None = Field(default=None, min_length=1, max_length=100)
    i_want: str | None = Field(default=None, min_length=1)
    so_that: str | None = Field(default=None, min_length=1)
    priority: str | None = Field(default=None, max_length=20)
    status: str | None = Field(default=None, max_length=20)


class UserStoryResponse(UserStoryCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    story_id: str


class UseCaseCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    actor: str = Field(min_length=1, max_length=100)
    goal: str = Field(min_length=1)
    preconditions: str | None = None
    main_flow: str = Field(min_length=1)
    alternate_flows: str | None = None
    postconditions: str | None = None


class UseCaseUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    actor: str | None = Field(default=None, min_length=1, max_length=100)
    goal: str | None = Field(default=None, min_length=1)
    preconditions: str | None = None
    main_flow: str | None = Field(default=None, min_length=1)
    alternate_flows: str | None = None
    postconditions: str | None = None


class UseCaseResponse(UseCaseCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    use_case_id: str


class TraceabilityLinkCreate(BaseModel):
    requirement_id: int
    user_story_id: int | None = None
    use_case_id: int | None = None
    coverage: str = Field(default="covered", max_length=20)
    notes: str | None = None

    @model_validator(mode="after")
    def validate_target(self):
        if self.user_story_id is None and self.use_case_id is None:
            raise ValueError("At least one traceability target is required")
        return self


class TraceabilityLinkResponse(TraceabilityLinkCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int


class SRSResponse(BaseModel):
    project_id: int
    project_name: str
    summary_markdown: str
