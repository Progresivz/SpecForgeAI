from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.auth.security import get_current_user
from app.crud.knowledge import delete_entry, get_entries, get_entry, upsert_entry
from app.crud.project import get_project
from app.database.deps import get_db
from app.models.user import User
from app.schemas.knowledge import (KnowledgeEntryCreate, KnowledgeEntryResponse, KnowledgeIndexResponse,
                                   KnowledgeSearchResponse, KnowledgeSearchResult)
from app.services.knowledge_service import index_project, search_entries, tags_for_entry

router = APIRouter(tags=["Knowledge Base"])


def _project(db, project_id, user_id):
    project = get_project(db, project_id, user_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


def _response(entry):
    tags = getattr(entry, "tags", None)

    if isinstance(tags, str):
        tags = [
            tag.strip()
            for tag in tags.split(",")
            if tag.strip()
        ]
    elif tags is None:
        tags = []
    else:
        tags = list(tags)

    return KnowledgeEntryResponse.model_validate(
        {
            "id": entry.id,
            "source_type": entry.source_type,
            "source_id": entry.source_id,
            "title": entry.title,
            "content": entry.content,
            "tags": tags,
            "updated_at": entry.updated_at,
        }
    )

@router.post("/projects/{project_id}/knowledge/index", response_model=KnowledgeIndexResponse)
def index(project_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    project = _project(db, project_id, current_user.id)
    indexed, removed = index_project(db, project)
    return {"project_id": project_id, "indexed": indexed, "removed": removed}


@router.post("/projects/{project_id}/knowledge", response_model=KnowledgeEntryResponse, status_code=status.HTTP_201_CREATED)
def create(project_id: int, data: KnowledgeEntryCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    _project(db, project_id, current_user.id)
    return _response(upsert_entry(db, project_id, data))


@router.get("/projects/{project_id}/knowledge", response_model=list[KnowledgeEntryResponse])
def list_entries(project_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    _project(db, project_id, current_user.id)
    return [_response(e) for e in get_entries(db, project_id, current_user.id)]


@router.get("/projects/{project_id}/knowledge/search", response_model=KnowledgeSearchResponse)
def search(
    project_id: int,
    q: str = Query(min_length=1, max_length=300),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _project(db, project_id, current_user.id)

    matches = search_entries(
        get_entries(db, project_id, current_user.id),
        q,
        limit,
    )

    results = []
    for score, terms, entry in matches:
        results.append(
            KnowledgeSearchResult(
                id=entry.id,
                source_type=entry.source_type,
                source_id=entry.source_id,
                title=entry.title,
                content=entry.content,
                tags=tags_for_entry(entry),
                updated_at=entry.updated_at,
                score=score,
                matched_terms=terms,
            )
        )

    return {
        "query": q,
        "total": len(results),
        "results": results,
    }


@router.delete("/knowledge/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete(entry_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    entry = get_entry(db, entry_id, current_user.id)
    if not entry:
        raise HTTPException(status_code=404, detail="Knowledge entry not found")
    delete_entry(db, entry)
