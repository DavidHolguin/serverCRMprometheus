-- Agregar nuevo tipo de evento para errores en la carga de conocimiento de agentes
INSERT INTO dim_tipos_eventos (tipo_evento_id, categoria, nombre, descripcion, impacto_score, requiere_seguimiento, grupo_analisis)
VALUES
    (21, 'agente', 'agent_knowledge_error', 'Error en la carga de conocimiento para agente', 3, true, 'system_health')
ON CONFLICT (tipo_evento_id) DO UPDATE
SET 
    categoria = EXCLUDED.categoria,
    nombre = EXCLUDED.nombre,
    descripcion = EXCLUDED.descripcion,
    impacto_score = EXCLUDED.impacto_score,
    requiere_seguimiento = EXCLUDED.requiere_seguimiento,
    grupo_analisis = EXCLUDED.grupo_analisis,
    is_active = true;

-- En caso que el tipo_evento_id 21 ya esté usado, agregar una alternativa con el próximo ID disponible
INSERT INTO dim_tipos_eventos (tipo_evento_id, categoria, nombre, descripcion, impacto_score, requiere_seguimiento, grupo_analisis)
SELECT 
    COALESCE((SELECT MAX(tipo_evento_id) + 1 FROM dim_tipos_eventos), 50),
    'agente', 
    'agent_knowledge_error', 
    'Error en la carga de conocimiento para agente', 
    3, 
    true, 
    'system_health'
WHERE NOT EXISTS (
    SELECT 1 FROM dim_tipos_eventos WHERE nombre = 'agent_knowledge_error'
);