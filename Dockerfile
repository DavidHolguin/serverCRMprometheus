# Usar la versión más reciente de Python 3.11 slim para reducir vulnerabilidades
FROM python:3.11-slim-bookworm

# LangChain 0.3 requiere Python 3.9+ (3.11 es recomendado para mejor rendimiento)
WORKDIR /app

# Crear un usuario no privilegiado para ejecutar la aplicación
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Instalar dependencias del sistema incluyendo ffmpeg para procesamiento de audio
# y dependencias para navegadores headless (necesarias para carga de URLs)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    python3-dev \
    ffmpeg \
    # Dependencias para navegadores headless
    wget \
    gnupg \
    ca-certificates \
    # Dependencias para procesamiento de PDF
    poppler-utils \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements primero para mejor caché
COPY requirements.txt .

# Instalar todas las dependencias de una vez utilizando el archivo requirements.txt
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    # Instalar navegadores para Playwright (necesarios para carga de URLs)
    pip install playwright && \
    playwright install --with-deps chromium && \
    pip cache purge

# Copiar el resto de la aplicación
COPY . .

# Hacer ejecutable el script de entrada
RUN chmod +x /app/entrypoint.sh && \
    # Establecer permisos adecuados para el usuario no privilegiado
    chown -R appuser:appuser /app

# Cambiar al usuario no privilegiado para mayor seguridad
USER appuser

# Exponer puerto 8000 (predeterminado)
EXPOSE 8000

# Variable de entorno para el puerto (valor predeterminado: 8000)
ENV PORT=8000

# Usar el script de entrada como punto de entrada
ENTRYPOINT ["/app/entrypoint.sh"]
