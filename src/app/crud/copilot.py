from sqlalchemy.orm import Session

from app.models.copilot_conversation import CopilotConversation, CopilotMessage


def create_conversation(
    db: Session,
    project_id: int,
    user_id: int,
    title: str = "New Copilot Conversation",
) -> CopilotConversation:
    conversation = CopilotConversation(
        project_id=project_id,
        user_id=user_id,
        title=title,
    )
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    return conversation


def get_conversation(
    db: Session,
    conversation_id: int,
    project_id: int,
    user_id: int,
) -> CopilotConversation | None:
    return (
        db.query(CopilotConversation)
        .filter(
            CopilotConversation.id == conversation_id,
            CopilotConversation.project_id == project_id,
            CopilotConversation.user_id == user_id,
        )
        .first()
    )


def add_message(
    db: Session,
    conversation: CopilotConversation,
    role: str,
    content: str,
    mode: str,
) -> CopilotMessage:
    message = CopilotMessage(
        conversation_id=conversation.id,
        role=role,
        content=content,
        mode=mode,
    )
    db.add(message)
    db.commit()
    db.refresh(message)

    # Touch conversation.updated_at.
    db.refresh(conversation)

    return message


def list_messages(
    db: Session,
    conversation: CopilotConversation,
) -> list[CopilotMessage]:
    return (
        db.query(CopilotMessage)
        .filter(CopilotMessage.conversation_id == conversation.id)
        .order_by(CopilotMessage.id.asc())
        .all()
    )