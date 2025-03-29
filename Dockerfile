FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install dependencies
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Exponer puerto 8000 (predeterminado)
EXPOSE 8000

# Comando para ejecutar la aplicación con la variable PORT
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
