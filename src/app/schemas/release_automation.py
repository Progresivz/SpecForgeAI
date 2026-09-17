from datetime import datetime
from pydantic import BaseModel, ConfigDict

class ReleaseAutomationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    project_id: int
    release_id: int
    release_notes: str
    test_suite: str
    ai_review: str
    decision: str
    score: int
    evidence: str
    created_at: datetime
