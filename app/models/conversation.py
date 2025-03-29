from datetime import datetime
from typing import Optional, Any, Dict, List
from pydantic import BaseModel, Field, UUID4
from app.models.base import *

class ConversationBase(BaseModel):
    """Base model for conversations"""
    lead_id: UUID4
    chatbot_id: UUID4
    canal_id: UUID4
    canal_identificador: str = Field(..., description="Channel identifier (e.g., phone number, chat ID)")
    estado: str = Field(default="active", description="Status of the conversation (active, closed)")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional metadata")

class ConversationCreate(ConversationBase):
    """Model for creating a new conversation"""
    pass

class ConversationInDB(ConversationBase):
    """Model for a conversation stored in the database"""
    id: UUID4
    ultimo_mensaje: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    chatbot_activo: bool = True

class ConversationResponse(ConversationInDB):
    """Model for conversation response"""
    pass

class ConversationHistory(BaseModel):
    """Model for conversation history"""
    conversation_id: UUID4
    messages: List[Dict[str, Any]]
    metadata: Optional[Dict[str, Any]] = None
