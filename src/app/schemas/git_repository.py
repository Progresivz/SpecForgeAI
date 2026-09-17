from datetime import datetime
from pydantic import BaseModel, Field

class GitRepositoryCreate(BaseModel):
    repo_path: str = Field(min_length=1, max_length=1000)
    default_branch: str = Field(default="main", min_length=1, max_length=255)
    enabled: bool = True

class GitRepositoryResponse(GitRepositoryCreate):
    id: int
    project_id: int
    model_config = {"from_attributes": True}

class GitFileChange(BaseModel):
    status: str
    path: str
    old_path: str | None = None

class GitStatusResponse(BaseModel):
    branch: str
    ahead: int = 0
    behind: int = 0
    clean: bool
    changes: list[GitFileChange]

class GitCommit(BaseModel):
    hash: str
    short_hash: str
    author: str
    email: str
    date: datetime
    subject: str

class GitContributor(BaseModel):
    name: str
    email: str
    commits: int

class GitCompareResponse(BaseModel):
    base: str
    head: str
    files_changed: int
    insertions: int
    deletions: int
    changes: list[GitFileChange]

class GitRiskResponse(BaseModel):
    level: str
    score: int
    reasons: list[str]
    affected_files: list[str]

class RollbackSuggestion(BaseModel):
    priority: str
    reason: str
    commit: str | None = None
    suggestion: str

class GitChangelogResponse(BaseModel):
    title: str
    content_markdown: str
