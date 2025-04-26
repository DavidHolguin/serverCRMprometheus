-- Agregar nuevo tipo de evento para errores en la carga de conocimiento de agentes
INSERT INTO dim_tipos_eventos (tipo_evento_id, categoria, nombre, descripcion, impacto_score, requiere_seguimiento, grupo_analisis)
VALUES
    (uuid_generate_v4(), 'agente', 'agent_knowledge_error', 'Error en la carga de conocimiento para agente', 3, true, 'system_health')
ON CONFLICT (nombre) DO UPDATE
SET 
    categoria = EXCLUDED.categoria,
    descripcion = EXCLUDED.descripcion,
    impacto_score = EXCLUDED.impacto_score,
    requiere_seguimiento = EXCLUDED.requiere_seguimiento,
    grupo_analisis = EXCLUDED.grupo_analisis,
    is_active = true;