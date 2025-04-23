-- Función que se ejecutará con el trigger
CREATE OR REPLACE FUNCTION public.create_profile_on_signup()
RETURNS TRIGGER AS $$
DECLARE
  role_value text;
  profile_exists boolean;
BEGIN
  -- Verificar si el rol es un tipo enumerado y obtener un valor válido
  BEGIN
    -- Verificar primero si ya existe un perfil para este usuario (evitar duplicados)
    SELECT EXISTS (SELECT 1 FROM public.profiles WHERE id = NEW.id) INTO profile_exists;
    
    IF profile_exists THEN
      RAISE LOG 'Ya existe un perfil para el usuario %', NEW.email;
      RETURN NEW;
    END IF;
    
    -- Verificar el tipo de dato de role
    SELECT pg_catalog.format_type(a.atttypid, a.atttypmod) 
    INTO role_value
    FROM pg_catalog.pg_attribute a
    JOIN pg_catalog.pg_class c ON a.attrelid = c.oid
    JOIN pg_catalog.pg_namespace n ON c.relnamespace = n.oid
    WHERE c.relname = 'profiles' 
    AND n.nspname = 'public'
    AND a.attname = 'role';
    
    -- Si es un enum, seleccionar el primer valor como predeterminado, de lo contrario usar 'admin'
    IF role_value LIKE '%enum%' THEN
      EXECUTE 'SELECT enum_range(NULL::' || role_value || ')[1]' INTO role_value;
    ELSE
      role_value := 'admin';
    END IF;
    
    -- Forzar registrar errores
    SET log_statement = 'all';
    SET client_min_messages = 'debug';
    
    -- Insertamos el nuevo perfil utilizando los datos del usuario recién creado
    RAISE LOG 'Intentando crear perfil para usuario % con rol %', NEW.email, role_value;
    
    INSERT INTO public.profiles (
      id,
      updated_at,
      created_at,
      email,
      full_name,
      avatar_url,
      role,
      onboarding_completed,
      onboarding_step,
      is_active
    ) VALUES (
      NEW.id,
      NOW(),
      NOW(),
      NEW.email,
      COALESCE(NEW.raw_user_meta_data->>'full_name', ''),
      '',
      role_value, -- Usar el valor apropiado basado en el tipo
      FALSE,
      'bienvenida',
      TRUE
    );
    
    RAISE LOG 'Perfil creado exitosamente para %', NEW.email;
  EXCEPTION WHEN OTHERS THEN
    -- Esta vez hacemos que falle el trigger para poder diagnosticar el problema
    RAISE EXCEPTION 'Error al crear perfil para %: % (rol=%)', NEW.email, SQLERRM, role_value;
  END;
  
  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Creación del trigger - asegurarse que se ejecute en el contexto correcto
DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;

CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW EXECUTE FUNCTION public.create_profile_on_signup();

-- Verificar si los registros existen y crear manualmente los que faltan
DO $$
DECLARE
  user_record RECORD;
  profile_exists BOOLEAN;
  role_value TEXT := 'admin'; -- Valor predeterminado
BEGIN
  -- Verificamos el tipo de la columna role y obtenemos un valor válido
  BEGIN
    SELECT pg_catalog.format_type(a.atttypid, a.atttypmod) 
    INTO role_value
    FROM pg_catalog.pg_attribute a
    JOIN pg_catalog.pg_class c ON a.attrelid = c.oid
    JOIN pg_catalog.pg_namespace n ON c.relnamespace = n.oid
    WHERE c.relname = 'profiles' 
    AND n.nspname = 'public'
    AND a.attname = 'role';
    
    IF role_value LIKE '%enum%' THEN
      EXECUTE 'SELECT enum_range(NULL::' || role_value || ')[1]' INTO role_value;
    END IF;
  EXCEPTION WHEN OTHERS THEN
    role_value := 'admin'; -- Si hay error, usar 'admin' como valor predeterminado
  END;
  
  -- Iterar sobre todos los usuarios que no tienen perfil
  FOR user_record IN 
    SELECT au.id, au.email, au.raw_user_meta_data 
    FROM auth.users au
    WHERE NOT EXISTS (SELECT 1 FROM public.profiles p WHERE p.id = au.id)
  LOOP
    RAISE NOTICE 'Creando perfil faltante para usuario %', user_record.email;
    
    -- Insertar el perfil faltante
    INSERT INTO public.profiles (
      id, updated_at, created_at, email, full_name, avatar_url, 
      role, onboarding_completed, onboarding_step, is_active
    ) VALUES (
      user_record.id, NOW(), NOW(), user_record.email,
      COALESCE(user_record.raw_user_meta_data->>'full_name', ''),
      '', role_value, FALSE, 'bienvenida', TRUE
    );
  END LOOP;
END $$;
