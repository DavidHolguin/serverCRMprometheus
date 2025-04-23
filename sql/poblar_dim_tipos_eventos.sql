-- Poblar la tabla dim_tipos_eventos con los tipos de eventos iniciales del sistema
-- Estos IDs deben coincidir con los definidos en el EventService

-- Eliminar los registros existentes (opcional, comentar si no se quiere eliminar)
-- DELETE FROM dim_tipos_eventos;

-- Insertar tipos de eventos básicos
INSERT INTO dim_tipos_eventos (tipo_evento_id, categoria, nombre, descripcion, impacto_score, requiere_seguimiento, grupo_analisis)
VALUES
    -- Tipos de eventos de conversaciones
    (1, 'conversacion', 'conversation_created', 'Creación de nueva conversación', 2, false, 'engagement'),
    (2, 'mensaje', 'message_received', 'Mensaje recibido del lead', 3, false, 'engagement'),
    (3, 'mensaje', 'chatbot_response', 'Respuesta generada por chatbot', 2, false, 'chatbot_performance'),
    (4, 'mensaje', 'message_sent_to_channel', 'Mensaje enviado a canal', 1, false, 'channel_performance'),
    (5, 'evaluacion', 'lead_evaluation_started', 'Inicio de evaluación de lead', 1, false, 'lead_scoring'),
    (6, 'configuracion', 'chatbot_status_changed', 'Cambio de estado del chatbot', 2, true, 'agent_activity'),
    (7, 'lead', 'lead_created', 'Creación de nuevo lead', 4, true, 'lead_acquisition'),
    (8, 'error', 'error_occurred', 'Error en el sistema', 3, true, 'system_health'),
    
    -- Tipos de eventos adicionales para interacciones
    (9, 'agente', 'agent_message', 'Mensaje enviado por agente', 3, false, 'agent_activity'),
    (10, 'agente', 'agent_assigned', 'Asignación de agente a lead', 3, true, 'agent_activity'),
    (11, 'lead', 'lead_stage_changed', 'Cambio de etapa del lead', 4, true, 'lead_journey'),
    (12, 'lead', 'lead_score_updated', 'Actualización de score de lead', 2, false, 'lead_scoring'),
    (13, 'evaluacion', 'lead_evaluation_completed', 'Evaluación de lead completada', 2, false, 'lead_scoring'),
    (14, 'interaccion', 'product_interest_detected', 'Interés en producto detectado', 5, true, 'lead_interests'),
    (15, 'interaccion', 'lead_intention_detected', 'Intención detectada en lead', 4, true, 'lead_journey'),
    (16, 'automatizacion', 'automation_triggered', 'Automatización activada', 3, false, 'system_automation'),
    (17, 'automatizacion', 'automation_executed', 'Automatización ejecutada', 2, false, 'system_automation'),
    (18, 'marketing', 'marketing_campaign_interaction', 'Interacción con campaña de marketing', 3, false, 'marketing_performance'),
    (19, 'configuracion', 'chatbot_config_updated', 'Configuración de chatbot actualizada', 2, false, 'chatbot_performance'),
    (20, 'sistema', 'system_health_check', 'Verificación de salud del sistema', 1, false, 'system_health')
ON CONFLICT (tipo_evento_id) DO UPDATE
SET 
    categoria = EXCLUDED.categoria,
    nombre = EXCLUDED.nombre,
    descripcion = EXCLUDED.descripcion,
    impacto_score = EXCLUDED.impacto_score,
    requiere_seguimiento = EXCLUDED.requiere_seguimiento,
    grupo_analisis = EXCLUDED.grupo_analisis,
    is_active = true;