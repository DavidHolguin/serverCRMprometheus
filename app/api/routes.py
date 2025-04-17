from fastapi import APIRouter, HTTPException, Depends, Body, Query, Path, Request, Response, status
from typing import Dict, Any, List, Optional
from uuid import UUID, uuid4
import logging
import os
import json

# Configurar logger
logger = logging.getLogger(__name__)

from app.models.message import (
    ChannelMessageRequest, 
    ChannelMessageResponse, 
    AgentMessageRequest,
    ToggleChatbotRequest,
    ToggleChatbotResponse
)
from app.models.audio import AudioMessageRequest, AudioMessageResponse
from app.models.conversation import ConversationHistory
from app.services.conversation_service import conversation_service
from app.models.examples import EXAMPLES
from app.api.endpoints.evaluations import router as evaluations_router
from app.core.config import settings
from app.db.supabase_client import supabase

# Create API router
api_router = APIRouter()

# Incluir router de evaluaciones
api_router.include_router(
    evaluations_router,
    prefix="/evaluations",
    tags=["evaluations"]
)

@api_router.post("/message", response_model=ChannelMessageResponse)
async def process_message(request: ChannelMessageRequest):
    """
    Process a message from any channel and generate a response
    
    Args:
        request: The message request containing channel, company, chatbot, and message information
        
    Returns:
        The response message
    """
    try:
        response = conversation_service.process_channel_message(
            canal_id=request.canal_id,
            canal_identificador=request.canal_identificador,
            empresa_id=request.empresa_id,
            chatbot_id=request.chatbot_id,
            mensaje=request.mensaje,
            lead_id=request.lead_id,
            metadata=request.metadata
        )
        
        return ChannelMessageResponse(
            mensaje_id=response["mensaje_id"],
            conversacion_id=response["conversacion_id"],
            respuesta=response["respuesta"],
            metadata=response["metadata"]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing message: {str(e)}")

@api_router.get("/conversation/{conversation_id}/history", response_model=ConversationHistory)
async def get_conversation_history(
    conversation_id: UUID = Path(..., description="The ID of the conversation"),
    limit: int = Query(10, description="Maximum number of messages to retrieve")
):
    """
    Get the history of a conversation
    
    Args:
        conversation_id: The ID of the conversation
        limit: Maximum number of messages to retrieve
        
    Returns:
        The conversation history
    """
    try:
        from app.services.langchain_service import langchain_service
        
        messages = langchain_service._get_conversation_history(conversation_id, limit)
        
        return ConversationHistory(
            conversation_id=conversation_id,
            messages=messages
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving conversation history: {str(e)}")

WHATSAPP_VERIFY_TOKEN = settings.WHATSAPP_VERIFY_TOKEN

@api_router.get("/webhook")
async def verify_whatsapp_webhook(
    request: Request,
    response: Response
):
    """
    Verifica el webhook de WhatsApp usando el token de verificación.
    """
    logger.info("Recibida solicitud GET en /webhook para verificación")
    # Extraer parámetros de la query string
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")

    logger.debug(f"Mode: {mode}, Token: {token}, Challenge: {challenge}")

    # Verificar si es una solicitud de suscripción y el token coincide
    if mode == "subscribe" and token == WHATSAPP_VERIFY_TOKEN:
        logger.info("Verificación de webhook de WhatsApp exitosa.")
        # Devolver el challenge con status code 200
        response.status_code = status.HTTP_200_OK
        return Response(content=challenge, media_type="text/plain")
    else:
        # Si el token no coincide o falta el modo, devolver error 403
        logger.warning(f"Fallo en la verificación del webhook de WhatsApp. Token recibido: {token}, Token esperado: {WHATSAPP_VERIFY_TOKEN}")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Token de verificación inválido o modo incorrecto")

@api_router.post("/webhook")
async def handle_whatsapp_webhook(request: Request):
    """
    Maneja los eventos entrantes del webhook de WhatsApp (mensajes, etc.),
    buscando o creando leads y separando datos personales.
    """
    logger.info("Recibida solicitud POST en /webhook")
    try:
        # Verificar si hay contenido en el cuerpo de la solicitud
        body = await request.body()
        if not body:
            logger.warning("Se recibió una solicitud con cuerpo vacío")
            return Response(status_code=status.HTTP_200_OK)
            
        # Intentar parsear el cuerpo como JSON
        try:
            payload = await request.json()
        except json.JSONDecodeError as json_err:
            logger.warning(f"Error al decodificar JSON: {json_err}. Contenido recibido: {body[:100]}...")
            return Response(status_code=status.HTTP_200_OK)
            
        logger.debug(f"Payload recibido: {payload}")

        # 1. Validar estructura básica del payload de WhatsApp
        if not payload.get("object") == "whatsapp_business_account":
            logger.warning("Payload no es de una cuenta de WhatsApp Business.")
            return Response(status_code=status.HTTP_200_OK)

        entries = payload.get("entry", [])
        if not entries:
            logger.warning("Payload sin 'entry'.")
            return Response(status_code=status.HTTP_200_OK)

        for entry in entries:
            changes = entry.get("changes", [])
            if not changes:
                continue

            for change in changes:
                value = change.get("value", {})
                if not value:
                    continue

                # Solo procesar mensajes entrantes por ahora
                if "messages" in value:
                    messages = value.get("messages", [])
                    contacts = value.get("contacts", []) # Obtener info del contacto

                    for message in messages:
                        # 2. Extraer Identificador y datos básicos
                        phone_number = message.get("from")
                        message_body = message.get("text", {}).get("body")
                        message_id_wa = message.get("id")
                        timestamp = message.get("timestamp")

                        if not phone_number or not message_body:
                            logger.info(f"Mensaje incompleto recibido (ID: {message_id_wa}). Ignorando.")
                            continue

                        logger.info(f"Procesando mensaje de {phone_number}: '{message_body}'")

                        # --- Inicio Lógica de Lead y Canal ---

                        # Buscar canal de WhatsApp
                        channel_result = supabase.table("canales").select("id").eq("tipo", "whatsapp").limit(1).execute()
                        if not channel_result.data:
                            logger.error("Canal de WhatsApp no encontrado en la base de datos.")
                            continue # Saltar al siguiente mensaje/cambio
                        canal_id = UUID(channel_result.data[0]["id"])

                        # Buscar configuración de chatbot activa para este canal
                        # Asumimos una config activa por canal WhatsApp para simplificar
                        chatbot_channel_result = supabase.table("chatbot_canales").select("chatbot_id, empresa_id").eq("canal_id", str(canal_id)).eq("is_active", True).limit(1).execute()
                        if not chatbot_channel_result.data:
                            logger.warning(f"No se encontró configuración de chatbot activa para el canal WhatsApp (ID: {canal_id}).")
                            continue
                        chatbot_config = chatbot_channel_result.data[0]
                        chatbot_id = UUID(chatbot_config["chatbot_id"])
                        empresa_id = UUID(chatbot_config["empresa_id"])

                        # --- Fin Lógica de Lead y Canal ---

                        # --- Inicio Lógica de Búsqueda/Creación de Lead ---
                        lead_id = None
                        lead_found = False

                        # 3. Buscar Lead existente por canal_id y canal_identificador (teléfono)
                        lead_result = supabase.table("leads") \
                            .select("id") \
                            .eq("telefono", phone_number) \
                            .eq("empresa_id", str(empresa_id)) \
                            .limit(1).execute()

                        if lead_result.data:
                            lead_id = UUID(lead_result.data[0]["id"])
                            lead_found = True
                            logger.info(f"Lead existente encontrado para {phone_number}: ID {lead_id}")
                        else:
                            # 3.1. Crear Lead si no existe
                            logger.info(f"Lead no encontrado para {phone_number}. Creando nuevo lead...")
                            try:
                                # Crear registro básico en leads
                                insert_lead_result = supabase.table("leads").insert({
                                    "empresa_id": str(empresa_id),
                                    "origen_canal_id": str(canal_id), # Marcar de dónde vino originalmente
                                    "telefono": phone_number # Guardar teléfono directamente si el modelo lo permite
                                }).execute()

                                if not insert_lead_result.data:
                                    logger.error(f"Error al crear el lead para {phone_number}")
                                    continue # Saltar al siguiente mensaje

                                lead_id = UUID(insert_lead_result.data[0]["id"])
                                logger.info(f"Nuevo lead creado para {phone_number}: ID {lead_id}")

                                # 3.2. Guardar Datos Personales (si existen en el payload)
                                if contacts:
                                    profile_name = contacts[0].get("profile", {}).get("name")
                                    if profile_name:
                                        logger.info(f"Guardando nombre '{profile_name}' en lead_datos_personales para lead {lead_id}")
                                        supabase.table("lead_datos_personales").insert({
                                            "lead_id": str(lead_id),
                                            "campo": "nombre_whatsapp", # Usar un nombre de campo específico
                                            "valor": profile_name
                                        }).execute()

                            except Exception as e_create:
                                logger.error(f"Excepción al crear lead o guardar datos para {phone_number}: {e_create}", exc_info=True)
                                continue # Saltar al siguiente mensaje si falla la creación

                        # --- Fin Lógica de Búsqueda/Creación de Lead ---

                        if not lead_id:
                             logger.error(f"No se pudo obtener o crear un lead_id para {phone_number}. Abortando procesamiento para este mensaje.")
                             continue

                        # 4. Preparar Metadata para el Servicio (SIN datos personales crudos)
                        metadata_for_service = {
                            "whatsapp_message_id": message_id_wa,
                            "timestamp": timestamp,
                            "lead_found": lead_found # Podría ser útil para el servicio saber si es nuevo
                        }

                        # 5. Llamar al Servicio de Conversación
                        try:
                            logger.debug(f"Llamando a process_channel_message para lead {lead_id}")
                            response_data = conversation_service.process_channel_message(
                                canal_id=canal_id,
                                canal_identificador=phone_number,
                                empresa_id=empresa_id,
                                chatbot_id=chatbot_id,
                                mensaje=message_body,
                                lead_id=lead_id, # Pasar el ID del lead encontrado o creado
                                metadata=metadata_for_service # Pasar metadata sanitizada
                            )
                            logger.info(f"Respuesta generada para {phone_number} (Lead: {lead_id}): {response_data.get('respuesta')[:50]}...")
                        except Exception as e_service:
                            logger.error(f"Error al procesar mensaje para lead {lead_id} en conversation_service: {e_service}", exc_info=True)

        # Responder a WhatsApp con 200 OK para confirmar la recepción
        return Response(status_code=status.HTTP_200_OK)

    except Exception as e:
        logger.error(f"Error general al manejar el webhook de WhatsApp: {e}", exc_info=True)
        # Devolver 500 para indicar un error interno grave
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error interno al procesar el webhook")

@api_router.post("/agent/message", response_model=ChannelMessageResponse)
async def agent_send_message(request: AgentMessageRequest = Body(..., example=EXAMPLES["agent_message"]["value"])):
    """
    Allow a human agent to send a message to a lead
    
    Args:
        request: The message request containing conversation_id, agent_id, and message content
        
    Returns:
        The response message
    """
    try:
        conversation_id = request.conversation_id
        agent_id = request.agent_id
        mensaje = request.mensaje
        
        # Get conversation details
        from app.db.supabase_client import supabase
        conv_result = supabase.table("conversaciones").select("*").eq("id", str(conversation_id)).limit(1).execute()
        
        if not conv_result.data or len(conv_result.data) == 0:
            raise HTTPException(status_code=404, detail=f"Conversation {conversation_id} not found")
        
        conversation = conv_result.data[0]
        
        # Check if chatbot is active and deactivate it if needed
        if request.deactivate_chatbot and conversation.get("chatbot_activo", True):
            supabase.table("conversaciones").update({"chatbot_activo": False}).eq("id", str(conversation_id)).execute()
        
        # Save agent message
        from app.services.langchain_service import langchain_service
        
        message_data = {
            "conversacion_id": str(conversation_id),
            "origen": "agent",
            "remitente_id": str(agent_id),
            "contenido": mensaje,
            "tipo_contenido": "text",
            "metadata": request.metadata
        }
        
        # Save message directly to database
        message_result = supabase.table("mensajes").insert(message_data).execute()
        
        if not message_result.data or len(message_result.data) == 0:
            raise HTTPException(status_code=500, detail="Failed to save agent message")
        
        mensaje_id = UUID(message_result.data[0]["id"])
        
        # Update conversation's last message timestamp
        supabase.table("conversaciones").update({
            "ultimo_mensaje": "now()",
            "metadata": {
                **(conversation.get("metadata") or {}),
                "last_agent_id": str(agent_id)
            }
        }).eq("id", str(conversation_id)).execute()
        
        # Send message to the lead through the appropriate channel
        from app.services.channel_service import channel_service
        channel_response = channel_service.send_message_to_channel(
            conversation_id=conversation_id,
            message=mensaje,
            metadata={
                "agent_id": str(agent_id),
                "origin": "agent",
                "message_id": str(mensaje_id)
            }
        )
        
        return ChannelMessageResponse(
            mensaje_id=mensaje_id,
            conversacion_id=conversation_id,
            respuesta=mensaje,
            metadata={
                "agent_id": str(agent_id),
                "origin": "agent",
                "channel_response": channel_response
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing agent message: {str(e)}")

@api_router.post("/agent/toggle-chatbot", response_model=ToggleChatbotResponse)
async def toggle_chatbot(request: ToggleChatbotRequest = Body(..., example=EXAMPLES["toggle_chatbot"]["value"])):
    """
    Toggle the chatbot active status for a specific conversation
    
    Args:
        request: The request containing conversation_id and the desired chatbot_activo state
        
    Returns:
        The updated conversation data
    """
    try:
        conversation_id = request.conversation_id
        chatbot_activo = request.chatbot_activo
        
        # Update conversation
        from app.db.supabase_client import supabase
        result = supabase.table("conversaciones").update({
            "chatbot_activo": chatbot_activo
        }).eq("id", str(conversation_id)).execute()
        
        if not result.data or len(result.data) == 0:
            raise HTTPException(status_code=404, detail=f"Conversation {conversation_id} not found")
        
        return ToggleChatbotResponse(
            success=True,
            conversation_id=str(conversation_id),
            chatbot_activo=chatbot_activo,
            data=result.data[0]
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error toggling chatbot status: {str(e)}")
