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
            # Primero intentar obtener configuración del canal específico
            access_token = config.get("access_token")
            phone_number_id = config.get("phone_number_id")
            api_version = config.get("api_version")
            waba_id = settings.WHATSAPP_WABA_ID
            business_id = settings.WHATSAPP_BUSINESS_PHONE
            app_id = config.get("app_id")  # Intentar obtener app_id de la configuración
            
            # Si no hay configuración en el canal, usar las variables globales de configuración
            if not access_token:
                access_token = settings.WHATSAPP_ACCESS_TOKEN
                print(f"Usando token de acceso global de la configuración")
            
            if not api_version:
                api_version = settings.WHATSAPP_API_VERSION
                print(f"Usando versión de API global: {api_version}")
                
            # Intentar obtener app_id de configuración global si no está en config
            if not app_id and hasattr(settings, 'WHATSAPP_APP_ID'):
                app_id = settings.WHATSAPP_APP_ID
                print(f"Usando WHATSAPP_APP_ID global: {app_id}")
            
            # Verificar si tenemos los valores necesarios para la API
            if not access_token:
                error_msg = "Error en configuración de WhatsApp: Falta access_token"
                print(error_msg)
                return {"success": False, "error": error_msg}
            
            # Intentar múltiples estrategias para el phone_number_id
            if not phone_number_id:
                print("No se encontró phone_number_id en la configuración del canal, intentando descubrirlo...")
                
                # Intentar descubrir automáticamente el Phone Number ID
                discovered_id = self._discover_whatsapp_phone_number_id(
                    access_token=access_token,
                    business_id=business_id,
                    waba_id=waba_id
                )
                
                if discovered_id:
                    phone_number_id = discovered_id
                    print(f"Usando Phone Number ID descubierto: {phone_number_id}")
                elif hasattr(settings, 'WHATSAPP_BUSINESS_PHONE'):
                    phone_number_id = settings.WHATSAPP_BUSINESS_PHONE
                    print(f"Usando BUSINESS_PHONE como respaldo: {phone_number_id}")
            
            if not phone_number_id:
                error_msg = "Error en configuración de WhatsApp: No se pudo obtener un phone_number_id válido"
                print(error_msg)
                return {"success": False, "error": error_msg}
            
            # Log para depuración
            print(f"Enviando mensaje a WhatsApp: número={phone_number}, phone_number_id={phone_number_id}")
            print(f"Usando API versión: {api_version}")
            print(f"Access token (primeros 10 caracteres): {access_token[:10]}...")
            if app_id:
                print(f"Usando App ID: {app_id}")
            
            # Clean phone number (remove + if present)
            if phone_number.startswith("+"):
                phone_number = phone_number[1:]
            
            # Construir URL, incluyendo app_id si está disponible
            base_url = f"https://graph.facebook.com/{api_version}/{phone_number_id}/messages"
            if app_id:
                # Añadir app_id como parámetro de consulta
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
            
            print(f"URL WhatsApp API: {base_url}")
            print(f"Payload: {payload}")
            
            # Intentar enviar el mensaje
            response = requests.post(base_url, headers=headers, json=payload)
            
            # Si el primer intento falla y tenemos un WABA_ID diferente, intentar con él
            if response.status_code != 200 and phone_number_id != waba_id:
                phone_number_id = waba_id
                print(f"Primer intento fallido. Intentando con WABA_ID: {phone_number_id}")
                
                base_url = f"https://graph.facebook.com/{api_version}/{phone_number_id}/messages"
                if app_id:
                    base_url += f"?app_id={app_id}"
                    
                response = requests.post(base_url, headers=headers, json=payload)
            
            # Imprimir información de la respuesta para depuración
            print(f"Respuesta de WhatsApp API: status_code={response.status_code}")
            
            try:
                response_data = response.json()
                print(f"Respuesta JSON: {response_data}")
            except:
                print(f"La respuesta no es JSON válido: {response.text[:200]}")
                response_data = {"raw_response": response.text[:200]}
            
            # Verificar el código de estado
            if response.status_code != 200:
                print(f"Error al enviar mensaje a WhatsApp: {response.status_code}")
                error_message = response_data.get("error", {}).get("message", "Unknown error")
                print(f"Mensaje de error: {error_message}")
                
                # Verificar si es un error de app_id
                if error_message and "Provide valid app ID" in error_message:
                    print("Error de App ID: Debes proporcionar un app_id válido en la configuración.")
                    print("Agrega WHATSAPP_APP_ID a tu archivo .env o en la configuración del canal.")
                
                # Verificar si es un error de token
                if response.status_code == 401 or (response.status_code == 400 and "token" in str(error_message).lower()):
                    print("Error de autenticación. Verifica que el token sea válido y esté vigente.")
                
                # Verificar si es un error de phone_number_id
                if "Object with ID" in str(error_message) and "does not exist" in str(error_message):
                    print(f"El phone_number_id ({phone_number_id}) no es válido o no tiene permisos.")
                    print(f"Verifica que el phone_number_id sea correcto y que tu aplicación tenga acceso.")
                    print("Posibles soluciones:")
                    print("1. Verifica el phone_number_id en Meta Business Suite > WhatsApp > Configuración > API")
                    print("2. Asegúrate que tu aplicación tenga permisos whatsapp_business_messaging")
                    print("3. Verifica que hayas completado la verificación del negocio en Meta Business")
                    print("4. Ejecuta este comando para obtener los números de teléfono:")
                    print(f"   curl -X GET 'https://graph.facebook.com/{api_version}/{waba_id}/phone_numbers' -H 'Authorization: Bearer {access_token[:10]}...'")
                
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
            print(f"Excepción al enviar mensaje a WhatsApp: {e}")
            import traceback
            traceback.print_exc()
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
            # Estrategia 1: Intentar obtener los números de teléfono asociados a la WABA
            api_version = settings.WHATSAPP_API_VERSION
            url = f"https://graph.facebook.com/{api_version}/{waba_id}/phone_numbers"
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }
            
            print(f"Intentando descubrir Phone Number ID desde WABA: {url}")
            response = requests.get(url, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                if "data" in data and len(data["data"]) > 0:
                    # Tomar el primer número de teléfono de la lista
                    phone_number_id = data["data"][0].get("id")
                    display_phone_number = data["data"][0].get("display_phone_number")
                    print(f"¡Phone Number ID descubierto! ID: {phone_number_id}, Número: {display_phone_number}")
                    return phone_number_id
            
            # Estrategia 2: Intentar con el business_id como phone_number_id
            print(f"Intentando con business_id como alternativa: {business_id}")
            return business_id
            
        except Exception as e:
            print(f"Error al intentar descubrir Phone Number ID: {e}")
            return None

# Create singleton instance
channel_service = ChannelService()
