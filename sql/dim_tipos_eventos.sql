CREATE TABLE IF NOT EXISTS dim_tipos_eventos (
    tipo_evento_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    categoria VARCHAR(50) NOT NULL,  -- agente, chatbot, lead, canal, sistema
    nombre VARCHAR(100) NOT NULL,
    descripcion TEXT,
    impacto_score INTEGER,  -- valor de impacto para métricas
    requiere_seguimiento BOOLEAN DEFAULT FALSE,
    grupo_analisis VARCHAR(50),  -- para agrupar eventos relacionados
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Insertar tipos de eventos comunes
INSERT INTO dim_tipos_eventos (categoria, nombre, descripcion, impacto_score, requiere_seguimiento, grupo_analisis)
VALUES
    -- Eventos de agentes
    ('agente', 'login', 'Agente inició sesión', 1, FALSE, 'actividad_agente'),
    ('agente', 'logout', 'Agente cerró sesión', 1, FALSE, 'actividad_agente'),
    ('agente', 'asignacion_lead', 'Lead asignado a agente', 3, TRUE, 'manejo_leads'),
    ('agente', 'transferencia_lead', 'Lead transferido entre agentes', 4, TRUE, 'manejo_leads'),
    ('agente', 'cambio_estado_lead', 'Cambio de estado/etapa de lead por agente', 5, TRUE, 'manejo_leads'),
    ('agente', 'nota_agregada', 'Agente agregó una nota o comentario', 2, FALSE, 'seguimiento'),
    ('agente', 'respuesta_rapida', 'Agente usó respuesta rápida/plantilla', 3, FALSE, 'comunicacion'),
    ('agente', 'tiempo_respuesta', 'Tiempo de respuesta del agente', 4, TRUE, 'rendimiento'),
    ('agente', 'calificacion_recibida', 'Agente recibió calificación', 5, TRUE, 'rendimiento'),
    
    -- Eventos de chatbot
    ('chatbot', 'conversacion_iniciada', 'Chatbot inició conversación', 3, TRUE, 'engagement'),
    ('chatbot', 'conversacion_transferida', 'Chatbot transfirió conversación a agente', 4, TRUE, 'escalacion'),
    ('chatbot', 'intent_no_reconocido', 'Chatbot no reconoció la intención', 2, FALSE, 'calidad'),
    ('chatbot', 'respuesta_evaluada', 'Respuesta del chatbot fue evaluada', 3, TRUE, 'calidad'),
    ('chatbot', 'lead_calificado', 'Chatbot calificó un lead', 5, TRUE, 'calificacion'),
    
    -- Eventos de canales
    ('canal', 'configuracion_actualizada', 'Configuración de canal actualizada', 2, FALSE, 'admin'),
    ('canal', 'integracion_error', 'Error en integración de canal', 5, TRUE, 'errores'),
    ('canal', 'mensaje_recibido', 'Mensaje recibido en canal', 2, FALSE, 'trafico'),
    ('canal', 'canal_inactivo', 'Canal marcado como inactivo', 4, TRUE, 'admin'),
    
    -- Eventos de leads
    ('lead', 'primera_interaccion', 'Primera interacción del lead', 5, TRUE, 'adquisicion'),
    ('lead', 'solicitud_informacion', 'Lead solicitó información específica', 4, TRUE, 'interes'),
    ('lead', 'queja', 'Lead presentó una queja', 5, TRUE, 'satisfaccion'),
    ('lead', 'inactividad', 'Lead inactivo por período extendido', 3, TRUE, 'engagement'),
    
    -- Eventos de sistema
    ('sistema', 'automatizacion_ejecutada', 'Se ejecutó un flujo de automatización', 3, FALSE, 'automatizacion'),
    ('sistema', 'error_integracion', 'Error en integración con sistema externo', 4, TRUE, 'errores'),
    ('sistema', 'backup_completado', 'Backup de datos completado', 1, FALSE, 'mantenimiento');
