CREATE TABLE IF NOT EXISTS fact_eventos_acciones (
    evento_accion_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Dimensiones
    tiempo_id INTEGER NOT NULL,
    empresa_id UUID NOT NULL,
    tipo_evento_id UUID NOT NULL,
    entidad_origen_id UUID NOT NULL,
    entidad_destino_id UUID,
    
    -- IDs relacionados
    lead_id UUID,
    agente_id UUID,
    chatbot_id UUID,
    canal_id UUID,
    conversacion_id UUID,
    mensaje_id UUID,
    
    -- Métricas y atributos
    valor_score INTEGER,
    duracion_segundos INTEGER,
    resultado VARCHAR(50),
    estado_final VARCHAR(50),
    
    -- Datos adicionales
    detalle TEXT,
    metadata JSONB,
    latitud NUMERIC,
    longitud NUMERIC,
    
    -- Metadatos de la fila
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Constraints
    FOREIGN KEY (tiempo_id) REFERENCES dim_tiempo(tiempo_id),
    FOREIGN KEY (empresa_id) REFERENCES empresas(id),
    FOREIGN KEY (tipo_evento_id) REFERENCES dim_tipos_eventos(tipo_evento_id),
    FOREIGN KEY (entidad_origen_id) REFERENCES dim_entidades(entidad_id),
    FOREIGN KEY (entidad_destino_id) REFERENCES dim_entidades(entidad_id),
    FOREIGN KEY (lead_id) REFERENCES leads(id),
    FOREIGN KEY (agente_id) REFERENCES profiles(id),
    FOREIGN KEY (chatbot_id) REFERENCES chatbots(id),
    FOREIGN KEY (canal_id) REFERENCES canales(id),
    FOREIGN KEY (conversacion_id) REFERENCES conversaciones(id),
    FOREIGN KEY (mensaje_id) REFERENCES mensajes(id)
);

-- Índices para mejorar rendimiento de consultas
CREATE INDEX idx_fact_eventos_tiempo ON fact_eventos_acciones(tiempo_id);
CREATE INDEX idx_fact_eventos_empresa ON fact_eventos_acciones(empresa_id);
CREATE INDEX idx_fact_eventos_tipo ON fact_eventos_acciones(tipo_evento_id);
CREATE INDEX idx_fact_eventos_lead ON fact_eventos_acciones(lead_id);
CREATE INDEX idx_fact_eventos_agente ON fact_eventos_acciones(agente_id);
CREATE INDEX idx_fact_eventos_conversacion ON fact_eventos_acciones(conversacion_id);
CREATE INDEX idx_fact_eventos_created ON fact_eventos_acciones(created_at);

-- Particionamiento para optimizar consultas históricas (opcional)
-- Esto es un ejemplo, ajustar según volumen de datos y necesidades específicas
CREATE TABLE fact_eventos_acciones_y2023m01 PARTITION OF fact_eventos_acciones
    FOR VALUES FROM ('2023-01-01') TO ('2023-02-01');
-- ... Crear particiones adicionales según sea necesario
