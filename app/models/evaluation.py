from typing import Dict, Any, List, Optional
from datetime import datetime
from pydantic import BaseModel, Field
from uuid import UUID

from app.models.base import BaseDBModel


class EvaluacionLeadBase(BaseModel):
    """Modelo base para evaluaciones de leads"""
    lead_id: UUID
    conversacion_id: UUID
    mensaje_id: UUID
    fecha_evaluacion: datetime
    score_potencial: int = Field(ge=1, le=10)
    score_satisfaccion: int = Field(ge=1, le=10)
    interes_productos: List[str] = []
    comentario: str
    palabras_clave: List[str] = []
    llm_configuracion_id: Optional[UUID] = None
    version_algoritmo: str = "1.0.0"
    nuevo_score: int = Field(ge=0, le=100, default=0)


class EvaluacionLeadCreate(EvaluacionLeadBase):
    """Modelo para crear una evaluación de lead"""
    prompt_utilizado: str
    score_calculation_metadata: Dict[str, Any] = {}


class EvaluacionLeadResponse(EvaluacionLeadBase):
    """Modelo para respuesta de evaluación de lead"""
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    nuevo_score: int = Field(ge=0, le=100)


class EvaluacionConfiguracion(BaseModel):
    """Configuración para evaluaciones de leads"""
    id: UUID
    empresa_id: UUID
    version: str = "1.0.0"
    recency_factor: float = Field(0.7, ge=0.0, le=1.0)
    sentiment_weight: float = Field(0.3, ge=0.0, le=1.0)
    intent_weight: float = Field(0.3, ge=0.0, le=1.0)
    product_interest_weight: float = Field(0.3, ge=0.0, le=1.0)
    engagement_weight: float = Field(0.2, ge=0.0, le=1.0)
    min_satisfaction_threshold: int = Field(4, ge=1, le=10)
    drastic_change_threshold: int = Field(3, ge=1, le=10)
    normalize_keywords: bool = True
    product_match_algorithm: str = "hybrid"
    temperature_calculation_enabled: bool = True
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    # Configuraciones específicas para contexto educativo
    educacion_config: Dict[str, Any] = {
        "programa_academico_peso": 0.35,
        "nivel_educativo_peso": 0.25,
        "urgencia_inscripcion_peso": 0.20,
        "disponibilidad_economica_peso": 0.15,
        "ubicacion_geografica_peso": 0.05
    }


class ProductoSinonimo(BaseModel):
    """Modelo para sinónimos de productos"""
    id: UUID
    empresa_id: UUID
    producto_id: UUID
    palabra_clave: str
    created_at: datetime


class LeadProductInterest(BaseModel):
    """Modelo para interés en productos específicos"""
    id: UUID
    lead_id: UUID
    producto_id: UUID
    evaluacion_id: Optional[int] = None
    mensaje_id: Optional[UUID] = None
    score: float = Field(5.0, ge=0.0, le=10.0)
    created_at: datetime


class LeadTemperature(BaseModel):
    """Modelo para temperatura de lead"""
    id: int
    lead_id: UUID
    empresa_id: UUID
    periodo_inicio: datetime
    periodo_fin: datetime
    temperatura: str
    score_periodo: float
    ultima_actividad: datetime
    interes_productos: List[str] = []
    prioridad: int = Field(3, ge=1, le=5)
    accion_sugerida: str = ""
    created_at: datetime
    updated_at: Optional[datetime] = None


class EvaluacionCalidad(BaseModel):
    """Modelo para métricas de calidad de evaluaciones"""
    id: int
    evaluacion_id: int
    precision_productos: float = Field(0.0, ge=0.0, le=1.0)
    precision_intencion: float = Field(0.0, ge=0.0, le=1.0)
    correlacion_comportamiento: float = Field(0.0, ge=0.0, le=1.0)
    created_at: datetime


class DashboardStats(BaseModel):
    """Modelo para estadísticas del dashboard"""
    total_leads: int = 0
    leads_por_temperatura: Dict[str, int] = {"caliente": 0, "tibia": 0, "fría": 0}
    programas_populares: List[Dict[str, Any]] = []
    palabras_clave_frecuentes: List[Dict[str, Any]] = []
    conversion_por_etapa: List[Dict[str, Any]] = []
    score_promedio: float = 0.0
    tendencia_semanal: List[Dict[str, Any]] = []
