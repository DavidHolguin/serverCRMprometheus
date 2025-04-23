-- Trigger para registrar eventos cuando un agente inicia sesión
CREATE OR REPLACE FUNCTION trigger_agente_login() RETURNS TRIGGER AS $$
BEGIN
    -- Suponiendo que hay un campo last_sign_in que se actualiza
    IF OLD.last_sign_in IS DISTINCT FROM NEW.last_sign_in THEN
        PERFORM registrar_evento(
            NEW.empresa_id, 
            'login', 
            'agente',
            'agente', 
            NEW.id,
            NULL, 
            NULL,
            NULL, 
            NEW.id,
            NULL, 
            NULL,
            NULL, 
            NULL,
            NULL, 
            NULL,
            'exitoso', 
            'activo',
            'Agente ' || NEW.full_name || ' inició sesión',
            jsonb_build_object('ip', current_setting('request.headers', true)::jsonb->>'x-forwarded-for')
        );
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER tr_agente_login
AFTER UPDATE OF last_sign_in ON profiles
FOR EACH ROW
EXECUTE FUNCTION trigger_agente_login();

-- Trigger para registrar eventos cuando un lead cambia de etapa
CREATE OR REPLACE FUNCTION trigger_lead_cambio_etapa() RETURNS TRIGGER AS $$
DECLARE
    v_empresa_id UUID;
    v_agente_id UUID;
BEGIN
    -- Obtener la empresa_id del lead
    SELECT empresa_id, asignado_a INTO v_empresa_id, v_agente_id 
    FROM leads 
    WHERE id = NEW.lead_id;
    
    -- Registrar el evento
    PERFORM registrar_evento(
        v_empresa_id, 
        'cambio_estado_lead', 
        'lead',
        'lead', 
        NEW.lead_id,
        'stage', 
        NEW.stage_id_nuevo,
        NEW.lead_id, 
        v_agente_id,
        NULL, 
        NULL,
        NULL, 
        NULL,
        NULL, 
        NEW.tiempo_en_stage::interval::integer,
        'completado', 
        'actualizado',
        'Lead cambió de etapa ' || NEW.stage_id_anterior || ' a ' || NEW.stage_id_nuevo,
        jsonb_build_object(
            'stage_anterior', NEW.stage_id_anterior,
            'stage_nuevo', NEW.stage_id_nuevo,
            'tiempo_en_stage', NEW.tiempo_en_stage,
            'motivo', NEW.motivo
        )
    );
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER tr_lead_cambio_etapa
AFTER INSERT ON lead_stage_history
FOR EACH ROW
EXECUTE FUNCTION trigger_lead_cambio_etapa();

-- Trigger para registrar eventos de chatbot
CREATE OR REPLACE FUNCTION trigger_chatbot_mensaje() RETURNS TRIGGER AS $$
DECLARE
    v_empresa_id UUID;
    v_lead_id UUID;
BEGIN
    -- Obtener empresa_id y lead_id desde la conversación
    SELECT c.chatbot_id, c.lead_id INTO v_empresa_id, v_lead_id
    FROM conversaciones c
    WHERE c.id = NEW.conversacion_id;
    
    -- Si es un mensaje del chatbot
    IF NEW.origen = 'chatbot' THEN
        PERFORM registrar_evento(
            v_empresa_id, 
            'respuesta_chatbot', 
            'chatbot',
            'chatbot', 
            NEW.remitente_id,
            'lead', 
            v_lead_id,
            v_lead_id, 
            NULL,
            NEW.remitente_id, 
            NULL,
            NEW.conversacion_id, 
            NEW.id,
            NEW.score_impacto, 
            NULL,
            'enviado', 
            NULL,
            LEFT(NEW.contenido, 100) || '...',
            jsonb_build_object(
                'contenido_completo', NEW.contenido,
                'tipo_contenido', NEW.tipo_contenido,
                'metadata', NEW.metadata
            )
        );
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER tr_chatbot_mensaje
AFTER INSERT ON mensajes
FOR EACH ROW
WHEN (NEW.origen = 'chatbot')
EXECUTE FUNCTION trigger_chatbot_mensaje();

-- Trigger para registrar eventos de canal
CREATE OR REPLACE FUNCTION trigger_canal_mensaje() RETURNS TRIGGER AS $$
DECLARE
    v_empresa_id UUID;
    v_lead_id UUID;
BEGIN
    -- Obtener empresa_id y lead_id desde la conversación
    SELECT c.canal_id, c.lead_id INTO v_empresa_id, v_lead_id
    FROM conversaciones c
    WHERE c.id = NEW.conversacion_id;
    
    PERFORM registrar_evento(
        v_empresa_id, 
        'mensaje_recibido', 
        'canal',
        'canal', 
        NEW.remitente_id,
        'conversacion', 
        NEW.conversacion_id,
        v_lead_id, 
        NULL,
        NULL, 
        v_empresa_id,
        NEW.conversacion_id, 
        NEW.id,
        NULL, 
        NULL,
        'recibido', 
        NULL,
        'Mensaje recibido en canal',
        jsonb_build_object(
            'origen', NEW.origen,
            'tipo_contenido', NEW.tipo_contenido
        )
    );
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER tr_canal_mensaje
AFTER INSERT ON mensajes
FOR EACH ROW
WHEN (NEW.origen = 'canal')
EXECUTE FUNCTION trigger_canal_mensaje();
