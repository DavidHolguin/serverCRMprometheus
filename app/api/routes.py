from fastapi import APIRouter, HTTPException, Depends, Body, Query, Path
from typing import Dict, Any, List, Optional
from uuid import UUID, uuid4
import logging

# Configurar logger
logger = logging.getLogger(__name__)

from app.models.message import (
    ChannelMessageRequest, 
    ChannelMessageResponse, 
    AgentMessageRequest,
    ToggleChatbotRequest,
    ToggleChatbotResponse
)
# Importar los modelos de audio desde el módulo correcto
from app.models.audio import AudioMessageRequest, AudioMessageResponse
from app.models.conversation import ConversationHistory
from app.services.conversation_service import conversation_service
from app.models.examples import EXAMPLES
from app.api.endpoints.evaluations import router as evaluations_router

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

# Channel-specific endpoints

@api_router.post("/channels/web", response_model=ChannelMessageResponse)
async def process_web_message(request: Dict[str, Any] = Body(..., example=EXAMPLES["web_message"]["value"])):
    """
    Process a message from a web chat
    
    Args:
        request: The message request containing the necessary information
        
    Returns:
        The response message
    """
    try:
        # Validate required fields
        required_fields = ["empresa_id", "chatbot_id", "mensaje", "session_id"]
        for field in required_fields:
            if field not in request:
                raise HTTPException(status_code=400, detail=f"Missing required field: {field}")
        
        # Get channel ID for web chat
        from app.db.supabase_client import supabase
        channel_result = supabase.table("canales").select("id").eq("tipo", "web").limit(1).execute()
        
        if not channel_result.data or len(channel_result.data) == 0:
            raise HTTPException(status_code=404, detail="Web channel not found")
        
        canal_id = UUID(channel_result.data[0]["id"])
        
        # Ya no accedemos directamente a datos personales
        # Los metadatos serán sanitizados en el servicio de conversación
        sanitized_metadata = None
        if "metadata" in request:
            # Mantenemos una copia de los metadatos pero sin datos personales
            sanitized_metadata = {k: v for k, v in request["metadata"].items() 
                                if k not in ["nombre", "apellido", "email", "telefono", 
                                            "direccion", "dni", "nif"]}
        
        # Create message request
        message_request = ChannelMessageRequest(
            canal_id=canal_id,
            canal_identificador=request["session_id"],
            empresa_id=UUID(request["empresa_id"]),
            chatbot_id=UUID(request["chatbot_id"]),
            mensaje=request["mensaje"],
            lead_id=UUID(request["lead_id"]) if "lead_id" in request and request["lead_id"] else None,
            metadata=sanitized_metadata,
            session_id=request["session_id"]
        )
        
        # Process message
        return await process_message(message_request)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing web message: {str(e)}")

@api_router.post("/channels/whatsapp", response_model=ChannelMessageResponse)
async def process_whatsapp_message(request: Dict[str, Any] = Body(..., example=EXAMPLES["whatsapp_message"]["value"])):
    """
    Process a message from WhatsApp
    
    Args:
        request: The message request containing the necessary information
        
    Returns:
        The response message
    """
    try:
        # Validate required fields
        required_fields = ["empresa_id", "chatbot_id", "mensaje", "phone_number"]
        for field in required_fields:
            if field not in request:
                raise HTTPException(status_code=400, detail=f"Missing required field: {field}")
        
        # Get channel ID for WhatsApp
        from app.db.supabase_client import supabase
        channel_result = supabase.table("canales").select("id").eq("tipo", "whatsapp").limit(1).execute()
        
        if not channel_result.data or len(channel_result.data) == 0:
            raise HTTPException(status_code=404, detail="WhatsApp channel not found")
        
        canal_id = UUID(channel_result.data[0]["id"])
        
        # Sanitizar los metadatos para no incluir información personal
        sanitized_metadata = None
        if "metadata" in request:
            # Mantenemos una copia de los metadatos pero sin datos personales
            sanitized_metadata = {k: v for k, v in request["metadata"].items() 
                                if k not in ["nombre", "apellido", "email", "telefono", 
                                            "direccion", "dni", "nif"]}
        
        # Create message request
        message_request = ChannelMessageRequest(
            canal_id=canal_id,
            canal_identificador=request["phone_number"],
            empresa_id=UUID(request["empresa_id"]),
            chatbot_id=UUID(request["chatbot_id"]),
            mensaje=request["mensaje"],
            lead_id=UUID(request["lead_id"]) if "lead_id" in request and request["lead_id"] else None,
            metadata=sanitized_metadata,
            phone_number=request["phone_number"]
        )
        
        # Process message
        return await process_message(message_request)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing WhatsApp message: {str(e)}")

@api_router.post("/channels/messenger", response_model=ChannelMessageResponse)
async def process_messenger_message(request: Dict[str, Any] = Body(..., example=EXAMPLES["messenger_message"]["value"])):
    """
    Process a message from Facebook Messenger
    
    Args:
        request: The message request containing the necessary information
        
    Returns:
        The response message
    """
    try:
        # Validate required fields
        required_fields = ["empresa_id", "chatbot_id", "mensaje", "sender_id"]
        for field in required_fields:
            if field not in request:
                raise HTTPException(status_code=400, detail=f"Missing required field: {field}")
        
        # Get channel ID for Messenger
        from app.db.supabase_client import supabase
        channel_result = supabase.table("canales").select("id").eq("tipo", "messenger").limit(1).execute()
        
        if not channel_result.data or len(channel_result.data) == 0:
            raise HTTPException(status_code=404, detail="Messenger channel not found")
        
        canal_id = UUID(channel_result.data[0]["id"])
        
        # Sanitizar los metadatos para no incluir información personal
        sanitized_metadata = None
        if "metadata" in request:
            # Mantenemos una copia de los metadatos pero sin datos personales
            sanitized_metadata = {k: v for k, v in request["metadata"].items() 
                                if k not in ["nombre", "apellido", "email", "telefono", 
                                            "direccion", "dni", "nif"]}
        
        # Create message request
        message_request = ChannelMessageRequest(
            canal_id=canal_id,
            canal_identificador=request["sender_id"],
            empresa_id=UUID(request["empresa_id"]),
            chatbot_id=UUID(request["chatbot_id"]),
            mensaje=request["mensaje"],
            lead_id=UUID(request["lead_id"]) if "lead_id" in request and request["lead_id"] else None,
            metadata=sanitized_metadata,
            sender_id=request["sender_id"]
        )
        
        # Process message
        return await process_message(message_request)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing Messenger message: {str(e)}")

@api_router.post("/channels/telegram", response_model=ChannelMessageResponse)
async def process_telegram_message(request: Dict[str, Any] = Body(..., example=EXAMPLES["telegram_message"]["value"])):
    """
    Process a message from Telegram
    
    Args:
        request: The message request containing the necessary information
        
    Returns:
        The response message
    """
    try:
        # Validate required fields
        required_fields = ["empresa_id", "chatbot_id", "mensaje", "chat_id"]
        for field in required_fields:
            if field not in request:
                raise HTTPException(status_code=400, detail=f"Missing required field: {field}")
        
        # Get channel ID for Telegram
        from app.db.supabase_client import supabase
        channel_result = supabase.table("canales").select("id").eq("tipo", "telegram").limit(1).execute()
        
        if not channel_result.data or len(channel_result.data) == 0:
            raise HTTPException(status_code=404, detail="Telegram channel not found")
        
        canal_id = UUID(channel_result.data[0]["id"])
        
        # Sanitizar los metadatos para no incluir información personal
        sanitized_metadata = None
        if "metadata" in request:
            # Mantenemos una copia de los metadatos pero sin datos personales
            sanitized_metadata = {k: v for k, v in request["metadata"].items() 
                                if k not in ["nombre", "apellido", "email", "telefono", 
                                            "direccion", "dni", "nif"]}
        
        # Create message request
        message_request = ChannelMessageRequest(
            canal_id=canal_id,
            canal_identificador=request["chat_id"],
            empresa_id=UUID(request["empresa_id"]),
            chatbot_id=UUID(request["chatbot_id"]),
            mensaje=request["mensaje"],
            lead_id=UUID(request["lead_id"]) if "lead_id" in request and request["lead_id"] else None,
            metadata=sanitized_metadata,
            chat_id=request["chat_id"]
        )
        
        # Process message
        return await process_message(message_request)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing Telegram message: {str(e)}")

@api_router.post("/channels/instagram", response_model=ChannelMessageResponse)
async def process_instagram_message(request: Dict[str, Any] = Body(..., example=EXAMPLES["instagram_message"]["value"])):
    """
    Process a message from Instagram
    
    Args:
        request: The message request containing the necessary information
        
    Returns:
        The response message
    """
    try:
        # Validate required fields
        required_fields = ["empresa_id", "chatbot_id", "mensaje", "instagram_id"]
        for field in required_fields:
            if field not in request:
                raise HTTPException(status_code=400, detail=f"Missing required field: {field}")
        
        # Get channel ID for Instagram
        from app.db.supabase_client import supabase
        channel_result = supabase.table("canales").select("id").eq("tipo", "instagram").limit(1).execute()
        
        if not channel_result.data or len(channel_result.data) == 0:
            raise HTTPException(status_code=404, detail="Instagram channel not found")
        
        canal_id = UUID(channel_result.data[0]["id"])
        
        # Sanitizar los metadatos para no incluir información personal
        sanitized_metadata = None
        if "metadata" in request:
            # Mantenemos una copia de los metadatos pero sin datos personales
            sanitized_metadata = {k: v for k, v in request["metadata"].items() 
                                if k not in ["nombre", "apellido", "email", "telefono", 
                                            "direccion", "dni", "nif"]}
        
        # Create message request
        message_request = ChannelMessageRequest(
            canal_id=canal_id,
            canal_identificador=request["instagram_id"],
            empresa_id=UUID(request["empresa_id"]),
            chatbot_id=UUID(request["chatbot_id"]),
            mensaje=request["mensaje"],
            lead_id=UUID(request["lead_id"]) if "lead_id" in request and request["lead_id"] else None,
            metadata=sanitized_metadata,
            instagram_id=request["instagram_id"]
        )
        
        # Process message
        return await process_message(message_request)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing Instagram message: {str(e)}")

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

@api_router.post("/channels/audio", response_model=AudioMessageResponse)
async def process_audio_message(request: AudioMessageRequest = Body(...)):
    """
    Procesa un mensaje de audio, lo transcribe con Whisper y genera una respuesta
    
    Args:
        request: El mensaje de audio y metadatos necesarios
        
    Returns:
        La respuesta generada a partir del audio transcrito
    """
    try:
        from app.services.audio_service import audio_service
        from app.db.supabase_client import supabase
        
        # Si no se proporciona canal_id, buscamos el canal web por defecto
        canal_id = request.canal_id
        if canal_id is None:
            channel_result = supabase.table("canales").select("id").eq("tipo", "web").limit(1).execute()
            if not channel_result.data or len(channel_result.data) == 0:
                raise HTTPException(status_code=404, detail="Web channel not found")
            canal_id = UUID(channel_result.data[0]["id"])
        
        # Si no se proporciona canal_identificador, usamos un valor predeterminado
        canal_identificador = request.canal_identificador
        if canal_identificador is None:
            # Usar un identificador basado en la sesión o generar uno nuevo
            canal_identificador = f"audio_session_{uuid4()}"
            
        # Procesar el mensaje de audio
        result = audio_service.process_audio_message(
            canal_id=canal_id,
            canal_identificador=canal_identificador,
            empresa_id=request.empresa_id,
            chatbot_id=request.chatbot_id,
            audio_base64=request.audio_base64,
            formato_audio=request.formato_audio,
            idioma=request.idioma,
            conversacion_id=request.conversacion_id,
            lead_id=request.lead_id,
            metadata=request.metadata
        )
        
        # Construir respuesta
        return AudioMessageResponse(
            mensaje_id=result["mensaje_id"],
            conversacion_id=result["conversacion_id"],
            audio_id=result["audio_id"],
            transcripcion=result["transcripcion"],
            respuesta=result["respuesta"],
            duracion_segundos=result["duracion_segundos"],
            idioma_detectado=result["idioma_detectado"],
            metadata=result["metadata"]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error procesando mensaje de audio: {str(e)}")

@api_router.post("/webhook/{channel_type}", response_model=ChannelMessageResponse)
async def process_webhook_message(
    channel_type: str = Path(..., description="Type of channel (telegram, messenger, whatsapp, instagram, etc.)"),
    request: Dict[str, Any] = Body(...),
    webhook_secret: Optional[str] = Query(None, description="Webhook secret for verification")
):
    """
    Process incoming webhook messages from different channels
    
    Args:
        channel_type: The type of channel (telegram, messenger, whatsapp, instagram, etc.)
        request: The webhook payload from the channel
        webhook_secret: Secret for webhook verification (optional)
        
    Returns:
        The response message
    """
    try:
        # Get channel information
        from app.db.supabase_client import supabase
        
        # Find the channel by type
        channel_result = supabase.table("canales").select("id").eq("tipo", channel_type).limit(1).execute()
        
        if not channel_result.data or len(channel_result.data) == 0:
            raise HTTPException(status_code=404, detail=f"Channel type '{channel_type}' not found")
        
        canal_id = UUID(channel_result.data[0]["id"])
        
        # Get chatbot configuration for this channel
        chatbot_channel_result = supabase.table("chatbot_canales").select("*") \
            .eq("canal_id", str(canal_id)) \
            .eq("is_active", True) \
            .execute()
            
        if not chatbot_channel_result.data or len(chatbot_channel_result.data) == 0:
            raise HTTPException(status_code=404, detail=f"No active chatbot configuration found for channel '{channel_type}'")
        
        chatbot_channel = chatbot_channel_result.data[0]
        
        # Verify webhook secret if provided
        if webhook_secret and chatbot_channel.get("webhook_secret") and webhook_secret != chatbot_channel.get("webhook_secret"):
            raise HTTPException(status_code=401, detail="Invalid webhook secret")
        
        # Extract message data based on channel type
        message_data = {}
        chatbot_id = UUID(chatbot_channel["chatbot_id"])
        
        # Process request data based on channel type and sanitizar información personal
        if channel_type == "telegram":
            # Check if the message is directly in the request or nested inside a property
            telegram_data = request
            
            # Check if the message is nested inside another property
            if "message" not in request:
                # Try to find the Telegram data in any of the properties
                for key, value in request.items():
                    if isinstance(value, dict) and "message" in value:
                        telegram_data = value
                        break
                
                # If still no message found, raise error
                if "message" not in telegram_data:
                    raise HTTPException(status_code=400, detail="Invalid Telegram webhook payload")
            
            message = telegram_data["message"]
            chat = message.get("chat", {})
            
            # Sanitizar datos personales del chat
            safe_chat = {k: v for k, v in chat.items() 
                        if k not in ["first_name", "last_name", "username", "email"]}
            
            # Sanitizar datos personales del remitente
            safe_from = {k: v for k, v in message.get("from", {}).items() 
                        if k not in ["first_name", "last_name", "username", "email", "phone_number"]}
            
            message_data = {
                "canal_id": canal_id,
                "canal_identificador": str(chat.get("id")),
                "chatbot_id": chatbot_id,
                "mensaje": message.get("text", ""),
                "metadata": {
                    "from": safe_from,
                    "chat": safe_chat,
                    "message_id": message.get("message_id")
                },
                "chat_id": str(chat.get("id"))
            }
            
        elif channel_type == "messenger":
            # Verificar si es una solicitud de verificación de webhook
            if "object" not in request:
                raise HTTPException(status_code=400, detail="Invalid Messenger webhook payload")
                
            # Verificar que el objeto sea una página
            if request["object"] != "page":
                raise HTTPException(status_code=400, detail="Webhook object is not a page")
                
            if "entry" not in request or not request["entry"]:
                raise HTTPException(status_code=400, detail="Invalid Messenger webhook payload: no entries")
                
            # Procesar la primera entrada (normalmente solo hay una)
            entry = request["entry"][0]
            
            # Verificar si hay mensajes de mensajería
            if "messaging" not in entry or not entry["messaging"]:
                logger.warning("Entrada de Messenger sin mensajes de mensajería")
                return {"success": True, "message": "No messaging data found"}
                
            # Obtener el primer evento de mensajería
            messaging = entry["messaging"][0]
            
            # Verificar si hay un remitente
            if "sender" not in messaging or "id" not in messaging["sender"]:
                raise HTTPException(status_code=400, detail="Invalid Messenger webhook: no sender ID")
                
            sender = messaging["sender"]
            sender_id = sender.get("id")
            
            # Verificar el tipo de evento (mensaje, postback, etc.)
            message_text = ""
            
            if "message" in messaging:
                message = messaging["message"]
                
                # Verificar si es un mensaje de texto
                if "text" in message:
                    message_text = message["text"]
                # Si no hay texto, podría ser un adjunto (imagen, audio, etc.)
                elif "attachments" in message:
                    # Procesar el primer adjunto
                    attachment = message["attachments"][0]
                    message_text = f"[Adjunto de tipo: {attachment.get('type', 'desconocido')}]"
            # Verificar si es un postback (botón presionado)
            elif "postback" in messaging:
                postback = messaging["postback"]
                message_text = postback.get("payload", "")
                
            # Sanitizar datos personales
            safe_sender = {"id": sender.get("id")}
            
            # Crear los datos del mensaje
            message_data = {
                "canal_id": canal_id,
                "canal_identificador": sender_id,
                "chatbot_id": chatbot_id,
                "mensaje": message_text,
                "metadata": {
                    "sender": safe_sender,
                    "recipient": {"id": messaging.get("recipient", {}).get("id")},
                    "timestamp": messaging.get("timestamp")
                },
                "sender_id": sender_id
            }
            
            logger.info(f"Mensaje de Messenger procesado: {message_text[:50]}...")
            
        elif channel_type == "whatsapp":
            if "entry" not in request:
                raise HTTPException(status_code=400, detail="Invalid WhatsApp webhook payload")
                
            entry = request["entry"][0] if request["entry"] else {}
            changes = entry.get("changes", [{}])[0] if entry.get("changes") else {}
            value = changes.get("value", {})
            messages = value.get("messages", [{}])[0] if value.get("messages") else {}
            
            # Sanitizar contactos - eliminar datos personales
            safe_contacts = []
            if value.get("contacts"):
                for contact in value.get("contacts", []):
                    safe_contact = {"wa_id": contact.get("wa_id")}
                    safe_contacts.append(safe_contact)
            
            message_data = {
                "canal_id": canal_id,
                "canal_identificador": messages.get("from"),
                "chatbot_id": chatbot_id,
                "mensaje": messages.get("text", {}).get("body", ""),
                "metadata": {
                    "contacts": safe_contacts,
                    "message_id": messages.get("id")
                },
                "phone_number": messages.get("from")
            }
            
        elif channel_type == "instagram":
            if "entry" not in request:
                raise HTTPException(status_code=400, detail="Invalid Instagram webhook payload")
                
            entry = request["entry"][0] if request["entry"] else {}
            messaging = entry.get("messaging", [{}])[0] if entry.get("messaging") else {}
            sender = messaging.get("sender", {})
            message = messaging.get("message", {})
            
            # Sanitizar datos personales
            safe_sender = {"id": sender.get("id")}
            
            message_data = {
                "canal_id": canal_id,
                "canal_identificador": sender.get("id"),
                "chatbot_id": chatbot_id,
                "mensaje": message.get("text", ""),
                "metadata": {
                    "sender": safe_sender,
                    "recipient": {"id": messaging.get("recipient", {}).get("id")},
                    "timestamp": messaging.get("timestamp")
                },
                "instagram_id": sender.get("id")
            }
            
        else:
            # Generic handler for other channels
            # Sanitizar cualquier dato personal
            safe_metadata = {k: v for k, v in request.items() 
                            if k not in ["nombre", "apellido", "email", "telefono", 
                                        "direccion", "dni", "nif", "name", "phone", 
                                        "first_name", "last_name", "username"]}
            
            message_data = {
                "canal_id": canal_id,
                "canal_identificador": request.get("sender_id", str(uuid4())),
                "chatbot_id": chatbot_id,
                "mensaje": request.get("text", request.get("message", "")),
                "metadata": safe_metadata
            }
        
        # Get empresa_id from chatbot
        chatbot_result = supabase.table("chatbots").select("empresa_id").eq("id", str(chatbot_id)).limit(1).execute()
        
        if not chatbot_result.data or len(chatbot_result.data) == 0:
            raise HTTPException(status_code=404, detail=f"Chatbot with ID '{chatbot_id}' not found")
            
        empresa_id = UUID(chatbot_result.data[0]["empresa_id"])
        message_data["empresa_id"] = empresa_id
        
        # Create message request with sanitized data
        message_request = ChannelMessageRequest(**message_data)
        
        # Process message
        return await process_message(message_request)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing webhook message: {str(e)}")

# Verification endpoint for channels that require GET verification (like Facebook Messenger)
@api_router.get("/webhook/{channel_type}")
async def verify_webhook(
    channel_type: str = Path(..., description="Type of channel (telegram, messenger, whatsapp, instagram, etc.)"),
    hub_mode: Optional[str] = Query(None, description="Hub mode for Facebook verification"),
    hub_verify_token: Optional[str] = Query(None, description="Verification token for Facebook"),
    hub_challenge: Optional[str] = Query(None, description="Challenge string for Facebook verification")
):
    """
    Verify webhook for channels that require verification (like Facebook)
    
    Args:
        channel_type: The type of channel
        hub_mode: Hub mode for Facebook verification
        hub_verify_token: Verification token for Facebook
        hub_challenge: Challenge string for Facebook verification
        
    Returns:
        Challenge string if verification is successful
    """
    try:
        # Get channel information
        from app.db.supabase_client import supabase
        
        # Find the channel by type
        channel_result = supabase.table("canales").select("id").eq("tipo", channel_type).limit(1).execute()
        
        if not channel_result.data or len(channel_result.data) == 0:
            raise HTTPException(status_code=404, detail=f"Channel type '{channel_type}' not found")
        
        canal_id = channel_result.data[0]["id"]
        
        # Get chatbot configuration for this channel
        chatbot_channel_result = supabase.table("chatbot_canales").select("configuracion") \
            .eq("canal_id", canal_id) \
            .eq("is_active", True) \
            .execute()
            
        if not chatbot_channel_result.data or len(chatbot_channel_result.data) == 0:
            raise HTTPException(status_code=404, detail=f"No active chatbot configuration found for channel '{channel_type}'")
        
        configuracion = chatbot_channel_result.data[0].get("configuracion", {})
        
        # Facebook verification (Messenger, WhatsApp, Instagram)
        if hub_mode == "subscribe" and hub_verify_token:
            # Para Messenger, el verify_token debe coincidir con el configurado en tu app de Facebook
            verify_token = configuracion.get("verify_token")
            
            if not verify_token:
                logger.warning(f"verify_token no encontrado en la configuración para {channel_type}")
                raise HTTPException(status_code=403, detail="Verification token not configured")
            
            if hub_verify_token == verify_token:
                logger.info(f"Verificación exitosa del webhook para {channel_type}")
                # Devolver el hub_challenge es crucial para que Facebook confirme la verificación
                return hub_challenge
                
            logger.warning(f"Token de verificación inválido para {channel_type}")
            raise HTTPException(status_code=403, detail="Invalid verification token")
            
        # Telegram verification
        if channel_type == "telegram":
            return {"ok": True, "result": "Webhook is ready"}
            
        # Generic response for other channels
        return {"status": "ok", "message": "Webhook is ready"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error verificando webhook: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error verifying webhook: {str(e)}")
