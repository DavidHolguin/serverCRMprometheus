from supabase import create_client, Client
from app.core.config import settings

# Exponer estas variables para que puedan ser importadas por otros módulos
supabase_url = settings.SUPABASE_URL
supabase_key = settings.SUPABASE_KEY

def get_supabase_client() -> Client:
    """
    Create and return a Supabase client instance.
    
    Returns:
        Client: A Supabase client instance
    """
    return create_client(supabase_url, supabase_key)

supabase = get_supabase_client()
