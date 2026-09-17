from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field

class FindingUpdate(BaseModel):
    status: str = Field(pattern='^(open|accepted|resolved|dismissed)$')

class FindingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id:int; project_id:int; source:str; severity:str; category:str; title:str; description:str; file_path:str|None; status:str; linked_task_id:int|None; linked_maintenance_id:int|None; created_at:datetime; updated_at:datetime

class TestResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id:int; project_id:int; requirement_id:int|None; task_id:int|None; title:str; test_type:str; priority:str; steps:str; expected_result:str; status:str; source:str; created_at:datetime

class ActivityResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id:int; project_id:int; actor_user_id:int|None; action:str; entity_type:str|None; entity_id:int|None; summary:str; details:str|None; created_at:datetime
