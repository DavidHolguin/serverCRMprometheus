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
            nombre: The name of the lead
            metadata: Additional metadata
            
        Returns:
            The lead data
        """
        try:
            # Extract contact info from metadata if available
            email = None
            telefono = None
            
            if metadata:
                email = metadata.get("email")
                telefono = metadata.get("phone") or metadata.get("telefono")
            
            # Try to find existing lead by phone or email
            if telefono:
                result = supabase.table("leads").select("*").eq("empresa_id", str(empresa_id)) \
                    .eq("telefono", telefono).limit(1).execute()
                
                if result.data and len(result.data) > 0:
                    return result.data[0]
            
            if email:
                result = supabase.table("leads").select("*").eq("empresa_id", str(empresa_id)) \
                    .eq("email", email).limit(1).execute()
                
                if result.data and len(result.data) > 0:
                    return result.data[0]
            
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
            
            # Create new lead
            lead_data = {
                "empresa_id": str(empresa_id),
                "canal_origen": "chat",
                "canal_id": str(canal_id),
                "nombre": nombre,
                "telefono": telefono,
                "email": email,
                "pipeline_id": pipeline_id,
                "stage_id": stage_id,
                "estado": "nuevo",
                "score": 10  # Initial score for new leads
            }
            
            result = supabase.table("leads").insert(lead_data).execute()
            
            if result.data and len(result.data) > 0:
                return result.data[0]
            
            raise ValueError("Failed to create lead")
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
                # Extract name from metadata or use channel identifier
                nombre = metadata.get("nombre", canal_identificador) if metadata else canal_identificador
                lead = self.get_or_create_lead(empresa_id, canal_id, nombre, metadata)
                lead_id = UUID(lead["id"])
            
            # Get or create conversation
            conversation = self.get_or_create_conversation(lead_id, chatbot_id, canal_id, canal_identificador)
            conversation_id = UUID(conversation["id"])
            
            # Save user message
            user_message = langchain_service.save_message(conversation_id, mensaje, is_user=True)
            
            # Generate response
            response = langchain_service.generate_response(conversation_id, chatbot_id, empresa_id, mensaje)
            
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
                
                # Incluir la evaluación en los metadatos de respuesta
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
                # Si falla la evaluación, continuar sin ella
                metadata_response = {
                    "user_message_id": user_message["id"]
                }
            
            return {
                "mensaje_id": bot_message["id"],
                "conversacion_id": str(conversation_id),
                "respuesta": response,
                "metadata": metadata_response
            }
        except Exception as e:
            print(f"Error in process_channel_message: {e}")
            raise

# Create singleton instance
conversation_service = ConversationService()
