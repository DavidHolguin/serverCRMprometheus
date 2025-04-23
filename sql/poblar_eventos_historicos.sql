-- Función para migrar datos históricos a la tabla de fact_eventos_acciones
CREATE OR REPLACE FUNCTION migrar_datos_historicos() RETURNS void AS $$
DECLARE
    r_lead RECORD;
    r_interaccion RECORD;
    r_mensaje RECORD;
    r_evento RECORD;
    v_tiempo_id INTEGER;
    v_tipo_evento_id UUID;
    v_entidad_origen_id UUID;
    v_entidad_destino_id UUID;
BEGIN
    -- 1. Migrar interacciones de lead existentes
    FOR r_interaccion IN 
        SELECT 
            li.*, 
            lit.nombre AS tipo_nombre,
            'lead_interaction' AS tipo_categoria  -- Valor fijo en lugar de lit.categoria
        FROM 
            lead_interactions li
            JOIN lead_interaction_types lit ON li.interaction_type_id = lit.id
    LOOP
        -- Obtener tiempo_id
        SELECT tiempo_id INTO v_tiempo_id 
        FROM dim_tiempo 
        WHERE fecha = DATE(r_interaccion.created_at)
        LIMIT 1;
        
        -- Si no existe tiempo, crear
        IF v_tiempo_id IS NULL THEN
            INSERT INTO dim_tiempo (
                fecha, dia_semana, dia, semana, mes, trimestre, anio, 
                es_fin_semana, nombre_dia, nombre_mes, fecha_completa
            )
            VALUES (
                DATE(r_interaccion.created_at),
                EXTRACT(DOW FROM r_interaccion.created_at),
                EXTRACT(DAY FROM r_interaccion.created_at),
                EXTRACT(WEEK FROM r_interaccion.created_at),
                EXTRACT(MONTH FROM r_interaccion.created_at),
                EXTRACT(QUARTER FROM r_interaccion.created_at),
                EXTRACT(YEAR FROM r_interaccion.created_at),
                CASE WHEN EXTRACT(DOW FROM r_interaccion.created_at) IN (0, 6) THEN TRUE ELSE FALSE END,
                TO_CHAR(r_interaccion.created_at, 'Day'),
                TO_CHAR(r_interaccion.created_at, 'Month'),
                r_interaccion.created_at
            )
            RETURNING tiempo_id INTO v_tiempo_id;
        END IF;
        
        -- Obtener tipo_evento_id o crear si no existe
        SELECT tipo_evento_id INTO v_tipo_evento_id 
        FROM dim_tipos_eventos 
        WHERE nombre = r_interaccion.tipo_nombre
        LIMIT 1;
        
        IF v_tipo_evento_id IS NULL THEN
            INSERT INTO dim_tipos_eventos (categoria, nombre, descripcion)
            VALUES ('lead', r_interaccion.tipo_nombre, 'Interacción migrada de lead_interactions')
            RETURNING tipo_evento_id INTO v_tipo_evento_id;
        END IF;
        
        -- Determinar origen y destino de la interacción
        SELECT entidad_id INTO v_entidad_origen_id
        FROM dim_entidades
        WHERE tipo_entidad = 'lead' AND entidad_original_id = r_interaccion.lead_id;
        
        IF r_interaccion.agente_id IS NOT NULL THEN
            SELECT entidad_id INTO v_entidad_destino_id
            FROM dim_entidades
            WHERE tipo_entidad = 'agente' AND entidad_original_id = r_interaccion.agente_id;
        END IF;
        
        -- Obtener empresa_id desde el lead
        INSERT INTO fact_eventos_acciones (
            tiempo_id, empresa_id, tipo_evento_id, entidad_origen_id, entidad_destino_id,
            lead_id, agente_id, conversacion_id, mensaje_id,
            valor_score, detalle, metadata, created_at
        )
        SELECT 
            v_tiempo_id, l.empresa_id, v_tipo_evento_id, v_entidad_origen_id, v_entidad_destino_id,
            r_interaccion.lead_id, r_interaccion.agente_id, r_interaccion.conversacion_id, r_interaccion.mensaje_id,
            r_interaccion.valor_score, r_interaccion.notas, r_interaccion.metadata, r_interaccion.created_at
        FROM leads l
        WHERE l.id = r_interaccion.lead_id;
    END LOOP;
    
    -- 2. Migrar eventos de la tabla eventos
    FOR r_evento IN 
        SELECT * FROM eventos
    LOOP
        -- Obtener tiempo_id
        SELECT tiempo_id INTO v_tiempo_id 
        FROM dim_tiempo 
        WHERE fecha = DATE(r_evento.created_at)
        LIMIT 1;
        
        -- Si no existe tiempo, crear
        IF v_tiempo_id IS NULL THEN
            INSERT INTO dim_tiempo (
                fecha, dia_semana, dia, semana, mes, trimestre, anio, 
                es_fin_semana, nombre_dia, nombre_mes, fecha_completa
            )
            VALUES (
                DATE(r_evento.created_at),
                EXTRACT(DOW FROM r_evento.created_at),
                EXTRACT(DAY FROM r_evento.created_at),
                EXTRACT(WEEK FROM r_evento.created_at),
                EXTRACT(MONTH FROM r_evento.created_at),
                EXTRACT(QUARTER FROM r_evento.created_at),
                EXTRACT(YEAR FROM r_evento.created_at),
                CASE WHEN EXTRACT(DOW FROM r_evento.created_at) IN (0, 6) THEN TRUE ELSE FALSE END,
                TO_CHAR(r_evento.created_at, 'Day'),
                TO_CHAR(r_evento.created_at, 'Month'),
                r_evento.created_at
            )
            RETURNING tiempo_id INTO v_tiempo_id;
        END IF;
        
        -- Obtener tipo_evento_id o crear si no existe
        SELECT tipo_evento_id INTO v_tipo_evento_id 
        FROM dim_tipos_eventos 
        WHERE nombre = r_evento.tipo
        LIMIT 1;
        
        IF v_tipo_evento_id IS NULL THEN
            INSERT INTO dim_tipos_eventos (categoria, nombre, descripcion)
            VALUES (r_evento.entidad_tipo, r_evento.tipo, 'Evento migrado de tabla eventos')
            RETURNING tipo_evento_id INTO v_tipo_evento_id;
        END IF;
        
        -- Determinar origen y destino del evento
        SELECT entidad_id INTO v_entidad_origen_id
        FROM dim_entidades
        WHERE tipo_entidad = r_evento.entidad_tipo AND entidad_original_id = r_evento.entidad_id;
        
        IF v_entidad_origen_id IS NULL THEN
            INSERT INTO dim_entidades (tipo_entidad, entidad_original_id, nombre)
            VALUES (r_evento.entidad_tipo, r_evento.entidad_id, r_evento.entidad_tipo || ' ' || r_evento.entidad_id)
            RETURNING entidad_id INTO v_entidad_origen_id;
        END IF;
        
        -- Insertar en la tabla de hechos
        INSERT INTO fact_eventos_acciones (
            tiempo_id, empresa_id, tipo_evento_id, entidad_origen_id,
            metadata, resultado, created_at
        ) VALUES (
            v_tiempo_id, r_evento.empresa_id, v_tipo_evento_id, v_entidad_origen_id,
            r_evento.datos, CASE WHEN r_evento.procesado THEN 'procesado' ELSE 'pendiente' END, r_evento.created_at
        );
    END LOOP;
    
    -- 3. Migrar mensajes relevantes
    FOR r_mensaje IN 
        SELECT m.*, c.lead_id, c.empresa_id, c.chatbot_id, c.canal_id
        FROM mensajes m
        JOIN conversaciones c ON m.conversacion_id = c.id
        WHERE m.score_impacto > 3 -- Solo mensajes con impacto significativo
    LOOP
        -- Obtener tiempo_id
        SELECT tiempo_id INTO v_tiempo_id 
        FROM dim_tiempo 
        WHERE fecha = DATE(r_mensaje.created_at)
        LIMIT 1;
        
        -- Si no existe tiempo, crear
        IF v_tiempo_id IS NULL THEN
            INSERT INTO dim_tiempo (
                fecha, dia_semana, dia, semana, mes, trimestre, anio, 
                es_fin_semana, nombre_dia, nombre_mes, fecha_completa
            )
            VALUES (
                DATE(r_mensaje.created_at),
                EXTRACT(DOW FROM r_mensaje.created_at),
                EXTRACT(DAY FROM r_mensaje.created_at),
                EXTRACT(WEEK FROM r_mensaje.created_at),
                EXTRACT(MONTH FROM r_mensaje.created_at),
                EXTRACT(QUARTER FROM r_mensaje.created_at),
                EXTRACT(YEAR FROM r_mensaje.created_at),
                CASE WHEN EXTRACT(DOW FROM r_mensaje.created_at) IN (0, 6) THEN TRUE ELSE FALSE END,
                TO_CHAR(r_mensaje.created_at, 'Day'),
                TO_CHAR(r_mensaje.created_at, 'Month'),
                r_mensaje.created_at
            )
            RETURNING tiempo_id INTO v_tiempo_id;
        END IF;
        
        -- Determinar tipo de evento según origen
        SELECT tipo_evento_id INTO v_tipo_evento_id 
        FROM dim_tipos_eventos 
        WHERE 
            CASE 
                WHEN r_mensaje.origen = 'chatbot' THEN nombre = 'respuesta_chatbot' AND categoria = 'chatbot'
                WHEN r_mensaje.origen = 'agente' THEN nombre = 'respuesta_agente' AND categoria = 'agente'
                WHEN r_mensaje.origen = 'lead' THEN nombre = 'mensaje_lead' AND categoria = 'lead'
                WHEN r_mensaje.origen = 'canal' THEN nombre = 'mensaje_recibido' AND categoria = 'canal'
                ELSE nombre = 'mensaje_sistema' AND categoria = 'sistema'
            END
        LIMIT 1;
        
        IF v_tipo_evento_id IS NULL THEN
            INSERT INTO dim_tipos_eventos (categoria, nombre, descripcion)
            VALUES (
                CASE 
                    WHEN r_mensaje.origen = 'chatbot' THEN 'chatbot'
                    WHEN r_mensaje.origen = 'agente' THEN 'agente'
                    WHEN r_mensaje.origen = 'lead' THEN 'lead'
                    WHEN r_mensaje.origen = 'canal' THEN 'canal'
                    ELSE 'sistema'
                END,
                CASE 
                    WHEN r_mensaje.origen = 'chatbot' THEN 'respuesta_chatbot'
                    WHEN r_mensaje.origen = 'agente' THEN 'respuesta_agente'
                    WHEN r_mensaje.origen = 'lead' THEN 'mensaje_lead'
                    WHEN r_mensaje.origen = 'canal' THEN 'mensaje_recibido'
                    ELSE 'mensaje_sistema'
                END,
                'Evento de mensaje migrado'
            )
            RETURNING tipo_evento_id INTO v_tipo_evento_id;
        END IF;
        
        -- Determinar entidad origen
        SELECT entidad_id INTO v_entidad_origen_id
        FROM dim_entidades
        WHERE 
            CASE 
                WHEN r_mensaje.origen = 'chatbot' THEN tipo_entidad = 'chatbot' AND entidad_original_id = r_mensaje.remitente_id
                WHEN r_mensaje.origen = 'agente' THEN tipo_entidad = 'agente' AND entidad_original_id = r_mensaje.remitente_id
                WHEN r_mensaje.origen = 'lead' THEN tipo_entidad = 'lead' AND entidad_original_id = r_mensaje.remitente_id
                WHEN r_mensaje.origen = 'canal' THEN tipo_entidad = 'canal' AND entidad_original_id = r_mensaje.canal_id
                ELSE tipo_entidad = 'sistema' AND entidad_original_id = r_mensaje.remitente_id
            END;
        
        -- Insertar en la tabla de hechos
        INSERT INTO fact_eventos_acciones (
            tiempo_id, empresa_id, tipo_evento_id, entidad_origen_id,
            lead_id, agente_id, chatbot_id, canal_id, conversacion_id, mensaje_id,
            valor_score, detalle, metadata, created_at
        ) VALUES (
            v_tiempo_id, r_mensaje.empresa_id, v_tipo_evento_id, v_entidad_origen_id,
            r_mensaje.lead_id, 
            CASE WHEN r_mensaje.origen = 'agente' THEN r_mensaje.remitente_id ELSE NULL END,
            r_mensaje.chatbot_id,
            r_mensaje.canal_id,
            r_mensaje.conversacion_id,
            r_mensaje.id,
            r_mensaje.score_impacto,
            LEFT(r_mensaje.contenido, 100),
            jsonb_build_object(
                'contenido_completo', r_mensaje.contenido,
                'tipo_contenido', r_mensaje.tipo_contenido,
                'metadata', r_mensaje.metadata,
                'leido', r_mensaje.leido
            ),
            r_mensaje.created_at
        );
    END LOOP;
    
END;
$$ LANGUAGE plpgsql;

-- Ejecutar la migración
SELECT migrar_datos_historicos();
