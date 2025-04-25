-- Script SQL para crear las tablas necesarias para el sistema de agentes
-- Este script crea las tablas principales y las relaciones

-- Tabla principal de agentes
CREATE TABLE IF NOT EXISTS agentes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL REFERENCES empresas(id),
    name TEXT NOT NULL,
    description TEXT,
    avatar_url TEXT,
    type TEXT NOT NULL,
    autonomy_level INTEGER NOT NULL,
    specialization JSONB,
    status TEXT NOT NULL,
    performance_metrics JSONB,
    evolution_config JSONB,
    llm_config_id UUID REFERENCES llm_configuraciones(id),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE
);

-- Tabla para almacenar la personalidad de los agentes
CREATE TABLE IF NOT EXISTS agente_personalidad (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id UUID NOT NULL REFERENCES agentes(id) ON DELETE CASCADE,
    traits JSONB,
    communication_style JSONB,
    interaction_preferences JSONB,
    contextual_adaptability INTEGER NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE
);

-- Tabla para almacenar los objetivos de los agentes
CREATE TABLE IF NOT EXISTS agente_objetivos (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id UUID NOT NULL REFERENCES agentes(id) ON DELETE CASCADE,
    type TEXT NOT NULL,
    description TEXT NOT NULL,
    metrics JSONB,
    progress FLOAT NOT NULL,
    priority INTEGER NOT NULL,
    target_date TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE
);

-- Tabla para almacenar las habilidades de los agentes
CREATE TABLE IF NOT EXISTS agente_habilidades (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id UUID NOT NULL REFERENCES agentes(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    description TEXT,
    type TEXT NOT NULL,
    level INTEGER NOT NULL,
    parameters JSONB,
    requirements JSONB,
    usage_metrics JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE
);

-- Tabla para almacenar las experiencias de los agentes
CREATE TABLE IF NOT EXISTS agente_experiencias (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id UUID NOT NULL REFERENCES agentes(id) ON DELETE CASCADE,
    interaction_type TEXT NOT NULL,
    context JSONB,
    result TEXT NOT NULL,
    learning_acquired JSONB,
    performance_impact FLOAT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Tabla para almacenar la evolución de los agentes
CREATE TABLE IF NOT EXISTS agente_evolucion (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id UUID NOT NULL REFERENCES agentes(id) ON DELETE CASCADE,
    version TEXT NOT NULL,
    changes JSONB,
    previous_metrics JSONB,
    new_metrics JSONB,
    evolution_date TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Tabla para almacenar el conocimiento de los agentes
CREATE TABLE IF NOT EXISTS agente_conocimiento (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id UUID NOT NULL REFERENCES agentes(id) ON DELETE CASCADE,
    type TEXT NOT NULL,
    source TEXT NOT NULL,
    format TEXT NOT NULL,
    content TEXT NOT NULL,
    metadata JSONB,
    priority INTEGER DEFAULT 1,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE
);

-- Tabla para almacenar los vectores de embeddings del conocimiento
CREATE TABLE IF NOT EXISTS agente_conocimiento_vectores (
    knowledge_id UUID PRIMARY KEY REFERENCES agente_conocimiento(id) ON DELETE CASCADE,
    embedding vector(1536)
);

-- Crear función para búsqueda por similitud
CREATE OR REPLACE FUNCTION match_knowledge_vectors(
    query_embedding vector(1536),
    match_threshold float,
    match_count int,
    agent_id uuid
)
RETURNS TABLE (
    id uuid,
    agent_id uuid,
    type text,
    source text,
    format text,
    content text,
    metadata jsonb,
    priority integer,
    created_at timestamptz,
    updated_at timestamptz,
    similarity float
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        ac.id,
        ac.agent_id,
        ac.type,
        ac.source,
        ac.format,
        ac.content,
        ac.metadata,
        ac.priority,
        ac.created_at,
        ac.updated_at,
        1 - (acv.embedding <=> query_embedding) as similarity
    FROM
        agente_conocimiento ac
    JOIN
        agente_conocimiento_vectores acv ON ac.id = acv.knowledge_id
    WHERE
        ac.agent_id = $4
        AND 1 - (acv.embedding <=> query_embedding) > $2
    ORDER BY
        similarity DESC
    LIMIT $3;
END;
$$;

-- Función para actualizar el campo updated_at automáticamente
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Crear triggers para actualizar campos updated_at automáticamente
CREATE TRIGGER update_agentes_updated_at
    BEFORE UPDATE ON agentes
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_agente_personalidad_updated_at
    BEFORE UPDATE ON agente_personalidad
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_agente_objetivos_updated_at
    BEFORE UPDATE ON agente_objetivos
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_agente_habilidades_updated_at
    BEFORE UPDATE ON agente_habilidades
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_agente_conocimiento_updated_at
    BEFORE UPDATE ON agente_conocimiento
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();