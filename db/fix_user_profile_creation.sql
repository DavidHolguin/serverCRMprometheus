-- Paso 1: Crear una tabla de logs para diagnóstico
CREATE TABLE IF NOT EXISTS public.system_logs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  event_type TEXT NOT NULL,
  description TEXT,
  error_message TEXT,
  user_id UUID,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

-- Paso 2: Crear una función robusta para el trigger SIMPLIFICADA
CREATE OR REPLACE FUNCTION public.create_user_profile_robust()
RETURNS TRIGGER AS $$
BEGIN
  -- Registrar inicio de la operación
  INSERT INTO public.system_logs (event_type, description, user_id)
  VALUES ('CREATE_PROFILE_ATTEMPT', 'Intentando crear perfil de usuario simplificado', NEW.id);

  -- Verificar si ya existe un perfil para este usuario
  IF EXISTS (SELECT 1 FROM public.profiles WHERE id = NEW.id) THEN
    -- Registrar que ya existe
    INSERT INTO public.system_logs (event_type, description, user_id)
    VALUES ('PROFILE_EXISTS', 'El perfil ya existe para el usuario', NEW.id);
    RETURN NEW;
  END IF;

  -- Intentar crear el perfil con manejo de errores - SOLO CAMPOS ESENCIALES
  BEGIN
    INSERT INTO public.profiles (
      id,
      email,
      role,
      created_at,
      updated_at
    ) VALUES (
      NEW.id,
      NEW.email,
      'admin_empresa',
      now(),
      now()
    );
    
    -- Registrar éxito
    INSERT INTO public.system_logs (event_type, description, user_id)
    VALUES ('PROFILE_CREATED', 'Perfil de usuario creado exitosamente', NEW.id);
  EXCEPTION WHEN OTHERS THEN
    -- Registrar error detallado
    INSERT INTO public.system_logs (event_type, description, error_message, user_id)
    VALUES ('PROFILE_ERROR', 'Error al crear perfil de usuario', SQLERRM, NEW.id);
  END;

  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Paso 3: Limpiar triggers existentes para evitar duplicados - MEJORADO
DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
DROP TRIGGER IF EXISTS create_profile_trigger ON auth.users;
DROP TRIGGER IF EXISTS handle_new_user_trigger ON auth.users;
DROP TRIGGER IF EXISTS create_admin_profile_trigger ON auth.users;
DROP TRIGGER IF EXISTS create_user_profile_trigger ON auth.users;
DROP TRIGGER IF EXISTS create_profile_on_signup ON auth.users; -- Agregado para evitar error de trigger duplicado

-- Paso 4: Verificar que el trigger no exista antes de crearlo - MEJORADO
DO $$
BEGIN
  -- Intentar eliminar el trigger si existe, sin verificación previa
  BEGIN
    EXECUTE 'DROP TRIGGER IF EXISTS create_profile_on_signup ON auth.users';
  EXCEPTION WHEN OTHERS THEN
    -- Ignorar errores de eliminación
    INSERT INTO public.system_logs (event_type, description, error_message)
    VALUES ('TRIGGER_DROP_ATTEMPT', 'Intento de eliminar trigger existente', SQLERRM);
  END;
  
  -- Crear el nuevo trigger con un nombre único para esta sesión
  DECLARE
    trigger_name TEXT := 'create_profile_' || to_char(now(), 'YYYYMMDD_HH24MISS');
  BEGIN
    EXECUTE 'CREATE TRIGGER ' || trigger_name || '
      AFTER INSERT ON auth.users
      FOR EACH ROW
      EXECUTE FUNCTION public.create_user_profile_robust()';
    
    INSERT INTO public.system_logs (event_type, description)
    VALUES ('TRIGGER_CREATED', 'Se creó el trigger ' || trigger_name);
  EXCEPTION WHEN OTHERS THEN
    -- Registrar cualquier error que ocurra durante este proceso
    INSERT INTO public.system_logs (event_type, description, error_message)
    VALUES ('TRIGGER_ERROR', 'Error al crear el trigger', SQLERRM);
  END;
END $$;

-- Paso 5: Verificar la estructura de la tabla profiles y crearla si no existe
DO $$
BEGIN
  -- Verificar si la tabla profiles existe, si no, crearla
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.tables 
    WHERE table_schema = 'public' AND table_name = 'profiles'
  ) THEN
    CREATE TABLE public.profiles (
      id UUID PRIMARY KEY,
      email TEXT,
      role TEXT DEFAULT 'admin_empresa',
      created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
      updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    );
    
    -- Crear políticas RLS básicas
    ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;
    
    CREATE POLICY "Los usuarios pueden ver sus propios perfiles"
      ON public.profiles FOR SELECT
      USING (auth.uid() = id);
      
    CREATE POLICY "Los usuarios pueden actualizar sus propios perfiles"
      ON public.profiles FOR UPDATE
      USING (auth.uid() = id);
    
    INSERT INTO public.system_logs (event_type, description)
    VALUES ('TABLE_CREATED', 'Se ha creado la tabla profiles');
  ELSE
    -- Verificar que los campos necesarios existan
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'profiles' AND column_name = 'email') THEN
      ALTER TABLE public.profiles ADD COLUMN email TEXT;
      INSERT INTO public.system_logs (event_type, description)
      VALUES ('COLUMN_ADDED', 'Se ha añadido la columna email a la tabla profiles');
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'profiles' AND column_name = 'role') THEN
      ALTER TABLE public.profiles ADD COLUMN role TEXT DEFAULT 'admin_empresa';
      INSERT INTO public.system_logs (event_type, description)
      VALUES ('COLUMN_ADDED', 'Se ha añadido la columna role a la tabla profiles');
    END IF;
  END IF;
END $$;

-- Paso 6: Función para verificar usuarios sin perfil y crearlos manualmente - SIMPLIFICADA
CREATE OR REPLACE FUNCTION public.fix_missing_profiles()
RETURNS TEXT AS $$
DECLARE
  users_fixed INTEGER := 0;
  user_rec RECORD;
BEGIN
  FOR user_rec IN 
    SELECT u.id, u.email
    FROM auth.users u 
    LEFT JOIN public.profiles p ON u.id = p.id 
    WHERE p.id IS NULL
  LOOP
    BEGIN
      -- Inserción simplificada con solo campos esenciales
      INSERT INTO public.profiles (
        id,
        email,
        role,
        created_at,
        updated_at
      ) VALUES (
        user_rec.id,
        user_rec.email,
        'admin_empresa',
        now(),
        now()
      );
      users_fixed := users_fixed + 1;
      
      INSERT INTO public.system_logs (event_type, description, user_id)
      VALUES ('PROFILE_FIXED', 'Perfil creado manualmente', user_rec.id);
    EXCEPTION WHEN OTHERS THEN
      INSERT INTO public.system_logs (event_type, description, error_message, user_id)
      VALUES ('FIX_PROFILE_ERROR', 'Error al corregir perfil faltante', SQLERRM, user_rec.id);
    END;
  END LOOP;
  
  RETURN 'Se han corregido ' || users_fixed || ' perfiles faltantes';
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Paso 7: Verificar que el trigger se haya creado correctamente
CREATE OR REPLACE FUNCTION public.verify_trigger_creation()
RETURNS TEXT AS $$
DECLARE
  trigger_exists BOOLEAN;
BEGIN
  SELECT EXISTS (
    SELECT 1 FROM pg_trigger 
    WHERE tgname = 'create_profile_on_signup' 
    AND tgrelid = 'auth.users'::regclass::oid
  ) INTO trigger_exists;

  IF trigger_exists THEN
    RETURN 'Trigger create_profile_on_signup creado exitosamente';
  ELSE
    RETURN 'Error: El trigger create_profile_on_signup no se creó correctamente';
  END IF;
END;
$$ LANGUAGE plpgsql;

-- Paso 8: Función para verificar la estructura de la tabla profiles
CREATE OR REPLACE FUNCTION public.check_profiles_table()
RETURNS JSONB AS $$
DECLARE
  result JSONB;
BEGIN
  SELECT jsonb_build_object(
    'tabla_existe', (
      SELECT EXISTS (
        SELECT 1 FROM information_schema.tables 
        WHERE table_schema = 'public' AND table_name = 'profiles'
      )
    ),
    'columnas', (
      SELECT jsonb_agg(jsonb_build_object(
        'nombre', column_name,
        'tipo', data_type
      ))
      FROM information_schema.columns
      WHERE table_schema = 'public' AND table_name = 'profiles'
    ),
    'triggers_activos', (
      SELECT jsonb_agg(tgname)
      FROM pg_trigger
      WHERE tgrelid = 'auth.users'::regclass::oid AND tgisinternal = false
    ),
    'usuarios_sin_perfil', (
      SELECT COUNT(*)
      FROM auth.users u
      LEFT JOIN public.profiles p ON u.id = p.id
      WHERE p.id IS NULL
    )
  ) INTO result;
  
  RETURN result;
END;
$$ LANGUAGE plpgsql;

-- Paso 9: Función para obtener usuarios sin perfil
CREATE OR REPLACE FUNCTION public.get_users_without_profile()
RETURNS SETOF JSONB AS $$
BEGIN
  RETURN QUERY
  SELECT jsonb_build_object(
    'id', u.id,
    'email', u.email,
    'created_at', u.created_at
  )
  FROM auth.users u
  LEFT JOIN public.profiles p ON u.id = p.id
  WHERE p.id IS NULL;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Paso 10: Función para limpiar triggers antiguos y mantener solo el más reciente
CREATE OR REPLACE FUNCTION public.cleanup_profile_triggers()
RETURNS TEXT AS $$
DECLARE
    trigger_rec RECORD;
    latest_trigger TEXT;
    triggers_removed INTEGER := 0;
BEGIN
    -- Encontrar el trigger más reciente (asumiendo el formato create_profile_YYYYMMDD_HHMMSS)
    SELECT tgname INTO latest_trigger
    FROM pg_trigger
    WHERE tgrelid = 'auth.users'::regclass::oid 
      AND tgname LIKE 'create\_profile\_%'
      AND tgisinternal = false
    ORDER BY tgname DESC
    LIMIT 1;
    
    -- Si no hay triggers, retornar mensaje
    IF latest_trigger IS NULL THEN
        RETURN 'No se encontraron triggers de perfil para limpiar';
    END IF;
    
    -- Eliminar todos los triggers excepto el más reciente
    FOR trigger_rec IN
        SELECT tgname
        FROM pg_trigger
        WHERE tgrelid = 'auth.users'::regclass::oid 
          AND tgname LIKE 'create\_profile\_%'
          AND tgname != latest_trigger
          AND tgisinternal = false
    LOOP
        BEGIN
            EXECUTE 'DROP TRIGGER ' || trigger_rec.tgname || ' ON auth.users';
            triggers_removed := triggers_removed + 1;
            
            INSERT INTO public.system_logs (event_type, description)
            VALUES ('TRIGGER_REMOVED', 'Se eliminó el trigger antiguo ' || trigger_rec.tgname);
        EXCEPTION WHEN OTHERS THEN
            INSERT INTO public.system_logs (event_type, description, error_message)
            VALUES ('TRIGGER_REMOVE_ERROR', 'Error al eliminar trigger ' || trigger_rec.tgname, SQLERRM);
        END;
    END LOOP;
    
    RETURN 'Se mantuvo el trigger ' || latest_trigger || ' y se eliminaron ' || triggers_removed || ' triggers antiguos';
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Paso 11: Función para verificar el estado general del sistema de perfiles
CREATE OR REPLACE FUNCTION public.check_profile_system_health()
RETURNS JSONB AS $$
DECLARE
    health_report JSONB;
BEGIN
    SELECT jsonb_build_object(
        'profiles_table', check_profiles_table(),
        'triggers', (
            SELECT jsonb_agg(jsonb_build_object(
                'nombre', tgname,
                'función', tgfoid::regproc::text
            ))
            FROM pg_trigger
            WHERE tgrelid = 'auth.users'::regclass::oid AND tgisinternal = false
        ),
        'usuarios_totales', (SELECT COUNT(*) FROM auth.users),
        'usuarios_con_perfil', (
            SELECT COUNT(*) FROM auth.users u
            JOIN public.profiles p ON u.id = p.id
        ),
        'usuarios_sin_perfil', (
            SELECT COUNT(*) FROM auth.users u
            LEFT JOIN public.profiles p ON u.id = p.id
            WHERE p.id IS NULL
        ),
        'ultimo_log', (
            SELECT row_to_json(l)
            FROM public.system_logs l
            ORDER BY created_at DESC
            LIMIT 1
        )
    ) INTO health_report;
    
    RETURN health_report;
END;
$$ LANGUAGE plpgsql;
