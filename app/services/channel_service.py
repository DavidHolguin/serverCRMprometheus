"""
Channel service for sending messages to external channels
"""
from typing import Dict, Any, Optional, List
from uuid import UUID
import requests
import json
import logging

from app.db.supabase_client import supabase
from app.core.config import settings

# Configurar logger
logger = logging.getLogger(__name__)

class ChannelService:
    """Service for sending messages to external channels"""
    
    def send_message_to_channel(self, conversation_id: UUID, message: str, 
                               metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Send a message to a lead through the appropriate channel
        
        Args:
            conversation_id: The ID of the conversation
            message: The message content
            metadata: Additional metadata (optional)
            
        Returns:
            Response data including success status and channel info
        """
        try:
            # Get conversation details
            conv_result = supabase.table("conversaciones").select("*").eq("id", str(conversation_id)).limit(1).execute()
            
            if not conv_result.data or len(conv_result.data) == 0:
                raise ValueError(f"Conversation {conversation_id} not found")
            
            conversation = conv_result.data[0]
            canal_id = UUID(conversation["canal_id"])
            canal_identificador = conversation["canal_identificador"]
            
            # Get channel details
            channel_result = supabase.table("canales").select("*").eq("id", str(canal_id)).limit(1).execute()
            
            if not channel_result.data or len(channel_result.data) == 0:
                raise ValueError(f"Channel with ID {canal_id} not found")
            
            channel = channel_result.data[0]
            channel_type = channel["tipo"]
            
            # Get chatbot channel configuration
            chatbot_id = UUID(conversation["chatbot_id"])
            chatbot_channel_result = supabase.table("chatbot_canales").select("*") \
                .eq("canal_id", str(canal_id)) \
                .eq("chatbot_id", str(chatbot_id)) \
                .eq("is_active", True) \
                .execute()
                
            if not chatbot_channel_result.data or len(chatbot_channel_result.data) == 0:
                raise ValueError(f"No active chatbot configuration found for channel {channel_type}")
            
            chatbot_channel = chatbot_channel_result.data[0]
            configuracion = chatbot_channel.get("configuracion", {})
            
            # Send message based on channel type
            response = None
            
            if channel_type == "telegram":
                response = self._send_telegram_message(configuracion, canal_identificador, message)
            elif channel_type == "whatsapp":
                response = self._send_whatsapp_message(configuracion, canal_identificador, message)
            elif channel_type == "messenger":
                response = self._send_messenger_message(configuracion, canal_identificador, message)
            elif channel_type == "instagram":
                response = self._send_instagram_message(configuracion, canal_identificador, message)
            elif channel_type == "web" or channel_type == "webchat" or channel_type == "sitio_web" or channel_type == "website":
                # Web messages are handled by the client polling the API
                response = {"success": True, "info": "Web messages are handled by client polling"}
            else:
                raise ValueError(f"Unsupported channel type: {channel_type}")
            
            return {
                "success": True,
                "channel_type": channel_type,
                "channel_identifier": canal_identificador,
                "response": response
            }
            
        except Exception as e:
            logger.error(f"Error in send_message_to_channel: {e}", exc_info=True)
            raise
    
    def get_channel_info(self, canal_id: UUID) -> Dict[str, Any]:
        """
        Get channel information
        
        Args:
            canal_id: The ID of the channel
            
        Returns:
            Dictionary with channel information
        """
        try:
            channel_result = supabase.table("canales").select("*").eq("id", str(canal_id)).limit(1).execute()
            
            if not channel_result.data or len(channel_result.data) == 0:
                raise ValueError(f"Channel with ID {canal_id} not found")
            
            return channel_result.data[0]
        except Exception as e:
            logger.error(f"Error getting channel info: {e}", exc_info=True)
            raise
    
    def get_supported_channels(self) -> List[Dict[str, Any]]:
        """
        Get a list of all supported channels
        
        Returns:
            List of channel data dictionaries
        """
        try:
            channel_result = supabase.table("canales").select("id,nombre,tipo,descripcion,logo_url,is_active").eq("is_active", True).execute()
            return channel_result.data or []
        except Exception as e:
            logger.error(f"Error getting supported channels: {e}", exc_info=True)
            return []
    
    def send_agent_message(self, conversation_id: UUID, agent_id: UUID, message: str, 
                          metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Send a message from a human agent to a lead through the appropriate channel
        
        Args:
            conversation_id: The ID of the conversation
            agent_id: The ID of the agent sending the message
            message: The message content
            metadata: Additional metadata (optional)
            
        Returns:
            Response data including success status and channel info
        """
        try:
            # Get conversation details to verify it exists
            conv_result = supabase.table("conversaciones").select("*").eq("id", str(conversation_id)).limit(1).execute()
            
            if not conv_result.data or len(conv_result.data) == 0:
                raise ValueError(f"Conversation {conversation_id} not found")
            
            conversation = conv_result.data[0]
            
            # Save agent message to the database
            message_data = {
                "conversacion_id": str(conversation_id),
                "origen": "agent",
                "remitente_id": str(agent_id),
                "contenido": message,
                "tipo_contenido": "text",
                "metadata": metadata or {}
            }
            
            # Insert message into the mensajes table
            message_result = supabase.table("mensajes").insert(message_data).execute()
            
            if not message_result.data or len(message_result.data) == 0:
                raise ValueError("Failed to save agent message")
            
            mensaje_id = UUID(message_result.data[0]["id"])
            
            # Update conversation's last message timestamp
            supabase.table("conversaciones").update({
                "ultimo_mensaje": "now()",
                "metadata": {
                    **(conversation.get("metadata") or {}),
                    "last_agent_id": str(agent_id)
                }
            }).eq("id", str(conversation_id)).execute()
            
            # Send message through the appropriate channel
            channel_response = self.send_message_to_channel(
                conversation_id=conversation_id,
                message=message,
                metadata={
                    "agent_id": str(agent_id),
                    "origin": "agent",
                    "message_id": str(mensaje_id),
                    **(metadata or {})
                }
            )
            
            return {
                "success": True,
                "mensaje_id": mensaje_id,
                "conversation_id": conversation_id,
                "channel_response": channel_response
            }
            
        except Exception as e:
            logger.error(f"Error sending agent message: {e}", exc_info=True)
            raise
    
    def _send_telegram_message(self, config: Dict[str, Any], chat_id: str, message: str) -> Dict[str, Any]:
        """Send message to Telegram"""
        try:
            bot_token = config.get("bot_token")
            if not bot_token:
                raise ValueError("Bot token not found in Telegram configuration")
            
            url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
            payload = {
                "chat_id": chat_id,
                "text": message,
                "parse_mode": "HTML"
            }
            
            response = requests.post(url, json=payload)
            response.raise_for_status()
            
            return response.json()
        except Exception as e:
            logger.error(f"Error sending Telegram message: {e}", exc_info=True)
            raise
    
    def _send_whatsapp_message(self, config: Dict[str, Any], phone_number: str, message: str) -> Dict[str, Any]:
        """Send message to WhatsApp"""
        try:
            access_token = config.get("access_token")
            phone_number_id = config.get("phone_number_id")
            api_version = config.get("api_version")
            waba_id = "567403046458633"
            business_id = settings.WHATSAPP_BUSINESS_PHONE
            app_id = config.get("app_id")
            
            if not access_token:
                access_token = settings.WHATSAPP_ACCESS_TOKEN
            
            if not phone_number_id:
                phone_number_id = "567403046458633"
            
            if not api_version:
                api_version = settings.WHATSAPP_API_VERSION
            
            if not app_id and hasattr(settings, 'WHATSAPP_APP_ID'):
                app_id = settings.WHATSAPP_APP_ID
            
            if not access_token:
                error_msg = "Error en configuración de WhatsApp: Falta access_token"
                logger.error(error_msg)
                return {"success": False, "error": error_msg}
            
            if not phone_number_id:
                discovered_id = self._discover_whatsapp_phone_number_id(
                    access_token=access_token,
                    business_id=business_id,
                    waba_id=waba_id
                )
                
                if discovered_id:
                    phone_number_id = discovered_id
                elif hasattr(settings, 'WHATSAPP_BUSINESS_PHONE'):
                    phone_number_id = settings.WHATSAPP_BUSINESS_PHONE
            
            if not phone_number_id:
                error_msg = "Error en configuración de WhatsApp: No se pudo obtener un phone_number_id válido"
                logger.error(error_msg)
                return {"success": False, "error": error_msg}
            
            if phone_number.startswith("+"):
                phone_number = phone_number[1:]
            
            base_url = f"https://graph.facebook.com/{api_version}/{phone_number_id}/messages"
            if app_id:
                base_url += f"?app_id={app_id}"
                
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "messaging_product": "whatsapp",
                "to": phone_number,
                "type": "text",
                "text": {
                    "body": message
                }
            }
            
            response = requests.post(base_url, headers=headers, json=payload)
            
            if response.status_code != 200 and phone_number_id != waba_id:
                phone_number_id = waba_id
                base_url = f"https://graph.facebook.com/{api_version}/{phone_number_id}/messages"
                if app_id:
                    base_url += f"?app_id={app_id}"
                    
                response = requests.post(base_url, headers=headers, json=payload)
            
            try:
                response_data = response.json()
            except:
                response_data = {"raw_response": response.text[:200]}
            
            if response.status_code != 200:
                error_message = response_data.get("error", {}).get("message", "Unknown error")
                logger.error(f"Error al enviar mensaje a WhatsApp: {error_message}")
                return {
                    "success": False, 
                    "status_code": response.status_code, 
                    "response": response_data
                }
            
            return {
                "success": True, 
                "status_code": response.status_code, 
                "response": response_data
            }
        except Exception as e:
            logger.error(f"Excepción al enviar mensaje a WhatsApp: {e}", exc_info=True)
            return {"success": False, "error": str(e)}
    
    def _send_messenger_message(self, config: Dict[str, Any], sender_id: str, message: str) -> Dict[str, Any]:
        """
        Send message to Facebook Messenger
        
        Args:
            config: Configuration dictionary with access_token and page_id
            sender_id: The recipient's Facebook ID
            message: The message to send
            
        Returns:
            Response data from the Facebook API
            
        Raises:
            ValueError: If required configuration is missing
            Exception: If there's an error sending the message
        """
        try:
            access_token = config.get("access_token")
            page_id = config.get("page_id")
            
            if not access_token:
                raise ValueError("Access token not found in Messenger configuration")
            
            url = "https://graph.facebook.com/v18.0/me/messages"
            
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "recipient": {
                    "id": sender_id
                },
                "message": {
                    "text": message
                }
            }
            
            response = requests.post(url, headers=headers, json=payload)
            
            if response.status_code != 200:
                error_data = response.json()
                error_message = error_data.get("error", {}).get("message", "Unknown error")
                logger.error(f"Facebook API error: {error_message}")
                return {"success": False, "error": error_message}
            
            response_data = response.json()
            return {"success": True, "data": response_data}
            
        except Exception as e:
            logger.error(f"Error sending Messenger message: {e}", exc_info=True)
            return {"success": False, "error": str(e)}
    
    def _send_instagram_message(self, config: Dict[str, Any], instagram_id: str, message: str) -> Dict[str, Any]:
        """Send message to Instagram"""
        try:
            access_token = config.get("access_token")
            
            if not access_token:
                raise ValueError("Access token not found in Instagram configuration")
            
            url = "https://graph.facebook.com/v17.0/me/messages"
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }
            payload = {
                "recipient": {
                    "id": instagram_id
                },
                "message": {
                    "text": message
                }
            }
            
            response = requests.post(url, headers=headers, json=payload)
            response.raise_for_status()
            
            return response.json()
        except Exception as e:
            logger.error(f"Error sending Instagram message: {e}", exc_info=True)
            raise

    def _discover_whatsapp_phone_number_id(self, access_token: str, business_id: str, waba_id: str) -> str:
        """
        Intenta descubrir el Phone Number ID correcto para enviar mensajes de WhatsApp
        
        Args:
            access_token: Token de acceso de Meta
            business_id: ID del negocio en Meta
            waba_id: ID de la cuenta de WhatsApp Business
            
        Returns:
            El Phone Number ID descubierto o None si no se encuentra
        """
        try:
            api_version = settings.WHATSAPP_API_VERSION
            url = f"https://graph.facebook.com/{api_version}/{waba_id}/phone_numbers"
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }
            
            response = requests.get(url, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                if "data" in data and len(data["data"]) > 0:
                    phone_number_id = data["data"][0].get("id")
                    return phone_number_id
            
            return business_id
            
        except Exception as e:
            logger.error(f"Error al intentar descubrir Phone Number ID: {e}", exc_info=True)
            return None

# Create singleton instance
channel_service = ChannelService()
