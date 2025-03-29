from typing import Dict, Any

# Examples for API documentation
EXAMPLES = {
    "agent_message": {
        "summary": "Agent message example",
        "description": "Example of a message sent by a human agent to a lead",
        "value": {
            "conversation_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
            "agent_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
            "mensaje": "Hola, soy un agente humano. ¿En qué puedo ayudarte?",
            "deactivate_chatbot": True,
            "metadata": {
                "agent_name": "Juan Pérez",
                "department": "Ventas"
            }
        }
    },
    "toggle_chatbot": {
        "summary": "Toggle chatbot example",
        "description": "Example of toggling chatbot active status",
        "value": {
            "conversation_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
            "chatbot_activo": False
        }
    },
    "web_message": {
        "summary": "Web message example",
        "description": "Example of a message from web channel",
        "value": {
            "empresa_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
            "chatbot_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
            "mensaje": "Hola, necesito información sobre sus productos",
            "session_id": "web-session-123456",
            "lead_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
            "metadata": {
                "browser": "Chrome",
                "page": "/productos"
            }
        }
    },
    "whatsapp_message": {
        "summary": "WhatsApp message example",
        "description": "Example of a message from WhatsApp channel",
        "value": {
            "empresa_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
            "chatbot_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
            "mensaje": "Hola, necesito información sobre sus productos",
            "phone_number": "+573001234567",
            "lead_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
            "metadata": {
                "name": "Cliente WhatsApp",
                "profile_pic": "https://example.com/pic.jpg"
            }
        }
    },
    "messenger_message": {
        "summary": "Messenger message example",
        "description": "Example of a message from Facebook Messenger channel",
        "value": {
            "empresa_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
            "chatbot_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
            "mensaje": "Hola, necesito información sobre sus productos",
            "sender_id": "fb-user-123456",
            "lead_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
            "metadata": {
                "name": "Cliente Facebook",
                "profile_url": "https://facebook.com/user123"
            }
        }
    },
    "telegram_message": {
        "summary": "Telegram message example",
        "description": "Example of a message from Telegram channel",
        "value": {
            "empresa_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
            "chatbot_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
            "mensaje": "Hola, necesito información sobre sus productos",
            "chat_id": "telegram-123456",
            "lead_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
            "metadata": {
                "username": "@cliente_telegram",
                "first_name": "Cliente"
            }
        }
    },
    "instagram_message": {
        "summary": "Instagram message example",
        "description": "Example of a message from Instagram channel",
        "value": {
            "empresa_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
            "chatbot_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
            "mensaje": "Hola, necesito información sobre sus productos",
            "instagram_id": "ig-user-123456",
            "lead_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
            "metadata": {
                "username": "@cliente_instagram",
                "profile_pic": "https://instagram.com/pic.jpg"
            }
        }
    }
}
