from typing import Dict, Any, List, Optional
from uuid import UUID, uuid4
from datetime import datetime

from app.db.supabase_client import supabase
from app.services.langchain_service import langchain_service
from app.services.lead_evaluation_service import lead_evaluation_service

class ConversationService:
    """Service for handling conversations and messages"""
    
    def get_or_create_conversation(self, lead_id: UUID, chatbot_id: UUID, canal_id: UUID, 
                                  canal_identificador: str) -> Dict[str, Any]:
        """
        Get an existing conversation or create a new one
        
        Args:
            lead_id: The ID of the lead
            chatbot_id: The ID of the chatbot
            canal_id: The ID of the channel
            canal_identificador: The channel identifier
            
        Returns:
            The conversation data
        """
        try:
            # Try to find existing active conversation
            result = supabase.table("conversaciones").select("*").eq("lead_id", str(lead_id)) \
                .eq("chatbot_id", str(chatbot_id)).eq("canal_id", str(canal_id)) \
                .eq("canal_identificador", canal_identificador).eq("estado", "active").limit(1).execute()
            
            if result.data and len(result.data) > 0:
                return result.data[0]
            
            # Create new conversation
            conversation_data = {
                "lead_id": str(lead_id),
                "chatbot_id": str(chatbot_id),
                "canal_id": str(canal_id),
                "canal_identificador": canal_identificador,
                "estado": "active",
                "chatbot_activo": True
            }
            
            result = supabase.table("conversaciones").insert(conversation_data).execute()
            
            if result.data and len(result.data) > 0:
                return result.data[0]
            
            raise ValueError("Failed to create conversation")
        except Exception as e:
            print(f"Error in get_or_create_conversation: {e}")
            raise
    
    def get_or_create_lead(self, empresa_id: UUID, canal_id: UUID, 
                          nombre: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Get an existing lead or create a new one
        
        Args:
            empresa_id: The ID of the company
            canal_id: The ID of the channel
            nombre: The name of the lead (Se usará solo para el token anónimo)
            metadata: Additional metadata
            
        Returns:
            The lead data
        """
        try:
            # Ya no buscamos leads por datos personales
            # Simplemente creamos un nuevo lead y generamos un token anónimo si es necesario
            
            # Get default pipeline for the company
            pipeline_result = supabase.table("pipelines").select("id").eq("empresa_id", str(empresa_id)) \
                .eq("is_default", True).limit(1).execute()
            
            pipeline_id = None
            if pipeline_result.data and len(pipeline_result.data) > 0:
                pipeline_id = pipeline_result.data[0].get("id")
                
                # Get first stage of the pipeline
                stage_result = supabase.table("pipeline_stages").select("id").eq("pipeline_id", pipeline_id) \
                    .order("posicion").limit(1).execute()
                
                stage_id = None
                if stage_result.data and len(stage_result.data) > 0:
                    stage_id = stage_result.data[0].get("id")
            
            # Create new lead (sin datos personales)
            lead_data = {
                "empresa_id": str(empresa_id),
                "canal_origen": "chat",
                "canal_id": str(canal_id),
                "pipeline_id": pipeline_id,
                "stage_id": stage_id,
                "estado": "nuevo",
                "score": 10  # Initial score for new leads
            }
            
            # Insertar el lead básico
            lead_result = supabase.table("leads").insert(lead_data).execute()
            
            if not lead_result.data or len(lead_result.data) == 0:
                raise ValueError("Failed to create lead")
            
            lead = lead_result.data[0]
            lead_id = lead["id"]
            
            # Generamos un token anónimo para este lead (opcional)
            token_anonimo = str(uuid4())
            
            # Crear entrada en pii_tokens en lugar de datos personales
            token_data = {
                "lead_id": lead_id,
                "token_anonimo": token_anonimo,
                "is_active": True,
                "expires_at": None  # Sin fecha de expiración por ahora
            }
            
            # Insertar el token anónimo
            supabase.table("pii_tokens").insert(token_data).execute()
            
            return lead
        except Exception as e:
            print(f"Error in get_or_create_lead: {e}")
            raise
    
    def process_channel_message(self, canal_id: UUID, canal_identificador: str, 
                               empresa_id: UUID, chatbot_id: UUID, mensaje: str, 
                               lead_id: Optional[UUID] = None, 
                               metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Process a message from a channel
        
        Args:
            canal_id: The ID of the channel
            canal_identificador: The channel identifier
            empresa_id: The ID of the company
            chatbot_id: The ID of the chatbot
            mensaje: The message content
            lead_id: The ID of the lead (optional)
            metadata: Additional metadata (optional)
            
        Returns:
            Response data including the message ID, conversation ID, and response
        """
        try:
            # Get or create lead if not provided
            if not lead_id:
                # Ya no usamos nombres ni datos personales del metadata
                # Creamos un lead anónimo con identificador único
                lead = self.get_or_create_lead(empresa_id, canal_id, "anónimo", None)
                lead_id = UUID(lead["id"])
            
            # Sanitizamos el mensaje de entrada (para asegurar que no contenga datos personales)
            sanitized_mensaje = self.sanitize_message(mensaje)
            
            # Get or create conversation
            conversation = self.get_or_create_conversation(lead_id, chatbot_id, canal_id, canal_identificador)
            conversation_id = UUID(conversation["id"])
            
            # Verificar si el chatbot está activo para esta conversación
            chatbot_activo = conversation.get("chatbot_activo", True)
            if not chatbot_activo:
                print(f"Chatbot está desactivado para la conversación {conversation_id}. No se generará respuesta automática.")
                return {
                    "mensaje_id": None,
                    "conversacion_id": str(conversation_id),
                    "respuesta": None,
                    "metadata": {"chatbot_disabled": True}
                }
            
            # Guardar mensaje sanitizado
            user_message = langchain_service.save_message(conversation_id, sanitized_mensaje, is_user=True)
            
            # Si hay metadata, la sanitizamos antes de guardarla
            if metadata:
                # Eliminamos cualquier dato personal de los metadatos
                safe_metadata = self.sanitize_metadata(metadata)
                # Actualizar metadata del mensaje si es necesario
                if user_message.get("id"):
                    supabase.table("mensajes").update({"metadata": safe_metadata}).eq("id", user_message["id"]).execute()
            
            # Generar respuesta con el mensaje sanitizado
            response = langchain_service.generate_response(conversation_id, chatbot_id, empresa_id, sanitized_mensaje)
            
            # Save chatbot response
            bot_message = langchain_service.save_message(conversation_id, response, is_user=False)
            
            # Evaluar el mensaje del usuario para determinar el valor del lead
            try:
                evaluation = lead_evaluation_service.evaluate_message(
                    lead_id=lead_id,
                    conversacion_id=conversation_id,
                    mensaje_id=UUID(user_message["id"]),
                    empresa_id=empresa_id
                )
                
                metadata_response = {
                    "user_message_id": user_message["id"],
                    "evaluation": {
                        "id": evaluation["id"],
                        "score_potencial": evaluation["score_potencial"],
                        "score_satisfaccion": evaluation["score_satisfaccion"]
                    }
                }
            except Exception as eval_error:
                print(f"Error al evaluar el mensaje: {eval_error}")
                metadata_response = {
                    "user_message_id": user_message["id"]
                }
            
            # ENVIAR RESPUESTA AL CANAL (WhatsApp, etc.)
            from app.services.channel_service import channel_service
            try:
                # Agregamos log para debug
                print(f"Enviando respuesta '{response[:30]}...' a {canal_identificador} en el canal {canal_id}")
                
                channel_response = channel_service.send_message_to_channel(
                    conversation_id=conversation_id,
                    message=response,
                    metadata={
                        "origin": "chatbot",
                        "message_id": bot_message["id"],
                        "chatbot_id": str(chatbot_id)
                    }
                )
                
                # Agregar la información de envío a los metadatos del mensaje
                supabase.table("mensajes").update({
                    "metadata": {
                        **(bot_message.get("metadata") or {}),
                        "channel_delivery": channel_response
                    }
                }).eq("id", bot_message["id"]).execute()
                
                metadata_response["channel_delivery"] = channel_response
                
            except Exception as channel_error:
                print(f"Error al enviar mensaje al canal: {channel_error}")
                metadata_response["channel_error"] = str(channel_error)
            
            return {
                "mensaje_id": bot_message["id"],
                "conversacion_id": str(conversation_id),
                "respuesta": response,
                "metadata": metadata_response
            }
        except Exception as e:
            print(f"Error in process_channel_message: {e}")
            raise

    def sanitize_message(self, mensaje: str) -> str:
        """
        Sanitiza un mensaje para eliminar posible información personal
        
        Args:
            mensaje: El mensaje a sanitizar
            
        Returns:
            Mensaje sanitizado
        """
        # En una implementación real, aquí podrías usar expresiones regulares o NLP
        # para detectar y ofuscar información personal como emails, teléfonos, etc.
        # Por simplicidad, solo implementamos una versión básica
        
        # Ejemplo simple: guardaríamos el mensaje en mensajes_sanitizados
        # y devolveríamos el mensaje sin modificar por ahora
        return mensaje

    def sanitize_metadata(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sanitiza los metadatos para eliminar información personal
        
        Args:
            metadata: Los metadatos a sanitizar
            
        Returns:
            Metadatos sanitizados
        """
        # Creamos una copia de los metadatos
        safe_metadata = metadata.copy() if metadata else {}
        
        # Eliminamos campos conocidos de datos personales
        fields_to_remove = [
            "nombre", "apellido", "email", "correo", "telefono", "phone", 
            "direccion", "address", "dni", "nif", "doc", "documento"
        ]
        
        for field in fields_to_remove:
            if field in safe_metadata:
                del safe_metadata[field]
        
        return safe_metadata

# Create singleton instance
conversation_service = ConversationService()
