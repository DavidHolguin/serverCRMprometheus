from typing import Dict, Any, List, Optional
from uuid import UUID, uuid4
from datetime import datetime

from app.db.supabase_client import supabase
from app.services.langchain_service import langchain_service
from app.services.lead_evaluation_service import lead_evaluation_service
from app.services.event_service import event_service

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
            # Primero buscar cualquier conversación existente para este lead en este canal,
            # independientemente de si el chatbot está activo o no
            result = supabase.table("conversaciones").select("*").eq("lead_id", str(lead_id)) \
                .eq("canal_id", str(canal_id)) \
                .eq("canal_identificador", canal_identificador) \
                .order("created_at", desc=True).limit(1).execute()
            
            if result.data and len(result.data) > 0:
                return result.data[0]
            
            # Si no encontramos una conversación existente, crear una nueva
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
                # Registrar evento de creación de conversación
                conversation = result.data[0]
                empresa_id = self._get_empresa_id_from_chatbot(chatbot_id)
                
                event_service.log_event(
                    empresa_id=empresa_id,
                    event_type=event_service.EVENT_CONVERSATION_STARTED,
                    entidad_origen_tipo="lead",
                    entidad_origen_id=lead_id,
                    entidad_destino_tipo="chatbot",
                    entidad_destino_id=chatbot_id,
                    lead_id=lead_id,
                    chatbot_id=chatbot_id,
                    canal_id=canal_id,
                    conversacion_id=conversation["id"],
                    resultado="success",
                    estado_final="active",
                    detalle=f"Nueva conversación creada en canal {canal_identificador}",
                    metadata={"canal_identificador": canal_identificador}
                )
                
                return conversation
            
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
            
            # Registrar evento de creación de lead - usar primera_interaccion para leads nuevos
            event_service.log_event(
                empresa_id=empresa_id,
                event_type=event_service.EVENT_FIRST_INTERACTION,
                entidad_origen_tipo="canal",
                entidad_origen_id=canal_id,
                lead_id=lead_id,
                canal_id=canal_id,
                resultado="success",
                estado_final="nuevo",
                valor_score=10,
                detalle="Nuevo lead creado desde chat",
                metadata={"canal_origen": "chat", "pipeline_id": pipeline_id, "stage_id": stage_id}
            )
            
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
            
            # Guardar mensaje sanitizado (independientemente de si el chatbot está activo)
            user_message = langchain_service.save_message(conversation_id, sanitized_mensaje, is_user=True)
            
            # Registrar evento de mensaje recibido
            message_event_metadata = {
                "canal_identificador": canal_identificador,
                "chatbot_activo": chatbot_activo,
                "mensaje_length": len(sanitized_mensaje)
            }
            
            # Si hay metadata, la sanitizamos antes de guardarla
            if metadata:
                # Eliminamos cualquier dato personal de los metadatos
                safe_metadata = self.sanitize_metadata(metadata)
                # Actualizar metadata del mensaje si es necesario
                if user_message.get("id"):
                    supabase.table("mensajes").update({"metadata": safe_metadata}).eq("id", user_message["id"]).execute()
                
                # Agregar metadatos sanitizados al evento
                message_event_metadata.update(safe_metadata)
            
            # Registrar evento de mensaje recibido del lead
            event_service.log_event(
                empresa_id=empresa_id,
                event_type=event_service.EVENT_MESSAGE_RECEIVED,
                entidad_origen_tipo="lead",
                entidad_origen_id=lead_id,
                entidad_destino_tipo="chatbot" if chatbot_activo else None,
                entidad_destino_id=chatbot_id if chatbot_activo else None,
                lead_id=lead_id,
                chatbot_id=chatbot_id,
                canal_id=canal_id,
                conversacion_id=conversation_id,
                mensaje_id=user_message["id"],
                metadata=message_event_metadata
            )
            
            # Inicializar variables de respuesta
            response = ""
            bot_message = None
            metadata_response = {"user_message_id": user_message["id"]}
            
            # Calcular hora de inicio para medir duración
            start_time = datetime.utcnow()
            
            # Solo generar respuesta si el chatbot está activo
            if chatbot_activo:
                try:
                    # Generar respuesta con el mensaje sanitizado
                    langchain_config = {
                        "configurable": {
                            "session_id": str(conversation_id)
                        }
                    }
                    
                    response = langchain_service.generate_response(
                        conversation_id, 
                        chatbot_id, 
                        empresa_id, 
                        sanitized_mensaje,
                        config=langchain_config,
                        special_format=True
                    )
                    
                    # Calcular duración de procesamiento
                    processing_duration = (datetime.utcnow() - start_time).total_seconds()
                    
                    # Guardar respuesta del chatbot solo si no está vacía (si el chatbot está activo)
                    if response:
                        bot_message = langchain_service.save_message(conversation_id, response, is_user=False)
                        
                        # Registrar evento de respuesta del chatbot
                        event_service.log_event(
                            empresa_id=empresa_id,
                            event_type=event_service.EVENT_CHATBOT_RESPONSE,
                            entidad_origen_tipo="chatbot",
                            entidad_origen_id=chatbot_id,
                            entidad_destino_tipo="lead",
                            entidad_destino_id=lead_id,
                            lead_id=lead_id,
                            chatbot_id=chatbot_id,
                            canal_id=canal_id,
                            conversacion_id=conversation_id,
                            mensaje_id=bot_message["id"],
                            duracion_segundos=processing_duration,
                            resultado="success",
                            detalle="Respuesta generada correctamente",
                            metadata={"respuesta_length": len(response)}
                        )
                        
                        # ENVIAR RESPUESTA AL CANAL (WhatsApp, etc.)
                        from app.services.channel_service import channel_service
                        try:
                            # Agregamos log para debug
                            print(f"Enviando respuesta '{response[:30]}...' a {canal_identificador} en el canal {canal_id}")
                            
                            # Registrar hora de inicio para medir duración del envío
                            send_start_time = datetime.utcnow()
                            
                            channel_response = channel_service.send_message_to_channel(
                                conversation_id=conversation_id,
                                message=response,
                                metadata={
                                    "origin": "chatbot",
                                    "message_id": bot_message["id"],
                                    "chatbot_id": str(chatbot_id)
                                }
                            )
                            
                            # Calcular duración del envío
                            send_duration = (datetime.utcnow() - send_start_time).total_seconds()
                            
                            # Agregar la información de envío a los metadatos del mensaje
                            supabase.table("mensajes").update({
                                "metadata": {
                                    **(bot_message.get("metadata") or {}),
                                    "channel_delivery": channel_response
                                }
                            }).eq("id", bot_message["id"]).execute()
                            
                            metadata_response["channel_delivery"] = channel_response
                            
                            # Registrar evento de envío de mensaje al canal
                            event_service.log_event(
                                empresa_id=empresa_id,
                                event_type=event_service.EVENT_MESSAGE_SENT,
                                entidad_origen_tipo="chatbot",
                                entidad_origen_id=chatbot_id,
                                entidad_destino_tipo="canal",
                                entidad_destino_id=canal_id,
                                lead_id=lead_id,
                                chatbot_id=chatbot_id,
                                canal_id=canal_id,
                                conversacion_id=conversation_id,
                                mensaje_id=bot_message["id"],
                                duracion_segundos=send_duration,
                                resultado="success",
                                detalle=f"Mensaje enviado a canal {canal_identificador}",
                                metadata={"canal_identificador": canal_identificador}
                            )
                            
                        except Exception as channel_error:
                            print(f"Error al enviar mensaje al canal: {channel_error}")
                            metadata_response["channel_error"] = str(channel_error)
                            
                            # Registrar error de envío
                            event_service.log_event(
                                empresa_id=empresa_id,
                                event_type=event_service.EVENT_ERROR_OCCURRED,
                                entidad_origen_tipo="chatbot",
                                entidad_origen_id=chatbot_id,
                                entidad_destino_tipo="canal",
                                entidad_destino_id=canal_id,
                                lead_id=lead_id,
                                chatbot_id=chatbot_id,
                                canal_id=canal_id,
                                conversacion_id=conversation_id,
                                mensaje_id=bot_message["id"],
                                resultado="error",
                                detalle=f"Error al enviar mensaje: {str(channel_error)}",
                                metadata={"error": str(channel_error), "canal_identificador": canal_identificador}
                            )
                except Exception as response_error:
                    print(f"Error al generar respuesta: {response_error}")
                    metadata_response["response_error"] = str(response_error)
                    
                    # Registrar error de generación de respuesta
                    event_service.log_event(
                        empresa_id=empresa_id,
                        event_type=event_service.EVENT_ERROR_OCCURRED,
                        entidad_origen_tipo="chatbot",
                        entidad_origen_id=chatbot_id,
                        lead_id=lead_id,
                        chatbot_id=chatbot_id,
                        canal_id=canal_id,
                        conversacion_id=conversation_id,
                        mensaje_id=user_message["id"],
                        resultado="error",
                        detalle=f"Error al generar respuesta: {str(response_error)}",
                        metadata={"error": str(response_error)}
                    )
                    # Registramos el error pero continuamos para devolver una respuesta válida
            else:
                metadata_response["chatbot_disabled"] = True
            
            # Iniciar proceso de evaluación en segundo plano solo si el chatbot está activo o si se requiere
            if chatbot_activo or metadata.get("evaluate_anyway", False):
                self._start_async_evaluation(lead_id, conversation_id, UUID(user_message["id"]), empresa_id)
            
            # Respuesta inmediata sin esperar evaluación
            # IMPORTANTE: Asegurar que siempre devolvemos un mensaje_id válido, incluso cuando el bot está desactivado
            mensaje_id = bot_message["id"] if bot_message else user_message["id"]
            
            return {
                "mensaje_id": mensaje_id,  # Siempre devolvemos un ID válido
                "conversacion_id": str(conversation_id),
                "respuesta": response,
                "lead_id": str(lead_id),  # Añadimos el lead_id a la respuesta para referencia
                "metadata": metadata_response
            }
        except Exception as e:
            print(f"Error in process_channel_message: {e}")
            raise
    
    def _start_async_evaluation(self, lead_id: UUID, conversacion_id: UUID, mensaje_id: UUID, empresa_id: UUID) -> None:
        """
        Inicia la evaluación de un mensaje en segundo plano
        
        Args:
            lead_id: El ID del lead
            conversacion_id: El ID de la conversación
            mensaje_id: El ID del mensaje a evaluar
            empresa_id: El ID de la empresa
        """
        try:
            # Registrar evento de inicio de evaluación
            event_service.log_event(
                empresa_id=empresa_id,
                event_type=event_service.EVENT_LEAD_EVALUATION,
                lead_id=lead_id,
                conversacion_id=conversacion_id,
                mensaje_id=mensaje_id,
                resultado="started",
                detalle="Iniciando evaluación asincrónica del lead"
            )
            
            # En un entorno de producción, aquí se enviaría la tarea a un worker o cola
            # Para esta implementación, ejecutamos directamente pero sin esperar el resultado
            from app.services.lead_evaluation_service import lead_evaluation_service
            from threading import Thread
            
            # Crear una función que ejecute la evaluación
            def evaluate_in_background():
                try:
                    lead_evaluation_service.evaluate_message(
                        lead_id=lead_id,
                        conversacion_id=conversacion_id,
                        mensaje_id=mensaje_id,
                        empresa_id=empresa_id
                    )
                except Exception as eval_error:
                    print(f"Error en evaluación asíncrona: {eval_error}")
                    
                    # Registrar error en la evaluación
                    event_service.log_event(
                        empresa_id=empresa_id,
                        event_type=event_service.EVENT_ERROR_OCCURRED,
                        lead_id=lead_id,
                        conversacion_id=conversacion_id,
                        mensaje_id=mensaje_id,
                        resultado="error",
                        detalle=f"Error en evaluación asincrónica: {str(eval_error)}",
                        metadata={"error": str(eval_error)}
                    )
            
            # Iniciar la evaluación en un hilo separado
            evaluation_thread = Thread(target=evaluate_in_background)
            evaluation_thread.daemon = True  # El hilo no bloqueará la finalización del programa
            evaluation_thread.start()
            
        except Exception as e:
            print(f"Error al iniciar evaluación asíncrona: {e}")
            # No propagamos la excepción para no bloquear la respuesta

    def toggle_chatbot_status(self, conversacion_id: UUID, chatbot_activo: bool) -> Dict[str, Any]:
        """
        Cambia el estado del chatbot en una conversación
        
        Args:
            conversacion_id: El ID de la conversación
            chatbot_activo: True para activar el chatbot, False para desactivarlo
            
        Returns:
            Datos de la conversación actualizada
        """
        try:
            # Actualizar el estado del chatbot en la base de datos
            result = supabase.table("conversaciones").update({
                "chatbot_activo": chatbot_activo
            }).eq("id", str(conversacion_id)).execute()
            
            if result.data and len(result.data) > 0:
                conversation = result.data[0]
                
                # Obtener IDs necesarios para el evento
                lead_id = conversation.get("lead_id")
                chatbot_id = conversation.get("chatbot_id")
                canal_id = conversation.get("canal_id")
                
                # Obtener empresa_id desde el chatbot
                empresa_id = self._get_empresa_id_from_chatbot(chatbot_id)
                
                # Registrar evento de cambio de estado
                event_service.log_event(
                    empresa_id=empresa_id,
                    event_type=event_service.EVENT_CHATBOT_STATUS_CHANGED,
                    entidad_origen_tipo="chatbot",
                    entidad_origen_id=chatbot_id,
                    lead_id=lead_id,
                    chatbot_id=chatbot_id,
                    canal_id=canal_id,
                    conversacion_id=conversacion_id,
                    resultado="success",
                    estado_final="active" if chatbot_activo else "inactive",
                    detalle=f"Chatbot {'activado' if chatbot_activo else 'desactivado'} en conversación"
                )
                
                return conversation
            
            raise ValueError("No se pudo actualizar el estado del chatbot")
            
        except Exception as e:
            print(f"Error en toggle_chatbot_status: {e}")
            raise
            
    def _get_empresa_id_from_chatbot(self, chatbot_id: UUID) -> UUID:
        """
        Obtiene el ID de la empresa a partir del ID del chatbot
        
        Args:
            chatbot_id: El ID del chatbot
            
        Returns:
            El ID de la empresa
        """
        try:
            result = supabase.table("chatbots").select("empresa_id").eq("id", str(chatbot_id)).limit(1).execute()
            
            if result.data and len(result.data) > 0:
                return UUID(result.data[0].get("empresa_id"))
            
            # Si no se encuentra, usar un ID por defecto (esto es solo un fallback y debería lograrse)
            return UUID("00000000-0000-0000-0000-000000000000")
            
        except Exception as e:
            print(f"Error al obtener empresa_id desde chatbot: {e}")
            # En caso de error, devolver un ID por defecto
            return UUID("00000000-0000-0000-0000-000000000000")

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
