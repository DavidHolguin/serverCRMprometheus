-- Vista para análisis de actividad de agentes
CREATE OR REPLACE VIEW vw_analisis_actividad_agentes AS
SELECT 
    dt.anio,
    dt.mes,
    dt.nombre_mes,
    dt.semana,
    de.nombre AS agente_nombre,
    count(*) AS total_eventos,
    count(DISTINCT fa.lead_id) AS total_leads_atendidos,
    avg(fa.duracion_segundos) AS tiempo_respuesta_promedio,
    sum(CASE WHEN dte.nombre = 'respuesta_rapida' THEN 1 ELSE 0 END) AS total_respuestas_rapidas,
    sum(fa.valor_score) AS score_total,
    jsonb_object_agg(dte.nombre, count(*)) AS eventos_por_tipo
FROM 
    fact_eventos_acciones fa
    JOIN dim_tiempo dt ON fa.tiempo_id = dt.tiempo_id
    JOIN dim_entidades de ON fa.entidad_origen_id = de.entidad_id
    JOIN dim_tipos_eventos dte ON fa.tipo_evento_id = dte.tipo_evento_id
WHERE 
    de.tipo_entidad = 'agente'
    AND dte.categoria = 'agente'
GROUP BY 
    dt.anio, dt.mes, dt.nombre_mes, dt.semana, de.nombre
ORDER BY 
    dt.anio DESC, dt.mes DESC, dt.semana DESC, total_eventos DESC;

-- Vista para análisis de rendimiento de chatbots
CREATE OR REPLACE VIEW vw_analisis_rendimiento_chatbots AS
SELECT 
    dt.anio,
    dt.mes,
    dt.nombre_mes,
    de.nombre AS chatbot_nombre,
    count(*) AS total_interacciones,
    count(DISTINCT fa.lead_id) AS total_leads_atendidos,
    sum(CASE WHEN dte.nombre = 'conversacion_transferida' THEN 1 ELSE 0 END) AS transferencias_agente,
    sum(CASE WHEN dte.nombre = 'lead_calificado' THEN 1 ELSE 0 END) AS leads_calificados,
    sum(CASE WHEN dte.nombre = 'intent_no_reconocido' THEN 1 ELSE 0 END) AS intents_no_reconocidos,
    avg(CASE WHEN dte.nombre = 'respuesta_evaluada' THEN fa.valor_score ELSE NULL END) AS promedio_evaluacion
FROM 
    fact_eventos_acciones fa
    JOIN dim_tiempo dt ON fa.tiempo_id = dt.tiempo_id
    JOIN dim_entidades de ON fa.entidad_origen_id = de.entidad_id
    JOIN dim_tipos_eventos dte ON fa.tipo_evento_id = dte.tipo_evento_id
WHERE 
    de.tipo_entidad = 'chatbot'
    AND dte.categoria = 'chatbot'
GROUP BY 
    dt.anio, dt.mes, dt.nombre_mes, de.nombre
ORDER BY 
    dt.anio DESC, dt.mes DESC, total_interacciones DESC;

-- Vista para análisis de rendimiento de canales
CREATE OR REPLACE VIEW vw_analisis_rendimiento_canales AS
SELECT 
    dt.anio,
    dt.mes,
    dt.nombre_mes,
    de.nombre AS canal_nombre,
    (de.metadata->>'tipo')::text AS tipo_canal,
    count(*) AS total_eventos,
    count(DISTINCT fa.conversacion_id) AS total_conversaciones,
    count(DISTINCT fa.lead_id) AS total_leads,
    sum(CASE WHEN dte.nombre = 'integracion_error' THEN 1 ELSE 0 END) AS total_errores,
    avg(CASE WHEN fa.valor_score IS NOT NULL THEN fa.valor_score ELSE NULL END) AS promedio_score
FROM 
    fact_eventos_acciones fa
    JOIN dim_tiempo dt ON fa.tiempo_id = dt.tiempo_id
    JOIN dim_entidades de ON fa.entidad_origen_id = de.entidad_id
    JOIN dim_tipos_eventos dte ON fa.tipo_evento_id = dte.tipo_evento_id
WHERE 
    de.tipo_entidad = 'canal'
    AND dte.categoria = 'canal'
GROUP BY 
    dt.anio, dt.mes, dt.nombre_mes, de.nombre, de.metadata->>'tipo'
ORDER BY 
    dt.anio DESC, dt.mes DESC, total_eventos DESC;

-- Vista para análisis de journey de leads
CREATE OR REPLACE VIEW vw_analisis_journey_leads AS
WITH eventos_lead AS (
    SELECT 
        fa.lead_id,
        min(dt.fecha_completa) AS fecha_primera_interaccion,
        max(dt.fecha_completa) AS fecha_ultima_interaccion,
        count(*) AS total_interacciones,
        array_agg(DISTINCT de.tipo_entidad) AS entidades_interaccion,
        count(DISTINCT fa.conversacion_id) AS total_conversaciones,
        sum(fa.valor_score) AS suma_score,
        jsonb_object_agg(dte.nombre, count(*)) AS eventos_por_tipo
    FROM 
        fact_eventos_acciones fa
        JOIN dim_tiempo dt ON fa.tiempo_id = dt.tiempo_id
        JOIN dim_tipos_eventos dte ON fa.tipo_evento_id = dte.tipo_evento_id
        JOIN dim_entidades de ON fa.entidad_origen_id = de.entidad_id
    WHERE 
        fa.lead_id IS NOT NULL
    GROUP BY 
        fa.lead_id
)
SELECT 
    l.id AS lead_id,
    COALESCE(ldp.nombre || ' ' || ldp.apellido, 'Lead ' || SUBSTRING(l.id::text, 1, 8)) AS lead_nombre,
    l.estado,
    ps.nombre AS stage_nombre,
    p.nombre AS pipeline_nombre,
    COALESCE(pr.full_name, 'Sin asignar') AS asignado_a,
    el.fecha_primera_interaccion,
    el.fecha_ultima_interaccion,
    el.total_interacciones,
    el.total_conversaciones,
    el.entidades_interaccion,
    el.suma_score,
    l.score AS score_actual,
    EXTRACT(DAY FROM (NOW() - el.fecha_primera_interaccion)) AS dias_desde_primera_interaccion,
    EXTRACT(DAY FROM (NOW() - el.fecha_ultima_interaccion)) AS dias_desde_ultima_interaccion,
    el.eventos_por_tipo
FROM 
    leads l
    LEFT JOIN eventos_lead el ON l.id = el.lead_id
    LEFT JOIN lead_datos_personales ldp ON l.id = ldp.lead_id
    LEFT JOIN pipeline_stages ps ON l.stage_id = ps.id
    LEFT JOIN pipelines p ON l.pipeline_id = p.id
    LEFT JOIN profiles pr ON l.asignado_a = pr.id
ORDER BY 
    el.fecha_ultima_interaccion DESC NULLS LAST;

-- Vista para KPIs generales del sistema
CREATE OR REPLACE VIEW vw_kpis_sistema AS
WITH kpis_por_empresa AS (
    SELECT 
        fa.empresa_id,
        date_trunc('day', dt.fecha_completa) AS fecha,
        count(DISTINCT fa.lead_id) AS leads_activos,
        count(DISTINCT CASE WHEN dte.categoria = 'agente' THEN fa.agente_id END) AS agentes_activos,
        count(DISTINCT CASE WHEN dte.categoria = 'chatbot' THEN fa.chatbot_id END) AS chatbots_activos,
        count(DISTINCT fa.conversacion_id) AS conversaciones_totales,
        count(DISTINCT CASE WHEN dte.nombre = 'conversacion_iniciada' THEN fa.conversacion_id END) AS conversaciones_nuevas,
        count(*) AS eventos_totales,
        avg(fa.valor_score) AS score_promedio,
        count(DISTINCT CASE WHEN dte.nombre = 'cambio_estado_lead' THEN fa.lead_id END) AS leads_con_cambio_estado
    FROM 
        fact_eventos_acciones fa
        JOIN dim_tiempo dt ON fa.tiempo_id = dt.tiempo_id
        JOIN dim_tipos_eventos dte ON fa.tipo_evento_id = dte.tipo_evento_id
    GROUP BY 
        fa.empresa_id, date_trunc('day', dt.fecha_completa)
)
SELECT 
    e.nombre AS empresa_nombre,
    kpe.fecha,
    kpe.leads_activos,
    kpe.agentes_activos,
    kpe.chatbots_activos,
    kpe.conversaciones_totales,
    kpe.conversaciones_nuevas,
    kpe.eventos_totales,
    kpe.score_promedio,
    kpe.leads_con_cambio_estado,
    
    -- Porcentajes y métricas derivadas
    ROUND((kpe.conversaciones_nuevas::numeric / NULLIF(kpe.conversaciones_totales, 0)) * 100, 2) AS porcentaje_conversaciones_nuevas,
    ROUND((kpe.leads_con_cambio_estado::numeric / NULLIF(kpe.leads_activos, 0)) * 100, 2) AS porcentaje_conversion_etapas,
    ROUND(kpe.eventos_totales::numeric / NULLIF(kpe.leads_activos, 0), 2) AS eventos_por_lead
FROM 
    kpis_por_empresa kpe
    JOIN empresas e ON kpe.empresa_id = e.id
ORDER BY 
    e.nombre, kpe.fecha DESC;
