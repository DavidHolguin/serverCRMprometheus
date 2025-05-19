from typing import Dict, Any, List, Optional, Tuple
from uuid import UUID
import re

from app.db.supabase_client import supabase
from app.services.event_service import event_service

class DataCaptureService:
    """Servicio para capturar datos personales de mensajes"""
    
    # Chatbot ID específico para captura de datos
    CAPTURE_CHATBOT_ID = "c5fdb8dc-38cb-425a-b760-3ca6c4a32621"
    
    def __init__(self):
        """Inicializa el servicio de captura de datos"""
        pass
    
    def is_capture_chatbot(self, chatbot_id: str) -> bool:
        """Verifica si el chatbot es el específico para captura de datos"""
        return chatbot_id == self.CAPTURE_CHATBOT_ID
    
    def extract_personal_data(self, message: str) -> Dict[str, Any]:
        """Extrae datos personales de un mensaje
        
        Args:
            message: El mensaje del usuario
            
        Returns:
            Diccionario con los datos personales extraídos
        """
        data = {}
        
        # Extraer nombre
        nombre_match = re.search(r'(?:me llamo|soy|nombre[\s:]+es|nombre[\s:]+)\s*([A-Za-zÁáÉéÍíÓóÚúÑñ\s]+)(?:\s|\.|,|$)', message, re.IGNORECASE)
        if nombre_match:
            data['nombre'] = nombre_match.group(1).strip()
        
        # Extraer correo electrónico
        email_match = re.search(r'[\w._%+-]+@[\w.-]+\.[a-zA-Z]{2,}', message)
        if email_match:
            data['email'] = email_match.group(0)
        
        # Extraer número de teléfono (varios formatos)
        phone_patterns = [
            r'\b(?:\+?\d{1,3}[\s-]?)?(?:\(\d{1,4}\)[\s-]?)?\d{6,10}\b',  # Formato internacional
            r'\b\d{10}\b',  # 10 dígitos sin separadores
            r'\b\d{3}[\s-]?\d{3}[\s-]?\d{4}\b',  # Formato XXX-XXX-XXXX
        ]
        
        for pattern in phone_patterns:
            phone_match = re.search(pattern, message)
            if phone_match:
                # Limpiar el número de teléfono (eliminar espacios, guiones, etc.)
                phone = re.sub(r'[\s()-]', '', phone_match.group(0))
                data['telefono'] = phone
                break
        
        # Extraer programa de interés
        program_match = re.search(r'(?:interesad[oa] en|quiero|me interesa|programa|curso)[\s:]+([A-Za-zÁáÉéÍíÓóÚúÑñ\s]+)(?:\s|\.|,|$)', message, re.IGNORECASE)
        if program_match:
            data['programa_interes'] = program_match.group(1).strip()
        
        return data
    
    def store_personal_data(self, lead_id: UUID, data: Dict[str, Any]) -> bool:
        """Almacena los datos personales en la base de datos
        
        Args:
            lead_id: ID del lead
            data: Datos personales a almacenar
            
        Returns:
            True si se almacenaron correctamente, False en caso contrario
        """
        try:
            # Verificar si ya existen datos para este lead
            result = supabase.table("lead_datos_personales").select("*").eq("lead_id", str(lead_id)).execute()
            
            if result.data and len(result.data) > 0:
                # Actualizar datos existentes
                update_data = {k: v for k, v in data.items() if v is not None and v != ""}
                if update_data:
                    supabase.table("lead_datos_personales").update(update_data).eq("lead_id", str(lead_id)).execute()
            else:
                # Insertar nuevos datos
                insert_data = {"lead_id": str(lead_id), **data}
                supabase.table("lead_datos_personales").insert(insert_data).execute()
            
            return True
        except Exception as e:
            print(f"Error al almacenar datos personales: {e}")
            return False
    
    def generate_data_capture_response(self, lead_id: UUID, data: Dict[str, Any], message: str) -> str:
        """Genera una respuesta basada en los datos capturados
        
        Args:
            lead_id: ID del lead
            data: Datos personales capturados
            message: Mensaje original del usuario
            
        Returns:
            Respuesta generada
        """
        # Verificar qué datos faltan
        missing_data = []
        if 'nombre' not in data or not data['nombre']:
            missing_data.append("nombre")
        if 'email' not in data or not data['email']:
            missing_data.append("correo electrónico")
        if 'telefono' not in data or not data['telefono']:
            missing_data.append("número de teléfono")
        if 'programa_interes' not in data or not data['programa_interes']:
            missing_data.append("programa de interés")
        
        # Si hay datos capturados, mostrarlos y preguntar si son correctos
        if data:
            response = "He capturado los siguientes datos:\n"
            if 'nombre' in data and data['nombre']:
                response += f"- Nombre: {data['nombre']}\n"
            if 'email' in data and data['email']:
                response += f"- Correo electrónico: {data['email']}\n"
            if 'telefono' in data and data['telefono']:
                response += f"- Teléfono: {data['telefono']}\n"
            if 'programa_interes' in data and data['programa_interes']:
                response += f"- Programa de interés: {data['programa_interes']}\n"
            
            if missing_data:
                response += "\nAún necesito los siguientes datos:\n"
                for item in missing_data:
                    response += f"- Tu {item}\n"
                response += "\n¿Podrías proporcionarme esta información?"
            else:
                response += "\n¿Son correctos estos datos? Si hay algún error, por favor indícame cuál dato debo corregir."
        else:
            # Si no se capturó ningún dato, solicitar información
            response = "Hola, soy un asistente para registrar tus datos. Por favor, proporcióname la siguiente información:\n\n"
            response += "- Tu nombre completo\n"
            response += "- Tu correo electrónico\n"
            response += "- Tu número de teléfono\n"
            response += "- El programa en el que estás interesado/a\n"
        
        return response
    
    def process_confirmation(self, message: str, lead_id: UUID) -> Tuple[bool, str]:
        """Procesa un mensaje de confirmación o corrección de datos
        
        Args:
            message: Mensaje del usuario
            lead_id: ID del lead
            
        Returns:
            Tupla con (es_confirmacion, respuesta)
        """
        # Patrones para detectar confirmación
        confirmation_patterns = [
            r'\b(s[ií]|correcto|exacto|est[áa] bien|perfecto)\b',
            r'\best[áa]n? bien\b',
            r'\bconfirm[oa]\b'
        ]
        
        # Patrones para detectar negación
        negation_patterns = [
            r'\b(no|incorrecto|error|equivocad[oa])\b',
            r'\bno est[áa]n? bien\b',
            r'\best[áa]n? mal\b'
        ]
        
        # Verificar si es una confirmación
        for pattern in confirmation_patterns:
            if re.search(pattern, message, re.IGNORECASE):
                # Marcar el lead como confirmado
                try:
                    supabase.table("leads").update({"estado": "confirmado"}).eq("id", str(lead_id)).execute()
                    return True, "¡Gracias por confirmar tus datos! Han sido registrados correctamente. Pronto nos pondremos en contacto contigo."
                except Exception as e:
                    print(f"Error al actualizar estado del lead: {e}")
                    return True, "Gracias por confirmar tus datos. Han sido registrados, pero hubo un problema al actualizar tu estado. No te preocupes, igualmente nos pondremos en contacto contigo."
        
        # Verificar si es una negación
        for pattern in negation_patterns:
            if re.search(pattern, message, re.IGNORECASE):
                # Extraer datos corregidos
                corrected_data = self.extract_personal_data(message)
                if corrected_data:
                    # Actualizar solo los datos proporcionados
                    self.store_personal_data(lead_id, corrected_data)
                    return False, "He actualizado los datos que me has proporcionado. ¿Podrías confirmar si ahora están correctos?"
                else:
                    return False, "Entiendo que hay un error en tus datos. ¿Podrías indicarme específicamente qué dato necesita ser corregido?"
        
        # Si no es confirmación ni negación, intentar extraer datos
        new_data = self.extract_personal_data(message)
        if new_data:
            self.store_personal_data(lead_id, new_data)
            return False, "He actualizado tu información con los nuevos datos proporcionados. ¿Podrías confirmar si ahora están correctos?"
        
        # Si no se detecta nada específico
        return False, "No he podido determinar si los datos son correctos. Por favor, responde 'sí' si los datos son correctos, o indícame específicamente qué dato necesita ser corregido."

# Crear instancia del servicio
data_capture_service = DataCaptureService()