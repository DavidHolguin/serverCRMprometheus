#!/bin/bash

# Script para instalar dependencias adicionales necesarias para el procesamiento de audio

echo "Instalando ffmpeg para procesamiento de audio..."
apt-get update && apt-get install -y ffmpeg

echo "Instalando dependencias de Python desde requirements.txt..."
pip install -r requirements.txt

echo "Verificando instalación de pydub..."
python -c "import pydub; print('pydub instalado correctamente: versión', pydub.__version__)"

echo "Instalación de dependencias completada."