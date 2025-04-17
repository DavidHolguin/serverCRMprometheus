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
    canal_id: UUID4 = Field(..., description="ID of the channel")
    canal_identificador: str = Field(..., description="Channel identifier (e.g., phone number, chat ID)")
    empresa_id: UUID4 = Field(..., description="ID of the company")
    chatbot_id: UUID4 = Field(..., description="ID of the chatbot")
    lead_id: Optional[UUID4] = Field(None, description="ID of the lead (optional)")
    mensaje: str = Field(..., description="Message content")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")
    
    # Channel-specific identifiers (only one will be used based on the channel)
    session_id: Optional[str] = Field(None, description="Session ID for web channel")
    phone_number: Optional[str] = Field(None, description="Phone number for WhatsApp channel")
    sender_id: Optional[str] = Field(None, description="Sender ID for Messenger channel")
    chat_id: Optional[str] = Field(None, description="Chat ID for Telegram channel")
    instagram_id: Optional[str] = Field(None, description="Instagram ID for Instagram channel")
    
class ChannelMessageResponse(BaseModel):
    """Model for channel message responses"""
    mensaje_id: UUID4
    conversacion_id: UUID4
    respuesta: str
    metadata: Optional[Dict[str, Any]] = None

class AgentMessageRequest(BaseModel):
    """Model for agent message requests"""
    conversation_id: UUID4 = Field(..., description="ID of the conversation")
    agent_id: UUID4 = Field(..., description="ID of the agent sending the message")
    mensaje: str = Field(..., description="Message content")
    deactivate_chatbot: bool = Field(False, description="Whether to deactivate the chatbot for this conversation")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")

class ToggleChatbotRequest(BaseModel):
    """Model for toggling chatbot status"""
    conversation_id: UUID4 = Field(..., description="ID of the conversation")
    chatbot_activo: bool = Field(..., description="Whether the chatbot should be active")

class ToggleChatbotResponse(BaseModel):
    """Model for toggle chatbot response"""
    success: bool = Field(..., description="Whether the operation was successful")
    conversation_id: str = Field(..., description="ID of the conversation")
    chatbot_activo: bool = Field(..., description="Current chatbot active status")
    data: Dict[str, Any] = Field(..., description="Full conversation data")

class MessageEvaluationRequest(BaseModel):
    """Model for asynchronous message evaluation requests"""
    mensaje_id: UUID4 = Field(..., description="ID of the message to evaluate")
    conversacion_id: UUID4 = Field(..., description="ID of the conversation")
    lead_id: UUID4 = Field(..., description="ID of the lead")
    empresa_id: UUID4 = Field(..., description="ID of the company")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata for the evaluation")

class MessageEvaluationResponse(BaseModel):
    """Model for message evaluation responses"""
    evaluation_id: Optional[UUID4] = Field(None, description="ID of the created evaluation (if successful)")
    mensaje_id: UUID4 = Field(..., description="ID of the evaluated message")
    success: bool = Field(..., description="Whether the evaluation was successful")
    error: Optional[str] = Field(None, description="Error message if evaluation failed")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata from the evaluation")
