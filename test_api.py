import requests
import json
import sys

def test_message_api():
    url = "http://localhost:8000/api/v1/message"
    
    payload = {
        "canal_id": "6810131f-86a6-4455-97e5-b6c4879f5a49",
        "canal_identificador": "2fc29382-92ef-4824-8f97-74f5fb0c87a1",
        "empresa_id": "4ccc4539-5b24-4313-9074-649832a48b68",
        "chatbot_id": "056a7247-c0d6-46c6-a5ef-8bfd2b9d2382",
        "lead_id": "525eb201-e24c-4550-ae65-91d7d309cc69",
        "mensaje": "Hola",
        "metadata": {
            "additionalProp1": {}
        }
    }
    
    headers = {
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_message_api()
