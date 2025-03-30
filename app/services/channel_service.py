"""
Channel service for sending messages to external channels
"""
from typing import Dict, Any, Optional
from uuid import UUID
import requests
import json

from app.db.supabase_client import supabase
from app.core.config import settings

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
            elif channel_type == "web":
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
            print(f"Error in send_message_to_channel: {e}")
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
            print(f"Error sending Telegram message: {e}")
            raise
    
    def _send_whatsapp_message(self, config: Dict[str, Any], phone_number: str, message: str) -> Dict[str, Any]:
        """Send message to WhatsApp"""
        try:
            access_token = config.get("access_token")
            phone_number_id = config.get("phone_number_id")
            
            if not access_token or not phone_number_id:
                raise ValueError("Access token or phone number ID not found in WhatsApp configuration")
            
            # Clean phone number (remove + if present)
            if phone_number.startswith("+"):
                phone_number = phone_number[1:]
            
            url = f"https://graph.facebook.com/v17.0/{phone_number_id}/messages"
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
            
            response = requests.post(url, headers=headers, json=payload)
            response.raise_for_status()
            
            return response.json()
        except Exception as e:
            print(f"Error sending WhatsApp message: {e}")
            raise
    
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
            
            # Actualizado a v18.0 según la documentación más reciente
            url = "https://graph.facebook.com/v18.0/me/messages"
            
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }
            
            # Formato estándar para enviar mensajes a la API de Messenger
            payload = {
                "recipient": {
                    "id": sender_id
                },
                "message": {
                    "text": message
                }
            }
            
            # Realizar la solicitud a la API de Facebook
            response = requests.post(url, headers=headers, json=payload)
            
            # Verificar si hay errores en la respuesta
            if response.status_code != 200:
                error_data = response.json()
                error_message = error_data.get("error", {}).get("message", "Unknown error")
                print(f"Facebook API error: {error_message}")
                return {"success": False, "error": error_message}
            
            response_data = response.json()
            return {"success": True, "data": response_data}
            
        except Exception as e:
            print(f"Error sending Messenger message: {e}")
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
            print(f"Error sending Instagram message: {e}")
            raise

# Create singleton instance
channel_service = ChannelService()
