#!/bin/bash

# Script de entrada mejorado con diagnósticos

echo "=== Iniciando servidor CRM ==="
echo "Fecha y hora: $(date)"

# Establecer puerto predeterminado si no está definido
PORT="${PORT:-8000}"
echo "Puerto configurado: $PORT"

# Verificar dependencias críticas
echo "=== Verificando dependencias críticas ==="
python -c "import sys; print(f'Python: {sys.version}')"
pip list | grep -E "fastapi|uvicorn|pydantic|langchain|openai|PyPDF2|pandas|beautifulsoup4"

# Configuración del entorno
echo "=== Variables de entorno ==="
echo "PYTHONPATH: $PYTHONPATH"
echo "RAILWAY_ENVIRONMENT: $RAILWAY_ENVIRONMENT"
echo "RAILWAY_SERVICE_NAME: $RAILWAY_SERVICE_NAME"

# Verificar si se puede acceder a la base de datos
echo "=== Verificando conexión a base de datos ==="
python -c "
try:
    from app.db.supabase_client import supabase
    supabase.table('agentes').select('id').limit(1).execute()
    print('✅ Conexión a Supabase establecida correctamente')
except Exception as e:
    print(f'❌ Error de conexión: {str(e)}')
"

# Verificar directorio de trabajo
echo "=== Estructura de archivos ==="
ls -la

# Iniciar la aplicación con tiempos de espera más largos
echo "=== Iniciando la aplicación ==="
echo "$(date) - Iniciando uvicorn..."
exec uvicorn app.main:app --host 0.0.0.0 --port "$PORT" --timeout-keep-alive 120
