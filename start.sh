#!/bin/bash
# Script de inicio para la aplicación

# Usar el puerto proporcionado por Railway o el valor predeterminado 8000
PORT=${PORT:-8000}

# Iniciar la aplicación con el puerto correcto
exec uvicorn app.main:app --host 0.0.0.0 --port $PORT
