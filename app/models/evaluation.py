from datetime import datetime
from typing import Optional, Any, Dict, List
from pydantic import BaseModel, Field, UUID4
from app.models.base import *

class EvaluacionBase(BaseModel):
    """Modelo base para evaluaciones de leads"""
    lead_id: UUID4
    conversacion_id: UUID4
    mensaje_id: UUID4
    score_potencial: int = Field(..., description="Puntuación de 1 a 10 que indica el potencial del lead como cliente")
    score_satisfaccion: int = Field(..., description="Puntuación de 1 a 10 que indica la satisfacción del lead con la conversación")
    interes_productos: List[str] = Field(default_factory=list, description="Lista de productos en los que el lead ha mostrado interés")
    comentario: str = Field(..., description="Comentario o análisis breve sobre el valor del lead y su comportamiento")
    palabras_clave: List[str] = Field(default_factory=list, description="Palabras clave identificadas en la conversación que indican intenciones o intereses")

class EvaluacionCreate(EvaluacionBase):
    """Modelo para crear una nueva evaluación"""
    fecha_evaluacion: datetime = Field(default_factory=datetime.now)
    llm_configuracion_id: Optional[UUID4] = None
    prompt_utilizado: Optional[str] = None

class EvaluacionInDB(EvaluacionBase):
    """Modelo para una evaluación almacenada en la base de datos"""
    id: int
    fecha_evaluacion: datetime
    llm_configuracion_id: Optional[UUID4] = None
    prompt_utilizado: Optional[str] = None
    created_at: datetime
    updated_at: datetime

class EvaluacionResponse(EvaluacionInDB):
    """Modelo para respuesta de evaluación"""
    pass

class EvaluateMessageRequest(BaseModel):
    """Modelo para solicitar la evaluación de un mensaje"""
    lead_id: UUID4 = Field(..., description="ID del lead")
    conversacion_id: UUID4 = Field(..., description="ID de la conversación")
    mensaje_id: UUID4 = Field(..., description="ID del mensaje a evaluar")
    empresa_id: UUID4 = Field(..., description="ID de la empresa")

class EvaluateConversationRequest(BaseModel):
    """Modelo para solicitar la evaluación de una conversación completa"""
    conversacion_id: UUID4 = Field(..., description="ID de la conversación")
    empresa_id: UUID4 = Field(..., description="ID de la empresa")

class EvaluationStatsResponse(BaseModel):
    """Modelo para respuesta de estadísticas de evaluación"""
    top_leads: List[Dict[str, Any]] = Field(default_factory=list, description="Top leads por potencial")
    top_productos: List[Dict[str, Any]] = Field(default_factory=list, description="Productos de interés más comunes")
    top_keywords: List[Dict[str, Any]] = Field(default_factory=list, description="Palabras clave más comunes")
