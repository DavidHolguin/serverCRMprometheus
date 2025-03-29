from datetime import datetime
from typing import Optional, Any, Dict, List
from pydantic import BaseModel, Field, UUID4
from app.models.base import *

class ChatbotBase(BaseModel):
    """Base model for chatbots"""
    empresa_id: UUID4
    nombre: str
    descripcion: Optional[str] = None
    avatar_url: Optional[str] = None
    tono: Optional[str] = None
    personalidad: Optional[str] = None
    instrucciones: Optional[str] = None
    contexto: Optional[str] = None
    configuracion: Optional[Dict[str, Any]] = None
    pipeline_id: Optional[UUID4] = None
    is_active: bool = True

class ChatbotContextBase(BaseModel):
    """Base model for chatbot contexts"""
    chatbot_id: UUID4
    tipo: str
    contenido: Optional[str] = None
    orden: int = 0
    welcome_message: Optional[str] = None
    personality: Optional[str] = None
    general_context: Optional[str] = None
    communication_tone: Optional[str] = None
    main_purpose: Optional[str] = None
    key_points: Optional[List[str]] = None
    special_instructions: Optional[str] = None
    prompt_template: Optional[str] = None
    qa_examples: Optional[List[Dict[str, str]]] = None

class ChatbotChannelBase(BaseModel):
    """Base model for chatbot channels"""
    chatbot_id: UUID4
    canal_id: UUID4
    configuracion: Dict[str, Any]
    webhook_url: Optional[str] = None
    webhook_secret: Optional[str] = None
    is_active: bool = True
