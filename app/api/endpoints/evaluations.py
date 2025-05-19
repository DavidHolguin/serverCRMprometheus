from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException
from uuid import UUID
from datetime import datetime

from sqlalchemy.sql import text
from app.db.supabase_client import supabase
from app.services.lead_evaluation_service import lead_evaluation_service
from app.models.evaluation import EvaluacionLeadResponse, DashboardStats

router = APIRouter(prefix="/evaluations", tags=["evaluations"])

@router.post("/evaluate-message/", response_model=EvaluacionLeadResponse)
async def evaluate_message(
    lead_id: UUID,
    conversacion_id: UUID,
    mensaje_id: UUID,
    empresa_id: UUID
):
    """
    Evalúa un mensaje específico y actualiza la información del lead.
    
    Args:
        lead_id: ID del lead
        conversacion_id: ID de la conversación
        mensaje_id: ID del mensaje a evaluar
        empresa_id: ID de la empresa
        
    Returns:
        Resultado de la evaluación
    """
    try:
        result = lead_evaluation_service.evaluate_message(
            lead_id, conversacion_id, mensaje_id, empresa_id
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error evaluando mensaje: {str(e)}")

@router.post("/evaluate-conversation/", response_model=List[EvaluacionLeadResponse])
async def evaluate_conversation(
    conversacion_id: UUID,
    empresa_id: UUID
):
    """
    Evalúa todos los mensajes de un usuario en una conversación
    
    Args:
        conversacion_id: ID de la conversación
        empresa_id: ID de la empresa
        
    Returns:
        Lista de resultados de evaluaciones para cada mensaje
    """
    try:
        # Obtener información de la conversación
        result = supabase.table("conversaciones").select("lead_id").eq("id", str(conversacion_id)).limit(1).execute()
        
        if not result.data or len(result.data) == 0:
            raise HTTPException(status_code=404, detail="Conversación no encontrada")
            
        lead_id = UUID(result.data[0]["lead_id"])
        
        # Obtener todos los mensajes del usuario en la conversación
        result = supabase.table("mensajes").select("id").eq("conversacion_id", str(conversacion_id)).eq("origen", "user").order("created_at").execute()
        
        if not result.data or len(result.data) == 0:
            raise HTTPException(status_code=404, detail="No hay mensajes del usuario en esta conversación")
            
        # Evaluar cada mensaje
        evaluations = []
        for mensaje in result.data:
            mensaje_id = UUID(mensaje["id"])
            evaluation = lead_evaluation_service.evaluate_message(lead_id, conversacion_id, mensaje_id, empresa_id)
            evaluations.append(evaluation)
            
        return evaluations
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error evaluando conversación: {str(e)}")

@router.get("/lead-evaluations/{lead_id}", response_model=List[EvaluacionLeadResponse])
async def get_lead_evaluations(
    lead_id: UUID
):
    """
    Obtiene todas las evaluaciones para un lead específico
    
    Args:
        lead_id: ID del lead
        
    Returns:
        Lista de evaluaciones
    """
    try:
        result = supabase.table("evaluaciones_llm").select("*").eq("lead_id", str(lead_id)).order("fecha_evaluacion", desc=True).execute()
        
        if not result.data:
            return []
            
        return result.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error obteniendo evaluaciones: {str(e)}")

@router.get("/conversation-evaluations/{conversacion_id}", response_model=List[EvaluacionLeadResponse])
async def get_conversation_evaluations(
    conversacion_id: UUID
):
    """
    Obtiene todas las evaluaciones para una conversación específica
    
    Args:
        conversacion_id: ID de la conversación
        
    Returns:
        Lista de evaluaciones
    """
    try:
        result = supabase.table("evaluaciones_llm").select("*").eq("conversacion_id", str(conversacion_id)).order("fecha_evaluacion").execute()
        
        if not result.data:
            return []
            
        return result.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error obteniendo evaluaciones: {str(e)}")

@router.get("/dashboard-stats/{empresa_id}", response_model=DashboardStats)
async def get_dashboard_stats(
    empresa_id: UUID
):
    """
    Obtiene estadísticas para el dashboard de una empresa
    
    Args:
        empresa_id: ID de la empresa
        
    Returns:
        Estadísticas del dashboard
    """
    try:
        # Total de leads
        result = supabase.table("leads").select("id", count="exact").eq("empresa_id", str(empresa_id)).execute()
        total_leads = result.count if result.count is not None else 0
        
        # Leads por temperatura
        result = supabase.table("lead_temperature_history").\
            select("temperatura, count(*)").\
            eq("empresa_id", str(empresa_id)).\
            order("periodo_fin", desc=True).\
            group_by("temperatura").\
            execute()
        
        leads_por_temperatura = {"caliente": 0, "tibia": 0, "fría": 0}
        if result.data:
            for item in result.data:
                if item["temperatura"] in leads_por_temperatura:
                    leads_por_temperatura[item["temperatura"]] = item["count"]
        
        # Top programas populares (del contexto universitario)
        result = supabase.rpc(
            "get_top_programas_interes",
            {"empresa_id_param": str(empresa_id), "limit_param": 5}
        ).execute()
        
        programas_populares = result.data if result.data else []
        
        # Palabras clave más frecuentes
        result = supabase.rpc(
            "get_top_palabras_clave",
            {"empresa_id_param": str(empresa_id), "limit_param": 10}
        ).execute()
        
        palabras_clave_frecuentes = result.data if result.data else []
        
        # Conversión por etapa (específico para proceso de admisión)
        result = supabase.rpc(
            "get_conversion_por_etapa",
            {"empresa_id_param": str(empresa_id)}
        ).execute()
        
        conversion_por_etapa = result.data if result.data else []
        
        # Score promedio
        result = supabase.table("leads").\
            select("score").\
            eq("empresa_id", str(empresa_id)).\
            execute()
        
        score_promedio = 0
        if result.data and len(result.data) > 0:
            scores = [lead.get("score", 0) for lead in result.data if lead.get("score") is not None]
            if scores:
                score_promedio = sum(scores) / len(scores)
        
        # Tendencia semanal
        result = supabase.rpc(
            "get_tendencia_semanal_leads",
            {"empresa_id_param": str(empresa_id), "semanas_param": 8}
        ).execute()
        
        tendencia_semanal = result.data if result.data else []
        
        return {
            "total_leads": total_leads,
            "leads_por_temperatura": leads_por_temperatura,
            "programas_populares": programas_populares,
            "palabras_clave_frecuentes": palabras_clave_frecuentes,
            "conversion_por_etapa": conversion_por_etapa,
            "score_promedio": score_promedio,
            "tendencia_semanal": tendencia_semanal
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error obteniendo estadísticas: {str(e)}")

@router.get("/message-evaluation/{mensaje_id}", response_model=EvaluacionLeadResponse)
async def get_message_evaluation(
    mensaje_id: UUID
):
    """
    Obtiene la evaluación para un mensaje específico
    
    Args:
        mensaje_id: ID del mensaje
        
    Returns:
        Evaluación del mensaje
    """
    try:
        result = supabase.table("evaluaciones_llm").select("*").eq("mensaje_id", str(mensaje_id)).limit(1).execute()
        
        if not result.data or len(result.data) == 0:
            raise HTTPException(status_code=404, detail="Evaluación no encontrada")
            
        return result.data[0]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error obteniendo evaluación: {str(e)}")

@router.post("/programas-interes/{lead_id}", response_model=List[Dict[str, Any]])
async def get_programas_interes(
    lead_id: UUID,
    threshold: float = 5.0
):
    """
    Obtiene los programas académicos de interés para un lead específico
    
    Args:
        lead_id: ID del lead
        threshold: Umbral mínimo de score para considerar interés (por defecto 5.0)
        
    Returns:
        Lista de programas académicos con puntuación de interés
    """
    try:
        # Consultar intereses específicos en programas
        result = supabase.table("lead_product_interests").\
            select("producto_id, score, created_at").\
            eq("lead_id", str(lead_id)).\
            gte("score", threshold).\
            execute()
        
        if not result.data:
            return []
        
        # Obtener detalles de los productos
        producto_ids = [item["producto_id"] for item in result.data]
        productos_result = supabase.table("empresa_productos").\
            select("id, nombre, descripcion, caracteristicas, imagen_url").\
            in_("id", producto_ids).\
            execute()
        
        productos_map = {p["id"]: p for p in productos_result.data} if productos_result.data else {}
        
        # Combinar la información
        programas_interes = []
        for item in result.data:
            producto_id = item["producto_id"]
            if producto_id in productos_map:
                programa_info = productos_map[producto_id]
                programas_interes.append({
                    "producto_id": producto_id,
                    "nombre": programa_info.get("nombre", ""),
                    "descripcion": programa_info.get("descripcion", ""),
                    "score_interes": item["score"],
                    "fecha_deteccion": item["created_at"],
                    "imagen_url": programa_info.get("imagen_url", "")
                })
        
        # Ordenar por score de interés (mayor a menor)
        programas_interes.sort(key=lambda x: x["score_interes"], reverse=True)
        
        return programas_interes
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error obteniendo programas de interés: {str(e)}")

@router.post("/generar-recomendaciones/{lead_id}", response_model=Dict[str, Any])
async def generar_recomendaciones(
    lead_id: UUID,
    empresa_id: UUID
):
    """
    Genera recomendaciones educativas para un lead basado en su historial
    
    Args:
        lead_id: ID del lead
        empresa_id: ID de la empresa
        
    Returns:
        Recomendaciones para el lead
    """
    try:
        # Obtener información del lead
        lead_result = supabase.table("leads").select("*").eq("id", str(lead_id)).limit(1).execute()
        
        if not lead_result.data or len(lead_result.data) == 0:
            raise HTTPException(status_code=404, detail="Lead no encontrado")
            
        lead_info = lead_result.data[0]
        
        # Obtener intereses detectados
        intereses_result = supabase.table("lead_product_interests").\
            select("producto_id, score").\
            eq("lead_id", str(lead_id)).\
            order("score", desc=True).\
            limit(3).\
            execute()
        
        intereses = intereses_result.data if intereses_result.data else []
        
        # Obtener temperatura actual
        temp_result = supabase.table("lead_temperature_history").\
            select("temperatura, score_periodo").\
            eq("lead_id", str(lead_id)).\
            order("periodo_fin", desc=True).\
            limit(1).\
            execute()
        
        temperatura = "fría"
        score = lead_info.get("score", 0)
        
        if temp_result.data and len(temp_result.data) > 0:
            temperatura = temp_result.data[0]["temperatura"]
            score = temp_result.data[0].get("score_periodo", score)
        
        # Generar recomendaciones basadas en temperatura e intereses
        recomendaciones = []
        
        if temperatura == "caliente":
            recomendaciones.append("Contactar por teléfono para concretar proceso de inscripción")
            recomendaciones.append("Enviar información detallada sobre fechas de matrícula y documentación")
            recomendaciones.append("Ofrecer asesoría personalizada sobre financiación y becas")
            
        elif temperatura == "tibia":
            recomendaciones.append("Enviar información detallada de programas de interés")
            recomendaciones.append("Invitar a una sesión informativa o visita al campus")
            recomendaciones.append("Compartir testimonios de estudiantes actuales")
            
        else:  # fría
            recomendaciones.append("Enviar información general sobre la universidad")
            recomendaciones.append("Mantener contacto periódico con contenido relevante")
            recomendaciones.append("Invitar a eventos abiertos o webinars introductorios")
        
        # Recomendaciones específicas basadas en intereses
        programas_recomendados = []
        if intereses:
            producto_ids = [item["producto_id"] for item in intereses]
            
            # Obtener programas similares o complementarios
            programas_result = supabase.rpc(
                "recomendar_programas_similares",
                {"producto_ids": producto_ids, "empresa_id_param": str(empresa_id), "limit_param": 3}
            ).execute()
            
            programas_recomendados = programas_result.data if programas_result.data else []
        
        return {
            "lead_id": str(lead_id),
            "temperatura": temperatura,
            "score": score,
            "recomendaciones_accion": recomendaciones,
            "programas_recomendados": programas_recomendados,
            "creado_en": str(datetime.now())
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generando recomendaciones: {str(e)}")

@router.post("/configuracion/{empresa_id}", response_model=Dict[str, Any])
async def actualizar_configuracion_evaluacion(
    empresa_id: UUID,
    configuracion: Dict[str, Any]
):
    """
    Actualiza la configuración de evaluación para una empresa
    
    Args:
        empresa_id: ID de la empresa
        configuracion: Configuración actualizada
        
    Returns:
        Configuración guardada
    """
    try:
        # Verificar si ya existe configuración
        result = supabase.table("evaluacion_configuraciones").select("id").eq("empresa_id", str(empresa_id)).limit(1).execute()
        
        configuracion["updated_at"] = str(datetime.now())
        
        if result.data and len(result.data) > 0:
            # Actualizar existente
            config_id = result.data[0]["id"]
            result = supabase.table("evaluacion_configuraciones").update(configuracion).eq("id", config_id).execute()
        else:
            # Crear nueva
            configuracion["empresa_id"] = str(empresa_id)
            configuracion["created_at"] = str(datetime.now())
            result = supabase.table("evaluacion_configuraciones").insert(configuracion).execute()
        
        if not result.data or len(result.data) == 0:
            raise HTTPException(status_code=500, detail="Error guardando configuración")
            
        return result.data[0]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error actualizando configuración: {str(e)}")

@router.post("/sinonimos-producto/", response_model=Dict[str, Any])
async def agregar_sinonimo_producto(
    empresa_id: UUID,
    producto_id: UUID,
    palabra_clave: str
):
    """
    Agrega un sinónimo o palabra clave para un producto/programa académico
    
    Args:
        empresa_id: ID de la empresa
        producto_id: ID del producto/programa
        palabra_clave: Palabra clave o sinónimo a agregar
        
    Returns:
        Sinónimo guardado
    """
    try:
        # Verificar si ya existe
        result = supabase.table("producto_sinonimos").\
            select("id").\
            eq("empresa_id", str(empresa_id)).\
            eq("producto_id", str(producto_id)).\
            eq("palabra_clave", palabra_clave).\
            limit(1).\
            execute()
        
        if result.data and len(result.data) > 0:
            return {"id": result.data[0]["id"], "message": "El sinónimo ya existe"}
        
        # Crear nuevo
        sinonimo_data = {
            "empresa_id": str(empresa_id),
            "producto_id": str(producto_id),
            "palabra_clave": palabra_clave,
            "created_at": str(datetime.now())
        }
        
        result = supabase.table("producto_sinonimos").insert(sinonimo_data).execute()
        
        if not result.data or len(result.data) == 0:
            raise HTTPException(status_code=500, detail="Error guardando sinónimo")
            
        return result.data[0]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error agregando sinónimo: {str(e)}")

@router.get("/calidad-evaluaciones/{chatbot_id}", response_model=Dict[str, Any])
async def get_calidad_evaluaciones(
    chatbot_id: int,
    periodo_inicio: Optional[str] = None,
    periodo_fin: Optional[str] = None
):
    """
    Obtiene métricas de calidad de las evaluaciones para un chatbot
    
    Args:
        chatbot_id: ID del chatbot
        periodo_inicio: Fecha de inicio (opcional)
        periodo_fin: Fecha de fin (opcional)
        
    Returns:
        Métricas de calidad
    """
    try:
        # Construir query base
        query = supabase.table("metricas_calidad_llm").select("*").eq("chatbot_id", chatbot_id)
        
        # Aplicar filtros de periodo si existen
        if periodo_inicio:
            query = query.gte("periodo_inicio", periodo_inicio)
        if periodo_fin:
            query = query.lte("periodo_fin", periodo_fin)
        
        # Ejecutar consulta
        result = query.order("periodo_fin", desc=True).limit(1).execute()
        
        if not result.data or len(result.data) == 0:
            return {
                "chatbot_id": chatbot_id,
                "total_mensajes": 0,
                "mensajes_evaluados": 0,
                "promedio_puntuacion": 0,
                "distribucion_puntuaciones": {},
                "temas_problematicos": []
            }
            
        return result.data[0]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error obteniendo calidad de evaluaciones: {str(e)}")
