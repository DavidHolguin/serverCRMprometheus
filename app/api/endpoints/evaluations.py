from typing import Dict, Any, List, Optional
from uuid import UUID
from fastapi import APIRouter, HTTPException, Depends, Query

from app.services.lead_evaluation_service import lead_evaluation_service
from app.db.supabase_client import supabase
from app.api.deps import get_current_user
from app.models.evaluation import (
    EvaluacionResponse,
    EvaluateMessageRequest,
    EvaluateConversationRequest,
    EvaluationStatsResponse
)

router = APIRouter()

@router.post("/evaluate-message/", response_model=Dict[str, Any])
async def evaluate_message(
    request: EvaluateMessageRequest
    # Comentado para desarrollo: current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Evalúa un mensaje específico para determinar el valor del lead
    """
    try:
        # Comentado para desarrollo
        # if str(current_user["empresa_id"]) != str(request.empresa_id):
        #     raise HTTPException(status_code=403, detail="No tienes permiso para evaluar mensajes de esta empresa")
        
        # Realizar la evaluación
        evaluation = lead_evaluation_service.evaluate_message(
            lead_id=request.lead_id,
            conversacion_id=request.conversacion_id,
            mensaje_id=request.mensaje_id,
            empresa_id=request.empresa_id
        )
        
        return {
            "success": True,
            "data": evaluation
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al evaluar el mensaje: {str(e)}")

@router.post("/evaluate-conversation/", response_model=Dict[str, Any])
async def evaluate_conversation(
    request: EvaluateConversationRequest
    # Comentado para desarrollo: current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Evalúa todos los mensajes de una conversación para determinar el valor del lead
    """
    try:
        # Comentado para desarrollo
        # if str(current_user["empresa_id"]) != str(request.empresa_id):
        #     raise HTTPException(status_code=403, detail="No tienes permiso para evaluar conversaciones de esta empresa")
        
        # Obtener información de la conversación
        result = supabase.table("conversaciones").select("*").eq("id", str(request.conversacion_id)).limit(1).execute()
        
        if not result.data or len(result.data) == 0:
            raise HTTPException(status_code=404, detail=f"Conversación con ID {request.conversacion_id} no encontrada")
        
        conversation = result.data[0]
        lead_id = UUID(conversation["lead_id"])
        
        # Obtener mensajes del usuario en la conversación
        messages_result = supabase.table("mensajes").select("*").eq("conversacion_id", str(request.conversacion_id)).eq("origen", "user").order("created_at", desc=False).execute()
        
        if not messages_result.data:
            return {
                "success": True,
                "data": {
                    "message": "No hay mensajes de usuario para evaluar en esta conversación",
                    "evaluations": []
                }
            }
        
        # Evaluar cada mensaje
        evaluations = []
        for message in messages_result.data:
            try:
                evaluation = lead_evaluation_service.evaluate_message(
                    lead_id=lead_id,
                    conversacion_id=request.conversacion_id,
                    mensaje_id=UUID(message["id"]),
                    empresa_id=request.empresa_id
                )
                evaluations.append(evaluation)
            except Exception as e:
                print(f"Error al evaluar el mensaje {message['id']}: {e}")
                # Continuar con el siguiente mensaje si hay error
        
        return {
            "success": True,
            "data": {
                "conversation_id": str(request.conversacion_id),
                "lead_id": str(lead_id),
                "evaluations": evaluations
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al evaluar la conversación: {str(e)}")

@router.get("/lead-evaluations/{lead_id}", response_model=Dict[str, Any])
async def get_lead_evaluations(
    lead_id: UUID,
    limit: int = Query(10, ge=1, le=100)
    # Comentado para desarrollo: current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Obtiene las evaluaciones existentes para un lead específico
    """
    try:
        # Obtener información del lead para verificar permisos
        lead_result = supabase.table("leads").select("*").eq("id", str(lead_id)).limit(1).execute()
        
        if not lead_result.data or len(lead_result.data) == 0:
            raise HTTPException(status_code=404, detail=f"Lead con ID {lead_id} no encontrado")
        
        lead = lead_result.data[0]
        
        # Comentado para desarrollo
        # # Verificar que el usuario pertenece a la empresa del lead
        # if str(current_user["empresa_id"]) != str(lead["empresa_id"]):
        #     raise HTTPException(status_code=403, detail="No tienes permiso para ver evaluaciones de este lead")
        
        # Obtener evaluaciones
        evaluations_result = supabase.table("evaluaciones_llm").select("*").eq("lead_id", str(lead_id)).order("fecha_evaluacion", desc=True).limit(limit).execute()
        
        return {
            "success": True,
            "data": {
                "lead_id": str(lead_id),
                "evaluations": evaluations_result.data if evaluations_result.data else []
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al obtener evaluaciones: {str(e)}")

@router.get("/conversation-evaluations/{conversacion_id}", response_model=Dict[str, Any])
async def get_conversation_evaluations(
    conversacion_id: UUID
    # Comentado para desarrollo: current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Obtiene las evaluaciones existentes para una conversación específica
    """
    try:
        # Obtener información de la conversación
        conv_result = supabase.table("conversaciones").select("*").eq("id", str(conversacion_id)).limit(1).execute()
        
        if not conv_result.data or len(conv_result.data) == 0:
            raise HTTPException(status_code=404, detail=f"Conversación con ID {conversacion_id} no encontrada")
        
        conversation = conv_result.data[0]
        
        # Obtener información del lead para verificar permisos
        lead_result = supabase.table("leads").select("*").eq("id", str(conversation["lead_id"])).limit(1).execute()
        
        if not lead_result.data or len(lead_result.data) == 0:
            raise HTTPException(status_code=404, detail=f"Lead asociado a la conversación no encontrado")
        
        lead = lead_result.data[0]
        
        # Comentado para desarrollo
        # # Verificar que el usuario pertenece a la empresa del lead
        # if str(current_user["empresa_id"]) != str(lead["empresa_id"]):
        #     raise HTTPException(status_code=403, detail="No tienes permiso para ver evaluaciones de esta conversación")
        
        # Obtener evaluaciones
        evaluations_result = supabase.table("evaluaciones_llm").select("*").eq("conversacion_id", str(conversacion_id)).order("fecha_evaluacion", desc=True).execute()
        
        return {
            "success": True,
            "data": {
                "conversation_id": str(conversacion_id),
                "lead_id": str(conversation["lead_id"]),
                "evaluations": evaluations_result.data if evaluations_result.data else []
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al obtener evaluaciones: {str(e)}")

@router.get("/dashboard-stats/{empresa_id}", response_model=Dict[str, Any])
async def get_dashboard_stats(
    empresa_id: UUID,
    days: int = Query(30, ge=1, le=365)
    # Comentado para desarrollo: current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Obtiene estadísticas de evaluaciones para el dashboard
    """
    try:
        # Comentado para desarrollo
        # # Verificar que el usuario pertenece a la empresa
        # if str(current_user["empresa_id"]) != str(empresa_id):
        #     raise HTTPException(status_code=403, detail="No tienes permiso para ver estadísticas de esta empresa")
        
        # Consulta SQL para obtener estadísticas
        sql = f"""
        WITH lead_stats AS (
            SELECT 
                l.id as lead_id,
                l.nombre,
                l.score,
                COUNT(e.id) as total_evaluaciones,
                AVG(e.score_potencial) as promedio_potencial,
                AVG(e.score_satisfaccion) as promedio_satisfaccion,
                MAX(e.fecha_evaluacion) as ultima_evaluacion
            FROM 
                leads l
                LEFT JOIN evaluaciones_llm e ON l.id = e.lead_id
            WHERE 
                l.empresa_id = '{str(empresa_id)}'
                AND (e.fecha_evaluacion IS NULL OR e.fecha_evaluacion >= NOW() - INTERVAL '{days} days')
            GROUP BY 
                l.id, l.nombre, l.score
            ORDER BY 
                promedio_potencial DESC NULLS LAST
            LIMIT 10
        )
        SELECT * FROM lead_stats
        """
        
        # Ejecutar consulta
        result = supabase.rpc("ejecutar_sql", {"sql": sql}).execute()
        
        # Obtener productos de interés más comunes
        productos_sql = f"""
        WITH productos_interes AS (
            SELECT 
                UNNEST(interes_productos) as producto,
                COUNT(*) as menciones
            FROM 
                evaluaciones_llm e
                JOIN leads l ON e.lead_id = l.id
            WHERE 
                l.empresa_id = '{str(empresa_id)}'
                AND e.fecha_evaluacion >= NOW() - INTERVAL '{days} days'
            GROUP BY 
                producto
            ORDER BY 
                menciones DESC
            LIMIT 5
        )
        SELECT * FROM productos_interes
        """
        
        productos_result = supabase.rpc("ejecutar_sql", {"sql": productos_sql}).execute()
        
        # Obtener palabras clave más comunes
        keywords_sql = f"""
        WITH keywords AS (
            SELECT 
                UNNEST(palabras_clave) as keyword,
                COUNT(*) as menciones
            FROM 
                evaluaciones_llm e
                JOIN leads l ON e.lead_id = l.id
            WHERE 
                l.empresa_id = '{str(empresa_id)}'
                AND e.fecha_evaluacion >= NOW() - INTERVAL '{days} days'
            GROUP BY 
                keyword
            ORDER BY 
                menciones DESC
            LIMIT 10
        )
        SELECT * FROM keywords
        """
        
        keywords_result = supabase.rpc("ejecutar_sql", {"sql": keywords_sql}).execute()
        
        return {
            "success": True,
            "data": {
                "top_leads": result.data if result.data else [],
                "top_productos": productos_result.data if productos_result.data else [],
                "top_keywords": keywords_result.data if keywords_result.data else []
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al obtener estadísticas: {str(e)}")
