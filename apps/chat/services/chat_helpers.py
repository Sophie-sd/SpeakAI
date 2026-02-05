"""
Chat Helper Functions - Centralized business logic
Senior-level implementation following DRY principle
"""

from typing import Optional, Dict, Any
from apps.chat.models import ChatSession, ChatMessage
from django.contrib.auth import get_user_model

User = get_user_model()


def get_or_create_session(user: User, title: str = "Chat Session") -> ChatSession:
    """
    Get or create a chat session for the user.
    Returns the latest session if exists, otherwise creates a new one.

    Args:
        user: User instance
        title: Session title (default: "Chat Session")

    Returns:
        ChatSession instance
    """
    session = ChatSession.objects.filter(user=user).order_by("-updated_at").first()
    if not session:
        session = ChatSession.objects.create(user=user, title=title)
    return session


def create_user_message(
    session: ChatSession,
    content: str,
    source_type: str = "text",
    transcript: Optional[str] = None,
) -> ChatMessage:
    """
    Create a user message in the chat session.

    Args:
        session: ChatSession instance
        content: Message content
        source_type: 'text' or 'voice'
        transcript: Optional transcript (for voice messages)

    Returns:
        ChatMessage instance
    """
    message = ChatMessage.objects.create(
        session=session, role="user", content=content, source_type=source_type
    )
    if transcript:
        message.transcript = transcript
        message.save(update_fields=["transcript"])
    return message


def create_ai_message(
    session: ChatSession,
    response_data: Dict[str, Any],
    source_type: str = "text",
    audio_url: Optional[str] = None,
) -> ChatMessage:
    """
    Create an AI message from Gemini response.

    Args:
        session: ChatSession instance
        response_data: Dict with keys: response, translation, explanation, 
                      corrected_text, full_english_version, phase, has_errors
        source_type: 'text' or 'voice'
        audio_url: Optional audio URL for voice responses

    Returns:
        ChatMessage instance
    """
    message = ChatMessage.objects.create(
        session=session,
        role="model",
        content=response_data.get("response"),
        translation=response_data.get("translation"),
        explanation=response_data.get("explanation"),
        corrected_text=response_data.get("corrected_text"),
        full_english_version=response_data.get("full_english_version"),
        audio_url=audio_url,
        source_type=source_type,
        transcript=response_data.get("phase", "initial"),
    )
    
    # Set has_errors flag
    if response_data.get("has_errors", False):
        message.has_errors = True
        message.save(update_fields=["has_errors"])
    
    return message


def get_chat_history(
    session: ChatSession, exclude_message_id: Optional[int] = None
) -> Any:
    """
    Get ordered chat history for a session.

    Args:
        session: ChatSession instance
        exclude_message_id: Message ID to exclude (typically current message)

    Returns:
        QuerySet of ChatMessage ordered by created_at
    """
    history = ChatMessage.objects.filter(session=session).order_by("created_at")
    
    if exclude_message_id:
        history = history.exclude(id=exclude_message_id)
    
    return history
