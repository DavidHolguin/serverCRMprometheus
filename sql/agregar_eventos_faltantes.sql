-- Agregar tipos de eventos faltantes a dim_tipos_eventos
-- Script creado el 23 de abril de 2025

-- Agregar evento para respuestas del chatbot
INSERT INTO dim_tipos_eventos 
(tipo_evento_id, categoria, nombre, descripcion, impacto_score, requiere_seguimiento, grupo_analisis, is_active, created_at, updated_at)
VALUES 
(gen_random_uuid(), 'chatbot', 'chatbot_respuesta', 'Respuesta enviada por el chatbot', 3, false, 'comunicacion', true, NOW(), NOW());

-- Agregar evento para errores del sistema
INSERT INTO dim_tipos_eventos 
(tipo_evento_id, categoria, nombre, descripcion, impacto_score, requiere_seguimiento, grupo_analisis, is_active, created_at, updated_at)
VALUES 
(gen_random_uuid(), 'sistema', 'error_sistema', 'Error ocurrido en el sistema', 5, true, 'errores', true, NOW(), NOW());

-- Agregar evento para mensajes enviados
INSERT INTO dim_tipos_eventos 
(tipo_evento_id, categoria, nombre, descripcion, impacto_score, requiere_seguimiento, grupo_analisis, is_active, created_at, updated_at)
VALUES 
(gen_random_uuid(), 'canal', 'mensaje_enviado', 'Mensaje enviado a través de canal', 2, false, 'trafico', true, NOW(), NOW());

-- Agregar evento para evaluación de lead
INSERT INTO dim_tipos_eventos 
(tipo_evento_id, categoria, nombre, descripcion, impacto_score, requiere_seguimiento, grupo_analisis, is_active, created_at, updated_at)
VALUES 
(gen_random_uuid(), 'lead', 'evaluacion_lead', 'Evaluación automática del lead', 3, false, 'calificacion', true, NOW(), NOW());

-- Agregar evento para cambio de estado del chatbot
INSERT INTO dim_tipos_eventos 
(tipo_evento_id, categoria, nombre, descripcion, impacto_score, requiere_seguimiento, grupo_analisis, is_active, created_at, updated_at)
VALUES 
(gen_random_uuid(), 'chatbot', 'cambio_estado_chatbot', 'Cambio en el estado del chatbot', 2, false, 'configuracion', true, NOW(), NOW());