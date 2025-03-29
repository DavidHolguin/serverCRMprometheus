from datetime import datetime
from typing import Optional, Any, Dict, List
from pydantic import BaseModel, Field, UUID4
from app.models.base import *

class MessageBase(BaseModel):
    """Base model for messages"""
    conversacion_id: UUID4
    origen: str = Field(..., description="Origin of the message (user, chatbot, system)")
    contenido: str = Field(..., description="Content of the message")
    tipo_contenido: str = Field(default="text", description="Type of content (text, image, etc.)")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional metadata")

class MessageCreate(MessageBase):
    """Model for creating a new message"""
    remitente_id: Optional[UUID4] = Field(default=None, description="ID of the sender")
    score_impacto: int = Field(default=0, description="Impact score of the message")

class MessageInDB(MessageBase):
    """Model for a message stored in the database"""
    id: UUID4
    remitente_id: Optional[UUID4] = None
    score_impacto: int = 0
    created_at: datetime
    leido: bool = False

class MessageResponse(MessageInDB):
    """Model for message response"""
    pass

class ChannelMessageRequest(BaseModel):
    """Model for incoming channel message requests"""
    canal_id: UUID4
    canal_identificador: str = Field(..., description="Channel identifier (e.g., phone number, chat ID)")
    empresa_id: UUID4
    chatbot_id: UUID4
    lead_id: Optional[UUID4] = None
    mensaje: str
    metadata: Optional[Dict[str, Any]] = None
    
class ChannelMessageResponse(BaseModel):
    """Model for channel message responses"""
    mensaje_id: UUID4
    conversacion_id: UUID4
    respuesta: str
    metadata: Optional[Dict[str, Any]] = None
