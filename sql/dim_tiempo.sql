CREATE TABLE IF NOT EXISTS dim_tiempo (
    tiempo_id SERIAL PRIMARY KEY,
    fecha DATE NOT NULL,
    hora TIME WITHOUT TIME ZONE,
    dia_semana SMALLINT,
    dia INTEGER,
    semana INTEGER,
    mes INTEGER,
    trimestre INTEGER,
    anio INTEGER,
    es_fin_semana BOOLEAN,
    es_feriado BOOLEAN,
    nombre_dia VARCHAR(10),
    nombre_mes VARCHAR(10),
    fecha_completa TIMESTAMP WITH TIME ZONE
);

-- Función para poblar la tabla de dimensión tiempo
CREATE OR REPLACE FUNCTION poblar_dim_tiempo(fecha_inicio DATE, fecha_fin DATE) 
RETURNS void AS $$
DECLARE
    fecha_actual DATE;
BEGIN
    fecha_actual := fecha_inicio;
    
    WHILE fecha_actual <= fecha_fin LOOP
        INSERT INTO dim_tiempo (
            fecha, dia_semana, dia, semana, mes, trimestre, anio, 
            es_fin_semana, nombre_dia, nombre_mes, fecha_completa
        )
        VALUES (
            fecha_actual,
            EXTRACT(DOW FROM fecha_actual),
            EXTRACT(DAY FROM fecha_actual),
            EXTRACT(WEEK FROM fecha_actual),
            EXTRACT(MONTH FROM fecha_actual),
            EXTRACT(QUARTER FROM fecha_actual),
            EXTRACT(YEAR FROM fecha_actual),
            CASE WHEN EXTRACT(DOW FROM fecha_actual) IN (0, 6) THEN TRUE ELSE FALSE END,
            TO_CHAR(fecha_actual, 'Day'),
            TO_CHAR(fecha_actual, 'Month'),
            fecha_actual::TIMESTAMP WITH TIME ZONE
        );
        
        fecha_actual := fecha_actual + INTERVAL '1 day';
    END LOOP;
END;
$$ LANGUAGE plpgsql;

-- Poblar la tabla para los próximos 5 años desde hoy
SELECT poblar_dim_tiempo(CURRENT_DATE, CURRENT_DATE + INTERVAL '5 years');
