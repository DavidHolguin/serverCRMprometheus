from pydantic import BaseModel, EmailStr, UUID4, HttpUrl
from typing import Optional, Dict, Any
from datetime import datetime

class LeadFormData(BaseModel):
    """Modelo para los datos del formulario web"""
    nombre: str
    email: Optional[EmailStr] = None  
    telefono: Optional[str] = None
    empresa_id: UUID4
    channel_id: Optional[UUID4] = None # ID del canal de formulario web (se usará uno por defecto si no se provee)
    pipeline_id: Optional[UUID4] = None
    stage_id: Optional[UUID4] = None
    pais: Optional[str] = None
    ciudad: Optional[str] = None
    direccion: Optional[str] = None
    origen_url: Optional[HttpUrl] = None
    pagina_titulo: Optional[str] = None
    tiempo_navegacion: Optional[int] = None  # en segundos
    profundidad_scroll: Optional[int] = None  # porcentaje de scroll
    ip_address: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None  # Para datos adicionales del formulario

class LeadFormResponse(BaseModel):
    """Modelo para la respuesta al crear un lead desde formulario"""
    lead_id: UUID4
    conversation_id: Optional[UUID4] = None
    status: str = "success"
    message: str
    created_at: datetime
