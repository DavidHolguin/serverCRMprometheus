from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import os

from app.core.config import settings
from app.api.routes import api_router

# Create FastAPI app
app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    debug=settings.DEBUG
)

# Lista de orígenes permitidos
allowed_origins = [
    "https://www.prometheuslabs.com.co",  # Dominio principal
    "http://localhost",                  # Localhost HTTP
    "http://localhost:3000",            # Común para React
    "http://localhost:8000",            # Común para servidores locales
    "http://localhost:8080",            # Otro puerto común
    "http://127.0.0.1",                 # Localhost IP
    "http://127.0.0.1:3000",            # Localhost IP con puerto
    "http://127.0.0.1:8000",
    "http://127.0.0.1:8080",
]

# Set up CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,  # Orígenes específicos permitidos
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API router
app.include_router(api_router, prefix=settings.API_V1_STR)

@app.get("/")
async def root():
    """Root endpoint to check if the API is running"""
    return {
        "message": "CRM Messaging Server API is running",
        "documentation": f"/docs",
        "version": "1.0.0"
    }

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.SERVER_HOST,
        port=settings.SERVER_PORT,
        reload=settings.DEBUG
    )
