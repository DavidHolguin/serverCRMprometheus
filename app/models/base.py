from datetime import datetime
from typing import Optional, Any, Dict, List
from pydantic import BaseModel, Field, UUID4

class BaseDBModel(BaseModel):
    """Clase base para modelos de base de datos con campos comunes"""
    id: Optional[UUID4] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True  # Reemplazado de orm_mode que está deprecado en Pydantic v2
