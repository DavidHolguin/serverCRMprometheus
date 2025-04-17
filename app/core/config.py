import os
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Settings(BaseModel):
    # API Settings
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "CRM Messaging Server"
    DEBUG: bool = Field(default_factory=lambda: os.getenv("DEBUG", "False").lower() == "true")
    
    # Server Settings
    SERVER_HOST: str = Field(default_factory=lambda: os.getenv("SERVER_HOST", "0.0.0.0"))
    SERVER_PORT: int = Field(default_factory=lambda: int(os.getenv("SERVER_PORT", "8000")))
    
    # Supabase Settings
    SUPABASE_URL: str = Field(default_factory=lambda: os.getenv("SUPABASE_URL", ""))
    SUPABASE_KEY: str = Field(default_factory=lambda: os.getenv("SUPABASE_KEY", ""))
    
    # OpenAI Settings
    OPENAI_API_KEY: str = Field(default_factory=lambda: os.getenv("OPENAI_API_KEY", ""))
    
    # LangChain Settings
    LANGCHAIN_TRACING_V2: bool = Field(default_factory=lambda: os.getenv("LANGCHAIN_TRACING_V2", "False").lower() == "true")
    LANGCHAIN_ENDPOINT: Optional[str] = Field(default_factory=lambda: os.getenv("LANGCHAIN_ENDPOINT", None))
    LANGCHAIN_API_KEY: Optional[str] = Field(default_factory=lambda: os.getenv("LANGCHAIN_API_KEY", None))
    LANGCHAIN_PROJECT: Optional[str] = Field(default_factory=lambda: os.getenv("LANGCHAIN_PROJECT", None))
    
    # WhatsApp Settings
    WHATSAPP_VERIFY_TOKEN: str = Field(default_factory=lambda: os.getenv("WHATSAPP_VERIFY_TOKEN", "DEFAULT_FALLBACK_TOKEN"))
    WHATSAPP_ACCESS_TOKEN: str = Field(default_factory=lambda: os.getenv("WHATSAPP_ACCESS_TOKEN", ""))
    WHATSAPP_PHONE_NUMBER_ID: str = Field(default_factory=lambda: os.getenv("WHATSAPP_PHONE_NUMBER_ID", ""))
    WHATSAPP_API_VERSION: str = Field(default_factory=lambda: os.getenv("WHATSAPP_API_VERSION", "v17.0"))
    WHATSAPP_BUSINESS_PHONE: str = Field(default_factory=lambda: os.getenv("WHATSAPP_BUSINESS_PHONE", ""))
    WHATSAPP_WABA_ID: str = Field(default_factory=lambda: os.getenv("WHATSAPP_WABA_ID", ""))
    
    # Default LLM Settings
    DEFAULT_MODEL: str = "gpt-4o-mini"
    DEFAULT_TEMPERATURE: float = 0.4
    DEFAULT_MAX_TOKENS: int = 500
    
    # Message Settings
    MAX_HISTORY_LENGTH: int = 10
    
    model_config = {"case_sensitive": True}

settings = Settings()
