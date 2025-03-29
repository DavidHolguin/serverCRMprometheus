from fastapi import APIRouter, HTTPException, Depends, Body, Query, Path
from typing import Dict, Any, List, Optional
from uuid import UUID

from app.models.message import ChannelMessageRequest, ChannelMessageResponse
from app.models.conversation import ConversationHistory
from app.services.conversation_service import conversation_service

# Create API router
api_router = APIRouter()

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
async def process_web_message(request: Dict[str, Any] = Body(...)):
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
        
        # Create message request
        message_request = ChannelMessageRequest(
            canal_id=canal_id,
            canal_identificador=request["session_id"],
            empresa_id=UUID(request["empresa_id"]),
            chatbot_id=UUID(request["chatbot_id"]),
            mensaje=request["mensaje"],
            lead_id=UUID(request["lead_id"]) if "lead_id" in request and request["lead_id"] else None,
            metadata=request.get("metadata")
        )
        
        # Process message
        return await process_message(message_request)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing web message: {str(e)}")

@api_router.post("/channels/whatsapp", response_model=ChannelMessageResponse)
async def process_whatsapp_message(request: Dict[str, Any] = Body(...)):
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
        
        # Create message request
        message_request = ChannelMessageRequest(
            canal_id=canal_id,
            canal_identificador=request["phone_number"],
            empresa_id=UUID(request["empresa_id"]),
            chatbot_id=UUID(request["chatbot_id"]),
            mensaje=request["mensaje"],
            lead_id=UUID(request["lead_id"]) if "lead_id" in request and request["lead_id"] else None,
            metadata=request.get("metadata")
        )
        
        # Process message
        return await process_message(message_request)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing WhatsApp message: {str(e)}")

@api_router.post("/channels/messenger", response_model=ChannelMessageResponse)
async def process_messenger_message(request: Dict[str, Any] = Body(...)):
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
        
        # Create message request
        message_request = ChannelMessageRequest(
            canal_id=canal_id,
            canal_identificador=request["sender_id"],
            empresa_id=UUID(request["empresa_id"]),
            chatbot_id=UUID(request["chatbot_id"]),
            mensaje=request["mensaje"],
            lead_id=UUID(request["lead_id"]) if "lead_id" in request and request["lead_id"] else None,
            metadata=request.get("metadata")
        )
        
        # Process message
        return await process_message(message_request)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing Messenger message: {str(e)}")

@api_router.post("/channels/telegram", response_model=ChannelMessageResponse)
async def process_telegram_message(request: Dict[str, Any] = Body(...)):
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
        
        # Create message request
        message_request = ChannelMessageRequest(
            canal_id=canal_id,
            canal_identificador=request["chat_id"],
            empresa_id=UUID(request["empresa_id"]),
            chatbot_id=UUID(request["chatbot_id"]),
            mensaje=request["mensaje"],
            lead_id=UUID(request["lead_id"]) if "lead_id" in request and request["lead_id"] else None,
            metadata=request.get("metadata")
        )
        
        # Process message
        return await process_message(message_request)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing Telegram message: {str(e)}")

@api_router.post("/channels/instagram", response_model=ChannelMessageResponse)
async def process_instagram_message(request: Dict[str, Any] = Body(...)):
    """
    Process a message from Instagram
    
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
        
        # Get channel ID for Instagram
        from app.db.supabase_client import supabase
        channel_result = supabase.table("canales").select("id").eq("tipo", "instagram").limit(1).execute()
        
        if not channel_result.data or len(channel_result.data) == 0:
            raise HTTPException(status_code=404, detail="Instagram channel not found")
        
        canal_id = UUID(channel_result.data[0]["id"])
        
        # Create message request
        message_request = ChannelMessageRequest(
            canal_id=canal_id,
            canal_identificador=request["sender_id"],
            empresa_id=UUID(request["empresa_id"]),
            chatbot_id=UUID(request["chatbot_id"]),
            mensaje=request["mensaje"],
            lead_id=UUID(request["lead_id"]) if "lead_id" in request and request["lead_id"] else None,
            metadata=request.get("metadata")
        )
        
        # Process message
        return await process_message(message_request)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing Instagram message: {str(e)}")
