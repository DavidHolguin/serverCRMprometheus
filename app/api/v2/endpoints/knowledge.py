from typing import List, Optional
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from uuid import UUID
import os
import shutil
from datetime import datetime

from app.api.deps import get_current_user
from app.services.v2.knowledge_service import knowledge_service
from app.models.v2.agent import AgentKnowledge

router = APIRouter()

@router.post("/upload", response_model=List[AgentKnowledge])
async def upload_document(
    file: UploadFile = File(...),
    agent_id: UUID = Form(...),
    metadata: Optional[str] = Form(None),
    current_user: dict = Depends(get_current_user)
):
    """
    Sube y procesa un documento para el conocimiento del agente
    """
    try:
        # Verificar permisos
        company_id = current_user.get("empresa_id")
        if not company_id:
            raise HTTPException(status_code=403, detail="No tienes acceso a esta empresa")

        # Crear directorio temporal si no existe
        temp_dir = "temp_uploads"
        os.makedirs(temp_dir, exist_ok=True)
        
        # Guardar archivo temporalmente
        file_path = os.path.join(temp_dir, file.filename)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        try:
            # Determinar tipo de archivo
            file_type = file.filename.split(".")[-1].lower()
            
            # Procesar documento
            result = await knowledge_service.process_document(
                file_path=file_path,
                file_type=file_type,
                agent_id=agent_id,
                company_id=UUID(company_id),
                metadata=eval(metadata) if metadata else None
            )
            
            return result
            
        finally:
            # Limpiar archivo temporal
            os.remove(file_path)
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/search/{agent_id}", response_model=List[AgentKnowledge])
async def search_knowledge(
    agent_id: UUID,
    query: str,
    limit: int = 5,
    current_user: dict = Depends(get_current_user)
):
    """
    Busca conocimiento similar para un agente
    """
    try:
        # Verificar permisos
        company_id = current_user.get("empresa_id")
        if not company_id:
            raise HTTPException(status_code=403, detail="No tienes acceso a esta empresa")

        # Realizar búsqueda
        results = await knowledge_service.search_similar_knowledge(
            query=query,
            agent_id=agent_id,
            limit=limit
        )
        
        return results
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))