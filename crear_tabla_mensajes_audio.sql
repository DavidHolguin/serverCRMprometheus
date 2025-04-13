-- Script para crear tabla de mensajes de audio y sus relaciones
-- Esta tabla almacenará referencias a los archivos de audio en el bucket de storage

-- Creación de la tabla para almacenar los mensajes de audio
CREATE TABLE IF NOT EXISTS public.mensajes_audio (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    mensaje_id UUID NOT NULL REFERENCES public.mensajes(id) ON DELETE CASCADE,
    conversacion_id UUID NOT NULL REFERENCES public.conversaciones(id) ON DELETE CASCADE,
    archivo_url TEXT NOT NULL,
    duracion_segundos NUMERIC,
    transcripcion TEXT,
    modelo_transcripcion TEXT,
    idioma_detectado TEXT,
    tamano_bytes INTEGER,
    formato TEXT,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Índices para mejorar el rendimiento
CREATE INDEX IF NOT EXISTS idx_mensajes_audio_mensaje_id ON public.mensajes_audio(mensaje_id);
CREATE INDEX IF NOT EXISTS idx_mensajes_audio_conversacion_id ON public.mensajes_audio(conversacion_id);

-- Trigger para actualizar automáticamente updated_at
CREATE OR REPLACE FUNCTION update_mensajes_audio_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_mensajes_audio_timestamp
BEFORE UPDATE ON public.mensajes_audio
FOR EACH ROW
EXECUTE FUNCTION update_mensajes_audio_updated_at();

-- Añadir políticas RLS (Row Level Security)
ALTER TABLE public.mensajes_audio ENABLE ROW LEVEL SECURITY;

-- Política para permitir a los usuarios autenticados ver sus propios audios
-- basados en la relación con la conversación y lead_id
CREATE POLICY mensajes_audio_select_policy ON public.mensajes_audio
    FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM public.conversaciones c
            JOIN public.leads l ON c.lead_id = l.id
            JOIN public.profiles p ON l.empresa_id = p.empresa_id
            WHERE c.id = mensajes_audio.conversacion_id
            AND p.id = auth.uid()
        )
    );

-- Política para permitir a los usuarios autenticados insertar audios
CREATE POLICY mensajes_audio_insert_policy ON public.mensajes_audio
    FOR INSERT
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM public.conversaciones c
            JOIN public.leads l ON c.lead_id = l.id
            JOIN public.profiles p ON l.empresa_id = p.empresa_id
            WHERE c.id = mensajes_audio.conversacion_id
            AND p.id = auth.uid()
        )
    );

-- Comentarios para documentación
COMMENT ON TABLE public.mensajes_audio IS 'Almacena los mensajes de audio y su transcripción';
COMMENT ON COLUMN public.mensajes_audio.mensaje_id IS 'Relación con el mensaje en la tabla mensajes';
COMMENT ON COLUMN public.mensajes_audio.conversacion_id IS 'ID de la conversación a la que pertenece el audio';
COMMENT ON COLUMN public.mensajes_audio.archivo_url IS 'URL del archivo de audio en el bucket de Supabase Storage';
COMMENT ON COLUMN public.mensajes_audio.transcripcion IS 'Texto transcrito del audio usando Whisper';
COMMENT ON COLUMN public.mensajes_audio.modelo_transcripcion IS 'Modelo de Whisper utilizado para la transcripción';