from datetime import datetime
from typing import Optional, Any, Dict, List
from pydantic import BaseModel, Field, UUID4, EmailStr
from app.models.base import *

class LeadBase(BaseModel):
    """Base model for leads"""
    empresa_id: UUID4
    canal_origen: Optional[str] = None
    canal_id: Optional[UUID4] = None
    nombre: str
    apellido: Optional[str] = None
    email: Optional[EmailStr] = None
    telefono: Optional[str] = None
    pais: Optional[str] = None
    ciudad: Optional[str] = None
    direccion: Optional[str] = None
    datos_adicionales: Optional[Dict[str, Any]] = None
    score: int = 0
    pipeline_id: Optional[UUID4] = None
    stage_id: Optional[UUID4] = None
    asignado_a: Optional[UUID4] = None
    estado: str = "nuevo"
    is_active: bool = True

class LeadCreate(LeadBase):
    """Model for creating a new lead"""
    pass

class LeadInDB(LeadBase):
    """Model for a lead stored in the database"""
    id: UUID4
    ultima_interaccion: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

class LeadResponse(LeadInDB):
    """Model for lead response"""
    pass
