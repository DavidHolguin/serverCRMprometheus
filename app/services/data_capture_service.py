from typing import Dict, Any, List, Optional, Tuple
from uuid import UUID
import re

from app.db.supabase_client import supabase
from app.services.event_service import event_service

class DataCaptureService:
    """Servicio para capturar datos personales de mensajes"""
    
    # Chatbot ID específico para captura de datos
    CAPTURE_CHATBOT_ID = "6082011f-53c9-470f-8485-9edfaceb720d"
    
    def __init__(self):
        """Inicializa el servicio de captura de datos"""
        pass
    
    def is_capture_chatbot(self, chatbot_id: str) -> bool:
        """Verifica si el chatbot es el específico para captura de datos"""
        return chatbot_id == self.CAPTURE_CHATBOT_ID
    
    def extract_personal_data(self, message: str) -> Dict[str, Any]:
        """Extrae datos personales de un mensaje o transcripción de audio
        
        Args:
            message: El mensaje del usuario o transcripción de audio
            
        Returns:
            Diccionario con los datos personales extraídos
        """
        data = {}
        
        # Extraer nombre (patrones ampliados para capturar más variaciones)
        nombre_patterns = [
            r'(?:me llamo|soy|nombre[\s:]+es|nombre[\s:]+|se llama|nombre[\s:]*|nombre completo[\s:]*|nombre del interesado[\s:]*|cliente[\s:]*|estudiante[\s:]*|persona[\s:]*|participante[\s:]*|interesado[\s:]*|candidato[\s:]*)\s*([A-Za-zÁáÉéÍíÓóÚúÑñ\s]+)(?:\s|\.|,|$)',
            r'(?:nombre[\s:]*|nombre completo[\s:]*)[\s:]*([A-Za-zÁáÉéÍíÓóÚúÑñ\s]+)(?:\s|\.|,|$)',
            r'(?:^|\s)([A-Za-zÁáÉéÍíÓóÚúÑñ]{2,}\s+[A-Za-zÁáÉéÍíÓóÚúÑñ]{2,}(?:\s+[A-Za-zÁáÉéÍíÓóÚúÑñ]{2,})?)(?:\s|\.|,|$)'
        ]
        
        for pattern in nombre_patterns:
            nombre_match = re.search(pattern, message, re.IGNORECASE)
            if nombre_match:
                nombre = nombre_match.group(1).strip()
                # Limpiar el nombre (eliminar palabras clave que puedan haberse capturado)
                nombre = re.sub(r'(?:correo|email|mail|arroba|@|teléfono|celular|móvil|programa|curso|interesad[oa]|quiere|quiero).*$', '', nombre, flags=re.IGNORECASE).strip()
                if len(nombre) > 3:  # Asegurar que el nombre tenga al menos 3 caracteres
                    data['nombre'] = nombre
                    break
        
        # Extraer correo electrónico (mejorado para capturar más formatos)
        email_patterns = [
            r'[\w._%+-]+@[\w.-]+\.[a-zA-Z]{2,}',
            r'(?:correo|email|mail|e-mail|correo electrónico)[\s:]*([\w._%+-]+@[\w.-]+\.[a-zA-Z]{2,})',
            r'(?:arroba|@)[\s:]*([\w._%+-]+(?:@|arroba)[\w.-]+\.[a-zA-Z]{2,})'
        ]
        
        for pattern in email_patterns:
            email_match = re.search(pattern, message, re.IGNORECASE)
            if email_match:
                email = email_match.group(1) if '@' in email_match.group(1) else email_match.group(0)
                # Limpiar y normalizar el correo
                email = email.lower().replace('arroba', '@').strip()
                data['email'] = email
                break
        
        # Extraer número de teléfono (varios formatos)
        phone_patterns = [
            r'(?:teléfono|celular|móvil|número|contacto|tel|cel)[\s:]*(?:\+?\d{1,3}[\s-]?)?(?:\(\d{1,4}\)[\s-]?)?\d{6,10}',
            r'(?:teléfono|celular|móvil|número|contacto|tel|cel)[\s:]*\d{3}[\s.-]?\d{3}[\s.-]?\d{4}',
            r'\b(?:\+?\d{1,3}[\s-]?)?(?:\(\d{1,4}\)[\s-]?)?\d{6,10}\b',  # Formato internacional
            r'\b\d{10}\b',  # 10 dígitos sin separadores
            r'\b\d{3}[\s.-]?\d{3}[\s.-]?\d{4}\b',  # Formato XXX-XXX-XXXX
        ]
        
        for pattern in phone_patterns:
            phone_match = re.search(pattern, message, re.IGNORECASE)
            if phone_match:
                # Extraer solo los dígitos del teléfono
                phone_text = phone_match.group(0)
                phone = re.sub(r'[^0-9]', '', phone_text)
                # Verificar que sea un número válido (al menos 7 dígitos)
                if len(phone) >= 7:
                    data['telefono'] = phone
                    break
        
        # Extraer programa de interés (patrones ampliados)
        program_patterns = [
            r'(?:interesad[oa] en|quiero|me interesa|programa|curso|carrera|estudiar|aprender|formación|capacitación|especialización|maestría|diplomado|seminario|taller)[\s:]+([A-Za-zÁáÉéÍíÓóÚúÑñ\s]+)(?:\s|\.|,|$)',
            r'(?:programa de interés|programa académico|área de interés)[\s:]*([A-Za-zÁáÉéÍíÓóÚúÑñ\s]+)(?:\s|\.|,|$)',
            r'(?:quiere estudiar|va a estudiar|le interesa)[\s:]*([A-Za-zÁáÉéÍíÓóÚúÑñ\s]+)(?:\s|\.|,|$)'
        ]
        
        for pattern in program_patterns:
            program_match = re.search(pattern, message, re.IGNORECASE)
            if program_match:
                programa = program_match.group(1).strip()
                # Limpiar el programa (eliminar palabras clave que puedan haberse capturado)
                programa = re.sub(r'(?:correo|email|mail|arroba|@|teléfono|celular|móvil).*$', '', programa, flags=re.IGNORECASE).strip()
                if len(programa) > 2:  # Asegurar que el programa tenga al menos 3 caracteres
                    data['programa_interes'] = programa
                    break
        
        return data
    
    def store_personal_data(self, lead_id: UUID, data: Dict[str, Any]) -> bool:
        """Almacena los datos personales en la base de datos
        
        Args:
            lead_id: ID del lead
            data: Datos personales a almacenar
            
        Returns:
            True si se almacenaron correctamente, False en caso contrario
        """
        from app.services.conversation_service import ConversationService
        
        try:
            # Asegurar que el lead existe primero
            conv_service = ConversationService()
            lead = supabase.table("leads").select("empresa_id,canal_id").eq("id", str(lead_id)).execute().data
            
            if not lead:
                # Crear lead básico si no existe
                chatbot_result = supabase.table("chatbots").select("empresa_id, canal_id").eq("id", self.CAPTURE_CHATBOT_ID).execute()
                
                if chatbot_result.data:
                    empresa_id = chatbot_result.data[0]['empresa_id']
                    canal_id = chatbot_result.data[0]['canal_id']
                    
                    lead = conv_service.get_or_create_lead(
                        empresa_id=UUID(empresa_id),
                        canal_id=UUID(canal_id),
                        nombre=data.get('nombre', 'Lead desde captura')
                    )
                else:
                    raise ValueError("Chatbot de captura no encontrado")
                lead_id = UUID(lead["id"])
            
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
        from app.services.conversation_service import ConversationService
        
        # Asegurar que el lead existe antes de confirmar
        conversation_service = ConversationService()
        try:
            # Verificar si el lead existe
            lead = supabase.table("leads").select("*").eq("id", str(lead_id)).execute().data
            if not lead:
                # Crear lead básico si no existe
                # Obtener empresa_id y canal_id del chatbot de captura
                chatbot_result = supabase.table("chatbots").select("empresa_id, canal_id").eq("id", self.CAPTURE_CHATBOT_ID).execute()
                
                if chatbot_result.data:
                    empresa_id = chatbot_result.data[0]['empresa_id']
                    canal_id = chatbot_result.data[0]['canal_id']
                    
                    lead = conversation_service.get_or_create_lead(
                        empresa_id=UUID(empresa_id),
                        canal_id=UUID(canal_id),
                        nombre="Cliente potencial"
                    )
                else:
                    raise ValueError("Chatbot de captura no encontrado")
                lead_id = UUID(lead["id"])
        except Exception as e:
            print(f"Error al verificar lead: {e}")
            return False, "Ocurrió un error al verificar tus datos"

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
                    # Obtener empresa_id del lead o del chatbot
                    lead_info = supabase.table("leads").select("empresa_id").eq("id", str(lead_id)).execute().data
                    
                    if lead_info and lead_info[0].get('empresa_id'):
                        empresa_id = lead_info[0]['empresa_id']
                    else:
                        # Si no hay empresa_id en el lead, obtenerlo del chatbot
                        chatbot_result = supabase.table("chatbots").select("empresa_id").eq("id", self.CAPTURE_CHATBOT_ID).execute()
                        if chatbot_result.data:
                            empresa_id = chatbot_result.data[0]['empresa_id']
                        else:
                            raise ValueError("No se pudo obtener empresa_id")
                    
                    # Actualizar estado del lead
                    supabase.table("leads").update({"estado": "confirmado"}).eq("id", str(lead_id)).execute()
                    
                    # Registrar evento de confirmación
                    event_service.log_event(
                        empresa_id=UUID(empresa_id),
                        event_type=event_service.EVENT_LEAD_CONFIRMED,
                        entidad_origen_tipo="lead",
                        entidad_origen_id=lead_id,
                        lead_id=lead_id,
                        resultado="success",
                        detalle="Lead confirmado mediante chatbot de captura"
                    )
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

    def process_capture_message(self, message: str, lead_id: Optional[UUID] = None, chatbot_id: Optional[str] = None) -> Dict[str, Any]:
        """Procesa un mensaje específicamente para el chatbot de captura de datos
        
        Args:
            message: Mensaje del usuario (puede ser transcripción de audio)
            lead_id: ID del lead si ya existe
            chatbot_id: ID del chatbot que recibió el mensaje
            
        Returns:
            Diccionario con la respuesta y el ID del lead
        """
        # Verificar si es el chatbot de captura
        if chatbot_id and not self.is_capture_chatbot(chatbot_id):
            return {"response": "Este no es un chatbot de captura de datos", "lead_id": lead_id}
        
        # Extraer datos personales del mensaje
        data = self.extract_personal_data(message)
        
        # Si no hay lead_id, crear uno nuevo con los datos disponibles
        if not lead_id:
            from app.services.conversation_service import ConversationService
            conv_service = ConversationService()
            
            # Obtener empresa_id y canal_id del chatbot de captura
            chatbot_result = supabase.table("chatbots").select("empresa_id, canal_id").eq("id", self.CAPTURE_CHATBOT_ID).execute()
            
            if not chatbot_result.data:
                return {"response": "Error: No se pudo encontrar el chatbot de captura", "lead_id": None}
            
            empresa_id = chatbot_result.data[0]['empresa_id']
            canal_id = chatbot_result.data[0]['canal_id']
            
            # Crear lead con los datos disponibles
            lead = conv_service.get_or_create_lead(
                empresa_id=UUID(empresa_id),
                canal_id=UUID(canal_id),
                nombre=data.get('nombre', 'Lead desde captura')
            )
            
            lead_id = UUID(lead["id"])
        
        # Almacenar los datos personales extraídos
        if data:
            self.store_personal_data(lead_id, data)
        
        # Generar respuesta basada en los datos capturados
        response = self.generate_data_capture_response(lead_id, data, message)
        
        return {
            "response": response,
            "lead_id": lead_id,
            "data": data
        }

# Crear instancia del servicio
data_capture_service = DataCaptureService()