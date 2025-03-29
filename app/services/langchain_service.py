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
        
        # Construct system message
        system_message = f"""
        # {chatbot['nombre']}
        
        ## Personalidad
        {context['personality']}
        
        ## Contexto general
        {context['general_context']}
        
        ## Tono de comunicación
        {context['communication_tone']}
        
        ## Propósito principal
        {context['main_purpose']}
        
        ## Puntos clave
        {json.dumps(context['key_points'], ensure_ascii=False)}
        
        ## Instrucciones especiales
        {context['special_instructions']}
        
        Responde de manera concisa y útil. Si no sabes la respuesta, admítelo claramente.
        """
        
        return {
            "system_message": system_message,
            "welcome_message": context["welcome_message"]
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
    
    def generate_response(self, conversation_id: UUID, chatbot_id: UUID, empresa_id: UUID, message: str) -> str:
        """
        Generate a response using LangChain and OpenAI
        
        Args:
            conversation_id: The ID of the conversation
            chatbot_id: The ID of the chatbot
            empresa_id: The ID of the company
            message: The user message
            
        Returns:
            Generated response
        """
        # Get LLM configuration
        llm_config = self._get_llm_config(empresa_id)
        
        # Create LLM
        llm = ChatOpenAI(
            model=llm_config["model"],
            temperature=llm_config["temperature"],
            openai_api_key=llm_config["api_key"],
            max_tokens=llm_config["max_tokens"]
        )
        
        # Get chatbot context
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
        response = chain_with_history.invoke(
            {"question": message},
            config={"configurable": {"session_id": str(conversation_id)}}
        )
        
        return response
    
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
