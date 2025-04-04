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
    
    # Default LLM Settings
    DEFAULT_MODEL: str = "gpt-4o-mini"
    DEFAULT_TEMPERATURE: float = 0.4
    DEFAULT_MAX_TOKENS: int = 500
    
    # Message Settings
    MAX_HISTORY_LENGTH: int = 10
    
    model_config = {"case_sensitive": True}

settings = Settings()
