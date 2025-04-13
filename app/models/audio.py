from pydantic import BaseModel, UUID4, Field, HttpUrl
from typing import Dict, Any, Optional, List
from uuid import UUID
from datetime import datetime

class AudioMessageRequest(BaseModel):
    """Modelo para solicitudes de mensajes de audio"""
    conversacion_id: Optional[UUID] = Field(None, description="ID de la conversación existente")
    lead_id: Optional[UUID] = Field(None, description="ID del lead (opcional si se proporciona conversacion_id)")
    empresa_id: UUID = Field(..., description="ID de la empresa")
    chatbot_id: UUID = Field(..., description="ID del chatbot")
    canal_id: Optional[UUID] = Field(None, description="ID del canal (se obtendrá automáticamente si no se proporciona)")
    canal_identificador: Optional[str] = Field(None, description="Identificador único del canal (ej. session_id, phone_number, etc.)")
    audio_base64: str = Field(..., description="Contenido del audio codificado en base64")
    formato_audio: str = Field(..., description="Formato del archivo de audio (mp3, wav, m4a, etc.)")
    idioma: Optional[str] = Field("es", description="Código de idioma para la transcripción (es, en, etc.)")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Metadatos adicionales")

class AudioMessageResponse(BaseModel):
    """Modelo para respuestas a mensajes de audio"""
    mensaje_id: UUID = Field(..., description="ID del mensaje creado")
    conversacion_id: UUID = Field(..., description="ID de la conversación")
    audio_id: UUID = Field(..., description="ID del registro de audio")
    transcripcion: str = Field(..., description="Texto transcrito del audio")
    respuesta: str = Field(..., description="Respuesta generada por el LLM")
    duracion_segundos: Optional[float] = Field(None, description="Duración del audio en segundos")
    idioma_detectado: Optional[str] = Field(None, description="Idioma detectado en el audio")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Metadatos adicionales")