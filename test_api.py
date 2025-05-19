import requests
import json
import sys
import uuid
import time

def test_message_api():
    """Prueba el endpoint de mensajes con dos mensajes consecutivos para evaluar cambios de tono"""
    url = "http://localhost:8000/api/v1/message"
    
    # Generar un identificador único para el canal
    canal_identificador = str(uuid.uuid4())
    lead_id = None
    conversacion_id = None
    
    # Primer mensaje - positivo
    payload_positive = {
        "canal_id": "6810131f-86a6-4455-97e5-b6c4879f5a49",
        "canal_identificador": canal_identificador,
        "empresa_id": "4ccc4539-5b24-4313-9074-649832a48b68",
        "chatbot_id": "056a7247-c0d6-46c6-a5ef-8bfd2b9d2382",
        "mensaje": "Hola, estoy muy interesado en comprar su producto premium. Estoy listo para hacer la compra hoy mismo.",
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
        print("=== ENVIANDO PRIMER MENSAJE (POSITIVO) ===")
        response = requests.post(url, json=payload_positive, headers=headers)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            lead_id = result.get('lead_id')
            conversacion_id = result.get('conversacion_id')
            
            print(f"\nLead ID: {lead_id}")
            print(f"Conversación ID: {conversacion_id}")
            
            # Obtener la evaluación del primer mensaje
            eval_url = f"http://localhost:8000/api/v1/evaluations/lead-evaluations/{lead_id}"
            eval_response = requests.get(eval_url, headers=headers)
            
            if eval_response.status_code == 200:
                eval_data = eval_response.json()
                print("\n=== EVALUACIÓN DEL PRIMER MENSAJE ===")
                print(json.dumps(eval_data, indent=2, ensure_ascii=False))
                
                # Esperar un momento para que se procese la evaluación
                print("\nEsperando 2 segundos antes de enviar el segundo mensaje...\n")
                time.sleep(2)
                
                # Segundo mensaje - negativo
                payload_negative = {
                    "canal_id": "6810131f-86a6-4455-97e5-b6c4879f5a49",
                    "canal_identificador": canal_identificador,
                    "empresa_id": "4ccc4539-5b24-4313-9074-649832a48b68",
                    "chatbot_id": "056a7247-c0d6-46c6-a5ef-8bfd2b9d2382",
                    "lead_id": lead_id,
                    "mensaje": "Lo siento, acabo de recibir una noticia terrible. Mi madre ha fallecido y no podré continuar con la compra.",
                    "metadata": {
                        "fuente": "test_api"
                    }
                }
                
                print("=== ENVIANDO SEGUNDO MENSAJE (NEGATIVO) ===")
                response2 = requests.post(url, json=payload_negative, headers=headers)
                print(f"Status Code: {response2.status_code}")
                
                if response2.status_code == 200:
                    # Esperar un momento para que se procese la evaluación
                    print("\nEsperando 2 segundos para que se procese la evaluación...\n")
                    time.sleep(2)
                    
                    # Obtener la evaluación actualizada
                    eval_response2 = requests.get(eval_url, headers=headers)
                    
                    if eval_response2.status_code == 200:
                        eval_data2 = eval_response2.json()
                        print("\n=== EVALUACIÓN DESPUÉS DEL SEGUNDO MENSAJE ===")
                        print(json.dumps(eval_data2, indent=2, ensure_ascii=False))
                        
                        # Comparar las evaluaciones
                        if len(eval_data) > 0 and len(eval_data2) > 0 and len(eval_data2) > len(eval_data):
                            primera_eval = eval_data[0] if isinstance(eval_data, list) else eval_data
                            ultima_eval = eval_data2[0] if isinstance(eval_data2, list) else eval_data2
                            
                            if isinstance(eval_data2, list) and len(eval_data2) > 1:
                                ultima_eval = eval_data2[0]  # La más reciente primero
                            
                            print("\n=== COMPARACIÓN DE EVALUACIONES ===")
                            print(f"Primera evaluación - Score Potencial: {primera_eval.get('score_potencial')}")
                            print(f"Última evaluación - Score Potencial: {ultima_eval.get('score_potencial')}")
                            
                            if primera_eval.get('score_potencial', 0) > ultima_eval.get('score_potencial', 0):
                                print("\n✅ ÉXITO: El sistema detectó correctamente el cambio negativo en el potencial del lead")
                            else:
                                print("\n❌ FALLO: El sistema no detectó el cambio negativo en el potencial del lead")
                    else:
                        print(f"Error al obtener la segunda evaluación: {eval_response2.status_code}")
                else:
                    print(f"Error en segundo mensaje: {response2.status_code}")
            else:
                print(f"Error al obtener la primera evaluación: {eval_response.status_code}")
        else:
            print(f"Error en primer mensaje: {response.status_code}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_message_api()
