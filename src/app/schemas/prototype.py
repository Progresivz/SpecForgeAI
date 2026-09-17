from pydantic import BaseModel, ConfigDict, Field

class PrototypeComponentCreate(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    component_type: str = Field(min_length=1, max_length=50)
    description: str = ''
    interaction: str = ''
    position: int = Field(default=0, ge=0)
class PrototypeComponentResponse(PrototypeComponentCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
class PrototypeScreenCreate(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    route: str = Field(default='/', max_length=200)
    purpose: str = ''
    layout: str = Field(default='standard', max_length=100)
    position: int = Field(default=0, ge=0)
    components: list[PrototypeComponentCreate] = Field(default_factory=list)
class PrototypeScreenResponse(PrototypeScreenCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    components: list[PrototypeComponentResponse] = Field(default_factory=list)
class PrototypeFlowCreate(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    from_screen: str = Field(min_length=1, max_length=150)
    to_screen: str = Field(min_length=1, max_length=150)
    trigger: str = ''
    notes: str = ''
class PrototypeFlowResponse(PrototypeFlowCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
class PrototypeDesignCreate(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    description: str = ''
    style_notes: str = ''
    screens: list[PrototypeScreenCreate] = Field(default_factory=list)
    flows: list[PrototypeFlowCreate] = Field(default_factory=list)
class PrototypeDesignResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    project_id: int
    name: str
    description: str
    style_notes: str
    screens: list[PrototypeScreenResponse] = Field(default_factory=list)
    flows: list[PrototypeFlowResponse] = Field(default_factory=list)
class PrototypeSpecResponse(BaseModel):
    project_id: int
    project_name: str
    summary_markdown: str
