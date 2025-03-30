import requests
import json
import sys
import uuid

def test_message_api():
    """Prueba el endpoint de mensajes que crea automáticamente un lead si no existe"""
    url = "http://localhost:8000/api/v1/message"
    
    # Generar un identificador único para el canal
    canal_identificador = str(uuid.uuid4())
    
    payload = {
        "canal_id": "6810131f-86a6-4455-97e5-b6c4879f5a49",
        "canal_identificador": canal_identificador,
        "empresa_id": "4ccc4539-5b24-4313-9074-649832a48b68",
        "chatbot_id": "056a7247-c0d6-46c6-a5ef-8bfd2b9d2382",
        "mensaje": "Hola, estoy interesado en comprar un producto de su empresa. ¿Podría darme más información sobre sus servicios?",
        "metadata": {
            "nombre": "Cliente de Prueba",
            "email": "test@example.com",
            "telefono": "123456789",
            "fuente": "test_api"
        }
    }
    
    headers = {
        "Content-Type": "application/json"
    }
    
    try:
        print("Enviando mensaje para crear un nuevo lead...")
        response = requests.post(url, json=payload, headers=headers)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"Response: {json.dumps(result, indent=2, ensure_ascii=False)}")
            
            # Extraer IDs para referencia
            if "lead_id" in result:
                print(f"\nLead ID creado: {result['lead_id']}")
            if "conversacion_id" in result:
                print(f"Conversación ID: {result['conversacion_id']}")
            if "mensaje_id" in result:
                print(f"Mensaje ID: {result['mensaje_id']}")
        else:
            print(f"Error: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_message_api()
