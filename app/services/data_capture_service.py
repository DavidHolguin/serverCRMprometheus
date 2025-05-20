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
            lead = supabase.table("leads").select("empresa_id,canal_id,estado").eq("id", str(lead_id)).execute().data
            
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
                    
                    # Verificar que el lead se haya creado correctamente
                    if not lead or "id" not in lead:
                        raise ValueError("No se pudo crear el lead correctamente")
                    
                    # Registrar evento de creación de lead
                    event_service.log_event(
                        empresa_id=UUID(empresa_id),
                        event_type=event_service.EVENT_FIRST_INTERACTION,
                        entidad_origen_tipo="chatbot",
                        entidad_origen_id=UUID(self.CAPTURE_CHATBOT_ID),
                        lead_id=UUID(lead["id"]),
                        canal_id=UUID(canal_id),
                        resultado="success",
                        estado_final="nuevo",
                        detalle="Nuevo lead creado desde chatbot de captura de datos"
                    )
                else:
                    raise ValueError("Chatbot de captura no encontrado")
                lead_id = UUID(lead["id"])
            else:
                # Si el lead existe pero está en estado confirmado, actualizar a 'en_proceso'
                if lead[0].get('estado') == "confirmado":
                    supabase.table("leads").update({"estado": "en_proceso"}).eq("id", str(lead_id)).execute()
                    
                    # Registrar evento de actualización de estado
                    event_service.log_event(
                        empresa_id=UUID(lead[0]['empresa_id']),
                        event_type=event_service.EVENT_LEAD_STATUS_CHANGED,
                        entidad_origen_tipo="lead",
                        entidad_origen_id=lead_id,
                        lead_id=lead_id,
                        resultado="success",
                        estado_inicial="confirmado",
                        estado_final="en_proceso",
                        detalle="Estado del lead actualizado por nuevos datos personales"
                    )
            
            # Verificar si ya existen datos para este lead
            result = supabase.table("lead_datos_personales").select("*").eq("lead_id", str(lead_id)).execute()
            
            if result.data and len(result.data) > 0:
                # Actualizar datos existentes
                update_data = {k: v for k, v in data.items() if v is not None and v != ""}
                if update_data:
                    update_result = supabase.table("lead_datos_personales").update(update_data).eq("lead_id", str(lead_id)).execute()
                    
                    # Verificar que la actualización fue exitosa
                    if not update_result.data or len(update_result.data) == 0:
                        print(f"Advertencia: No se actualizaron datos para el lead {lead_id}")
            else:
                # Insertar nuevos datos
                insert_data = {"lead_id": str(lead_id), **data}
                insert_result = supabase.table("lead_datos_personales").insert(insert_data).execute()
                
                # Verificar que la inserción fue exitosa
                if not insert_result.data or len(insert_result.data) == 0:
                    raise ValueError("No se pudieron insertar los datos personales")
                
                # Registrar evento de captura de datos personales
                empresa_id = lead[0]['empresa_id'] if lead and lead[0].get('empresa_id') else None
                if not empresa_id:
                    chatbot_result = supabase.table("chatbots").select("empresa_id").eq("id", self.CAPTURE_CHATBOT_ID).execute()
                    if chatbot_result.data:
                        empresa_id = chatbot_result.data[0]['empresa_id']
                
                if empresa_id:
                    event_service.log_event(
                        empresa_id=UUID(empresa_id),
                        event_type="lead_data_captured",
                        entidad_origen_tipo="chatbot",
                        entidad_origen_id=UUID(self.CAPTURE_CHATBOT_ID),
                        lead_id=lead_id,
                        resultado="success",
                        detalle="Datos personales capturados mediante chatbot"
                    )
            
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
                    
                    # Crear un nuevo lead con los datos básicos
                    lead = conversation_service.get_or_create_lead(
                        empresa_id=UUID(empresa_id),
                        canal_id=UUID(canal_id),
                        nombre="Cliente potencial"
                    )
                    
                    # Verificar que el lead se haya creado correctamente
                    if not lead or "id" not in lead:
                        raise ValueError("No se pudo crear el lead correctamente")
                    
                    # Registrar evento de creación de lead
                    event_service.log_event(
                        empresa_id=UUID(empresa_id),
                        event_type=event_service.EVENT_FIRST_INTERACTION,
                        entidad_origen_tipo="chatbot",
                        entidad_origen_id=UUID(self.CAPTURE_CHATBOT_ID),
                        lead_id=UUID(lead["id"]),
                        canal_id=UUID(canal_id),
                        resultado="success",
                        estado_final="nuevo",
                        detalle="Nuevo lead creado desde chatbot de captura"
                    )
                else:
                    raise ValueError("Chatbot de captura no encontrado")
                lead_id = UUID(lead["id"])
        except Exception as e:
            print(f"Error al verificar o crear lead: {e}")
            return False, "Ocurrió un error al verificar tus datos. Por favor, intenta nuevamente más tarde."

        # Patrones para detectar confirmación (ampliados para capturar más casos)
        confirmation_patterns = [
            r'\b(s[ií]|correcto|exacto|est[áa] bien|perfecto)\b',
            r'\best[áa]n? bien\b',
            r'\bconfirm[oa]\b',
            r'\bperfecto\b',
            r'\bexcelente\b',
            r'\bgenial\b',
            r'\bgracias\b',
            r'\bok\b'
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
                    # Verificar que existan datos personales para este lead
                    datos_personales = supabase.table("lead_datos_personales").select("*").eq("lead_id", str(lead_id)).execute().data
                    
                    if not datos_personales or len(datos_personales) == 0:
                        # Si no hay datos personales, intentar extraerlos del mensaje actual
                        datos_extraidos = self.extract_personal_data(message)
                        if datos_extraidos:
                            # Almacenar los datos extraídos
                            self.store_personal_data(lead_id, datos_extraidos)
                        else:
                            # Si no se pudieron extraer datos, solicitar información
                            return False, "Necesito tus datos personales antes de confirmar. Por favor, proporcióname tu nombre, correo electrónico, teléfono y programa de interés."
                    
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
                    update_result = supabase.table("leads").update({"estado": "confirmado"}).eq("id", str(lead_id)).execute()
                    
                    if not update_result.data or len(update_result.data) == 0:
                        raise ValueError("No se pudo actualizar el estado del lead")
                    
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
                    
                    # Limpiar datos temporales para permitir registrar un nuevo lead desde el mismo número
                    # Esto permite que el sistema esté listo para capturar un nuevo lead
                    try:
                        # Eliminar datos temporales de la sesión para este lead
                        # Esto reinicia el estado de captura para estar listo para un nuevo lead
                        supabase.table("lead_datos_temporales").delete().eq("lead_id", str(lead_id)).execute()
                        print(f"Datos temporales eliminados para lead {lead_id} - Listo para nuevo registro")
                    except Exception as temp_e:
                        print(f"Error al limpiar datos temporales: {temp_e}")
                    
                    return True, "¡Gracias por confirmar tus datos! Han sido registrados correctamente en nuestro CRM. Pronto nos pondremos en contacto contigo. Si deseas registrar a otra persona, puedes proporcionarme sus datos ahora."
                except Exception as e:
                    print(f"Error al actualizar estado del lead: {e}")
                    return True, "Gracias por confirmar tus datos. Han sido registrados, pero hubo un problema al actualizar tu estado. No te preocupes, igualmente nos pondremos en contacto contigo. Si deseas registrar a otra persona, puedes proporcionarme sus datos ahora."
        
        # Verificar si es una negación
        for pattern in negation_patterns:
            if re.search(pattern, message, re.IGNORECASE):
                # Extraer datos corregidos
                corrected_data = self.extract_personal_data(message)
                if corrected_data:
                    # Actualizar solo los datos proporcionados
                    success = self.store_personal_data(lead_id, corrected_data)
                    
                    if success:
                        # Obtener los datos actualizados para mostrarlos al usuario
                        updated_data = supabase.table("lead_datos_personales").select("*").eq("lead_id", str(lead_id)).execute().data
                        
                        if updated_data and len(updated_data) > 0:
                            response = "He actualizado los datos que me has proporcionado. Ahora tengo registrado:\n"
                            if updated_data[0].get('nombre'):
                                response += f"- Nombre: {updated_data[0].get('nombre')}\n"
                            if updated_data[0].get('email'):
                                response += f"- Correo electrónico: {updated_data[0].get('email')}\n"
                            if updated_data[0].get('telefono'):
                                response += f"- Teléfono: {updated_data[0].get('telefono')}\n"
                            if updated_data[0].get('programa_interes'):
                                response += f"- Programa de interés: {updated_data[0].get('programa_interes')}\n"
                            
                            response += "\n¿Son correctos estos datos? Por favor responde 'Sí' para confirmar."
                            return False, response
                    
                    return False, "He actualizado los datos que me has proporcionado. ¿Podrías confirmar si ahora están correctos?"
                else:
                    return False, "Entiendo que hay un error en tus datos. ¿Podrías indicarme específicamente qué dato necesita ser corregido?"
        
        # Si no es confirmación ni negación, intentar extraer datos
        new_data = self.extract_personal_data(message)
        if new_data:
            success = self.store_personal_data(lead_id, new_data)
            
            if success:
                # Obtener todos los datos actualizados para mostrarlos al usuario
                updated_data = supabase.table("lead_datos_personales").select("*").eq("lead_id", str(lead_id)).execute().data
                
                if updated_data and len(updated_data) > 0:
                    response = "He actualizado tu información con los nuevos datos proporcionados. Ahora tengo registrado:\n"
                    if updated_data[0].get('nombre'):
                        response += f"- Nombre: {updated_data[0].get('nombre')}\n"
                    if updated_data[0].get('email'):
                        response += f"- Correo electrónico: {updated_data[0].get('email')}\n"
                    if updated_data[0].get('telefono'):
                        response += f"- Teléfono: {updated_data[0].get('telefono')}\n"
                    if updated_data[0].get('programa_interes'):
                        response += f"- Programa de interés: {updated_data[0].get('programa_interes')}\n"
                    
                    # Verificar si faltan datos
                    missing_data = []
                    if not updated_data[0].get('nombre'):
                        missing_data.append("nombre")
                    if not updated_data[0].get('email'):
                        missing_data.append("correo electrónico")
                    if not updated_data[0].get('telefono'):
                        missing_data.append("número de teléfono")
                    if not updated_data[0].get('programa_interes'):
                        missing_data.append("programa de interés")
                    
                    if missing_data:
                        response += "\nAún necesito los siguientes datos:\n"
                        for item in missing_data:
                            response += f"- Tu {item}\n"
                        response += "\n¿Podrías proporcionarme esta información?"
                    else:
                        response += "\n¿Son correctos estos datos? Por favor responde 'Sí' para confirmar."
                    
                    return False, response
            
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
        
        # Verificar si el mensaje contiene una confirmación explícita (ampliado para capturar más casos)
        confirmation_patterns = [
            r'\b(s[ií]|correcto|exacto|est[áa] bien|perfecto)\b',
            r'\best[áa]n? bien\b',
            r'\bconfirm[oa]\b',
            r'\bperfecto\b',
            r'\bexcelente\b',
            r'\bgenial\b',
            r'\bok\b'
        ]
        
        is_explicit_confirmation = False
        for pattern in confirmation_patterns:
            if re.search(pattern, message, re.IGNORECASE):
                is_explicit_confirmation = True
                break
        
        # Detectar si el mensaje contiene datos personales
        data = self.extract_personal_data(message)
        has_personal_data = bool(data) and len(data) > 0
        
        # Si ya existe un lead_id, verificar si hay datos confirmados o si es un nuevo registro
        if lead_id:
            # Verificar si ya existen datos para este lead
            result = supabase.table("lead_datos_personales").select("*").eq("lead_id", str(lead_id)).execute()
            has_stored_data = result.data and len(result.data) > 0
            
            # Verificar si el lead ya está confirmado
            lead_info = supabase.table("leads").select("estado").eq("id", str(lead_id)).execute().data
            lead_confirmado = lead_info and lead_info[0].get('estado') == "confirmado"
            
            # Si el lead está confirmado y el mensaje contiene nuevos datos personales,
            # probablemente sea un nuevo registro desde el mismo número
            if lead_confirmado and has_personal_data and len(message.split()) > 3:
                # Crear un nuevo lead para este nuevo conjunto de datos
                from app.services.conversation_service import ConversationService
                conv_service = ConversationService()
                
                # Obtener empresa_id y canal_id del chatbot de captura
                chatbot_result = supabase.table("chatbots").select("empresa_id, canal_id").eq("id", self.CAPTURE_CHATBOT_ID).execute()
                
                if chatbot_result.data:
                    empresa_id = chatbot_result.data[0]['empresa_id']
                    canal_id = chatbot_result.data[0]['canal_id']
                    
                    # Crear nuevo lead con los datos disponibles
                    new_lead = conv_service.get_or_create_lead(
                        empresa_id=UUID(empresa_id),
                        canal_id=UUID(canal_id),
                        nombre=data.get('nombre', 'Nuevo lead desde captura')
                    )
                    
                    new_lead_id = UUID(new_lead["id"])
                    
                    # Almacenar los datos personales extraídos para el nuevo lead
                    self.store_personal_data(new_lead_id, data)
                    
                    # Generar respuesta para el nuevo lead
                    response = "¡Gracias por proporcionar tus datos! He registrado la siguiente información:\n"
                    if 'nombre' in data and data['nombre']:
                        response += f"- Nombre: {data['nombre']}\n"
                    if 'email' in data and data['email']:
                        response += f"- Correo electrónico: {data['email']}\n"
                    if 'telefono' in data and data['telefono']:
                        response += f"- Teléfono: {data['telefono']}\n"
                    if 'programa_interes' in data and data['programa_interes']:
                        response += f"- Programa de interés: {data['programa_interes']}\n"
                    
                    # Verificar si faltan datos
                    missing_data = []
                    if 'nombre' not in data or not data['nombre']:
                        missing_data.append("nombre")
                    if 'email' not in data or not data['email']:
                        missing_data.append("correo electrónico")
                    if 'telefono' not in data or not data['telefono']:
                        missing_data.append("número de teléfono")
                    if 'programa_interes' not in data or not data['programa_interes']:
                        missing_data.append("programa de interés")
                    
                    if missing_data:
                        response += "\nAún necesito los siguientes datos:\n"
                        for item in missing_data:
                            response += f"- Tu {item}\n"
                        response += "\n¿Podrías proporcionarme esta información?"
                    else:
                        response += "\n¿Son correctos estos datos? Por favor responde 'Sí' para confirmar."
                    
                    return {
                        "response": response,
                        "lead_id": new_lead_id,
                        "data": data,
                        "is_new_lead": True
                    }
            
            # Si hay datos almacenados y es una confirmación explícita
            if has_stored_data and is_explicit_confirmation:
                is_confirmation, response_text = self.process_confirmation(message, lead_id)
                return {
                    "response": response_text,
                    "lead_id": lead_id,
                    "is_confirmation": is_confirmation,
                    "data_confirmed": True
                }
            
            # Si hay datos almacenados y se reciben nuevos datos (posible corrección)
            if has_stored_data and has_personal_data:
                # Actualizar los datos existentes
                self.store_personal_data(lead_id, data)
                
                # Obtener todos los datos actualizados
                updated_result = supabase.table("lead_datos_personales").select("*").eq("lead_id", str(lead_id)).execute()
                updated_data = updated_result.data[0] if updated_result.data else {}
                
                response = "He actualizado tus datos con la información proporcionada. Ahora tengo registrado:\n"
                if updated_data.get('nombre'):
                    response += f"- Nombre: {updated_data.get('nombre')}\n"
                if updated_data.get('email'):
                    response += f"- Correo electrónico: {updated_data.get('email')}\n"
                if updated_data.get('telefono'):
                    response += f"- Teléfono: {updated_data.get('telefono')}\n"
                if updated_data.get('programa_interes'):
                    response += f"- Programa de interés: {updated_data.get('programa_interes')}\n"
                
                response += "\n¿Son correctos estos datos? Por favor responde 'Sí' para confirmar."
                
                return {
                    "response": response,
                    "lead_id": lead_id,
                    "data": updated_data,
                    "data_updated": True
                }
        
        # Si no hay lead_id o no hay datos almacenados, procesar como nuevo registro
        
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
        if has_personal_data:
            self.store_personal_data(lead_id, data)
            
            # Generar respuesta personalizada basada en los datos capturados
            response = "¡Gracias por proporcionar tus datos! He registrado la siguiente información:\n"
            if 'nombre' in data and data['nombre']:
                response += f"- Nombre: {data['nombre']}\n"
            if 'email' in data and data['email']:
                response += f"- Correo electrónico: {data['email']}\n"
            if 'telefono' in data and data['telefono']:
                response += f"- Teléfono: {data['telefono']}\n"
            if 'programa_interes' in data and data['programa_interes']:
                response += f"- Programa de interés: {data['programa_interes']}\n"
            
            # Verificar si faltan datos
            missing_data = []
            if 'nombre' not in data or not data['nombre']:
                missing_data.append("nombre")
            if 'email' not in data or not data['email']:
                missing_data.append("correo electrónico")
            if 'telefono' not in data or not data['telefono']:
                missing_data.append("número de teléfono")
            if 'programa_interes' not in data or not data['programa_interes']:
                missing_data.append("programa de interés")
            
            if missing_data:
                response += "\nAún necesito los siguientes datos:\n"
                for item in missing_data:
                    response += f"- Tu {item}\n"
                response += "\n¿Podrías proporcionarme esta información?"
            else:
                response += "\n¿Son correctos estos datos? Por favor responde 'Sí' para confirmar."
            
            return {
                "response": response,
                "lead_id": lead_id,
                "data": data,
                "data_captured": True
            }
        
        # Si el mensaje es solo una confirmación pero no se detectaron datos, intentar procesar como confirmación
        if is_explicit_confirmation:
            is_confirmation, response_text = self.process_confirmation(message, lead_id)
            return {
                "response": response_text,
                "lead_id": lead_id,
                "is_confirmation": is_confirmation
            }
        
        # Si no se detectaron datos ni confirmación, solicitar información
        response = "Hola, soy un asistente para registrar tus datos. Por favor, proporcióname la siguiente información:\n\n"
        response += "- Tu nombre completo\n"
        response += "- Tu correo electrónico\n"
        response += "- Tu número de teléfono\n"
        response += "- El programa en el que estás interesado/a\n"
        
        return {
            "response": response,
            "lead_id": lead_id
        }

# Crear instancia del servicio
data_capture_service = DataCaptureService()