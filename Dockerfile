FROM python:3.11-slim

WORKDIR /app

# Copiar archivos de proyecto
COPY . .

# Instalar dependencias
RUN pip install --no-cache-dir -r requirements.txt

# Exponer puerto 8000 (predeterminado)
EXPOSE 8000

# Comando para ejecutar la aplicación con la variable PORT
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
