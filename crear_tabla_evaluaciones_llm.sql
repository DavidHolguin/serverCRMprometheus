
CREATE TABLE IF NOT EXISTS public.evaluaciones_llm (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    lead_id UUID NOT NULL REFERENCES public.leads(id) ON DELETE CASCADE,
    conversacion_id UUID NOT NULL REFERENCES public.conversaciones(id) ON DELETE CASCADE,
    mensaje_id UUID NOT NULL REFERENCES public.mensajes(id) ON DELETE CASCADE,
    fecha_evaluacion TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    score_potencial INTEGER NOT NULL CHECK (score_potencial BETWEEN 1 AND 10),
    score_satisfaccion INTEGER NOT NULL CHECK (score_satisfaccion BETWEEN 1 AND 10),
    interes_productos TEXT[] DEFAULT '{}',
    comentario TEXT,
    palabras_clave TEXT[] DEFAULT '{}',
    llm_configuracion_id UUID,
    prompt_utilizado TEXT
);

CREATE INDEX IF NOT EXISTS idx_evaluaciones_llm_lead_id ON public.evaluaciones_llm(lead_id);
CREATE INDEX IF NOT EXISTS idx_evaluaciones_llm_conversacion_id ON public.evaluaciones_llm(conversacion_id);

