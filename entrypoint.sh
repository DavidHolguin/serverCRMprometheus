#!/bin/sh

# Establecer puerto predeterminado si no está definido
PORT="${PORT:-8000}"

# Iniciar la aplicación
exec uvicorn app.main:app --host 0.0.0.0 --port "$PORT"
