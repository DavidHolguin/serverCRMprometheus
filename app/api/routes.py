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
    ToggleChatbotResponse,
    AgentDirectMessageRequest
)
from app.models.audio import AudioMessageRequest, AudioMessageResponse
from app.models.conversation import ConversationHistory
from app.services.conversation_service import conversation_service
from app.services.audio_service import audio_service
from app.models.examples import EXAMPLES
from app.api.endpoints.evaluations import router as evaluations_router
from app.api.v2.router import v2_router
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

# Incluir router v2
api_router.include_router(v2_router)

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
        # Si se proporciona chatbot_canal_id, usar process_message_by_chatbot_channel
        if request.chatbot_canal_id:
            from app.services.channel_service import channel_service
            
            response = channel_service.process_message_by_chatbot_channel(
                chatbot_canal_id=request.chatbot_canal_id,
                canal_identificador=request.canal_identificador,
                mensaje=request.mensaje,
                lead_id=request.lead_id,
                metadata=request.metadata
            )
        else:
            # Método tradicional usando canal_id, empresa_id y chatbot_id
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

@api_router.post("/channels/audio", response_model=AudioMessageResponse)
async def process_audio_message(request: AudioMessageRequest = Body(...)):
    """
    Process audio messages from any channel, transcribe and generate a response
    
    Args:
        request: The audio message request containing audio data and channel information
        
    Returns:
        The response with transcription and chatbot reply
    """
    try:
        logger.info(f"Procesando mensaje de audio desde canal {request.canal_identificador}")
        
        # Si se proporciona chatbot_contexto_id, usar process_audio_by_chatbot_contexto
        if hasattr(request, 'chatbot_contexto_id') and request.chatbot_contexto_id:
            from app.services.channel_service import channel_service
            
            # Obtener configuración del contexto
            try:
                config = channel_service.get_chatbot_contexto_config(request.chatbot_contexto_id)
                canal_id = UUID(config["canal_id"])
                chatbot_id = UUID(config["chatbot_id"])
                empresa_id = UUID(config["empresa_id"])
            except Exception as e:
                logger.error(f"Error al obtener configuración del contexto: {str(e)}")
                raise ValueError(f"Error al obtener configuración del contexto: {str(e)}")
                
            # Asegurarnos de que conversacion_id sea None y no "None" o undefined
            conversacion_id = None
            if hasattr(request, 'conversacion_id') and request.conversacion_id and request.conversacion_id != "None" and request.conversacion_id != "undefined":
                conversacion_id = request.conversacion_id
            
            response = audio_service.process_audio_message(
                canal_id=canal_id,
                canal_identificador=request.canal_identificador,
                empresa_id=empresa_id,
                chatbot_id=chatbot_id,
                audio_base64=request.audio_base64,
                formato_audio=request.formato_audio,
                idioma=request.idioma,
                conversacion_id=conversacion_id,
                lead_id=request.lead_id,
                metadata=request.metadata
            )
        else:
            # Método tradicional usando canal_id, empresa_id y chatbot_id
            # Asegurarnos de que conversacion_id sea None y no "None" o undefined
            conversacion_id = None
            if hasattr(request, 'conversacion_id') and request.conversacion_id and request.conversacion_id != "None" and request.conversacion_id != "undefined":
                conversacion_id = request.conversacion_id
                
            response = audio_service.process_audio_message(
                canal_id=request.canal_id,
                canal_identificador=request.canal_identificador,
                empresa_id=request.empresa_id,
                chatbot_id=request.chatbot_id,
                audio_base64=request.audio_base64,
                formato_audio=request.formato_audio,
                idioma=request.idioma,
                conversacion_id=conversacion_id,
                lead_id=request.lead_id,
                metadata=request.metadata
            )
        
        logger.info(f"Audio procesado exitosamente para conversación {response['conversacion_id']}")
        
        return AudioMessageResponse(
            mensaje_id=response["mensaje_id"],
            conversacion_id=response["conversacion_id"],
            audio_id=response["audio_id"],
            transcripcion=response["transcripcion"],
            respuesta=response["respuesta"],
            duracion_segundos=response["duracion_segundos"],
            idioma_detectado=response["idioma_detectado"],
            metadata=response["metadata"]
        )
    except Exception as e:
        logger.error(f"Error al procesar mensaje de audio: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error al procesar mensaje de audio: {str(e)}")

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
                        message_id_wa = message.get("id")
                        timestamp = message.get("timestamp")
                        message_type = "text"  # Por defecto es texto
                        message_body = None
                        audio_data = None

                        # Verificar si es un mensaje de texto o audio
                        if "text" in message and message.get("text", {}).get("body"):
                            message_type = "text"
                            message_body = message.get("text", {}).get("body")
                        elif "audio" in message:
                            message_type = "audio"
                            audio_data = message.get("audio", {})
                            logger.info(f"Mensaje de audio recibido: {audio_data}")

                        if not phone_number or (message_type == "text" and not message_body and message_type == "audio" and not audio_data):
                            logger.info(f"Mensaje incompleto recibido (ID: {message_id_wa}). Ignorando.")
                            continue

                        logger.info(f"Procesando mensaje de tipo {message_type} de {phone_number}")

                        # --- Inicio Lógica de Lead y Canal ---

                        # Buscar canal de WhatsApp
                        channel_result = supabase.table("canales").select("id").eq("tipo", "whatsapp").limit(1).execute()
                        if not channel_result.data:
                            logger.error("Canal de WhatsApp no encontrado en la base de datos.")
                            continue # Saltar al siguiente mensaje/cambio
                        canal_id = UUID(channel_result.data[0]["id"])

                        # Buscar configuración de chatbot activa para este canal
                        chatbot_channel_result = supabase.table("chatbot_canales").select("chatbot_id").eq("canal_id", str(canal_id)).eq("is_active", True).limit(1).execute()
                        if not chatbot_channel_result.data:
                            logger.warning(f"No se encontró configuración de chatbot activa para el canal WhatsApp (ID: {canal_id}).")
                            continue
                        
                        chatbot_id = UUID(chatbot_channel_result.data[0]["chatbot_id"])
                        
                        # Obtener la empresa_id desde la tabla de chatbots usando el chatbot_id
                        chatbot_result = supabase.table("chatbots").select("empresa_id").eq("id", str(chatbot_id)).limit(1).execute()
                        if not chatbot_result.data:
                            logger.warning(f"No se encontró información del chatbot (ID: {chatbot_id}).")
                            continue
                        
                        empresa_id = UUID(chatbot_result.data[0]["empresa_id"])
                        logger.info(f"Procesando mensaje para empresa_id: {empresa_id}, chatbot_id: {chatbot_id}")

                        # --- Fin Lógica de Lead y Canal ---

                        # --- Inicio Lógica de Búsqueda/Creación de Lead ---
                        lead_id = None
                        lead_found = False

                        # 3. Buscar Lead existente por teléfono en lead_datos_personales
                        logger.info(f"Buscando lead con teléfono {phone_number}")
                        
                        # Buscar primero en lead_datos_personales
                        lead_datos_result = supabase.table("lead_datos_personales") \
                            .select("lead_id") \
                            .eq("telefono", phone_number) \
                            .limit(1).execute()
                            
                        if lead_datos_result.data:
                            lead_id = UUID(lead_datos_result.data[0]["lead_id"])
                            
                            # Verificar que el lead pertenezca a la misma empresa
                            lead_empresa_result = supabase.table("leads") \
                                .select("id") \
                                .eq("id", str(lead_id)) \
                                .eq("empresa_id", str(empresa_id)) \
                                .limit(1).execute()
                                
                            if lead_empresa_result.data:
                                lead_found = True
                                logger.info(f"Lead existente encontrado para {phone_number}: ID {lead_id}")
                            else:
                                lead_id = None  # Reset si el lead no pertenece a la empresa correcta
                                logger.warning(f"Lead encontrado para {phone_number} pero pertenece a otra empresa")
                        
                        if not lead_id:
                            # 3.1. Crear Lead si no existe
                            logger.info(f"Lead no encontrado para {phone_number}. Creando nuevo lead...")
                            try:
                                # Crear registro básico en leads
                                insert_lead_result = supabase.table("leads").insert({
                                    "empresa_id": str(empresa_id),
                                    "canal_origen": "whatsapp",
                                    "canal_id": str(canal_id), # Marcar de dónde vino originalmente
                                    "estado": "nuevo"
                                }).execute()

                                if not insert_lead_result.data:
                                    logger.error(f"Error al crear el lead para {phone_number}")
                                    continue # Saltar al siguiente mensaje

                                lead_id = UUID(insert_lead_result.data[0]["id"])
                                logger.info(f"Nuevo lead creado para {phone_number}: ID {lead_id}")

                                # 3.2. Guardar el teléfono en lead_datos_personales
                                supabase.table("lead_datos_personales").insert({
                                    "lead_id": str(lead_id),
                                    "telefono": phone_number
                                }).execute()
                                logger.info(f"Teléfono {phone_number} guardado para lead {lead_id}")

                                # 3.3. Guardar Datos Personales adicionales (si existen en el payload)
                                if contacts:
                                    profile_name = contacts[0].get("profile", {}).get("name")
                                    if profile_name:
                                        logger.info(f"Actualizando lead_datos_personales con nombre '{profile_name}' para lead {lead_id}")
                                        # Actualizar el registro recién creado con el nombre
                                        supabase.table("lead_datos_personales").update({
                                            "nombre": profile_name
                                        }).eq("lead_id", str(lead_id)).execute()

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
                            "lead_found": lead_found, # Podría ser útil para el servicio saber si es nuevo
                            "message_type": message_type
                        }
                        
                        # 5. Procesar el mensaje según su tipo
                        try:
                            if message_type == "text":
                                # Procesar mensaje de texto normal
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
                            
                            elif message_type == "audio":
                                # Procesar mensaje de audio
                                logger.info(f"Procesando mensaje de audio para WhatsApp, lead {lead_id}")
                                
                                # Para WhatsApp necesitamos descargar el audio desde la URL de la API
                                audio_id = audio_data.get("id")
                                mime_type = audio_data.get("mime_type", "audio/ogg")  # WhatsApp suele usar audio/ogg para los audios
                                
                                try:
                                    # Importar el servicio de audio
                                    from app.services.audio_service import audio_service
                                    
                                    # Preparar metadata para el audio
                                    audio_metadata = {
                                        **metadata_for_service,
                                        "mime_type": mime_type,
                                        "origin": "whatsapp"
                                    }
                                    
                                    # Procesar el audio de forma asíncrona (sin usar asyncio.run() que causa el error)
                                    # Como ya estamos en un contexto asíncrono, usamos await directamente
                                    response_data = await audio_service.process_whatsapp_audio(
                                        canal_id=canal_id,
                                        phone_number=phone_number,
                                        empresa_id=empresa_id,
                                        chatbot_id=chatbot_id,
                                        audio_id=audio_id,
                                        lead_id=lead_id,
                                        metadata=audio_metadata
                                    )
                                    
                                    logger.info(f"Audio de WhatsApp procesado exitosamente. Transcripción: {response_data.get('transcripcion')[:50]}...")
                                    logger.info(f"Respuesta generada para {phone_number} (Lead: {lead_id}): {response_data.get('respuesta')[:50]}...")
                                except Exception as e_audio:
                                    logger.error(f"Error al procesar audio de WhatsApp: {str(e_audio)}", exc_info=True)
                                    # Si falla el procesamiento de audio, intentamos responder con un mensaje genérico
                                    try:
                                        # Responder al usuario indicando que hubo un problema con el audio
                                        fallback_message = "Lo siento, hubo un problema al procesar tu mensaje de audio. ¿Podrías intentar enviar un mensaje de texto?"
                                        conversation_service.process_channel_message(
                                            canal_id=canal_id,
                                            canal_identificador=phone_number,
                                            empresa_id=empresa_id,
                                            chatbot_id=chatbot_id,
                                            mensaje=fallback_message,
                                            lead_id=lead_id,
                                            metadata={**metadata_for_service, "error_audio": str(e_audio), "is_system_message": True}
                                        )
                                    except Exception as e_fallback:
                                        logger.error(f"Error al enviar mensaje de fallback: {str(e_fallback)}", exc_info=True)

                        except Exception as e_service:
                            logger.error(f"Error al procesar mensaje para lead {lead_id}: {e_service}", exc_info=True)

        # Responder a WhatsApp con 200 OK para confirmar la recepción
        return Response(status_code=status.HTTP_200_OK)

    except Exception as e:
        logger.error(f"Error general al manejar el webhook de WhatsApp: {e}", exc_info=True)
        # Devolver 500 para indicar un error interno grave
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error interno al procesar el webhook")

@api_router.post("/agent/message", response_model=ChannelMessageResponse)
async def agent_send_message(request: AgentMessageRequest = Body(...)):
    """
    Endpoint unificado para que un agente humano envíe mensajes a leads.
    
    Esta ruta permite:
    1. Enviar un mensaje a una conversación existente (proporcionando conversation_id)
    2. Iniciar una nueva conversación con un lead (proporcionando lead_id y datos de canal)
    
    Args:
        request: La solicitud que contiene los datos del mensaje y la conversación/lead
        
    Returns:
        La respuesta del mensaje con detalles de la conversación
    """
    try:
        logger.info(f"Agente {request.agent_id} enviando mensaje")
        
        conversation_id = request.conversation_id
        is_new_conversation = False
        
        # Si no hay conversation_id, necesitamos verificar si existe una conversación o crear una nueva
        if not conversation_id:
            if not request.lead_id:
                raise ValueError("Debe proporcionar conversation_id o lead_id")
                
            # Verificar si tenemos chatbot_canal_id o los datos necesarios para crear una conversación
            if request.chatbot_canal_id:
                # Obtener la información de canal usando chatbot_canal_id
                from app.services.channel_service import channel_service
                
                try:
                    config = channel_service.get_chatbot_channel_config(request.chatbot_canal_id)
                    canal_id = UUID(config["canal_id"])
                    chatbot_id = UUID(config["chatbot_id"])
                    empresa_id = UUID(config["empresa_id"])
                except Exception as e:
                    raise ValueError(f"Error al obtener configuración del canal: {str(e)}")
            elif not request.channel_identifier or not request.chatbot_id or not request.empresa_id:
                raise ValueError("Para crear una nueva conversación debe proporcionar lead_id, chatbot_canal_id o la combinación de channel_identifier, chatbot_id y empresa_id")
            else:
                # Usar los valores proporcionados directamente
                chatbot_id = request.chatbot_id
                empresa_id = request.empresa_id
                
                # Buscar el canal_id basado en los datos del request
                # Este es un ejemplo, deberías adaptarlo según tu lógica
                channel_result = supabase.table("canales").select("*").eq("tipo", "web").limit(1).execute()
                if not channel_result.data:
                    raise ValueError("No se pudo determinar el canal")
                canal_id = UUID(channel_result.data[0]["id"])
            
            logger.info(f"Verificando conversación existente para lead {request.lead_id}")
            
            # Verificar si el lead existe
            lead_result = supabase.table("leads").select("*").eq("id", str(request.lead_id)).limit(1).execute()
            
            if not lead_result.data:
                raise ValueError(f"Lead con ID {request.lead_id} no encontrado")
            
            # Verificar si ya existe una conversación para este lead en este canal
            conversation_result = supabase.table("conversaciones").select("*")\
                .eq("lead_id", str(request.lead_id))\
                .eq("canal_id", str(canal_id))\
                .order("created_at", desc=True)\
                .limit(1)\
                .execute()
                
            if conversation_result.data:
                # Usar la conversación existente
                conversation_id = UUID(conversation_result.data[0]["id"])
                logger.info(f"Usando conversación existente {conversation_id}")
            else:
                # Crear una nueva conversación
                logger.info(f"Creando nueva conversación para lead {request.lead_id}")
                
                new_conversation = {
                    "lead_id": str(request.lead_id),
                    "chatbot_id": str(chatbot_id),
                    "canal_id": str(canal_id),
                    "canal_identificador": request.channel_identifier,
                    "estado": "activa",
                    "chatbot_activo": not request.deactivate_chatbot,  # Configuración inicial del chatbot
                    "metadata": {
                        "initiated_by": "agent",
                        "agent_id": str(request.agent_id),
                        **(request.metadata or {})
                    }
                }
                
                conversation_insert = supabase.table("conversaciones").insert(new_conversation).execute()
                
                if not conversation_insert.data:
                    raise ValueError("Error al crear nueva conversación")
                    
                conversation_id = UUID(conversation_insert.data[0]["id"])
                is_new_conversation = True
                logger.info(f"Nueva conversación creada: {conversation_id}")
        else:
            # Verificar si la conversación existe
            conv_result = supabase.table("conversaciones").select("*").eq("id", str(conversation_id)).limit(1).execute()
            
            if not conv_result.data:
                raise ValueError(f"Conversación con ID {conversation_id} no encontrada")
        
        # Usar el servicio de canal para enviar el mensaje
        from app.services.channel_service import channel_service
        
        response = channel_service.send_agent_message(
            conversation_id=conversation_id,
            agent_id=request.agent_id,
            message=request.mensaje,
            metadata={
                "deactivate_chatbot": request.deactivate_chatbot,
                **(request.metadata or {})
            }
        )
        
        # Desactivar chatbot si se solicita
        if request.deactivate_chatbot:
            supabase.table("conversaciones").update({
                "chatbot_activo": False
            }).eq("id", str(conversation_id)).execute()
            logger.info(f"Chatbot desactivado para la conversación {conversation_id}")
        
        return ChannelMessageResponse(
            mensaje_id=response["mensaje_id"],
            conversacion_id=conversation_id,
            respuesta=request.mensaje,
            metadata={
                "agent_id": str(request.agent_id),
                "conversation_created": is_new_conversation,
                "lead_id": str(request.lead_id) if request.lead_id else None,
                "channel_response": response.get("channel_response", {}),
                "origin": "agent"
            }
        )
    except ValueError as ve:
        logger.error(f"Error de validación al procesar mensaje de agente: {str(ve)}")
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.error(f"Error al procesar mensaje de agente: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error al procesar mensaje de agente: {str(e)}")

@api_router.post("/agent/direct-message", response_model=ChannelMessageResponse)
async def agent_send_direct_message(request: AgentDirectMessageRequest = Body(...)):
    """
    Allow a human agent to send a direct message to a lead, creating a new conversation if needed
    
    Args:
        request: The direct message request containing lead_id, channel info and message content
        
    Returns:
        The response message with conversation details
    """
    try:
        logger.info(f"Agente {request.agent_id} enviando mensaje directo a lead {request.lead_id} por canal {request.channel_id}")
        
        # Verificar si el lead existe
        lead_result = supabase.table("leads").select("*").eq("id", str(request.lead_id)).limit(1).execute()
        
        if not lead_result.data:
            raise ValueError(f"Lead con ID {request.lead_id} no encontrado")
        
        # Verificar si ya existe una conversación para este lead en este canal
        conversation_result = supabase.table("conversaciones").select("*")\
            .eq("lead_id", str(request.lead_id))\
            .eq("canal_id", str(request.channel_id))\
            .order("created_at", desc=True)\
            .limit(1)\
            .execute()
            
        conversation_id = None
        
        if conversation_result.data:
            # Usar la conversación existente
            conversation_id = UUID(conversation_result.data[0]["id"])
            logger.info(f"Usando conversación existente {conversation_id}")
        else:
            # Crear una nueva conversación
            logger.info(f"Creando nueva conversación para lead {request.lead_id} en canal {request.channel_id}")
            
            new_conversation = {
                "lead_id": str(request.lead_id),
                "chatbot_id": str(request.chatbot_id),
                "canal_id": str(request.channel_id),
                "canal_identificador": request.channel_identifier,
                "estado": "activa",
                "chatbot_activo": False,  # Desactivamos el chatbot ya que es un mensaje directo del agente
                "metadata": {
                    "initiated_by": "agent",
                    "agent_id": str(request.agent_id)
                }
            }
            
            conversation_insert = supabase.table("conversaciones").insert(new_conversation).execute()
            
            if not conversation_insert.data:
                raise ValueError("Error al crear nueva conversación")
                
            conversation_id = UUID(conversation_insert.data[0]["id"])
            logger.info(f"Nueva conversación creada: {conversation_id}")
        
        # Usar el servicio de canal para enviar el mensaje
        from app.services.channel_service import channel_service
        
        response = channel_service.send_agent_message(
            conversation_id=conversation_id,
            agent_id=request.agent_id,
            message=request.mensaje,
            metadata=request.metadata
        )
        
        return ChannelMessageResponse(
            mensaje_id=response["mensaje_id"],
            conversacion_id=conversation_id,
            respuesta=request.mensaje,
            metadata={
                "agent_id": str(request.agent_id),
                "lead_id": str(request.lead_id),
                "channel_id": str(request.channel_id),
                "channel_identifier": request.channel_identifier,
                "channel_response": response.get("channel_response", {}),
                "conversation_created": conversation_id != UUID(conversation_result.data[0]["id"]) if conversation_result.data else True,
                "origin": "agent"
            }
        )
    except ValueError as ve:
        logger.error(f"Error de validación al procesar mensaje directo: {str(ve)}")
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.error(f"Error al procesar mensaje directo: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error al procesar mensaje directo: {str(e)}")

@api_router.get("/channels", response_model=List[Dict[str, Any]])
async def get_supported_channels():
    """
    Get a list of all supported channels
    
    Returns:
        List of channel data
    """
    try:
        from app.services.channel_service import channel_service
        channels = channel_service.get_supported_channels()
        
        return channels
    except Exception as e:
        logger.error(f"Error al obtener canales soportados: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error al obtener canales soportados: {str(e)}")

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
