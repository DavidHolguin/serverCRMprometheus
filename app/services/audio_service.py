import base64
import os
import tempfile
import uuid
import requests
from typing import Dict, Any, Optional, Tuple
from uuid import UUID

# Usar el cliente OpenAI actualizado
from openai import OpenAI
from pydub import AudioSegment
from pydub.utils import mediainfo

from app.core.config import settings
from app.db.supabase_client import supabase
from app.services.conversation_service import conversation_service


class AudioService:
    """Servicio para manejar mensajes de audio, transcripción y almacenamiento"""
    
    def __init__(self):
        """Inicializa el servicio de audio"""
        # Configurar el cliente de OpenAI con la nueva API
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
        # Bucket de Supabase para almacenar audios
        self.audio_bucket = "mensajes-audio"
        # Asegurarse de que el bucket exista
        self._ensure_bucket_exists()
    
    def _ensure_bucket_exists(self) -> None:
        """Asegura que el bucket para audios exista en Supabase Storage"""
        try:
            # Intentar listar el bucket para ver si existe
            supabase.storage.get_bucket(self.audio_bucket)
            print(f"Bucket {self.audio_bucket} encontrado correctamente")
        except Exception as e:
            try:
                # Si no existe, crear el bucket con acceso público
                # Lo configuramos como público para permitir acceso desde el frontend sin autenticación
                print(f"Intentando crear bucket {self.audio_bucket}...")
                
                # Intentar usar el servicio de almacenamiento directamente con RPC
                from app.db.supabase_client import supabase_url, supabase_key
                import requests
                
                headers = {
                    "apikey": supabase_key,
                    "Authorization": f"Bearer {supabase_key}",
                    "Content-Type": "application/json"
                }
                
                payload = {
                    "id": self.audio_bucket,
                    "name": self.audio_bucket,
                    "public": True
                }
                
                response = requests.post(
                    f"{supabase_url}/storage/buckets",
                    headers=headers,
                    json=payload
                )
                
                print(f"Respuesta de creación de bucket: {response.status_code} - {response.text}")
                
                if response.status_code == 200 or response.status_code == 201:
                    print(f"Bucket {self.audio_bucket} creado exitosamente")
                else:
                    print(f"Error al crear bucket: {response.text}")
                    
                    # Si no podemos crear el bucket, usaremos uno existente
                    print("Intentando usar un bucket alternativo...")
                    buckets = supabase.storage.list_buckets()
                    if buckets:
                        self.audio_bucket = buckets[0]["id"]
                        print(f"Usando bucket alternativo: {self.audio_bucket}")
                    
            except Exception as inner_e:
                print(f"Error al crear/encontrar bucket: {str(inner_e)}")
                # Intentar usar un bucket por defecto si existe
                try:
                    buckets = supabase.storage.list_buckets()
                    if buckets:
                        self.audio_bucket = buckets[0]["id"]
                        print(f"Usando bucket alternativo: {self.audio_bucket}")
                    else:
                        print("No se encontraron buckets disponibles")
                except:
                    print("No se pudieron listar buckets")
    
    def _decode_and_save_audio(self, audio_base64: str, formato: str) -> Tuple[str, str, int, float]:
        """
        Decodifica el audio en base64 y lo guarda temporalmente
        
        Args:
            audio_base64: Audio codificado en base64
            formato: Formato del audio (mp3, wav, etc.)
            
        Returns:
            Tuple con la ruta temporal del archivo, el formato normalizado, 
            tamaño en bytes y duración en segundos
        """
        try:
            # Decodificar el contenido base64
            audio_data = base64.b64decode(audio_base64)
            
            # Crear archivo temporal con la extensión correcta
            with tempfile.NamedTemporaryFile(delete=False, suffix=f".{formato.lower()}") as temp_file:
                temp_file.write(audio_data)
                temp_path = temp_file.name
            
            # Obtener información del archivo de audio
            audio_info = mediainfo(temp_path)
            
            # Calcular tamaño y duración
            file_size = os.path.getsize(temp_path)
            
            # Manejar el caso cuando la duración es 'N/A' o un valor no numérico
            try:
                duration_str = audio_info.get('duration', '0')
                duration = float(duration_str) if duration_str and duration_str.lower() != 'n/a' else 0
            except (ValueError, TypeError):
                print(f"No se pudo convertir la duración '{audio_info.get('duration')}' a float, usando 0")
                duration = 0
            
            # Normalizar formato
            formato_normalizado = audio_info.get('format_name', formato).split(',')[0]
            
            return temp_path, formato_normalizado, file_size, duration
        
        except Exception as e:
            import traceback
            traceback.print_exc()  # Imprimir el traceback completo para depuración
            raise ValueError(f"Error al decodificar o guardar el audio: {str(e)}")

    async def download_whatsapp_audio(self, audio_id: str, access_token: str) -> Tuple[str, str, int, float]:
        """
        Descarga un archivo de audio de WhatsApp usando la API de WhatsApp Cloud
        
        Args:
            audio_id: ID del audio proporcionado por WhatsApp
            access_token: Token de acceso para la API de WhatsApp
            
        Returns:
            Tuple con la ruta temporal del archivo, formato del audio, tamaño en bytes y duración en segundos
        """
        try:
            # URL para descargar el archivo de WhatsApp Cloud API
            url = f"https://graph.facebook.com/v18.0/{audio_id}"
            
            # Headers para la solicitud
            headers = {
                "Authorization": f"Bearer {access_token}"
            }
            
            # Obtener la información del archivo (URL de descarga)
            response = requests.get(url, headers=headers)
            if response.status_code != 200:
                raise ValueError(f"Error al obtener información del audio: {response.text}")
            
            # Extraer la URL de descarga del archivo
            file_info = response.json()
            download_url = file_info.get("url")
            
            if not download_url:
                raise ValueError("No se pudo obtener la URL de descarga del audio")
            
            # Descargar el archivo
            file_response = requests.get(download_url, headers=headers)
            if file_response.status_code != 200:
                raise ValueError(f"Error al descargar el audio: {file_response.status_code}")
            
            # Guardar el archivo temporalmente
            with tempfile.NamedTemporaryFile(delete=False, suffix=".ogg") as temp_file:
                temp_file.write(file_response.content)
                temp_path = temp_file.name
            
            # Obtener información del archivo de audio
            audio_info = mediainfo(temp_path)
            
            # Calcular tamaño y duración
            file_size = os.path.getsize(temp_path)
            
            # Manejar el caso cuando la duración es 'N/A' o un valor no numérico
            try:
                duration_str = audio_info.get('duration', '0')
                duration = float(duration_str) if duration_str and duration_str.lower() != 'n/a' else 0
            except (ValueError, TypeError):
                print(f"No se pudo convertir la duración '{audio_info.get('duration')}' a float, usando 0")
                duration = 0
            
            # Determinar el formato del archivo
            formato = audio_info.get('format_name', 'ogg').split(',')[0]
            
            return temp_path, formato, file_size, duration
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            raise ValueError(f"Error al descargar audio de WhatsApp: {str(e)}")
    
    def _upload_to_supabase(self, file_path: str, conversacion_id: UUID, mensaje_id: UUID) -> str:
        """
        Sube el archivo de audio a Supabase Storage
        
        Args:
            file_path: Ruta al archivo temporal
            conversacion_id: ID de la conversación
            mensaje_id: ID del mensaje
            
        Returns:
            URL del archivo en Supabase Storage
        """
        try:
            # Generar un nombre de archivo único
            file_name = f"{conversacion_id}/{mensaje_id}_{uuid.uuid4()}{os.path.splitext(file_path)[1]}"
            
            # Leer el contenido del archivo
            with open(file_path, 'rb') as f:
                file_content = f.read()
            
            # Subir el archivo al bucket
            print(f"Intentando subir archivo a bucket {self.audio_bucket}...")
            result = supabase.storage.from_(self.audio_bucket).upload(
                file_name,
                file_content
            )
            
            # Generar URL pública para el archivo
            file_url = supabase.storage.from_(self.audio_bucket).get_public_url(file_name)
            
            return file_url
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"Error al subir audio: {str(e)}")
            
            # Si falla la subida, devolver una URL ficticia para continuar el flujo
            return f"error://upload-failed/{conversacion_id}/{mensaje_id}"
        finally:
            # Eliminar el archivo temporal
            if os.path.exists(file_path):
                os.remove(file_path)
    
    def transcribe_audio(self, file_path: str, idioma: Optional[str] = None) -> Dict[str, Any]:
        """
        Transcribe el audio utilizando OpenAI Whisper con la API actualizada
        
        Args:
            file_path: Ruta al archivo de audio
            idioma: Código de idioma para la transcripción (opcional)
            
        Returns:
            Diccionario con la transcripción y metadatos
        """
        try:
            # Abrir el archivo de audio
            with open(file_path, "rb") as audio_file:
                # Configurar los parámetros para la transcripción usando la nueva API
                params = {}
                if idioma:
                    params["language"] = idioma
                    
                # Realizar la transcripción con la nueva API
                response = self.client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    response_format="verbose_json",
                    **params
                )
                
                # Convertir el objeto de respuesta a diccionario
                response_dict = response.model_dump()
                
                return {
                    "texto": response_dict.get("text", ""),
                    "idioma": response_dict.get("language", ""),
                    "duracion": response_dict.get("duration", 0),
                    "confianza": response_dict.get("confidence", 0),
                    "segmentos": response_dict.get("segments", [])
                }
                
        except Exception as e:
            import traceback
            traceback.print_exc()
            raise ValueError(f"Error al transcribir el audio: {str(e)}")

    def save_audio_message(self, 
                         conversacion_id: UUID, 
                         mensaje_id: UUID, 
                         audio_url: str,
                         transcripcion: str,
                         metadata: Dict[str, Any]) -> UUID:
        """
        Guarda la información del mensaje de audio en la base de datos
        
        Args:
            conversacion_id: ID de la conversación
            mensaje_id: ID del mensaje
            audio_url: URL del archivo de audio en Supabase
            transcripcion: Texto transcrito del audio
            metadata: Metadatos del audio y la transcripción
            
        Returns:
            ID del registro de audio creado
        """
        try:
            # Preparar los datos para insertar en la base de datos
            audio_data = {
                "mensaje_id": str(mensaje_id),
                "conversacion_id": str(conversacion_id),
                "archivo_url": audio_url,
                "transcripcion": transcripcion,
                "modelo_transcripcion": metadata.get("modelo", "whisper-1"),
                "idioma_detectado": metadata.get("idioma", ""),
                "duracion_segundos": metadata.get("duracion", 0),
                "tamano_bytes": metadata.get("tamano", 0),
                "formato": metadata.get("formato", ""),
                "metadata": {
                    "confianza": metadata.get("confianza", 0),
                    "segmentos": metadata.get("segmentos", []),
                    "adicional": metadata.get("adicional", {})
                }
            }
            
            # Insertar en la base de datos
            result = supabase.table("mensajes_audio").insert(audio_data).execute()
            
            # Verificar que se haya creado correctamente
            if not result.data or len(result.data) == 0:
                raise ValueError("Error al guardar el mensaje de audio en la base de datos")
            
            # Devolver el ID del registro creado
            return UUID(result.data[0]["id"])
            
        except Exception as e:
            raise ValueError(f"Error al guardar el mensaje de audio: {str(e)}")

    async def process_whatsapp_audio(self,
                                  canal_id: UUID,
                                  phone_number: str,
                                  empresa_id: UUID,
                                  chatbot_id: UUID,
                                  audio_id: str,
                                  lead_id: UUID,
                                  metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Procesa un mensaje de audio recibido a través de WhatsApp
        
        Args:
            canal_id: ID del canal de WhatsApp
            phone_number: Número de teléfono del remitente
            empresa_id: ID de la empresa
            chatbot_id: ID del chatbot
            audio_id: ID del audio proporcionado por WhatsApp
            lead_id: ID del lead
            metadata: Metadatos adicionales
        
        Returns:
            Diccionario con la información de la respuesta
        """
        try:
            # 1. Descargar el audio de WhatsApp
            access_token = settings.WHATSAPP_ACCESS_TOKEN
            if not access_token:
                raise ValueError("No se ha configurado el token de acceso para WhatsApp")
            
            temp_path, formato, tamano, duracion = await self.download_whatsapp_audio(audio_id, access_token)
            
            # 2. Transcribir el audio
            idioma = "es"  # Por defecto en español, se podría configurar dinámicamente
            transcripcion_result = self.transcribe_audio(temp_path, idioma)
            transcripcion_texto = transcripcion_result["texto"]
            
            # Preparar metadatos sanitizados
            sanitized_metadata = {}
            if metadata:
                # Filtrar datos personales
                sanitized_metadata = {k: v for k, v in metadata.items() 
                              if k not in ["nombre", "apellido", "email", "telefono", 
                                          "direccion", "dni", "nif"]}
            
            # Añadir información del audio a los metadatos
            sanitized_metadata.update({
                "tipo_mensaje": "audio",
                "formato_audio": formato,
                "duracion_audio": duracion,
                "tamano_audio": tamano,
                "idioma_detectado": transcripcion_result["idioma"],
                "origen": "whatsapp",
                "audio_id_whatsapp": audio_id
            })
            
            # 3. Procesar el mensaje de texto transcrito usando el servicio de conversación
            conversation_result = conversation_service.process_channel_message(
                canal_id=canal_id,
                canal_identificador=phone_number,
                empresa_id=empresa_id,
                chatbot_id=chatbot_id,
                mensaje=transcripcion_texto,
                lead_id=lead_id,
                metadata=sanitized_metadata
            )
            
            # Obtener el conversation_id del resultado
            result_conversation_id = UUID(conversation_result["conversacion_id"])
            
            # 4. Subir el audio a Supabase
            audio_url = self._upload_to_supabase(
                temp_path, 
                result_conversation_id, 
                conversation_result["mensaje_id"]
            )
            
            # 5. Guardar la información del audio en la base de datos
            audio_metadata = {
                "modelo": "whisper-1",
                "idioma": transcripcion_result["idioma"],
                "duracion": duracion,
                "tamano": tamano,
                "formato": formato,
                "confianza": transcripcion_result["confianza"],
                "segmentos": transcripcion_result["segmentos"],
                "adicional": sanitized_metadata
            }
            
            audio_id = self.save_audio_message(
                conversacion_id=result_conversation_id,
                mensaje_id=conversation_result["mensaje_id"],
                audio_url=audio_url,
                transcripcion=transcripcion_texto,
                metadata=audio_metadata
            )
            
            # 6. Preparar respuesta
            return {
                "mensaje_id": conversation_result["mensaje_id"],
                "conversacion_id": result_conversation_id,
                "audio_id": audio_id,
                "transcripcion": transcripcion_texto,
                "respuesta": conversation_result["respuesta"],
                "duracion_segundos": duracion,
                "idioma_detectado": transcripcion_result["idioma"],
                "metadata": {
                    **conversation_result["metadata"],
                    "audio": {
                        "url": audio_url,
                        "formato": formato,
                        "tamano_bytes": tamano,
                        "confianza_transcripcion": transcripcion_result["confianza"]
                    }
                }
            }
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            raise ValueError(f"Error al procesar mensaje de audio de WhatsApp: {str(e)}")

    def process_audio_message(self,
                            canal_id: UUID,
                            canal_identificador: str,
                            empresa_id: UUID,
                            chatbot_id: UUID,
                            audio_base64: str,
                            formato_audio: str,
                            idioma: Optional[str] = None,
                            conversacion_id: Optional[UUID] = None,
                            lead_id: Optional[UUID] = None,
                            metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Procesa un mensaje de audio completo: decodifica, transcribe, guarda y responde
        
        Args:
            canal_id: ID del canal
            canal_identificador: Identificador del canal
            empresa_id: ID de la empresa
            chatbot_id: ID del chatbot
            audio_base64: Audio codificado en base64
            formato_audio: Formato del audio
            idioma: Código del idioma para la transcripción
            conversacion_id: ID de la conversación existente (opcional)
            lead_id: ID del lead existente (opcional)
            metadata: Metadatos adicionales (opcional)
            
        Returns:
            Diccionario con la información de la respuesta
        """
        try:
            # 1. Decodificar y guardar temporalmente el audio
            temp_path, formato, tamano, duracion = self._decode_and_save_audio(audio_base64, formato_audio)
            
            # 2. Transcribir el audio
            transcripcion_result = self.transcribe_audio(temp_path, idioma)
            transcripcion_texto = transcripcion_result["texto"]
            
            # Preparar metadatos sanitizados (sin datos personales)
            sanitized_metadata = {}
            if metadata:
                # Filtrar datos personales
                sanitized_metadata = {k: v for k, v in metadata.items() 
                              if k not in ["nombre", "apellido", "email", "telefono", 
                                          "direccion", "dni", "nif"]}
            
            # Añadir información del audio a los metadatos
            sanitized_metadata.update({
                "tipo_mensaje": "audio",
                "formato_audio": formato,
                "duracion_audio": duracion,
                "tamano_audio": tamano,
                "idioma_detectado": transcripcion_result["idioma"]
            })
            
            # 3. Procesar el mensaje de texto transcrito usando el servicio de conversación
            conversation_result = conversation_service.process_channel_message(
                canal_id=canal_id,
                canal_identificador=canal_identificador,
                empresa_id=empresa_id,
                chatbot_id=chatbot_id,
                mensaje=transcripcion_texto,
                lead_id=lead_id,
                metadata=sanitized_metadata
            )
            
            # Obtener el conversation_id del resultado
            result_conversation_id = UUID(conversation_result["conversacion_id"])
            
            # 4. Subir el audio a Supabase
            audio_url = self._upload_to_supabase(
                temp_path, 
                result_conversation_id, 
                conversation_result["mensaje_id"]
            )
            
            # 5. Guardar la información del audio en la base de datos
            audio_metadata = {
                "modelo": "whisper-1",
                "idioma": transcripcion_result["idioma"],
                "duracion": duracion,
                "tamano": tamano,
                "formato": formato,
                "confianza": transcripcion_result["confianza"],
                "segmentos": transcripcion_result["segmentos"],
                "adicional": sanitized_metadata
            }
            
            audio_id = self.save_audio_message(
                conversacion_id=result_conversation_id,
                mensaje_id=conversation_result["mensaje_id"],
                audio_url=audio_url,
                transcripcion=transcripcion_texto,
                metadata=audio_metadata
            )
            
            # 6. Preparar respuesta
            return {
                "mensaje_id": conversation_result["mensaje_id"],
                "conversacion_id": result_conversation_id,
                "audio_id": audio_id,
                "transcripcion": transcripcion_texto,
                "respuesta": conversation_result["respuesta"],
                "duracion_segundos": duracion,
                "idioma_detectado": transcripcion_result["idioma"],
                "metadata": {
                    **conversation_result["metadata"],
                    "audio": {
                        "url": audio_url,
                        "formato": formato,
                        "tamano_bytes": tamano,
                        "confianza_transcripcion": transcripcion_result["confianza"]
                    }
                }
            }
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            raise ValueError(f"Error al procesar mensaje de audio: {str(e)}")


# Crear instancia singleton
audio_service = AudioService()