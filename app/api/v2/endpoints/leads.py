from typing import Optional
from fastapi import APIRouter, HTTPException
from uuid import UUID, uuid4
from datetime import datetime
import logging

from app.models.v2.lead_form import LeadFormData, LeadFormResponse
from app.db.supabase_client import supabase
from app.services.conversation_service import conversation_service

# Configurar logger
logger = logging.getLogger(__name__)

router = APIRouter()

# Canal de formulario web por defecto
WEB_FORM_CHANNEL_ID = "54826ff3-f024-4161-b157-60c37d8e8f3d"

@router.post("/web-form", response_model=LeadFormResponse)
async def create_lead_from_form(form_data: LeadFormData):
    """
    Crea un nuevo lead a partir de datos de un formulario web.
    
    Args:
        form_data: Datos del formulario web incluyendo información personal y metadata
        
    Returns:
        LeadFormResponse con los detalles del lead creado
    """
    try:
        # 1. Verificar si la empresa existe
        empresa_result = supabase.table("empresas").select("*").eq("id", str(form_data.empresa_id)).limit(1).execute()
        if not empresa_result.data:
            raise HTTPException(status_code=404, detail="Empresa no encontrada")
            
        # 2. Verificar si el lead ya existe por email o teléfono
        lead_id = None
        existing_lead = None
        
        if form_data.email:
            lead_datos_result = supabase.table("lead_datos_personales")\
                .select("lead_id")\
                .eq("email", form_data.email)\
                .limit(1)\
                .execute()
                
            if lead_datos_result.data:
                # Verificar que el lead pertenezca a la misma empresa
                lead_id_found = lead_datos_result.data[0]["lead_id"]
                lead_result = supabase.table("leads")\
                    .select("*")\
                    .eq("id", lead_id_found)\
                    .eq("empresa_id", str(form_data.empresa_id))\
                    .limit(1)\
                    .execute()
                    
                if lead_result.data:
                    existing_lead = lead_result.data[0]
                    lead_id = UUID(lead_id_found)
        
        if not lead_id and form_data.telefono:
            lead_datos_result = supabase.table("lead_datos_personales")\
                .select("lead_id")\
                .eq("telefono", form_data.telefono)\
                .limit(1)\
                .execute()
                
            if lead_datos_result.data:
                # Verificar que el lead pertenezca a la misma empresa
                lead_id_found = lead_datos_result.data[0]["lead_id"]
                lead_result = supabase.table("leads")\
                    .select("*")\
                    .eq("id", lead_id_found)\
                    .eq("empresa_id", str(form_data.empresa_id))\
                    .limit(1)\
                    .execute()
                    
                if lead_result.data:
                    existing_lead = lead_result.data[0]
                    lead_id = UUID(lead_id_found)
        
        # Determinar el canal_id
        canal_id = form_data.channel_id if form_data.channel_id else UUID(WEB_FORM_CHANNEL_ID)
        
        if not lead_id:
            # 3. Crear nuevo lead
            new_lead = {
                "empresa_id": str(form_data.empresa_id),
                "canal_origen": "formulario_web",
                "canal_id": str(canal_id),
                "pipeline_id": str(form_data.pipeline_id) if form_data.pipeline_id else None,
                "stage_id": str(form_data.stage_id) if form_data.stage_id else None,
                "estado": "nuevo",
                "score": 0,  # Score inicial
                "is_active": True
            }
            
            lead_result = supabase.table("leads").insert(new_lead).execute()
            if not lead_result.data:
                raise HTTPException(status_code=500, detail="Error al crear el lead")
                
            lead_id = UUID(lead_result.data[0]["id"])
            logger.info(f"Nuevo lead creado desde formulario web: {lead_id}")
            
            # 4. Guardar datos personales
            lead_datos = {
                "lead_id": str(lead_id),
                "nombre": form_data.nombre,
                "email": form_data.email,
                "telefono": form_data.telefono,
                "pais": form_data.pais,
                "ciudad": form_data.ciudad,
                "direccion": form_data.direccion
            }
            
            supabase.table("lead_datos_personales").insert(lead_datos).execute()
            
        else:
            # Actualizar datos personales del lead existente
            supabase.table("lead_datos_personales")\
                .update({
                    "nombre": form_data.nombre,
                    "email": form_data.email if form_data.email else None,
                    "telefono": form_data.telefono if form_data.telefono else None,
                    "pais": form_data.pais if form_data.pais else None,
                    "ciudad": form_data.ciudad if form_data.ciudad else None,
                    "direccion": form_data.direccion if form_data.direccion else None
                })\
                .eq("lead_id", str(lead_id))\
                .execute()
                
            logger.info(f"Datos actualizados para lead existente: {lead_id}")
            
        # 5. Crear o actualizar entrada en dim_entidades
        entidad_data = {
            "entidad_id": str(lead_id),
            "tipo_entidad": "lead",
            "entidad_original_id": str(lead_id),
            "nombre": form_data.nombre,
            "descripcion": "Lead creado desde formulario web",
            "metadata": {
                "email": form_data.email,
                "telefono": form_data.telefono,
                "pais": form_data.pais,
                "ciudad": form_data.ciudad
            },
            "is_active": True
        }
        
        # Verificar si ya existe la entidad
        entidad_result = supabase.table("dim_entidades")\
            .select("*")\
            .eq("entidad_id", str(lead_id))\
            .limit(1)\
            .execute()
            
        if not entidad_result.data:
            # Crear nueva entidad
            supabase.table("dim_entidades").insert(entidad_data).execute()
        else:
            # Actualizar entidad existente
            supabase.table("dim_entidades")\
                .update(entidad_data)\
                .eq("entidad_id", str(lead_id))\
                .execute()
        
        # 6. Registrar evento y metadata
        event_data =  {
            "origen_url": str(form_data.origen_url) if form_data.origen_url else None,
            "pagina_titulo": form_data.pagina_titulo,
            "tiempo_navegacion": form_data.tiempo_navegacion,
            "profundidad_scroll": form_data.profundidad_scroll,
            "ip_address": form_data.ip_address,
            **(form_data.metadata or {})
        }
          # Crear o obtener registro en dim_tiempo para la fecha actual
        fecha_actual = datetime.now()
        tiempo_result = supabase.table("dim_tiempo")\
            .select("tiempo_id")\
            .eq("fecha", fecha_actual.date().isoformat())\
            .limit(1)\
            .execute()

        tiempo_id = None
        if tiempo_result.data:
            tiempo_id = tiempo_result.data[0]["tiempo_id"]
        else:
            # Crear nuevo registro en dim_tiempo
            tiempo_data = {
                "fecha": fecha_actual.date().isoformat(),
                "dia_semana": fecha_actual.weekday(),
                "dia": fecha_actual.day,
                "semana": fecha_actual.isocalendar()[1],
                "mes": fecha_actual.month,
                "trimestre": (fecha_actual.month - 1) // 3 + 1,
                "anio": fecha_actual.year,
                "es_fin_semana": fecha_actual.weekday() >= 5,
                "nombre_dia": fecha_actual.strftime("%A"),
                "nombre_mes": fecha_actual.strftime("%B"),
                "fecha_completa": fecha_actual.isoformat()
            }
            tiempo_insert = supabase.table("dim_tiempo").insert(tiempo_data).execute()
            if tiempo_insert.data:
                tiempo_id = tiempo_insert.data[0]["tiempo_id"]
            else:
                raise HTTPException(status_code=500, detail="Error al crear registro de tiempo")

        # Obtener tipo_evento_id para formularios web
        tipo_evento_result = supabase.table("dim_tipos_eventos")\
            .select("tipo_evento_id")\
            .eq("nombre", "formulario_web_completado")\
            .eq("categoria", "lead")\
            .limit(1)\
            .execute()

        tipo_evento_id = None
        if tipo_evento_result.data:
            tipo_evento_id = tipo_evento_result.data[0]["tipo_evento_id"]
        else:
            # Crear nuevo tipo de evento
            tipo_evento_data = {
                "categoria": "lead",
                "nombre": "formulario_web_completado",
                "descripcion": "El lead completó un formulario web"
            }
            tipo_evento_insert = supabase.table("dim_tipos_eventos").insert(tipo_evento_data).execute()
            if tipo_evento_insert.data:
                tipo_evento_id = tipo_evento_insert.data[0]["tipo_evento_id"]
            else:
                raise HTTPException(status_code=500, detail="Error al crear tipo de evento")

        # Crear el registro en fact_eventos_acciones
        evento = {
            "evento_accion_id": str(uuid4()),
            "tiempo_id": tiempo_id,
            "empresa_id": str(form_data.empresa_id),
            "tipo_evento_id": tipo_evento_id,
            "entidad_origen_id": str(lead_id),  # El lead es la entidad que origina el evento
            "lead_id": str(lead_id),
            "canal_id": str(canal_id),
            "valor_score": 10,  # Valor por defecto por llenar formulario
            "resultado": "completado",
            "detalle": "Formulario web completado",
            "metadata": event_data,
            "created_at": fecha_actual.isoformat()
        }
        
        supabase.table("fact_eventos_acciones").insert(evento).execute()
        
        # 6. Crear conversación si no existe una activa
        conversation_id = None
        try:
            # Intentar obtener una conversación existente activa
            conv_result = supabase.table("conversaciones")\
                .select("id")\
                .eq("lead_id", str(lead_id))\
                .eq("canal_id", str(canal_id))\
                .eq("estado", "activa")\
                .limit(1)\
                .execute()
                
            if conv_result.data:
                conversation_id = UUID(conv_result.data[0]["id"])
            else:
                # Crear nueva conversación
                new_conversation = {
                    "lead_id": str(lead_id),
                    "canal_id": str(canal_id),
                    "canal_identificador": form_data.email or form_data.telefono,
                    "estado": "activa",
                    "metadata": event_data,
                    "chatbot_activo": True
                }
                
                conv_result = supabase.table("conversaciones").insert(new_conversation).execute()
                if conv_result.data:
                    conversation_id = UUID(conv_result.data[0]["id"])
                    
        except Exception as e:
            logger.error(f"Error al crear/obtener conversación: {str(e)}")
            # No lanzar error, ya que la creación del lead fue exitosa
            
        return LeadFormResponse(
            lead_id=lead_id,
            conversation_id=conversation_id,
            status="success",
            message="Lead creado/actualizado exitosamente",
            created_at=datetime.now()
        )
            
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error al procesar formulario web: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error al procesar formulario web: {str(e)}")
