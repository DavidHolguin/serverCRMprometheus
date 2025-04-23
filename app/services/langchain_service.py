from typing import List, Dict, Any, Optional
from uuid import UUID
import json

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_core.runnables import RunnablePassthrough
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.output_parsers import StrOutputParser

from app.core.config import settings
from app.db.supabase_client import supabase

class CustomChatMessageHistory(BaseChatMessageHistory):
    """Custom chat message history implementation for database storage"""
    
    def __init__(self, conversation_id: UUID):
        """Initialize with conversation ID"""
        self.conversation_id = conversation_id
        self._messages = []
        self._load_messages()
    
    def _load_messages(self):
        """Load messages from database"""
        from app.services.langchain_service import langchain_service
        history = langchain_service._get_conversation_history(self.conversation_id)
        
        self._messages = []
        for message in history:
            if message["origen"] == "user":
                self._messages.append(HumanMessage(content=message["contenido"]))
            else:
                self._messages.append(AIMessage(content=message["contenido"]))
    
    def add_message(self, message):
        """Add a message to the store"""
        self._messages.append(message)
    
    def add_user_message(self, message: str) -> None:
        """Add a user message to the store"""
        self._messages.append(HumanMessage(content=message))
    
    def add_ai_message(self, message: str) -> None:
        """Add an AI message to the store"""
        self._messages.append(AIMessage(content=message))
    
    @property
    def messages(self):
        """Retrieve all messages"""
        return self._messages
    
    def clear(self):
        """Clear all messages"""
        self._messages = []

class LangChainService:
    """Service for handling LangChain operations"""
    
    def __init__(self):
        """Initialize the LangChain service"""
        self.message_histories = {}  # In-memory cache of conversation message histories
    
    def _get_llm_config(self, empresa_id: UUID) -> Dict[str, Any]:
        """
        Get the LLM configuration for a specific company
        
        Args:
            empresa_id: The ID of the company
            
        Returns:
            Dict containing LLM configuration
        """
        # Get LLM configuration from database
        result = supabase.table("llm_configuraciones").select("*").eq("empresa_id", str(empresa_id)).eq("is_default", True).execute()
        
        if not result.data or len(result.data) == 0:
            # Use default configuration if not found
            return {
                "model": settings.DEFAULT_MODEL,
                "temperature": settings.DEFAULT_TEMPERATURE,
                "max_tokens": settings.DEFAULT_MAX_TOKENS,
                "api_key": settings.OPENAI_API_KEY
            }
        
        config = result.data[0]
        
        return {
            "model": config["modelo"],
            "temperature": config["configuracion"]["temperature"],
            "max_tokens": config["configuracion"]["max_tokens"],
            "api_key": config["api_key"] or settings.OPENAI_API_KEY
        }
    
    def _get_chatbot_prompt_template(self, chatbot_id: UUID) -> Dict[str, Any]:
        """
        Obtiene el prompt template asociado a un chatbot
        
        Args:
            chatbot_id: El ID del chatbot
            
        Returns:
            Dict conteniendo la información del prompt template
        """
        # Obtener el mapeo de prompt para este chatbot
        mapping_result = supabase.table("chatbot_prompt_mapping") \
            .select("*") \
            .eq("chatbot_id", str(chatbot_id)) \
            .eq("is_active", True) \
            .order("orden", desc=False) \
            .execute()
        
        if not mapping_result.data or len(mapping_result.data) == 0:
            # Si no hay un prompt template específico, usamos el contexto tradicional
            return None
        
        mapping = mapping_result.data[0]
        prompt_template_id = mapping["prompt_template_id"]
        parametros = mapping.get("parametros", {})
        
        # Obtener el prompt template
        template_result = supabase.table("prompt_templates") \
            .select("*") \
            .eq("id", prompt_template_id) \
            .eq("is_active", True) \
            .limit(1) \
            .execute()
        
        if not template_result.data or len(template_result.data) == 0:
            return None
        
        template = template_result.data[0]
        
        return {
            "id": template["id"],
            "nombre": template["nombre"],
            "tipo_template": template["tipo_template"],
            "contenido": template["contenido"],
            "variables": template["variables"],
            "parametros": parametros
        }
    
    def _get_chatbot_context(self, chatbot_id: UUID) -> Dict[str, Any]:
        """
        Get the context for a specific chatbot
        
        Args:
            chatbot_id: The ID of the chatbot
            
        Returns:
            Dict containing chatbot context information
        """
        # Get chatbot information
        chatbot_result = supabase.table("chatbots").select("*").eq("id", str(chatbot_id)).execute()
        
        if not chatbot_result.data or len(chatbot_result.data) == 0:
            raise ValueError(f"Chatbot with ID {chatbot_id} not found")
        
        chatbot = chatbot_result.data[0]
        
        # Get chatbot context
        context_result = supabase.table("chatbot_contextos").select("*").eq("chatbot_id", str(chatbot_id)).eq("tipo", "general").execute()
        
        if not context_result.data or len(context_result.data) == 0:
            raise ValueError(f"Context for chatbot with ID {chatbot_id} not found")
        
        context = context_result.data[0]
        
        # Verificar si hay ejemplos de Q&A en el contexto
        qa_examples = context.get("qa_examples", [])
        qa_examples_text = ""
        
        # Formatear los ejemplos de Q&A para el prompt
        if qa_examples and len(qa_examples) > 0:
            qa_examples_text = "\n## Ejemplos de preguntas y respuestas\n"
            for i, example in enumerate(qa_examples):
                if isinstance(example, dict) and "pregunta" in example and "respuesta" in example:
                    qa_examples_text += f"\nPregunta {i+1}: {example['pregunta']}\n"
                    qa_examples_text += f"Respuesta {i+1}: {example['respuesta']}\n"
        
        # Formatear los key_points de manera segura
        key_points_text = "[]"
        try:
            # Manejo seguro de key_points
            key_points = context.get('key_points', [])
            if key_points:
                # Si es una cadena (posiblemente JSON), intentamos analizarla
                if isinstance(key_points, str):
                    try:
                        key_points = json.loads(key_points)
                    except:
                        key_points = []
                
                # Si es una lista, intentamos formatearla como texto
                if isinstance(key_points, list):
                    key_points_items = []
                    for i, point in enumerate(key_points):
                        if isinstance(point, dict):
                            # Si es un diccionario, extraemos valores específicos si existen
                            if "text" in point:
                                key_points_items.append(f"- {point['text']}")
                            elif "title" in point:
                                key_points_items.append(f"- {point['title']}")
                            else:
                                # Si no tiene text o title, lo convertimos a cadena de manera segura
                                try:
                                    key_points_items.append(f"- Punto {i+1}: {json.dumps(point, ensure_ascii=False)}")
                                except:
                                    key_points_items.append(f"- Punto {i+1}")
                        elif isinstance(point, str):
                            key_points_items.append(f"- {point}")
                        else:
                            key_points_items.append(f"- Punto {i+1}")
                    
                    # Unir los puntos en un texto formateado
                    key_points_text = "\n".join(key_points_items)
                else:
                    # Si no es una lista ni una cadena, lo convertimos a cadena JSON
                    try:
                        key_points_text = json.dumps(key_points, ensure_ascii=False)
                    except:
                        key_points_text = "[]"
        except Exception as e:
            print(f"Error procesando key_points: {e}")
            key_points_text = "[]"
        
        # Verificar si hay un prompt_template_id en el contexto
        prompt_template_id = context.get("prompt_template")
        prompt_template = None
        
        # Si hay un ID de prompt_template, obtener el template de la tabla prompt_templates
        if prompt_template_id:
            try:
                # Obtener el prompt template
                template_result = supabase.table("prompt_templates") \
                    .select("*") \
                    .eq("id", prompt_template_id) \
                    .eq("is_active", True) \
                    .limit(1) \
                    .execute()
                
                if template_result.data and len(template_result.data) > 0:
                    template = template_result.data[0]
                    prompt_template = template["contenido"]
                    
                    # Reemplazar variables estándar
                    prompt_template = prompt_template.replace("{{chatbot_name}}", chatbot['nombre'])
                    prompt_template = prompt_template.replace("{{personality}}", context.get('personality') or "")
                    prompt_template = prompt_template.replace("{{general_context}}", context.get('general_context') or "")
                    prompt_template = prompt_template.replace("{{communication_tone}}", context.get('communication_tone') or "")
                    prompt_template = prompt_template.replace("{{main_purpose}}", context.get('main_purpose') or "")
                    prompt_template = prompt_template.replace("{{special_instructions}}", context.get('special_instructions') or "")
                    prompt_template = prompt_template.replace("{{qa_examples}}", qa_examples_text)
                    
                    # Usando la versión segura de key_points
                    prompt_template = prompt_template.replace("{{key_points}}", key_points_text)
            except Exception as e:
                print(f"Error obteniendo prompt template: {e}")
                # Si hay un error, se usará el formato predeterminado
        
        # Si no se encontró un prompt_template personalizado, construir uno estándar
        if not prompt_template:
            # Construir el prompt template usando concatenación en lugar de format strings
            prompt_template = "\n# " + chatbot['nombre'] + "\n\n"
            prompt_template += "## Personalidad\n" + (context.get('personality') or "") + "\n\n"
            prompt_template += "## Contexto general\n" + (context.get('general_context') or "") + "\n\n"
            prompt_template += "## Tono de comunicación\n" + (context.get('communication_tone') or "") + "\n\n"
            prompt_template += "## Propósito principal\n" + (context.get('main_purpose') or "") + "\n\n"
            prompt_template += "## Puntos clave\n" + key_points_text + "\n\n"
            prompt_template += "## Instrucciones especiales\n" + (context.get('special_instructions') or "") + "\n"
            prompt_template += qa_examples_text + "\n\n"
            prompt_template += "Responde de manera concisa y útil. Si no sabes la respuesta, admítelo claramente."

        return {
            "system_message": prompt_template,
            "welcome_message": context.get("welcome_message", "")
        }
    
    def _get_conversation_history(self, conversation_id: UUID, limit: int = settings.MAX_HISTORY_LENGTH) -> List[Dict[str, Any]]:
        """
        Get the conversation history for a specific conversation
        
        Args:
            conversation_id: The ID of the conversation
            limit: Maximum number of messages to retrieve
            
        Returns:
            List of messages in the conversation
        """
        result = supabase.table("mensajes").select("*").eq("conversacion_id", str(conversation_id)).order("created_at", desc=False).limit(limit).execute()
        
        return result.data if result.data else []
    
    def _get_or_create_message_history(self, conversation_id: UUID) -> CustomChatMessageHistory:
        """
        Get or create a message history for a specific conversation
        
        Args:
            conversation_id: The ID of the conversation
            
        Returns:
            CustomChatMessageHistory instance
        """
        if str(conversation_id) in self.message_histories:
            return self.message_histories[str(conversation_id)]
        
        # Create message history
        message_history = CustomChatMessageHistory(conversation_id)
        
        # Cache message history
        self.message_histories[str(conversation_id)] = message_history
        
        return message_history
    
    def generate_response(self, conversation_id, chatbot_id, empresa_id, message, config=None, special_format=False):
        """
        Generate a response using LangChain and OpenAI
        
        Args:
            conversation_id: The ID of the conversation
            chatbot_id: The ID of the chatbot
            empresa_id: The ID of the company
            message: The user message
            config: Optional configuration dictionary
            special_format: Whether to use special formatting for the 'id' variable
            
        Returns:
            Generated response
        """
        try:
            # Asegurarse de que tenemos una configuración válida
            if config is None:
                config = {
                    "configurable": {
                        "session_id": str(conversation_id)  # Usar conversation_id como session_id por defecto
                    }
                }
            
            # Check if chatbot is active for this conversation
            conv_result = supabase.table("conversaciones").select("chatbot_activo").eq("id", str(conversation_id)).limit(1).execute()
            
            if not conv_result.data or len(conv_result.data) == 0:
                raise ValueError(f"Conversation {conversation_id} not found")
            
            # If chatbot is not active, return empty response
            if not conv_result.data[0].get("chatbot_activo", True):
                return ""
                
            # Get LLM configuration
            llm_config = self._get_llm_config(empresa_id)
            
            # Create LLM
            llm = ChatOpenAI(
                model=llm_config["model"],
                temperature=llm_config["temperature"],
                openai_api_key=llm_config["api_key"],
                max_tokens=llm_config["max_tokens"]
            )
            
            # Get chatbot context (ahora incluye prompt_templates si existen)
            context = self._get_chatbot_context(chatbot_id)
            
            # Create prompt template
            prompt = ChatPromptTemplate.from_messages([
                ("system", context["system_message"]),
                MessagesPlaceholder(variable_name="history"),
                ("human", "{question}")
            ])
            
            # Create chain
            chain = prompt | llm | StrOutputParser()
            
            # Create message history
            message_history = self._get_or_create_message_history(conversation_id)
            
            # Create runnable with message history
            chain_with_history = RunnableWithMessageHistory(
                chain,
                lambda session_id: message_history,
                input_messages_key="question",
                history_messages_key="history"
            )
            
            # Generate response
            # Para solucionar el problema de formato, evitamos pasar variables especiales
            # y nos aseguramos de que todas las cadenas estén correctamente formateadas
            input_data = {
                "history": message_history.messages,
                "question": message
            }
            
            # Tratamos de arreglar tanto el formato especial como el normal
            if special_format:
                # Con comillas como parte del nombre de la variable
                input_data['"id"'] = str(chatbot_id)
            else:
                # Sin comillas en el nombre de la variable
                input_data["id"] = str(chatbot_id)
            
            response = chain_with_history.invoke(input_data, config)
            
            return response
        except Exception as e:
            print(f"Error detallado en generate_response: {str(e)}")
            # Podemos intentar una respuesta por defecto en caso de error
            return "Lo siento, estoy teniendo problemas para generar una respuesta. Por favor, inténtalo de nuevo más tarde."
    
    def save_message(self, conversation_id: UUID, message: str, is_user: bool = True) -> Dict[str, Any]:
        """
        Save a message to the database
        
        Args:
            conversation_id: The ID of the conversation
            message: The message content
            is_user: Whether the message is from the user (True) or chatbot (False)
            
        Returns:
            The saved message
        """
        try:
            # Get conversation to get lead_id and chatbot_id
            conv_result = supabase.table("conversaciones").select("*").eq("id", str(conversation_id)).limit(1).execute()
            
            if not conv_result.data or len(conv_result.data) == 0:
                raise ValueError(f"Conversation {conversation_id} not found")
            
            conversation = conv_result.data[0]
            
            # Create message
            message_data = {
                "conversacion_id": str(conversation_id),
                "origen": "user" if is_user else "chatbot",
                "remitente_id": str(conversation["lead_id"]) if is_user else str(conversation["chatbot_id"]),
                "contenido": message,
                "tipo_contenido": "text",
                "score_impacto": 1 if is_user else 0
            }
            
            # Save message
            result = supabase.table("mensajes").insert(message_data).execute()
            
            if result.data and len(result.data) > 0:
                # Update message history if exists
                if str(conversation_id) in self.message_histories:
                    if is_user:
                        self.message_histories[str(conversation_id)].add_user_message(message)
                    else:
                        self.message_histories[str(conversation_id)].add_ai_message(message)
                
                return result.data[0]
            
            raise ValueError("Failed to save message")
        except Exception as e:
            print(f"Error saving message: {e}")
            raise

# Create singleton instance
langchain_service = LangChainService()
