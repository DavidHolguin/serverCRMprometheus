from datetime import datetime
from typing import Optional, Any, Dict, List
from pydantic import BaseModel, Field, UUID4, validator
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
    # Campo principal para identificación de canal-chatbot (obligatorio)
    chatbot_canal_id: UUID4 = Field(..., description="ID de chatbot_canales que relaciona chatbot, canal y empresa")
    
    # Campos requeridos siempre
    canal_identificador: str = Field(..., description="Identificador del canal (ej: número de teléfono, chat ID)")
    mensaje: str = Field(..., description="Contenido del mensaje")
    
    # Campos opcionales
    lead_id: Optional[UUID4] = Field(None, description="ID del lead (opcional)")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Metadatos adicionales")
    conversacion_id: Optional[UUID4] = Field(None, description="ID de una conversación existente (opcional)")

class ChannelMessageResponse(BaseModel):
    """Model for channel message responses"""
    mensaje_id: UUID4
    conversacion_id: UUID4
    respuesta: str
    metadata: Optional[Dict[str, Any]] = None

class AgentMessageRequest(BaseModel):
    """Modelo unificado para mensajes de agente humano"""
    agent_id: UUID4 = Field(..., description="ID del agente que envía el mensaje")
    mensaje: str = Field(..., description="Contenido del mensaje")
    
    # Campos para conversación existente
    conversation_id: Optional[UUID4] = Field(None, description="ID de la conversación existente (opcional)")
    
    # Nuevo campo para relación chatbot-canal
    chatbot_canal_id: Optional[UUID4] = Field(None, description="ID de chatbot_canales que relaciona chatbot, canal y empresa")
    
    # Campos para nueva conversación o mensajes directos (opcionales si se proporciona chatbot_canal_id)
    lead_id: Optional[UUID4] = Field(None, description="ID del lead para iniciar nueva conversación (opcional)")
  
    channel_identifier: Optional[str] = Field(None, description="Identificador del canal (teléfono, chat ID, etc.)")
    chatbot_id: Optional[UUID4] = Field(None, description="ID del chatbot para asociar a la conversación")
    empresa_id: Optional[UUID4] = Field(None, description="ID de la empresa")
    
    # Configuración adicional
    deactivate_chatbot: bool = Field(False, description="Desactivar el chatbot para esta conversación")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Metadatos adicionales")
    
    @validator('conversation_id', 'lead_id')
    def validate_ids(cls, v, values):
        if 'conversation_id' in values and values['conversation_id'] is None and 'lead_id' in values and values['lead_id'] is None:
            raise ValueError("Debe proporcionar conversation_id o lead_id")
        return v
        
    @validator('chatbot_canal_id', 'chatbot_id', 'empresa_id')
    def validate_channel_chatbot(cls, v, values, **kwargs):
        field = kwargs.get('field')
        
        # Si se proporciona conversation_id, no necesitamos validar estos campos
        if 'conversation_id' in values and values['conversation_id'] is not None:
            return v
            
        # Si se está validando chatbot_canal_id y no está presente
        if field is not None and field.name == 'chatbot_canal_id' and v is None:
            # Solo validamos si estamos creando una nueva conversación
            if 'lead_id' in values and values['lead_id'] is not None:
                # Entonces verificamos que estén presentes chatbot_id y empresa_id
                if ('chatbot_id' not in values or values['chatbot_id'] is None) or \
                   ('empresa_id' not in values or values['empresa_id'] is None) or \
                   ('channel_identifier' not in values or values['channel_identifier'] is None):
                    raise ValueError("Para nueva conversación debe proporcionar chatbot_canal_id o la combinación de chatbot_id, empresa_id y channel_identifier")
                
        return v

class AgentDirectMessageRequest(BaseModel):
    """Model for direct agent message requests to a lead without an existing conversation"""
    agent_id: UUID4 = Field(..., description="ID del agente que envía el mensaje")
    lead_id: UUID4 = Field(..., description="ID del lead al que se envía el mensaje")
    mensaje: str = Field(..., description="Contenido del mensaje")
    
    # Nuevo campo para relación chatbot-canal
    chatbot_canal_id: Optional[UUID4] = Field(None, description="ID de chatbot_canales que relaciona chatbot, canal y empresa")
    
    # Campos originales (ahora opcionales si se proporciona chatbot_canal_id)
    channel_id: Optional[UUID4] = Field(None, description="ID del canal a utilizar (opcional si se proporciona chatbot_canal_id)")
    channel_identifier: str = Field(..., description="Identificador del canal (teléfono, chat ID, etc.)")
    chatbot_id: Optional[UUID4] = Field(None, description="ID del chatbot para asociar a la conversación (opcional si se proporciona chatbot_canal_id)")
    empresa_id: Optional[UUID4] = Field(None, description="ID de la empresa (opcional si se proporciona chatbot_canal_id)")
    
    metadata: Optional[Dict[str, Any]] = Field(None, description="Metadatos adicionales")
    
    @validator('chatbot_canal_id', 'channel_id', 'chatbot_id', 'empresa_id')
    def validate_required_ids(cls, v, values, **kwargs):
        field = kwargs.get('field')
        
        # Verificar si field existe y si estamos validando chatbot_canal_id
        if field is not None and field.name == 'chatbot_canal_id' and v is None:
            # Entonces verificamos que estén presentes channel_id, chatbot_id y empresa_id
            if ('channel_id' not in values or values['channel_id'] is None) or \
               ('chatbot_id' not in values or values['chatbot_id'] is None) or \
               ('empresa_id' not in values or values['empresa_id'] is None):
                raise ValueError("Debe proporcionar chatbot_canal_id o la combinación de channel_id, chatbot_id y empresa_id")
        
        return v

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
