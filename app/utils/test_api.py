import os
import sys
import requests
import json
import uuid
from datetime import datetime

# Add parent directory to path to import app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.db.supabase_client import supabase
from app.utils.helpers import logger

def get_test_data():
    """Get test data from the database"""
    # Get web channel ID
    channel_result = supabase.table("canales").select("id").eq("tipo", "web").limit(1).execute()
    
    if not channel_result.data or len(channel_result.data) == 0:
        logger.error("Web channel not found")
        return None
    
    canal_id = channel_result.data[0]["id"]
    
    # Get test company
    empresa_result = supabase.table("empresas").select("id").eq("nombre", "Empresa de Prueba").limit(1).execute()
    
    if not empresa_result.data or len(empresa_result.data) == 0:
        logger.error("Test company not found")
        return None
    
    empresa_id = empresa_result.data[0]["id"]
    
    # Get test chatbot
    chatbot_result = supabase.table("chatbots").select("id").eq("empresa_id", empresa_id).eq("nombre", "Chatbot de Prueba").limit(1).execute()
    
    if not chatbot_result.data or len(chatbot_result.data) == 0:
        logger.error("Test chatbot not found")
        return None
    
    chatbot_id = chatbot_result.data[0]["id"]
    
    return {
        "canal_id": canal_id,
        "empresa_id": empresa_id,
        "chatbot_id": chatbot_id
    }

def test_message_api():
    """Test the message API endpoint"""
    test_data = get_test_data()
    
    if not test_data:
        logger.error("Failed to get test data")
        return
    
    # Test message API
    url = "http://localhost:8000/api/v1/message"
    
    payload = {
        "canal_id": test_data["canal_id"],
        "canal_identificador": f"test_user_{uuid.uuid4()}",
        "empresa_id": test_data["empresa_id"],
        "chatbot_id": test_data["chatbot_id"],
        "mensaje": "Hola, ¿cómo estás?",
        "metadata": {
            "nombre": "Usuario de Prueba",
            "email": "test@example.com",
            "phone": "+1234567890"
        }
    }
    
    headers = {
        "Content-Type": "application/json"
    }
    
    try:
        logger.info(f"Sending test message to {url}")
        response = requests.post(url, headers=headers, json=payload)
        
        if response.status_code == 200:
            logger.info("Test message sent successfully")
            logger.info(f"Response: {response.json()}")
            
            # Test conversation history API
            conversation_id = response.json()["conversacion_id"]
            history_url = f"http://localhost:8000/api/v1/conversation/{conversation_id}/history"
            
            logger.info(f"Getting conversation history from {history_url}")
            history_response = requests.get(history_url)
            
            if history_response.status_code == 200:
                logger.info("Conversation history retrieved successfully")
                logger.info(f"History: {history_response.json()}")
            else:
                logger.error(f"Failed to get conversation history: {history_response.status_code} - {history_response.text}")
        else:
            logger.error(f"Failed to send test message: {response.status_code} - {response.text}")
    except Exception as e:
        logger.error(f"Error testing message API: {e}")

def test_web_channel_api():
    """Test the web channel API endpoint"""
    test_data = get_test_data()
    
    if not test_data:
        logger.error("Failed to get test data")
        return
    
    # Test web channel API
    url = "http://localhost:8000/api/v1/channels/web"
    
    payload = {
        "empresa_id": test_data["empresa_id"],
        "chatbot_id": test_data["chatbot_id"],
        "mensaje": "Hola, estoy interesado en sus productos",
        "session_id": f"web_session_{uuid.uuid4()}",
        "metadata": {
            "nombre": "Usuario Web",
            "email": "web@example.com",
            "referrer": "https://example.com/products"
        }
    }
    
    headers = {
        "Content-Type": "application/json"
    }
    
    try:
        logger.info(f"Sending test web message to {url}")
        response = requests.post(url, headers=headers, json=payload)
        
        if response.status_code == 200:
            logger.info("Test web message sent successfully")
            logger.info(f"Response: {response.json()}")
        else:
            logger.error(f"Failed to send test web message: {response.status_code} - {response.text}")
    except Exception as e:
        logger.error(f"Error testing web channel API: {e}")

def main():
    """Run API tests"""
    logger.info("Running API tests")
    
    # Test message API
    test_message_api()
    
    # Test web channel API
    test_web_channel_api()

if __name__ == "__main__":
    main()
