from typing import Dict, List, Optional, Any
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field

class AgentKnowledge(BaseModel):
    """Modelo para el conocimiento del agente"""
    id: UUID = Field(description="Identificador único del conocimiento")
    agent_id: UUID = Field(description="ID del agente al que pertenece el conocimiento")
    type: str = Field(description="Tipo de conocimiento (base, especializado, experiencial)")
    source: str = Field(description="Fuente del conocimiento")
    format: str = Field(description="Formato del conocimiento (texto, vectores, reglas, experiencia)")
    content: str = Field(description="Contenido del conocimiento")
    embeddings: Optional[List[float]] = Field(description="Vectores de embeddings para búsqueda semántica", default=None)
    metadata: Dict[str, Any] = Field(description="Metadatos adicionales", default_factory=dict)
    priority: int = Field(description="Prioridad del conocimiento", default=1)
    created_at: datetime = Field(description="Fecha de creación")
    updated_at: Optional[datetime] = Field(description="Fecha de última actualización", default=None)

class AgentSkill(BaseModel):
    """Modelo para las habilidades del agente"""
    id: UUID = Field(description="Identificador único de la habilidad")
    agent_id: UUID = Field(description="ID del agente al que pertenece la habilidad")
    name: str = Field(description="Nombre de la habilidad")
    description: str = Field(description="Descripción de la habilidad")
    type: str = Field(description="Tipo de habilidad")
    level: int = Field(description="Nivel de la habilidad (1-10)")
    parameters: Dict[str, Any] = Field(description="Parámetros de configuración de la habilidad", default_factory=dict)
    requirements: Dict[str, Any] = Field(description="Requisitos para usar la habilidad", default_factory=dict)
    usage_metrics: Dict[str, Any] = Field(description="Métricas de uso de la habilidad", default_factory=dict)
    created_at: datetime = Field(description="Fecha de creación")
    updated_at: Optional[datetime] = Field(description="Fecha de última actualización", default=None)

class AgentObjective(BaseModel):
    """Modelo para los objetivos del agente"""
    id: UUID = Field(description="Identificador único del objetivo")
    agent_id: UUID = Field(description="ID del agente al que pertenece el objetivo")
    type: str = Field(description="Tipo de objetivo")
    description: str = Field(description="Descripción del objetivo")
    metrics: Dict[str, Any] = Field(description="Métricas para medir el progreso", default_factory=dict)
    progress: float = Field(description="Progreso hacia el objetivo (0-100)", ge=0, le=100)
    priority: int = Field(description="Prioridad del objetivo", ge=1, le=10)
    target_date: Optional[datetime] = Field(description="Fecha objetivo", default=None)
    created_at: datetime = Field(description="Fecha de creación")
    updated_at: Optional[datetime] = Field(description="Fecha de última actualización", default=None)

class AgentExperience(BaseModel):
    """Modelo para las experiencias del agente"""
    id: UUID = Field(description="Identificador único de la experiencia")
    agent_id: UUID = Field(description="ID del agente al que pertenece la experiencia")
    interaction_type: str = Field(description="Tipo de interacción")
    context: Dict[str, Any] = Field(description="Contexto de la experiencia", default_factory=dict)
    result: str = Field(description="Resultado de la interacción")
    learning_acquired: Dict[str, Any] = Field(description="Aprendizaje adquirido", default_factory=dict)
    performance_impact: float = Field(description="Impacto en el rendimiento (-10 a 10)", ge=-10, le=10)
    created_at: datetime = Field(description="Fecha de creación")

class AgentPersonality(BaseModel):
    """Modelo para la personalidad del agente"""
    id: UUID = Field(description="Identificador único de la personalidad")
    agent_id: UUID = Field(description="ID del agente al que pertenece la personalidad")
    traits: Dict[str, Any] = Field(description="Rasgos de personalidad", default_factory=dict)
    communication_style: Dict[str, Any] = Field(description="Estilo de comunicación", default_factory=dict)
    interaction_preferences: Dict[str, Any] = Field(description="Preferencias de interacción", default_factory=dict)
    contextual_adaptability: int = Field(description="Nivel de adaptabilidad al contexto (1-10)", ge=1, le=10)
    created_at: datetime = Field(description="Fecha de creación")
    updated_at: Optional[datetime] = Field(description="Fecha de última actualización", default=None)

class AgentEvolution(BaseModel):
    """Modelo para la evolución del agente"""
    id: UUID = Field(description="Identificador único de la evolución")
    agent_id: UUID = Field(description="ID del agente al que pertenece la evolución")
    version: str = Field(description="Versión del agente")
    changes: Dict[str, Any] = Field(description="Cambios realizados", default_factory=dict)
    previous_metrics: Dict[str, Any] = Field(description="Métricas anteriores", default_factory=dict)
    new_metrics: Dict[str, Any] = Field(description="Nuevas métricas", default_factory=dict)
    evolution_date: datetime = Field(description="Fecha de evolución")
    created_at: datetime = Field(description="Fecha de creación")

class Agent(BaseModel):
    """Modelo principal para los agentes"""
    id: UUID = Field(description="Identificador único del agente")
    company_id: UUID = Field(description="ID de la empresa a la que pertenece")
    name: str = Field(description="Nombre del agente")
    description: str = Field(description="Descripción del agente")
    avatar_url: Optional[str] = Field(description="URL del avatar del agente", default=None)
    type: str = Field(description="Tipo de agente")
    autonomy_level: int = Field(description="Nivel de autonomía (1-10)", ge=1, le=10)
    specialization: Dict[str, Any] = Field(description="Especialización del agente", default_factory=dict)
    status: str = Field(description="Estado actual del agente")
    performance_metrics: Dict[str, Any] = Field(description="Métricas de rendimiento", default_factory=dict)
    evolution_config: Dict[str, Any] = Field(description="Configuración de evolución", default_factory=dict)
    llm_config_id: UUID = Field(description="ID de la configuración LLM")
    is_active: bool = Field(description="Indica si el agente está activo", default=True)
    created_at: datetime = Field(description="Fecha de creación")
    updated_at: Optional[datetime] = Field(description="Fecha de última actualización", default=None)

    # Relaciones (opcional, dependiendo de cómo se implementen en la base de datos)
    knowledge: Optional[List[AgentKnowledge]] = None
    skills: Optional[List[AgentSkill]] = None
    objectives: Optional[List[AgentObjective]] = None
    experiences: Optional[List[AgentExperience]] = None
    personality: Optional[AgentPersonality] = None
    evolutions: Optional[List[AgentEvolution]] = None