#!/usr/bin/env python
"""
Script para actualizar a LangChain 0.3
Este script verifica las dependencias instaladas y actualiza a LangChain 0.3
"""

import sys
import subprocess
import os
import re
from typing import List, Dict, Any

def print_header(text: str) -> None:
    """Imprime un encabezado con formato"""
    print("\n" + "=" * 80)
    print(f" {text} ".center(80, "="))
    print("=" * 80)

def print_section(text: str) -> None:
    """Imprime una sección con formato"""
    print("\n" + "-" * 80)
    print(f" {text} ")
    print("-" * 80)

def run_command(command: List[str], description: str = None) -> None:
    """Ejecuta un comando en el sistema y muestra la salida"""
    if description:
        print(f"\n👉 {description}...")
    
    try:
        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True
        )
        if result.stdout:
            print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Error al ejecutar el comando: {' '.join(command)}")
        print(f"Código de salida: {e.returncode}")
        if e.stdout:
            print(f"Salida estándar:\n{e.stdout}")
        if e.stderr:
            print(f"Salida de error:\n{e.stderr}")
        return False

def check_python_version() -> bool:
    """Verifica que la versión de Python sea compatible con LangChain 0.3"""
    print_section("Verificando versión de Python")
    
    major, minor, _ = sys.version_info
    if major < 3 or (major == 3 and minor < 9):
        print(f"❌ Versión de Python detectada: {major}.{minor}")
        print("❌ LangChain 0.3 requiere Python 3.9 o superior.")
        print("❌ Por favor, actualiza tu versión de Python antes de continuar.")
        return False
    
    print(f"✅ Versión de Python compatible detectada: {major}.{minor}")
    return True

def create_backup_requirements() -> bool:
    """Crea una copia de seguridad del archivo requirements.txt"""
    print_section("Creando copia de seguridad de requirements.txt")
    
    if os.path.exists("requirements.txt"):
        backup_filename = "requirements.backup.txt"
        i = 1
        while os.path.exists(backup_filename):
            backup_filename = f"requirements.backup_{i}.txt"
            i += 1
        
        try:
            with open("requirements.txt", "r") as f:
                content = f.read()
            
            with open(backup_filename, "w") as f:
                f.write(content)
            
            print(f"✅ Copia de seguridad creada: {backup_filename}")
            return True
        except Exception as e:
            print(f"❌ Error al crear copia de seguridad: {str(e)}")
            return False
    else:
        print("❓ No se encontró el archivo requirements.txt")
        return False

def update_dependencies() -> bool:
    """Actualiza las dependencias para LangChain 0.3"""
    print_section("Instalando dependencias actualizadas")
    
    dependencies = [
        "pydantic>=2.4.2,<3.0",
        "langchain>=0.3.0,<0.4.0",
        "langchain-core>=0.3.0,<0.4.0",
        "langchain-community>=0.3.0,<0.4.0",
        "langchain-openai>=0.2.0,<0.3.0",
        "openai>=1.6.0",
        "langsmith>=0.1.0,<0.2.0",
        "langchain-text-splitters>=0.3.0,<0.4.0"
    ]
    
    command = [sys.executable, "-m", "pip", "install", "--upgrade"] + dependencies
    return run_command(command, "Instalando dependencias de LangChain 0.3")

def main():
    """Función principal"""
    print_header("ACTUALIZACIÓN A LANGCHAIN 0.3")
    print("""
Este script actualizará tus dependencias para usar LangChain 0.3.
Las principales mejoras incluyen:
1. Soporte completo para Pydantic 2
2. Herramientas simplificadas y nuevos paquetes de integración
3. Mejoras a las APIs para modelos de chat
4. Documentación renovada
    """)
    
    # Verificar versión de Python
    if not check_python_version():
        sys.exit(1)
    
    # Crear copia de seguridad
    create_backup_requirements()
    
    # Actualizar dependencias
    if not update_dependencies():
        print("\n❌ Error al actualizar dependencias.")
        sys.exit(1)
    
    print_header("ACTUALIZACIÓN COMPLETADA")
    print("""
Las dependencias han sido actualizadas a LangChain 0.3.

Recuerda verificar que las importaciones en el código sigan este formato:
- from langchain_core.prompts import ChatPromptTemplate
- from langchain_openai import ChatOpenAI
- from langchain_community.document_loaders import WebBaseLoader

Para más información sobre la migración a LangChain 0.3, visita:
https://python.langchain.com/v0.3/docs/
    """)

if __name__ == "__main__":
    main()