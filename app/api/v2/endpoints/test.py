from fastapi import APIRouter
from typing import Dict, Any

router = APIRouter()

@router.get("/ping", response_model=Dict[str, Any])
async def test_v2_api():
    """
    Endpoint simple para verificar que la API v2 está funcionando correctamente
    """
    return {
        "status": "success",
        "message": "API v2 está funcionando correctamente",
        "version": "2.0.0"
    }