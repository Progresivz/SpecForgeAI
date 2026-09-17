from typing import Literal
from pydantic import BaseModel, ConfigDict, Field

DocumentType = Literal['proposal','srs','design','database','api','test_plan','user_manual','installation','maintenance','release_notes','changelog']

class DocumentationDocumentCreate(BaseModel):
    document_type: DocumentType
    title: str = Field(min_length=1, max_length=200)
    content_markdown: str = ''
class DocumentationDocumentResponse(DocumentationDocumentCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
class DocumentationSetCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str = ''
    documents: list[DocumentationDocumentCreate] = Field(default_factory=list)
class DocumentationSetResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    project_id: int
    name: str
    description: str
    documents: list[DocumentationDocumentResponse] = Field(default_factory=list)
class DocumentationExportResponse(BaseModel):
    project_id: int
    document_type: str
    title: str
    format: str
    content: str
