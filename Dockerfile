FROM python:3.11-slim

WORKDIR /app

# Actualizar pip y instalar herramientas básicas
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

# Instalar dependencias básicas primero
COPY requirements.txt .
RUN pip install --no-cache-dir fastapi==0.104.1 uvicorn==0.23.2 pydantic==2.11.1 python-dotenv==1.0.0
RUN pip install --no-cache-dir httpx==0.25.1 python-multipart==0.0.6
RUN pip install --no-cache-dir supabase==1.2.0
RUN pip install --no-cache-dir langchain==0.3.21 langchain-community==0.3.20 langchain-openai==0.2.14
RUN pip install --no-cache-dir openai==1.69.0

# Copiar el resto del código
COPY . .

# Variable de entorno para el puerto (valor predeterminado 8000)
ENV PORT=8000

# Exponer el puerto que usará la aplicación
EXPOSE 8000

# Comando para ejecutar la aplicación
CMD uvicorn app.main:app --host 0.0.0.0 --port $PORT
