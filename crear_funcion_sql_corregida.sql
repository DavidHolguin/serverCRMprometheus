
CREATE OR REPLACE FUNCTION public.ejecutar_sql(sql text)
RETURNS SETOF json
LANGUAGE plpgsql
SECURITY DEFINER
AS c:\Users\Juliana\Videos\laboratorio prometeo\servidorCRM
BEGIN
  RETURN QUERY EXECUTE 'SELECT row_to_json(t) FROM (' || sql || ') t';
END;
c:\Users\Juliana\Videos\laboratorio prometeo\servidorCRM;

