from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends
from uuid import UUID
from datetime import datetime

from app.api.deps import get_current_user
from app.models.v2.agent import Agent, AgentPersonality, AgentObjective
from app.db.supabase_client import supabase

router = APIRouter()

@router.post("", response_model=Agent)
async def create_agent(
    agent: Agent,
    current_user: dict = Depends(get_current_user)
):
    """
    Crea un nuevo agente
    """
    try:
        company_id = current_user.get("empresa_id")
        if not company_id:
            raise HTTPException(status_code=403, detail="No tienes acceso a esta empresa")
            
        if str(agent.company_id) != company_id:
            raise HTTPException(status_code=403, detail="No puedes crear agentes para otra empresa")
            
        # Insertar el agente
        result = supabase.table("agentes").insert(
            agent.model_dump(exclude={'knowledge', 'skills', 'objectives', 'experiences', 'personality', 'evolutions'})
        ).execute()
        
        if not result.data:
            raise HTTPException(status_code=500, detail="Error al crear el agente")
            
        created_agent = result.data[0]
        
        # Si se proporcionó personalidad, crearla
        if agent.personality:
            personality_data = agent.personality.model_dump()
            personality_data["agent_id"] = created_agent["id"]
            supabase.table("agente_personalidad").insert(personality_data).execute()
            
        # Si se proporcionaron objetivos, crearlos
        if agent.objectives:
            objectives_data = [
                {**obj.model_dump(), "agent_id": created_agent["id"]}
                for obj in agent.objectives
            ]
            supabase.table("agente_objetivos").insert(objectives_data).execute()
            
        return Agent(**created_agent)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{agent_id}", response_model=Agent)
async def get_agent(
    agent_id: UUID,
    current_user: dict = Depends(get_current_user)
):
    """
    Obtiene un agente por su ID
    """
    try:
        company_id = current_user.get("empresa_id")
        if not company_id:
            raise HTTPException(status_code=403, detail="No tienes acceso a esta empresa")
            
        # Obtener el agente
        result = supabase.table("agentes").select("*").eq("id", str(agent_id)).execute()
        
        if not result.data:
            raise HTTPException(status_code=404, detail="Agente no encontrado")
            
        agent_data = result.data[0]
        
        # Verificar permisos
        if str(agent_data["company_id"]) != company_id:
            raise HTTPException(status_code=403, detail="No tienes acceso a este agente")
            
        # Obtener personalidad
        personality_result = supabase.table("agente_personalidad").select("*").eq("agent_id", str(agent_id)).execute()
        if personality_result.data:
            agent_data["personality"] = personality_result.data[0]
            
        # Obtener objetivos
        objectives_result = supabase.table("agente_objetivos").select("*").eq("agent_id", str(agent_id)).execute()
        if objectives_result.data:
            agent_data["objectives"] = objectives_result.data
            
        return Agent(**agent_data)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("", response_model=List[Agent])
async def list_agents(
    current_user: dict = Depends(get_current_user)
):
    """
    Lista todos los agentes de la empresa
    """
    try:
        company_id = current_user.get("empresa_id")
        if not company_id:
            raise HTTPException(status_code=403, detail="No tienes acceso a esta empresa")
            
        # Obtener agentes
        result = supabase.table("agentes").select("*").eq("company_id", company_id).execute()
        
        return [Agent(**agent_data) for agent_data in result.data]
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))