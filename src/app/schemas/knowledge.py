from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class KnowledgeEntryCreate(BaseModel):
    source_type: str = Field(min_length=1, max_length=50)
    source_id: str = Field(min_length=1, max_length=100)
    title: str = Field(min_length=1, max_length=300)
    content: str = Field(default="", max_length=20000)
    tags: list[str] = Field(default_factory=list, max_length=50)


class KnowledgeEntryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    source_type: str
    source_id: str
    title: str
    content: str
    tags: list[str] = []
    updated_at: datetime


class KnowledgeSearchResult(KnowledgeEntryResponse):
    score: float
    matched_terms: list[str]


class KnowledgeSearchResponse(BaseModel):
    query: str
    total: int
    results: list[KnowledgeSearchResult]


class KnowledgeIndexResponse(BaseModel):
    project_id: int
    indexed: int
    removed: int
