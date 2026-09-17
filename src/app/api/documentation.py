from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse, PlainTextResponse, Response
from sqlalchemy.orm import Session
from app.auth.security import get_current_user
from app.crud.project import get_project
from app.crud.documentation import create_or_replace, delete_documentation, get_documentation
from app.database.deps import get_db
from app.models.user import User
from app.schemas.documentation import (
    DocumentationExportResponse,
    DocumentationSetCreate,
    DocumentationSetResponse,
    DocumentationDocumentCreate,
)
from app.models.documentation import DocumentationDocument
from app.services.documentation_service import generate_documents, markdown_to_html
from app.services.documentation_export_service import markdown_to_docx, markdown_to_pdf
from app.services.ai_documentation_service import generate_ai_document

router=APIRouter(tags=['Documentation AI'])
def _project(db,pid,user):
    p=get_project(db,pid,user.id)
    if not p: raise HTTPException(404,'Project not found')
    return p

def _doc(db, project, doc_type):
    persisted = get_documentation(
        db,
        project.id,
        project.owner_id,
    )

    if persisted:
        for document in persisted.documents:
            if document.document_type == doc_type:
                return {
                    "document_type": document.document_type,
                    "title": document.title,
                    "content_markdown": document.content_markdown,
                }

    for document in generate_documents(project, None):
        if document["document_type"] == doc_type:
            return document

    raise HTTPException(
        status_code=404,
        detail="Document type not found",
    )

@router.post('/projects/{project_id}/documentation', response_model=DocumentationSetResponse, status_code=201)
def create_docs(project_id:int,data:DocumentationSetCreate,db:Session=Depends(get_db),current_user:User=Depends(get_current_user)):
    p=_project(db,project_id,current_user); return create_or_replace(db,p,data)

@router.post('/projects/{project_id}/documentation/generate', response_model=DocumentationSetResponse, status_code=201)
def generate_docs(project_id:int,db:Session=Depends(get_db),current_user:User=Depends(get_current_user)):
    p=_project(db,project_id,current_user); generated=generate_documents(p,db)
    data=DocumentationSetCreate(name=f'{p.name} Documentation',description='Generated from current project artifacts.',documents=generated)
    return create_or_replace(db,p,data)

@router.get('/projects/{project_id}/documentation', response_model=DocumentationSetResponse)
def get_docs(project_id:int,db:Session=Depends(get_db),current_user:User=Depends(get_current_user)):
    _project(db,project_id,current_user); d=get_documentation(db,project_id,current_user.id)
    if not d: raise HTTPException(404,'Documentation set not found')
    return d

@router.delete('/projects/{project_id}/documentation',status_code=204)
def delete_docs(project_id:int,db:Session=Depends(get_db),current_user:User=Depends(get_current_user)):
    _project(db,project_id,current_user); d=get_documentation(db,project_id,current_user.id)
    if not d: raise HTTPException(404,'Documentation set not found')
    delete_documentation(db,d)

@router.get(
    "/projects/{project_id}/documentation/{document_type}",
    response_model=DocumentationExportResponse,
)
def export_markdown(
    project_id: int,
    document_type: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    p = _project(db, project_id, current_user)
    d = _doc(db, p, document_type)

    return DocumentationExportResponse(
        project_id=p.id,
        document_type=d["document_type"],
        title=d["title"],
        format="markdown",
        content=d["content_markdown"],
    )

@router.get('/projects/{project_id}/documentation/{document_type}/html', response_class=HTMLResponse)
def export_html(project_id:int,document_type:str,db:Session=Depends(get_db),current_user:User=Depends(get_current_user)):
    p=_project(db,project_id,current_user); d = _doc(db, p, document_type)
    return HTMLResponse(markdown_to_html(d['content_markdown']))

@router.get('/projects/{project_id}/documentation/{document_type}/markdown', response_class=PlainTextResponse)
def download_markdown(project_id:int,document_type:str,db:Session=Depends(get_db),current_user:User=Depends(get_current_user)):
    p=_project(db,project_id,current_user); d = _doc(db, p, document_type)
    return PlainTextResponse(d['content_markdown'],headers={'Content-Disposition':f'attachment; filename="{document_type}.md"'})

@router.get(
    "/projects/{project_id}/documentation/{document_type}/docx",
)
def download_docx(
    project_id: int,
    document_type: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    p = _project(db, project_id, current_user)
    d = _doc(db, p, document_type)

    content = markdown_to_docx(
        d["content_markdown"]
    )

    return Response(
        content=content,
        media_type=(
            "application/vnd.openxmlformats-officedocument."
            "wordprocessingml.document"
        ),
        headers={
            "Content-Disposition": (
                f'attachment; filename="{document_type}.docx"'
            )
        },
    )

@router.get(
    "/projects/{project_id}/documentation/{document_type}/pdf",
)
def download_pdf(
    project_id: int,
    document_type: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    p = _project(db, project_id, current_user)
    d = _doc(db, p, document_type)

    content = markdown_to_pdf(
        d["content_markdown"]
    )

    return Response(
        content=content,
        media_type="application/pdf",
        headers={
            "Content-Disposition": (
                f'attachment; filename="{document_type}.pdf"'
            )
        },
    )

@router.post(
    "/projects/{project_id}/documentation/generate-ai/{document_type}",
    response_model=DocumentationExportResponse,
)
def generate_ai_docs(
    project_id: int,
    document_type: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    p = _project(db, project_id, current_user)

    try:
        generated = generate_ai_document(
            db,
            p,
            document_type,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc
    except RuntimeError as exc:
        raise HTTPException(
            status_code=503,
            detail=str(exc),
        ) from exc

    existing = get_documentation(
        db,
        project_id,
        current_user.id,
    )

    if existing:
        for document in existing.documents:
            if document.document_type == generated["document_type"]:
                document.title = generated["title"]
                document.content_markdown = generated["content_markdown"]
                db.commit()
                db.refresh(existing)
                break
        else:
            existing.documents.append(
                DocumentationDocumentCreate(
                    document_type=generated["document_type"],
                    title=generated["title"],
                    content_markdown=generated["content_markdown"],
                )
        )
            db.commit()
            db.refresh(existing)
    else:
        data = DocumentationSetCreate(
            name=f"{p.name} Documentation",
            description="AI-generated documentation from current project evidence.",
            documents=[
                DocumentationDocumentCreate(
                    document_type=generated["document_type"],
                    title=generated["title"],
                    content_markdown=generated["content_markdown"],
                )
            ],
        )
        existing = create_or_replace(db, p, data)

    return DocumentationExportResponse(
        project_id=p.id,
        document_type=generated["document_type"],
        title=generated["title"],
        format="markdown",
        content=generated["content_markdown"],
    )