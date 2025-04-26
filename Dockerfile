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

# Instalar todas las dependencias de una vez utilizando el archivo requirements.txt
# Esto es más eficiente y garantiza compatibilidad entre paquetes
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Instalar dependencias adicionales para procesar Excel y páginas web
RUN pip install --no-cache-dir pandas openpyxl requests beautifulsoup4 PyPDF2==2.12.1

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
