from typing import Dict, Any, Optional, Union, List
from uuid import UUID
from datetime import datetime
import asyncio
from concurrent.futures import ThreadPoolExecutor
from threading import Thread

from app.db.supabase_client import supabase
from app.core.config import settings

class EventService:
    """Servicio para registrar eventos en el sistema de análisis"""
    
    # Ejecutor de hilos para procesar eventos de forma asíncrona
    _executor = ThreadPoolExecutor(max_workers=settings.EVENT_WORKERS if hasattr(settings, 'EVENT_WORKERS') else 2)
    
    # Constantes para tipos de eventos comunes (usando los mismos nombres de tu base de datos)
    # Eventos de Chatbot
    EVENT_CONVERSATION_STARTED = "conversacion_iniciada"
    EVENT_CONVERSATION_TRANSFERRED = "conversacion_transferida"
    EVENT_INTENT_NOT_RECOGNIZED = "intent_no_reconocido"
    EVENT_RESPONSE_EVALUATED = "respuesta_evaluada"
    EVENT_LEAD_QUALIFIED = "lead_calificado"
    EVENT_CHATBOT_RESPONSE = "chatbot_respuesta"
    
    # Eventos de Canal
    EVENT_CHANNEL_CONFIG_UPDATED = "configuracion_actualizada"
    EVENT_INTEGRATION_ERROR = "integracion_error"
    EVENT_MESSAGE_RECEIVED = "mensaje_recibido"
    EVENT_CHANNEL_INACTIVE = "canal_inactivo"
    
    # Eventos de Lead
    EVENT_FIRST_INTERACTION = "primera_interaccion"
    EVENT_INFO_REQUEST = "solicitud_informacion"
    EVENT_COMPLAINT = "queja"
    EVENT_INACTIVITY = "inactividad"
    
    # Eventos de Agente
    EVENT_AGENT_LOGIN = "login"
    EVENT_AGENT_LOGOUT = "logout"
    EVENT_LEAD_ASSIGNED = "asignacion_lead"
    EVENT_LEAD_TRANSFERRED = "transferencia_lead"
    EVENT_LEAD_STATUS_CHANGED = "cambio_estado_lead"
    EVENT_NOTE_ADDED = "nota_agregada"
    EVENT_QUICK_RESPONSE = "respuesta_rapida"
    EVENT_RESPONSE_TIME = "tiempo_respuesta"
    EVENT_RATING_RECEIVED = "calificacion_recibida"
    
    # Eventos de Sistema
    EVENT_AUTOMATION_EXECUTED = "automatizacion_ejecutada"
    EVENT_INTEGRATION_ERROR_SYS = "error_integracion"
    EVENT_BACKUP_COMPLETED = "backup_completado"
    EVENT_ERROR_OCCURRED = "error_sistema"
    
    # Cache de los tipos de eventos para evitar múltiples consultas
    _event_type_cache = {}
    
    def __init__(self):
        """Inicializa el servicio de eventos y carga el caché de tipos de eventos"""
        self._load_event_types()
    
    def _load_event_types(self):
        """Carga los tipos de eventos desde la base de datos en el caché"""
        try:
            result = supabase.table("dim_tipos_eventos").select("tipo_evento_id,nombre,categoria").execute()
            
            if result.data:
                for event_type in result.data:
                    # Guardar el mapeo de nombre a ID
                    self._event_type_cache[event_type["nombre"]] = {
                        "id": event_type["tipo_evento_id"],
                        "categoria": event_type["categoria"]
                    }
        except Exception as e:
            print(f"Error al cargar tipos de eventos: {e}")
    
    def log_event(self, 
                 empresa_id: UUID,
                 event_type: str,
                 entidad_origen_tipo: str = None,
                 entidad_origen_id: Union[UUID, str] = None,
                 entidad_destino_tipo: str = None,
                 entidad_destino_id: Union[UUID, str] = None,
                 lead_id: Union[UUID, str] = None,
                 agente_id: Union[UUID, str] = None,
                 chatbot_id: Union[UUID, str] = None,
                 canal_id: Union[UUID, str] = None,
                 conversacion_id: Union[UUID, str] = None,
                 mensaje_id: Union[UUID, str] = None,
                 valor_score: float = None,
                 duracion_segundos: float = None,
                 resultado: str = None,
                 estado_final: str = None,
                 detalle: str = None,
                 metadata: Dict[str, Any] = None,
                 async_processing: bool = True) -> Dict[str, Any]:
        """
        Registra un evento en el sistema de análisis
        
        Args:
            empresa_id: ID de la empresa
            event_type: Tipo de evento (usar constantes de clase)
            entidad_origen_tipo: Tipo de entidad origen (lead, chatbot, agente)
            entidad_origen_id: ID de la entidad origen
            entidad_destino_tipo: Tipo de entidad destino
            entidad_destino_id: ID de la entidad destino
            lead_id: ID del lead involucrado (opcional)
            agente_id: ID del agente involucrado (opcional)
            chatbot_id: ID del chatbot involucrado (opcional)
            canal_id: ID del canal involucrado (opcional)
            conversacion_id: ID de la conversación (opcional)
            mensaje_id: ID del mensaje (opcional)
            valor_score: Valor de score (opcional)
            duracion_segundos: Duración en segundos (opcional)
            resultado: Resultado del evento (opcional)
            estado_final: Estado final (opcional)
            detalle: Detalles adicionales (opcional)
            metadata: Metadatos adicionales (opcional)
            async_processing: Si es True, procesa el evento de forma asíncrona
            
        Returns:
            Datos del evento registrado o None si es procesado de forma asíncrona
        """
        try:
            # Si el tipo de evento no está en caché, intentamos recargarlo
            if event_type not in self._event_type_cache:
                self._load_event_types()
                
                # Si sigue sin estar, registramos el error y continuamos con el flujo principal
                if event_type not in self._event_type_cache:
                    print(f"Advertencia: Tipo de evento '{event_type}' no encontrado en dim_tipos_eventos")
            
            # Preparar datos del evento
            event_data = self._prepare_event_data(
                empresa_id=empresa_id,
                event_type=event_type,
                entidad_origen_tipo=entidad_origen_tipo,
                entidad_origen_id=entidad_origen_id,
                entidad_destino_tipo=entidad_destino_tipo,
                entidad_destino_id=entidad_destino_id,
                lead_id=lead_id,
                agente_id=agente_id,
                chatbot_id=chatbot_id,
                canal_id=canal_id,
                conversacion_id=conversacion_id,
                mensaje_id=mensaje_id,
                valor_score=valor_score,
                duracion_segundos=duracion_segundos,
                resultado=resultado,
                estado_final=estado_final,
                detalle=detalle,
                metadata=metadata
            )
            
            # Procesar de forma asíncrona o síncrona según el parámetro
            if async_processing:
                self._process_event_async(event_data)
                return {"status": "processing", "event_type": event_type}
            else:
                return self._process_event(event_data)
                
        except Exception as e:
            print(f"Error al registrar evento {event_type}: {e}")
            # Log error pero no propagar excepción para no afectar flujo principal
            return {"status": "error", "error": str(e), "event_type": event_type}
    
    def _prepare_event_data(self, **kwargs) -> Dict[str, Any]:
        """Prepara los datos del evento para su registro"""
        # Obtener el ID del tipo de evento desde el mapeo
        event_type = kwargs.get('event_type')
        tipo_evento_info = self._event_type_cache.get(event_type)
        
        if not tipo_evento_info:
            # Si no encontramos el tipo de evento, buscamos uno genérico de la categoría adecuada
            # Esto es un fallback por si el evento específico no está definido
            categoria = self._infer_category(kwargs)
            for name, info in self._event_type_cache.items():
                if info["categoria"] == categoria:
                    tipo_evento_info = info
                    print(f"Usando evento genérico '{name}' para '{event_type}'")
                    break
        
        # Si aún así no tenemos un tipo de evento, usamos un UUID genérico (no debería ocurrir en producción)
        tipo_evento_id = tipo_evento_info["id"] if tipo_evento_info else "00000000-0000-0000-0000-000000000000"
        
        # Convertir todos los UUIDs a strings
        for key, value in kwargs.items():
            if isinstance(value, UUID):
                kwargs[key] = str(value)
                
        # Asegurar que duracion_segundos sea un entero
        if 'duracion_segundos' in kwargs and kwargs['duracion_segundos'] is not None:
            try:
                kwargs['duracion_segundos'] = int(float(kwargs['duracion_segundos']))
            except (ValueError, TypeError):
                kwargs['duracion_segundos'] = None
        
        # Asegurar que valor_score sea un entero
        if 'valor_score' in kwargs and kwargs['valor_score'] is not None:
            try:
                kwargs['valor_score'] = int(float(kwargs['valor_score']))
            except (ValueError, TypeError):
                kwargs['valor_score'] = None
        
        # Crear diccionario con todos los campos necesarios para fact_eventos_acciones
        now = datetime.utcnow()
        
        # Obtener ID de la dimensión tiempo
        tiempo_id = self._get_or_create_tiempo_id(now)
        
        # Manejar correctamente entidad_origen_tipo y entidad_origen_id
        # Si entidad_origen_tipo está especificado pero entidad_origen_id no, usar un valor por defecto
        entidad_origen_tipo = kwargs.get('entidad_origen_tipo')
        entidad_origen_id = kwargs.get('entidad_origen_id')
        
        # Si no se proporcionó tipo de entidad origen, usar 'sistema' como predeterminado
        if not entidad_origen_tipo:
            entidad_origen_tipo = 'sistema'
            entidad_origen_id = '00000000-0000-0000-0000-000000000000'
            
        # Si hay tipo pero no ID, usar el ID de sistema por defecto
        if entidad_origen_tipo and not entidad_origen_id:
            entidad_origen_id = '00000000-0000-0000-0000-000000000000'
            
        # Buscar o crear la entidad en dim_entidades
        entidad_origen_id_dimension = self._get_entidad_id(entidad_origen_tipo, entidad_origen_id)
        
        # Manejar similar para entidad_destino
        entidad_destino_tipo = kwargs.get('entidad_destino_tipo')
        entidad_destino_id = kwargs.get('entidad_destino_id')
        entidad_destino_id_dimension = None
        
        if entidad_destino_tipo and entidad_destino_id:
            entidad_destino_id_dimension = self._get_entidad_id(entidad_destino_tipo, entidad_destino_id)
            
        # Preparar datos para la tabla de hechos
        event_data = {
            "tiempo_id": tiempo_id,
            "empresa_id": kwargs.get('empresa_id'),
            "tipo_evento_id": tipo_evento_id,
            "entidad_origen_id": entidad_origen_id_dimension,  # Nunca será nulo ahora
            "entidad_destino_id": entidad_destino_id_dimension,
            "lead_id": kwargs.get('lead_id'),
            "agente_id": kwargs.get('agente_id'),
            "chatbot_id": kwargs.get('chatbot_id'),
            "canal_id": kwargs.get('canal_id'),
            "conversacion_id": kwargs.get('conversacion_id'),
            "mensaje_id": kwargs.get('mensaje_id'),
            "valor_score": kwargs.get('valor_score'),
            "duracion_segundos": kwargs.get('duracion_segundos'),
            "resultado": kwargs.get('resultado'),
            "estado_final": kwargs.get('estado_final'),
            "detalle": kwargs.get('detalle'),
            "metadata": kwargs.get('metadata'),
            "created_at": now.isoformat()
        }
        
        # Eliminar campos None para evitar problemas con valores NULL no permitidos
        return {k: v for k, v in event_data.items() if v is not None}
        
    def _infer_category(self, event_data: Dict[str, Any]) -> str:
        """Infiere la categoría del evento basado en los datos proporcionados"""
        # Reglas simples para inferir la categoría según los datos del evento
        if event_data.get('chatbot_id'):
            return "chatbot"
        elif event_data.get('agente_id'):
            return "agente"
        elif event_data.get('canal_id'):
            return "canal"
        elif event_data.get('lead_id'):
            return "lead"
        else:
            return "sistema"
    
    def _process_event(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Procesa un evento registrándolo en la tabla de hechos"""
        try:
            # Insertar en la tabla de hechos principal
            result = supabase.table("fact_eventos_acciones").insert(event_data).execute()
            
            # También podríamos insertar en otras tablas según necesidades específicas
            # Por ejemplo, insertar en una tabla de eventos recientes para consultas rápidas
            
            if result.data and len(result.data) > 0:
                return result.data[0]
            
            raise ValueError("No se pudo registrar el evento")
            
        except Exception as e:
            print(f"Error al procesar evento: {e}")
            # En producción, deberíamos registrar estos errores para reintento
            raise
    
    def _process_event_async(self, event_data: Dict[str, Any]) -> None:
        """Procesa un evento de forma asíncrona en un hilo separado"""
        try:
            # Enviar tarea al ejecutor de hilos
            self._executor.submit(self._process_event, event_data)
        except Exception as e:
            print(f"Error al enviar evento para procesamiento asíncrono: {e}")
    
    def _get_entidad_id(self, entidad_tipo: Optional[str], entidad_id: Optional[str]) -> Optional[str]:
        """
        Obtiene el ID de la entidad desde dim_entidades o la crea si no existe
        En una implementación completa, obtendríamos o crearíamos la entidad en dim_entidades
        """
        if not entidad_tipo or not entidad_id:
            return None
            
        try:
            # Buscar entidad en dim_entidades
            result = supabase.table("dim_entidades").select("entidad_id").eq("tipo_entidad", entidad_tipo).eq("entidad_original_id", str(entidad_id)).limit(1).execute()
            
            if result.data and len(result.data) > 0:
                return result.data[0].get("entidad_id")
            
            # Si no existe, crear nueva entidad
            # En un sistema de producción, esto debería manejarse a través de una cola o inserción batch
            new_entity = {
                "tipo_entidad": entidad_tipo,
                "entidad_original_id": str(entidad_id),
                "is_active": True,
                "created_at": datetime.utcnow().isoformat()
            }
            
            result = supabase.table("dim_entidades").insert(new_entity).execute()
            
            if result.data and len(result.data) > 0:
                return result.data[0].get("entidad_id")
                
            # Si falla la inserción, devolver un ID por defecto para evitar errores de restricción not-null
            return "00000000-0000-0000-0000-000000000000"
                
        except Exception as e:
            print(f"Error al obtener/crear entidad en dim_entidades: {e}")
            # En caso de error, devolver un ID por defecto para evitar errores de restricción not-null
            return "00000000-0000-0000-0000-000000000000"
    
    def _get_or_create_tiempo_id(self, dt: datetime) -> int:
        """
        Obtiene o crea un ID de tiempo en la dimensión tiempo
        En producción, esto se haría con un proceso ETL que precarga todos los tiempos posibles
        """
        # Extraer componentes de tiempo
        fecha = dt.date().isoformat()
        hora = dt.time().isoformat()
        
        # Buscar si ya existe
        result = supabase.table("dim_tiempo").select("tiempo_id").eq("fecha", fecha).eq("hora", hora).limit(1).execute()
        
        if result.data and len(result.data) > 0:
            return result.data[0].get("tiempo_id")
        
        # En producción, no deberíamos crear dimensiones sobre la marcha,
        # pero para simplificar lo hacemos así
        tiempo_data = {
            "fecha": fecha,
            "hora": hora,
            "dia_semana": dt.weekday(),
            "dia": dt.day,
            "semana": dt.isocalendar()[1],
            "mes": dt.month,
            "trimestre": (dt.month - 1) // 3 + 1,
            "anio": dt.year,
            "es_fin_semana": dt.weekday() >= 5,  # 5=Sábado, 6=Domingo
            "nombre_dia": dt.strftime("%A"),
            "nombre_mes": dt.strftime("%B"),
            "fecha_completa": dt.isoformat()
        }
        
        result = supabase.table("dim_tiempo").insert(tiempo_data).execute()
        
        if result.data and len(result.data) > 0:
            return result.data[0].get("tiempo_id")
            
        # Si falla, usar un tiempo por defecto (en producción necesitaríamos mejor manejo de errores)
        return 1

# Instancia singleton
event_service = EventService()