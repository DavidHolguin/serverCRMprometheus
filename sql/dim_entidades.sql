CREATE TABLE IF NOT EXISTS dim_entidades (
    entidad_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tipo_entidad VARCHAR(50) NOT NULL, -- agente, lead, chatbot, canal, etc.
    entidad_original_id UUID NOT NULL, -- ID de la entidad en su tabla original
    nombre VARCHAR(255),
    descripcion TEXT,
    metadata JSONB,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Índices
CREATE INDEX idx_dim_entidades_tipo_id ON dim_entidades(tipo_entidad, entidad_original_id);

-- Función para mantener actualizada la dimensión de entidades
CREATE OR REPLACE FUNCTION actualizar_dim_entidades() RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        INSERT INTO dim_entidades (
            tipo_entidad, 
            entidad_original_id, 
            nombre, 
            descripcion, 
            metadata, 
            is_active
        )
        VALUES (
            TG_ARGV[0], -- tipo de entidad pasado como argumento al trigger
            NEW.id,
            CASE 
                WHEN TG_ARGV[0] = 'agente' THEN NEW.full_name
                WHEN TG_ARGV[0] = 'chatbot' THEN NEW.nombre
                WHEN TG_ARGV[0] = 'canal' THEN NEW.nombre
                ELSE 'Desconocido'
            END,
            CASE 
                WHEN TG_ARGV[0] = 'agente' THEN NULL
                WHEN TG_ARGV[0] = 'chatbot' THEN NEW.descripcion
                WHEN TG_ARGV[0] = 'canal' THEN NEW.descripcion
                ELSE NULL
            END,
            CASE 
                WHEN TG_ARGV[0] = 'agente' THEN jsonb_build_object('email', NEW.email, 'role', NEW.role)
                WHEN TG_ARGV[0] = 'chatbot' THEN jsonb_build_object('avatar_url', NEW.avatar_url)
                WHEN TG_ARGV[0] = 'canal' THEN jsonb_build_object('tipo', NEW.tipo, 'logo_url', NEW.logo_url, 'color', NEW.color)
                ELSE '{}'::jsonb
            END,
            COALESCE(NEW.is_active, TRUE)
        );
    ELSIF TG_OP = 'UPDATE' THEN
        UPDATE dim_entidades
        SET 
            nombre = CASE 
                WHEN TG_ARGV[0] = 'agente' THEN NEW.full_name
                WHEN TG_ARGV[0] = 'chatbot' THEN NEW.nombre
                WHEN TG_ARGV[0] = 'canal' THEN NEW.nombre
                ELSE nombre
            END,
            descripcion = CASE 
                WHEN TG_ARGV[0] = 'agente' THEN descripcion
                WHEN TG_ARGV[0] = 'chatbot' THEN NEW.descripcion
                WHEN TG_ARGV[0] = 'canal' THEN NEW.descripcion
                ELSE descripcion
            END,
            metadata = CASE 
                WHEN TG_ARGV[0] = 'agente' THEN jsonb_build_object('email', NEW.email, 'role', NEW.role)
                WHEN TG_ARGV[0] = 'chatbot' THEN jsonb_build_object('avatar_url', NEW.avatar_url)
                WHEN TG_ARGV[0] = 'canal' THEN jsonb_build_object('tipo', NEW.tipo, 'logo_url', NEW.logo_url, 'color', NEW.color)
                ELSE metadata
            END,
            is_active = COALESCE(NEW.is_active, is_active),
            updated_at = NOW()
        WHERE 
            tipo_entidad = TG_ARGV[0] AND 
            entidad_original_id = NEW.id;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

-- Aplicar triggers para las principales entidades
CREATE TRIGGER tr_actualizar_agente_entidad
AFTER INSERT OR UPDATE ON profiles
FOR EACH ROW
EXECUTE FUNCTION actualizar_dim_entidades('agente');

CREATE TRIGGER tr_actualizar_chatbot_entidad
AFTER INSERT OR UPDATE ON chatbots
FOR EACH ROW
EXECUTE FUNCTION actualizar_dim_entidades('chatbot');

CREATE TRIGGER tr_actualizar_canal_entidad
AFTER INSERT OR UPDATE ON canales
FOR EACH ROW
EXECUTE FUNCTION actualizar_dim_entidades('canal');

-- Poblar inicialmente la tabla con datos existentes
INSERT INTO dim_entidades (tipo_entidad, entidad_original_id, nombre, is_active, created_at)
SELECT 'agente', id, full_name, is_active, created_at FROM profiles;

INSERT INTO dim_entidades (tipo_entidad, entidad_original_id, nombre, descripcion, is_active, created_at)
SELECT 'chatbot', id, nombre, descripcion, is_active, created_at FROM chatbots;

INSERT INTO dim_entidades (tipo_entidad, entidad_original_id, nombre, descripcion, metadata, is_active, created_at)
SELECT 'canal', id, nombre, descripcion, 
       jsonb_build_object('tipo', tipo, 'logo_url', logo_url, 'color', color),
       is_active, created_at FROM canales;

INSERT INTO dim_entidades (tipo_entidad, entidad_original_id, nombre, created_at)
SELECT 'lead', id, COALESCE(
    (SELECT CONCAT(dp.nombre, ' ', dp.apellido) 
     FROM lead_datos_personales dp 
     WHERE dp.lead_id = leads.id), 
    'Lead ' || SUBSTRING(id::text, 1, 8)
), created_at FROM leads;
