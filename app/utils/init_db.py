import os
import sys
import uuid
from datetime import datetime

# Add parent directory to path to import app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.db.supabase_client import supabase
from app.utils.helpers import logger

def create_test_channels():
    """Create test channels if they don't exist"""
    channels = [
        {
            "nombre": "Web Chat",
            "tipo": "web",
            "descripcion": "Canal de chat web integrado",
            "logo_url": "https://example.com/logos/web.png",
            "configuracion_requerida": {"api_key": True, "webhook_url": True},
            "is_active": True
        },
        {
            "nombre": "WhatsApp",
            "tipo": "whatsapp",
            "descripcion": "Canal de WhatsApp",
            "logo_url": "https://example.com/logos/whatsapp.png",
            "configuracion_requerida": {"api_key": True, "phone_number": True, "webhook_url": True},
            "is_active": True
        },
        {
            "nombre": "Facebook Messenger",
            "tipo": "messenger",
            "descripcion": "Canal de Facebook Messenger",
            "logo_url": "https://example.com/logos/messenger.png",
            "configuracion_requerida": {"page_id": True, "access_token": True, "webhook_url": True, "verify_token": True},
            "is_active": True
        },
        {
            "nombre": "Telegram",
            "tipo": "telegram",
            "descripcion": "Canal de Telegram",
            "logo_url": "https://example.com/logos/telegram.png",
            "configuracion_requerida": {"bot_token": True, "webhook_url": True},
            "is_active": True
        },
        {
            "nombre": "Instagram",
            "tipo": "instagram",
            "descripcion": "Canal de Instagram Direct",
            "logo_url": "https://example.com/logos/instagram.png",
            "configuracion_requerida": {"access_token": True, "webhook_url": True},
            "is_active": True
        }
    ]
    
    for channel in channels:
        # Check if channel exists
        result = supabase.table("canales").select("*").eq("tipo", channel["tipo"]).execute()
        
        if not result.data or len(result.data) == 0:
            # Create channel
            logger.info(f"Creating channel: {channel['nombre']}")
            supabase.table("canales").insert(channel).execute()
        else:
            logger.info(f"Channel already exists: {channel['nombre']}")

def create_test_empresa():
    """Create a test company if it doesn't exist"""
    # Check if test company exists
    result = supabase.table("empresas").select("*").eq("nombre", "Empresa de Prueba").execute()
    
    if not result.data or len(result.data) == 0:
        # Create company
        empresa = {
            "nombre": "Empresa de Prueba",
            "descripcion": "Empresa para pruebas del servidor de mensajes",
            "logo_url": "https://example.com/logos/test_company.png",
            "sitio_web": "https://example.com",
            "telefono": "+1234567890",
            "email": "info@example.com",
            "direccion": "123 Test St",
            "ciudad": "Test City",
            "pais": "Test Country",
            "codigo_postal": "12345",
            "configuracion": {},
            "is_active": True,
            "onboarding_completed": True
        }
        
        logger.info("Creating test company")
        result = supabase.table("empresas").insert(empresa).execute()
        
        if result.data and len(result.data) > 0:
            return result.data[0]["id"]
        else:
            logger.error("Failed to create test company")
            return None
    else:
        logger.info("Test company already exists")
        return result.data[0]["id"]

def create_test_llm_config(empresa_id):
    """Create a test LLM configuration if it doesn't exist"""
    # Check if LLM config exists for the company
    result = supabase.table("llm_configuraciones").select("*").eq("empresa_id", empresa_id).execute()
    
    if not result.data or len(result.data) == 0:
        # Create LLM config
        llm_config = {
            "empresa_id": empresa_id,
            "nombre": "Configuración OpenAI",
            "proveedor": "openai",
            "modelo": "gpt-4",
            "configuracion": {
                "temperature": 0.7,
                "max_tokens": 500,
                "top_p": 1.0
            },
            "api_key": os.environ.get("OPENAI_API_KEY", ""),
            "is_default": True,
            "is_active": True
        }
        
        logger.info("Creating test LLM configuration")
        supabase.table("llm_configuraciones").insert(llm_config).execute()
    else:
        logger.info("LLM configuration already exists")

def create_test_chatbot(empresa_id):
    """Create a test chatbot if it doesn't exist"""
    # Check if chatbot exists for the company
    result = supabase.table("chatbots").select("*").eq("empresa_id", empresa_id).eq("nombre", "Chatbot de Prueba").execute()
    
    if not result.data or len(result.data) == 0:
        # Create chatbot
        chatbot = {
            "empresa_id": empresa_id,
            "nombre": "Chatbot de Prueba",
            "descripcion": "Chatbot para pruebas del servidor de mensajes",
            "avatar_url": "https://example.com/avatars/test_bot.png",
            "tono": "Amigable y profesional",
            "personalidad": "Servicial y eficiente",
            "instrucciones": "Responder preguntas sobre la empresa y sus productos",
            "contexto": "Esta es una empresa de prueba para el servidor de mensajes",
            "configuracion": {
                "welcome_message": "¡Hola! Soy el chatbot de prueba. ¿En qué puedo ayudarte?",
                "fallback_message": "Lo siento, no entendí tu pregunta. ¿Podrías reformularla?"
            },
            "is_active": True
        }
        
        logger.info("Creating test chatbot")
        result = supabase.table("chatbots").insert(chatbot).execute()
        
        if result.data and len(result.data) > 0:
            chatbot_id = result.data[0]["id"]
            
            # Create chatbot context
            context = {
                "chatbot_id": chatbot_id,
                "tipo": "general",
                "orden": 0,
                "contenido": "Esta es una empresa de prueba para el servidor de mensajes. Ofrecemos productos y servicios de alta calidad.",
                "welcome_message": "¡Hola! Soy el chatbot de prueba. ¿En qué puedo ayudarte?",
                "personality": "Soy un asistente amigable y profesional, siempre dispuesto a ayudar.",
                "general_context": "Esta es una empresa de prueba para el servidor de mensajes. Ofrecemos productos y servicios de alta calidad.",
                "communication_tone": "Amigable, profesional y claro.",
                "main_purpose": "Ayudar a los usuarios a resolver sus dudas sobre la empresa y sus productos.",
                "key_points": ["Somos una empresa líder en el mercado", "Ofrecemos productos de alta calidad", "Nuestro servicio al cliente es excelente"],
                "special_instructions": "Si el usuario pregunta por precios específicos, pedir que contacte con ventas."
            }
            
            logger.info("Creating test chatbot context")
            supabase.table("chatbot_contextos").insert(context).execute()
            
            # Create chatbot channel configurations
            channels_result = supabase.table("canales").select("*").eq("is_active", True).execute()
            
            if channels_result.data:
                for channel in channels_result.data:
                    channel_config = {
                        "chatbot_id": chatbot_id,
                        "canal_id": channel["id"],
                        "configuracion": {
                            "is_enabled": True,
                            "welcome_message": f"¡Hola! Soy el chatbot de prueba en {channel['nombre']}. ¿En qué puedo ayudarte?"
                        },
                        "webhook_url": f"https://example.com/webhook/{channel['tipo']}/{uuid.uuid4()}",
                        "webhook_secret": str(uuid.uuid4()),
                        "is_active": True
                    }
                    
                    logger.info(f"Creating test chatbot channel config for {channel['nombre']}")
                    supabase.table("chatbot_canales").insert(channel_config).execute()
            
            # Create company FAQs
            faqs = [
                {
                    "empresa_id": empresa_id,
                    "pregunta": "¿Cuáles son los horarios de atención?",
                    "respuesta": "Nuestros horarios de atención son de lunes a viernes de 9:00 a 18:00 horas.",
                    "orden": 0
                },
                {
                    "empresa_id": empresa_id,
                    "pregunta": "¿Cómo puedo contactar con ventas?",
                    "respuesta": "Puede contactar con nuestro departamento de ventas a través del correo ventas@example.com o llamando al +1234567890.",
                    "orden": 1
                },
                {
                    "empresa_id": empresa_id,
                    "pregunta": "¿Cuál es la política de devoluciones?",
                    "respuesta": "Nuestra política de devoluciones permite devolver productos en un plazo de 30 días desde la compra, siempre que estén en perfecto estado.",
                    "orden": 2
                }
            ]
            
            for faq in faqs:
                logger.info(f"Creating FAQ: {faq['pregunta']}")
                supabase.table("empresa_faqs").insert(faq).execute()
            
            # Create company products
            products = [
                {
                    "empresa_id": empresa_id,
                    "nombre": "Producto A",
                    "descripcion": "Descripción del Producto A",
                    "caracteristicas": ["Característica 1", "Característica 2", "Característica 3"],
                    "precio": 99.99,
                    "imagen_url": "https://example.com/products/a.png",
                    "orden": 0,
                    "is_active": True
                },
                {
                    "empresa_id": empresa_id,
                    "nombre": "Producto B",
                    "descripcion": "Descripción del Producto B",
                    "caracteristicas": ["Característica 1", "Característica 2", "Característica 3"],
                    "precio": 149.99,
                    "imagen_url": "https://example.com/products/b.png",
                    "orden": 1,
                    "is_active": True
                },
                {
                    "empresa_id": empresa_id,
                    "nombre": "Producto C",
                    "descripcion": "Descripción del Producto C",
                    "caracteristicas": ["Característica 1", "Característica 2", "Característica 3"],
                    "precio": 199.99,
                    "imagen_url": "https://example.com/products/c.png",
                    "orden": 2,
                    "is_active": True
                }
            ]
            
            for product in products:
                logger.info(f"Creating product: {product['nombre']}")
                supabase.table("empresa_productos").insert(product).execute()
            
            return chatbot_id
        else:
            logger.error("Failed to create test chatbot")
            return None
    else:
        logger.info("Test chatbot already exists")
        return result.data[0]["id"]

def main():
    """Initialize the database with test data"""
    logger.info("Initializing database with test data")
    
    # Create test channels
    create_test_channels()
    
    # Create test company
    empresa_id = create_test_empresa()
    
    if empresa_id:
        # Create test LLM configuration
        create_test_llm_config(empresa_id)
        
        # Create test chatbot
        chatbot_id = create_test_chatbot(empresa_id)
        
        if chatbot_id:
            logger.info(f"Test data initialized successfully. Empresa ID: {empresa_id}, Chatbot ID: {chatbot_id}")
            
            # Print example curl command for testing
            print("\nExample curl command for testing the API:")
            print(f"""
curl -X POST http://localhost:8000/api/v1/message \\
  -H "Content-Type: application/json" \\
  -d '{{"canal_id": "<CANAL_ID>", "canal_identificador": "test_user", "empresa_id": "{empresa_id}", "chatbot_id": "{chatbot_id}", "mensaje": "Hola, ¿cómo estás?"}}'
            """)
        else:
            logger.error("Failed to initialize test data")
    else:
        logger.error("Failed to initialize test data")

if __name__ == "__main__":
    main()
