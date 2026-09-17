from sqlalchemy.orm import Session
from app.models.ai_artifact import AIArtifact
from app.models.documentation import DocumentationDocument, DocumentationSet
from app.models.knowledge import KnowledgeEntry


def apply_artifact(db: Session, artifact: AIArtifact, target_type: str, target_id: str | None, title: str | None):
    """Promote an AI draft into a project artifact without executing generated code."""
    final_title = title or artifact.title
    if target_type == "knowledge":
        entry = KnowledgeEntry(project_id=artifact.project_id, source_type="ai_artifact",
                               source_id=str(artifact.id), title=final_title, content=artifact.content,
                               tags=f"ai,{artifact.artifact_type}")
        db.add(entry)
    elif target_type == "documentation":
        docset = db.query(DocumentationSet).filter(DocumentationSet.project_id == artifact.project_id).first()
        if not docset:
            docset = DocumentationSet(project_id=artifact.project_id, name="AI Generated Documentation",
                                       description="Documentation promoted from SpecForge AI artifacts.")
            db.add(docset)
            db.flush()
        document_type = artifact.artifact_type if artifact.artifact_type in {
            "proposal", "srs", "design", "database", "api", "test_plan", "user_manual",
            "installation", "maintenance", "release_notes", "changelog"
        } else "design"
        document = None
        if target_id and target_id.isdigit():
            document = db.query(DocumentationDocument).filter(
                DocumentationDocument.id == int(target_id),
                DocumentationDocument.documentation_set_id == docset.id).first()
        if document is None:
            document = db.query(DocumentationDocument).filter(
                DocumentationDocument.documentation_set_id == docset.id,
                DocumentationDocument.document_type == document_type).first()
        if document is None:
            document = DocumentationDocument(documentation_set_id=docset.id, document_type=document_type,
                                              title=final_title, content_markdown=artifact.content)
            db.add(document)
        else:
            document.title = final_title
            document.content_markdown = artifact.content
        artifact.target_id = str(document.id) if document.id else None
    else:
        # Structured-domain promotion is deliberately non-destructive: retain the generated draft
        # as searchable knowledge until a human or a future structured importer approves field-level changes.
        entry = KnowledgeEntry(project_id=artifact.project_id, source_type=f"ai_{target_type}",
                               source_id=str(artifact.id), title=final_title, content=artifact.content,
                               tags=f"ai,{artifact.artifact_type},{target_type}")
        db.add(entry)
    artifact.status = "applied"
    artifact.target_type = target_type
    db.commit()
    db.refresh(artifact)
    return artifact
