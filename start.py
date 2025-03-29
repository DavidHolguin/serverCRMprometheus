import os
import sys
import uvicorn

if __name__ == "__main__":
    # Obtener el puerto de la variable de entorno o usar 8000 como predeterminado
    port = int(os.environ.get("PORT", 8000))
    
    print(f"Starting server on port {port}")
    
    # Iniciar la aplicación con el puerto correcto
    uvicorn.run("app.main:app", host="0.0.0.0", port=port)
