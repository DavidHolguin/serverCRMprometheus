import uvicorn
from app.core.config import settings

if __name__ == "__main__":
    print(f"Starting CRM Messaging Server on {settings.SERVER_HOST}:{settings.SERVER_PORT}")
    print(f"API documentation available at http://{settings.SERVER_HOST}:{settings.SERVER_PORT}/docs")
    
    uvicorn.run(
        "app.main:app",
        host=settings.SERVER_HOST,
        port=settings.SERVER_PORT,
        reload=settings.DEBUG
    )
