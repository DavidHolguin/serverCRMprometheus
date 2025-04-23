-- Función para registrar un evento en la tabla de hechos
CREATE OR REPLACE FUNCTION registrar_evento(
    p_empresa_id UUID,
    p_tipo_evento VARCHAR,
    p_categoria VARCHAR,
    p_entidad_origen_tipo VARCHAR,
    p_entidad_origen_id UUID,
    p_entidad_destino_tipo VARCHAR DEFAULT NULL,
    p_entidad_destino_id UUID DEFAULT NULL,
    p_lead_id UUID DEFAULT NULL,
    p_agente_id UUID DEFAULT NULL,
    p_chatbot_id UUID DEFAULT NULL,
    p_canal_id UUID DEFAULT NULL,
    p_conversacion_id UUID DEFAULT NULL,
    p_mensaje_id UUID DEFAULT NULL,
    p_valor_score INTEGER DEFAULT NULL,
    p_duracion_segundos INTEGER DEFAULT NULL,
    p_resultado VARCHAR DEFAULT NULL,
    p_estado_final VARCHAR DEFAULT NULL,
    p_detalle TEXT DEFAULT NULL,
    p_metadata JSONB DEFAULT NULL,
    p_latitud NUMERIC DEFAULT NULL,
    p_longitud NUMERIC DEFAULT NULL
) RETURNS UUID AS $$
DECLARE
    v_tiempo_id INTEGER;
    v_tipo_evento_id UUID;
    v_entidad_origen_id UUID;
    v_entidad_destino_id UUID;
    v_evento_accion_id UUID;
BEGIN
    -- Obtener ID de la tabla de tiempo
    SELECT tiempo_id INTO v_tiempo_id 
    FROM dim_tiempo 
    WHERE fecha = CURRENT_DATE
    LIMIT 1;
    
    -- Si no existe registro para hoy, crearlo
    IF v_tiempo_id IS NULL THEN
        INSERT INTO dim_tiempo (
            fecha, dia_semana, dia, semana, mes, trimestre, anio, 
            es_fin_semana, nombre_dia, nombre_mes, fecha_completa
        )
        VALUES (
            CURRENT_DATE,
            EXTRACT(DOW FROM CURRENT_DATE),
            EXTRACT(DAY FROM CURRENT_DATE),
            EXTRACT(WEEK FROM CURRENT_DATE),
            EXTRACT(MONTH FROM CURRENT_DATE),
            EXTRACT(QUARTER FROM CURRENT_DATE),
            EXTRACT(YEAR FROM CURRENT_DATE),
            CASE WHEN EXTRACT(DOW FROM CURRENT_DATE) IN (0, 6) THEN TRUE ELSE FALSE END,
            TO_CHAR(CURRENT_DATE, 'Day'),
            TO_CHAR(CURRENT_DATE, 'Month'),
            NOW()
        )
        RETURNING tiempo_id INTO v_tiempo_id;
    END IF;
    
    -- Obtener tipo de evento
    SELECT tipo_evento_id INTO v_tipo_evento_id 
    FROM dim_tipos_eventos 
    WHERE nombre = p_tipo_evento AND categoria = p_categoria;
    
    -- Si no existe el tipo de evento, crear uno genérico
    IF v_tipo_evento_id IS NULL THEN
        INSERT INTO dim_tipos_eventos (categoria, nombre, descripcion)
        VALUES (p_categoria, p_tipo_evento, 'Evento creado automáticamente')
        RETURNING tipo_evento_id INTO v_tipo_evento_id;
    END IF;
    
    -- Obtener entidad origen
    SELECT entidad_id INTO v_entidad_origen_id
    FROM dim_entidades
    WHERE tipo_entidad = p_entidad_origen_tipo AND entidad_original_id = p_entidad_origen_id;
    
    -- Si no existe la entidad origen, crearla
    IF v_entidad_origen_id IS NULL THEN
        INSERT INTO dim_entidades (tipo_entidad, entidad_original_id, nombre)
        VALUES (p_entidad_origen_tipo, p_entidad_origen_id, p_entidad_origen_tipo || ' ' || p_entidad_origen_id)
        RETURNING entidad_id INTO v_entidad_origen_id;
    END IF;
    
    -- Obtener entidad destino si se proporcionó
    IF p_entidad_destino_tipo IS NOT NULL AND p_entidad_destino_id IS NOT NULL THEN
        SELECT entidad_id INTO v_entidad_destino_id
        FROM dim_entidades
        WHERE tipo_entidad = p_entidad_destino_tipo AND entidad_original_id = p_entidad_destino_id;
        
        -- Si no existe la entidad destino, crearla
        IF v_entidad_destino_id IS NULL THEN
            INSERT INTO dim_entidades (tipo_entidad, entidad_original_id, nombre)
            VALUES (p_entidad_destino_tipo, p_entidad_destino_id, p_entidad_destino_tipo || ' ' || p_entidad_destino_id)
            RETURNING entidad_id INTO v_entidad_destino_id;
        END IF;
    END IF;
    
    -- Registrar el evento en la tabla de hechos
    INSERT INTO fact_eventos_acciones (
        tiempo_id, empresa_id, tipo_evento_id, entidad_origen_id, entidad_destino_id,
        lead_id, agente_id, chatbot_id, canal_id, conversacion_id, mensaje_id,
        valor_score, duracion_segundos, resultado, estado_final, detalle, metadata,
        latitud, longitud
    )
    VALUES (
        v_tiempo_id, p_empresa_id, v_tipo_evento_id, v_entidad_origen_id, v_entidad_destino_id,
        p_lead_id, p_agente_id, p_chatbot_id, p_canal_id, p_conversacion_id, p_mensaje_id,
        p_valor_score, p_duracion_segundos, p_resultado, p_estado_final, p_detalle, p_metadata,
        p_latitud, p_longitud
    )
    RETURNING evento_accion_id INTO v_evento_accion_id;
    
    RETURN v_evento_accion_id;
END;
$$ LANGUAGE plpgsql;
