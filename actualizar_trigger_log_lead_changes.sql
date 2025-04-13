-- Archivo para actualizar el trigger log_lead_changes eliminando referencias a datos personales
-- Este archivo debe ejecutarse en la base de datos para corregir el error

-- Primero eliminamos el trigger existente
DROP TRIGGER IF EXISTS on_lead_updated ON public.leads;

-- Creamos una nueva función para el trigger que no accede a los campos de datos personales
CREATE OR REPLACE FUNCTION public.log_lead_changes()
RETURNS trigger AS $$
BEGIN
  IF TG_OP = 'UPDATE' THEN
    -- Registrar cambios en campos importantes (solo campos no personales)
    IF NEW.score IS DISTINCT FROM OLD.score THEN
      INSERT INTO public.lead_history (lead_id, campo, valor_anterior, valor_nuevo, usuario_id)
      VALUES (NEW.id, 'score', OLD.score::text, NEW.score::text, auth.uid());
    END IF;
    
    IF NEW.stage_id IS DISTINCT FROM OLD.stage_id THEN
      INSERT INTO public.lead_history (lead_id, campo, valor_anterior, valor_nuevo, usuario_id)
      VALUES (NEW.id, 'stage_id', OLD.stage_id::text, NEW.stage_id::text, auth.uid());
    END IF;
    
    IF NEW.asignado_a IS DISTINCT FROM OLD.asignado_a THEN
      INSERT INTO public.lead_history (lead_id, campo, valor_anterior, valor_nuevo, usuario_id)
      VALUES (NEW.id, 'asignado_a', OLD.asignado_a::text, NEW.asignado_a::text, auth.uid());
    END IF;
    
    IF NEW.estado IS DISTINCT FROM OLD.estado THEN
      INSERT INTO public.lead_history (lead_id, campo, valor_anterior, valor_nuevo, usuario_id)
      VALUES (NEW.id, 'estado', OLD.estado, NEW.estado, auth.uid());
    END IF;
  END IF;
  
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Recreamos el trigger con la nueva función
CREATE TRIGGER on_lead_updated
AFTER UPDATE ON public.leads
FOR EACH ROW
EXECUTE FUNCTION public.log_lead_changes();

COMMENT ON FUNCTION public.log_lead_changes() IS 'Función actualizada para registrar cambios en leads sin acceder a datos personales';