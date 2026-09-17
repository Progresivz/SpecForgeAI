from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth.security import get_current_user
from app.crud.copilot import (
    add_message,
    create_conversation,
    get_conversation,
    list_messages,
)
from app.crud.project import get_project
from app.database.deps import get_db
from app.models.copilot_conversation import CopilotConversation
from app.models.user import User
from app.schemas.copilot import (
    CopilotChatRequest,
    CopilotChatResponse,
    CopilotConversationResponse,
    CopilotMessageResponse,
)
from app.services.copilot_service import chat


router = APIRouter(
    prefix="/projects/{project_id}/copilot",
    tags=["AI Copilot"],
)


def _project_or_404(
    db: Session,
    project_id: int,
    user_id: int,
):
    project = get_project(db, project_id, user_id)

    if not project:
        raise HTTPException(
            status_code=404,
            detail="Project not found",
        )

    return project


def _conversation_title(message: str) -> str:
    """
    Create a deterministic conversation title from the first user message.
    """
    title = " ".join(message.strip().split())

    if not title:
        return "New Copilot Conversation"

    if len(title) > 80:
        title = title[:77].rstrip() + "..."

    return title


@router.post(
    "/chat",
    response_model=CopilotChatResponse,
)
def copilot_chat(
    project_id: int,
    payload: CopilotChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if payload.project_id != project_id:
        raise HTTPException(
            status_code=400,
            detail="project_id in request body must match the URL",
        )

    project = _project_or_404(
        db,
        project_id,
        current_user.id,
    )

    conversation = None
    conversation_messages = []

    if payload.conversation_id is not None:
        conversation = get_conversation(
            db,
            payload.conversation_id,
            project_id,
            current_user.id,
        )

        if not conversation:
            raise HTTPException(
                status_code=404,
                detail="Copilot conversation not found",
            )

        conversation_messages = list_messages(
            db,
            conversation,
        )

    else:
        conversation = create_conversation(
            db=db,
            project_id=project_id,
            user_id=current_user.id,
            title=_conversation_title(payload.message),
        )

    add_message(
        db=db,
        conversation=conversation,
        role="user",
        content=payload.message,
        mode=payload.mode if payload.mode != "auto" else "general",
    )

    try:
        response, context, mode, actions = chat(
            db=db,
            project=project,
            message=payload.message,
            mode=payload.mode,
            include_context=payload.include_context,
            conversation_history=conversation_messages,
        )

        add_message(
            db=db,
            conversation=conversation,
            role="assistant",
            content=response,
            mode=mode,
        )

        return CopilotChatResponse(
            project_id=project_id,
            message=payload.message,
            response=response,
            mode=mode,
            conversation_id=conversation.id,
            context=context,
            suggested_actions=actions,
        )

    except RuntimeError as exc:
        raise HTTPException(
            status_code=503,
            detail=str(exc),
        ) from exc


@router.get(
    "/conversations",
    response_model=list[CopilotConversationResponse],
)
def list_conversations(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = _project_or_404(
        db,
        project_id,
        current_user.id,
    )

    conversations = (
        db.query(CopilotConversation)
        .filter(
            CopilotConversation.project_id == project.id,
            CopilotConversation.user_id == current_user.id,
        )
        .order_by(CopilotConversation.updated_at.desc())
        .all()
    )

    return [
        CopilotConversationResponse(
            id=conversation.id,
            project_id=conversation.project_id,
            title=conversation.title,
            created_at=conversation.created_at,
            updated_at=conversation.updated_at,
            messages=[],
        )
        for conversation in conversations
    ]


@router.get(
    "/conversations/{conversation_id}",
    response_model=CopilotConversationResponse,
)
def get_conversation_detail(
    project_id: int,
    conversation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _project_or_404(
        db,
        project_id,
        current_user.id,
    )

    conversation = get_conversation(
        db,
        conversation_id,
        project_id,
        current_user.id,
    )

    if not conversation:
        raise HTTPException(
            status_code=404,
            detail="Copilot conversation not found",
        )

    messages = list_messages(
        db,
        conversation,
    )

    return CopilotConversationResponse(
        id=conversation.id,
        project_id=conversation.project_id,
        title=conversation.title,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
        messages=[
            CopilotMessageResponse(
                id=message.id,
                role=message.role,
                content=message.content,
                mode=message.mode,
                created_at=message.created_at,
            )
            for message in messages
        ],
    )
