import json
from app.db.supabase_client import supabase

# Datos del contexto del chatbot
context_data = {
    'chatbot_id': '6ac8dbe6-81a7-4733-b28f-306b8b889c04',
    'tipo': 'general',
    'contenido': 'Contexto general del chatbot',
    'orden': 1,
    'welcome_message': 'Hola, ¿en qué puedo ayudarte hoy?',
    'personality': 'Amigable, servicial y profesional',
    'general_context': 'Asistente virtual para responder preguntas y ayudar a los usuarios',
    'communication_tone': 'Formal pero cercano',
    'main_purpose': 'Proporcionar información y asistencia a los usuarios',
    'key_points': json.dumps(['Ser útil', 'Ser claro', 'Ser preciso']),
    'special_instructions': 'Responder de manera concisa y útil'
}

# Verificar si ya existe un contexto para este chatbot
result = supabase.table('chatbot_contextos').select('*').eq('chatbot_id', context_data['chatbot_id']).eq('tipo', 'general').execute()

if result.data and len(result.data) > 0:
    print(f"Ya existe un contexto para el chatbot {context_data['chatbot_id']}")
    print("Actualizando contexto...")
    result = supabase.table('chatbot_contextos').update(context_data).eq('chatbot_id', context_data['chatbot_id']).eq('tipo', 'general').execute()
else:
    print(f"Creando contexto para el chatbot {context_data['chatbot_id']}...")
    result = supabase.table('chatbot_contextos').insert(context_data).execute()

print("Resultado:", result.data)
print("Contexto creado/actualizado con éxito!")
