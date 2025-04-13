FROM python:3.11-slim

WORKDIR /app

# Instalar dependencias del sistema incluyendo ffmpeg para procesamiento de audio
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    python3-dev \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements primero para mejor caché
COPY requirements.txt .

# Actualizar pip e instalar dependencias una por una
RUN pip install --upgrade pip && \
    pip install fastapi==0.104.1 && \
    pip install uvicorn==0.23.2 && \
    pip install pydantic==2.4.2 && \
    pip install python-dotenv==1.0.0 && \
    pip install httpx==0.25.1 && \
    pip install python-multipart==0.0.6 && \
    pip install supabase==1.0.4 && \
    pip install openai==0.28.1 && \
    pip install langchain==0.0.267 && \
    pip install langchain-community==0.0.13 && \
    pip install langchain-openai==0.0.2 && \
    pip install pydub==0.25.1 && \
    pip install numpy==1.26.0

# Copiar el resto de la aplicación
COPY . .

# Hacer ejecutable el script de entrada
RUN chmod +x /app/entrypoint.sh

# Exponer puerto 8000 (predeterminado)
EXPOSE 8000

# Variable de entorno para el puerto (valor predeterminado: 8000)
ENV PORT=8000

# Usar el script de entrada como punto de entrada
ENTRYPOINT ["/app/entrypoint.sh"]
