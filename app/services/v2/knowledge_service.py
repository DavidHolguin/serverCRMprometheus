from typing import Dict, List, Any, Optional
from uuid import UUID, uuid4
import json
from datetime import datetime
import logging
import sys
import importlib.util
import traceback
import re

# Importación necesaria para la serialización de datetime
from datetime import datetime, timezone

from langchain_openai import OpenAIEmbeddings

# Configurar logger
logger = logging.getLogger(__name__)

# Verificar y cargar PyPDF2 explícitamente
try:
    if importlib.util.find_spec("PyPDF2") is None:
        logger.error("PyPDF2 no está instalado. Intentando instalarlo...")
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "PyPDF2"])
        logger.info("PyPDF2 instalado correctamente.")
    
    import PyPDF2
    logger.info(f"PyPDF2 importado correctamente. Versión: {PyPDF2.__version__}")
    
    # Importamos cada loader directamente desde el archivo base
    # para evitar la carga del módulo language_parser problemático
    try:
        # Intentar importaciones directas para evitar problemas con módulos intermedios
        from langchain.document_loaders.csv_loader import CSVLoader
        from langchain.document_loaders.text import TextLoader
        # Si hay importaciones más específicas disponibles:
        from langchain.document_loaders.unstructured import UnstructuredFileLoader
        # Creamos clases simples para los loaders si es necesario
        class PyPDFLoader:
            def __init__(self, file_path):
                self.file_path = file_path
            
            def load(self):
                from langchain.docstore.document import Document
                # Lógica básica para cargar un PDF
                pdf = PyPDF2.PdfReader(self.file_path)
                return [Document(page_content=page.extract_text(), metadata={"source": self.file_path, "page": i}) 
                        for i, page in enumerate(pdf.pages)]
        
        class UnstructuredWordDocumentLoader(UnstructuredFileLoader):
            """Loader para documentos de Word usando Unstructured"""
            pass
        
        class UnstructuredExcelLoader(UnstructuredFileLoader):
            """Loader para archivos Excel usando Unstructured"""
            pass
    except ImportError as e:
        # Fallback - utilizar implementaciones más simples si las importaciones fallan
        logger.error(f"Error en importaciones de loaders: {e}")
        # Implementaciones mínimas que pueden funcionar para casos básicos
        from langchain.docstore.document import Document
        
        class CSVLoader:
            def __init__(self, file_path):
                self.file_path = file_path
            
            def load(self):
                import csv
                docs = []
                with open(self.file_path, 'r', encoding='utf-8') as f:
                    csv_reader = csv.reader(f)
                    headers = next(csv_reader)
                    for row in csv_reader:
                        content = " ".join(row)
                        docs.append(Document(page_content=content, metadata={"source": self.file_path}))
                return docs
        
        class PyPDFLoader:
            def __init__(self, file_path):
                self.file_path = file_path
            
            def load(self):
                pdf = PyPDF2.PdfReader(self.file_path)
                return [Document(page_content=page.extract_text(), metadata={"source": self.file_path, "page": i}) 
                        for i, page in enumerate(pdf.pages)]
        
        class TextLoader:
            def __init__(self, file_path):
                self.file_path = file_path
            
            def load(self):
                with open(self.file_path, 'r', encoding='utf-8') as f:
                    text = f.read()
                return [Document(page_content=text, metadata={"source": self.file_path})]
        
        class UnstructuredWordDocumentLoader:
            def __init__(self, file_path):
                self.file_path = file_path
            
            def load(self):
                # Implementación básica para documentos Word
                return [Document(page_content="[Contenido del documento Word]", metadata={"source": self.file_path})]
        
        class UnstructuredExcelLoader:
            def __init__(self, file_path):
                self.file_path = file_path
            
            def load(self):
                # Implementación básica para Excel
                return [Document(page_content="[Contenido del archivo Excel]", metadata={"source": self.file_path})]

except ImportError as e:
    logger.error(f"Error crítico al importar PyPDF2: {e}")
    # Si PyPDF2 no está disponible, definimos versiones muy básicas de nuestras clases
    # que al menos no causarán errores al inicializar el servicio
    from langchain.docstore.document import Document
    
    class PyPDFLoader:
        def __init__(self, file_path):
            self.file_path = file_path
        
        def load(self):
            raise ImportError("PyPDF2 no está instalado. No se puede procesar archivos PDF.")
    
    class CSVLoader:
        def __init__(self, file_path):
            self.file_path = file_path
        
        def load(self):
            raise ImportError("Error al cargar las dependencias necesarias.")
    
    class TextLoader:
        def __init__(self, file_path):
            self.file_path = file_path
        
            def load(self):
                with open(self.file_path, 'r', encoding='utf-8') as f:
                    text = f.read()
                return [Document(page_content=text, metadata={"source": self.file_path})]
    
    class UnstructuredWordDocumentLoader:
        def __init__(self, file_path):
            self.file_path = file_path
        
        def load(self):
            raise ImportError("No se pueden cargar documentos Word sin las dependencias necesarias.")
    
    class UnstructuredExcelLoader:
        def __init__(self, file_path):
            self.file_path = file_path
        
        def load(self):
            raise ImportError("No se pueden cargar archivos Excel sin las dependencias necesarias.")

from langchain.text_splitter import RecursiveCharacterTextSplitter
from supabase.client import Client as SupabaseClient

from app.core.config import settings
from app.db.supabase_client import supabase
from app.services.event_service import event_service
from app.models.v2.agent import AgentKnowledge

class KnowledgeService:
    """Servicio para gestionar el conocimiento de los agentes"""

    def __init__(self):
        """Inicializa el servicio de conocimiento"""
        try:
            # Verificar la clave API de OpenAI
            if not settings.OPENAI_API_KEY:
                logger.error("La clave API de OpenAI no está configurada")
                raise ValueError("La clave API de OpenAI no está configurada. Verifique las variables de entorno.")
                
            # Inicializar el modelo de embeddings con opciones explícitas
            self.embeddings = OpenAIEmbeddings(
                model="text-embedding-3-small",  # Modelo específico de pequeño tamaño
                openai_api_key=settings.OPENAI_API_KEY,
                openai_api_base=getattr(settings, 'OPENAI_API_BASE', None),  # URL base opcional
                dimensions=1536,  # Dimensiones por defecto para text-embedding-3-small
                show_progress_bar=False,  # Desactivar barra de progreso
                timeout=60  # Tiempo de espera en segundos
            )
            logger.info("Inicializado el modelo de embeddings text-embedding-3-small")
        except Exception as e:
            logger.error(f"Error al inicializar OpenAIEmbeddings: {str(e)}")
            # Crear una implementación de respaldo si falla
            self.embeddings = None
        
        # Usar parámetros en la inicialización para almacenarlos como atributos directos
        self.chunk_size = 1000
        self.chunk_overlap = 200
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap
        )
        
        # Verificar la disponibilidad de las dependencias al inicio
        logger.info("Verificando dependencias del servicio de conocimiento...")
        try:
            import PyPDF2
            logger.info(f"PyPDF2 disponible: versión {PyPDF2.__version__}")
            
            # Verificar la conexión a OpenAI
            try:
                import openai
                logger.info(f"openai SDK disponible: versión {openai.__version__}")
            except ImportError:
                logger.error("Biblioteca openai no disponible")
        except ImportError:
            logger.error("PyPDF2 no está disponible. La carga de PDFs no funcionará.")

    # Método auxiliar para convertir datetime a un formato serializable
    def _serialize_datetime(self, obj):
        """Convierte objetos datetime a strings ISO"""
        if isinstance(obj, datetime):
            return obj.isoformat()
        raise TypeError(f"Type {type(obj)} not serializable")
        
    def _clean_text(self, text: str) -> str:
        """
        Limpia el texto eliminando espacios en blanco y saltos de línea innecesarios
        
        Args:
            text: Texto a limpiar
            
        Returns:
            Texto limpio
        """
        if not text:
            return ""
            
        # Reemplazar múltiples espacios en blanco por uno solo
        text = re.sub(r'\s+', ' ', text)
        
        # Reemplazar múltiples saltos de línea por uno solo
        text = re.sub(r'\n+', '\n', text)
        
        # Eliminar espacios en blanco al inicio y fin de cada línea
        lines = [line.strip() for line in text.split('\n')]
        
        # Volver a unir las líneas
        text = '\n'.join(lines)
        
        # Eliminar líneas vacías consecutivas
        text = re.sub(r'\n\s*\n', '\n', text)
        
        # Eliminar espacios en blanco al inicio y fin del texto
        text = text.strip()
        
        return text
        
    async def process_document(
        self,
        file_path: str,
        file_type: str,
        agent_id: UUID,
        company_id: UUID,
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[AgentKnowledge]:
        """
        Procesa un documento y lo convierte en conocimiento para el agente
        
        Args:
            file_path: Ruta al archivo
            file_type: Tipo de archivo (pdf, csv, txt, docx, xlsx)
            agent_id: ID del agente
            company_id: ID de la empresa
            metadata: Metadatos adicionales
            
        Returns:
            Lista de objetos AgentKnowledge creados
        """
        try:
            # Verificar que el modelo de embeddings esté inicializado
            if not self.embeddings:
                raise ValueError("El modelo de embeddings no está inicializado correctamente")
            
            # Seleccionar el loader adecuado según el tipo de archivo
            loader = self._get_document_loader(file_path, file_type)
            
            # Cargar el documento
            logger.info(f"Cargando documento {file_path} con loader para tipo {file_type}")
            documents = loader.load()
            
            # Limpiar el contenido de cada documento antes de dividirlo
            for i, doc in enumerate(documents):
                clean_content = self._clean_text(doc.page_content)
                documents[i].page_content = clean_content
                logger.debug(f"Documento {i} limpiado. Tamaño original: {len(doc.page_content)}, tamaño limpio: {len(clean_content)}")
            
            # Dividir el texto en chunks
            logger.info(f"Dividiendo documento en chunks con tamaño {self.chunk_size} y solapamiento {self.chunk_overlap}")
            texts = self.text_splitter.split_documents(documents)
            
            # Generar embeddings
            logger.info(f"Generando embeddings para {len(texts)} chunks de texto")
            embeddings_list = []
            
            try:
                for i, text in enumerate(texts):
                    try:
                        # Registrar cada chunk que se procesa
                        logger.debug(f"Procesando chunk {i+1}/{len(texts)}, longitud: {len(text.page_content)} caracteres")
                        embedding = await self.embeddings.aembed_query(text.page_content)
                        embeddings_list.append(embedding)
                    except Exception as e:
                        logger.error(f"Error generando embedding para chunk {i+1}: {e}")
                        # Si falla un chunk individual, usar un embedding vacío para este chunk
                        # pero seguir procesando el resto
                        embeddings_list.append([0] * 1536)  # Vector de 1536 dimensiones con ceros
            except Exception as e:
                logger.error(f"Error fatal al generar embeddings: {e}")
                logger.error(traceback.format_exc())
                raise
            
            logger.info(f"Embeddings generados con éxito: {len(embeddings_list)}")
            
            # Crear entradas de conocimiento
            knowledge_entries = []
            for i, (text, embedding) in enumerate(zip(texts, embeddings_list)):
                try:
                    # Usar uuid4() para generar un UUID válido
                    knowledge_id = uuid4()
                    logger.debug(f"Creando conocimiento con ID: {knowledge_id}")
                    
                    # Limpiar el contenido una vez más antes de guardar
                    content = self._clean_text(text.page_content)
                    
                    # Fechas en formato ISO para serialización
                    current_time = datetime.now().isoformat()
                    
                    # Crear objeto de conocimiento
                    knowledge = AgentKnowledge(
                        id=knowledge_id,
                        agent_id=agent_id,
                        type="processed_document",
                        source=file_path,
                        format="text_with_embeddings",
                        content=content,  # Usar el contenido limpio
                        embeddings=embedding,
                        metadata={
                            **(metadata or {}),
                            "document_type": file_type,
                            "chunk_index": i,
                            "total_chunks": len(texts),
                            "original_metadata": text.metadata
                        },
                        priority=1,
                        created_at=datetime.now(),
                        updated_at=datetime.now()
                    )
                    
                    # Convertir a diccionario excluyendo embeddings
                    knowledge_dict = knowledge.model_dump(exclude={'embeddings'})
                    
                    # Asegurarnos que el ID esté como string en el diccionario
                    knowledge_dict['id'] = str(knowledge_id)
                    
                    # Usar el nombre de columna correcto según la estructura de la base de datos
                    # Asegurarnos que agente_id se envía correctamente
                    knowledge_dict['agente_id'] = str(agent_id)
                    
                    # Eliminar agent_id si existe (usamos agente_id en su lugar)
                    if 'agent_id' in knowledge_dict:
                        del knowledge_dict['agent_id']
                    
                    # Convertir fechas a strings ISO
                    knowledge_dict['created_at'] = knowledge_dict['created_at'].isoformat()
                    knowledge_dict['updated_at'] = knowledge_dict['updated_at'].isoformat()
                    
                    # Asegurar que tipo sea 'tipo' (no 'type') según la columna de la tabla
                    knowledge_dict['tipo'] = knowledge_dict.get('type', 'processed_document')
                    if 'type' in knowledge_dict:
                        del knowledge_dict['type']
                        
                    # Asegurar que usamos 'fuente' en lugar de 'source'
                    knowledge_dict['fuente'] = knowledge_dict.get('source', file_path)
                    if 'source' in knowledge_dict:
                        del knowledge_dict['source']
                        
                    # Asegurar que usamos 'formato' en lugar de 'format'
                    knowledge_dict['formato'] = knowledge_dict.get('format', 'text_with_embeddings')
                    if 'format' in knowledge_dict:
                        del knowledge_dict['format']
                        
                    # Asegurar que usamos 'contenido' en lugar de 'content'
                    knowledge_dict['contenido'] = knowledge_dict.get('content', content)  # Usar el contenido limpio
                    if 'content' in knowledge_dict:
                        del knowledge_dict['content']
                        
                    # Asegurar que usamos 'prioridad' en lugar de 'priority'
                    knowledge_dict['prioridad'] = knowledge_dict.get('priority', 1)
                    if 'priority' in knowledge_dict:
                        del knowledge_dict['priority']
                    
                    # Debugging - registrar el diccionario antes de enviarlo
                    logger.debug(f"Enviando a la base de datos: {json.dumps(knowledge_dict)}")
                    
                    # Guardar en la base de datos
                    result = supabase.table("agente_conocimiento").insert(knowledge_dict).execute()
                    
                    if result.data:
                        # Guardar embeddings en la tabla de vectores
                        vector_data = {
                            "knowledge_id": str(knowledge_id),
                            "embedding": embedding
                        }
                        vector_result = supabase.table("agente_conocimiento_vectores").insert(vector_data).execute()
                        logger.debug(f"Vector guardado para knowledge_id {knowledge_id}")
                        
                        knowledge_entries.append(knowledge)
                    else:
                        logger.warning(f"No se pudo guardar el conocimiento para chunk {i+1}")
                except Exception as e:
                    logger.error(f"Error al guardar conocimiento para chunk {i+1}: {str(e)}")
                    logger.error(traceback.format_exc())
            
            # Registrar evento de procesamiento exitoso
            try:
                event_service.log_event(
                    empresa_id=company_id,
                    event_type="agent_knowledge_added",
                    entidad_origen_tipo="agent",
                    entidad_origen_id=agent_id,
                    resultado="success",
                    detalle=f"Documento procesado exitosamente: {file_path}",
                    metadata={
                        "file_type": file_type,
                        "chunks_created": len(texts),
                        "knowledge_entries": len(knowledge_entries)
                    }
                )
            except Exception as e:
                logger.error(f"Error al registrar evento de éxito: {str(e)}")
            
            logger.info(f"Procesamiento completo. Guardados {len(knowledge_entries)} chunks de conocimiento")
            return knowledge_entries
            
        except Exception as e:
            logger.error(f"Error procesando documento: {e}")
            logger.error(traceback.format_exc())
            # Registrar evento de error
            try:
                event_service.log_event(
                    empresa_id=company_id,
                    event_type="agent_knowledge_error",
                    entidad_origen_tipo="agent",
                    entidad_origen_id=agent_id,
                    resultado="error",
                    detalle=f"Error procesando documento: {str(e)}",
                    metadata={
                        "file_type": file_type,
                        "error": str(e),
                        "traceback": traceback.format_exc()
                    }
                )
            except Exception as log_err:
                logger.error(f"Error al registrar evento de error: {str(log_err)}")
            raise

    def _get_document_loader(self, file_path: str, file_type: str):
        """
        Selecciona el loader adecuado según el tipo de archivo
        
        Args:
            file_path: Ruta al archivo
            file_type: Tipo de archivo
            
        Returns:
            Loader apropiado para el tipo de archivo
        """
        try:
            loaders = {
                "pdf": PyPDFLoader,
                "csv": CSVLoader,
                "txt": TextLoader,
                "docx": UnstructuredWordDocumentLoader,
                "xlsx": self._get_excel_loader,
                "xls": self._get_excel_loader,
                "url": self._get_url_loader,
                "html": self._get_html_loader
            }
            
            loader_func_or_class = loaders.get(file_type.lower())
            if not loader_func_or_class:
                raise ValueError(f"Tipo de archivo no soportado: {file_type}")
                
            if callable(loader_func_or_class) and not isinstance(loader_func_or_class, type):
                # Es una función que devuelve un loader, no una clase
                return loader_func_or_class(file_path)
            else:
                # Es una clase de loader
                return loader_func_or_class(file_path)
        except Exception as e:
            logger.error(f"Error al obtener loader para {file_type}: {e}")
            raise
    
    def _get_excel_loader(self, file_path):
        """
        Obtiene un loader específico para archivos Excel
        
        Args:
            file_path: Ruta al archivo Excel
            
        Returns:
            Loader para archivos Excel
        """
        try:
            # Intentar primero con un loader especializado de pandas
            try:
                import pandas as pd
                from langchain.docstore.document import Document
                
                # Definir un loader personalizado basado en pandas
                class PandasExcelLoader:
                    def __init__(self, file_path):
                        self.file_path = file_path
                    
                    def load(self):
                        # Leer todas las hojas del archivo Excel
                        sheets_dict = pd.read_excel(self.file_path, sheet_name=None)
                        documents = []
                        
                        # Procesar cada hoja como un documento separado
                        for sheet_name, df in sheets_dict.items():
                            # Convertir el dataframe a string
                            content = df.to_string(index=False)
                            # Crear un documento para cada hoja
                            doc = Document(
                                page_content=content,
                                metadata={"source": self.file_path, "sheet": sheet_name}
                            )
                            documents.append(doc)
                        
                        return documents
                
                return PandasExcelLoader(file_path)
            except ImportError:
                # Si pandas no está disponible, usar UnstructuredExcelLoader
                return UnstructuredExcelLoader(file_path)
        except Exception as e:
            logger.error(f"Error al crear loader para Excel: {e}")
            # Utilizar un loader simple como fallback
            from langchain.docstore.document import Document
            
            class SimpleExcelLoader:
                def __init__(self, file_path):
                    self.file_path = file_path
                
                def load(self):
                    return [Document(
                        page_content=f"[Contenido del archivo Excel: {self.file_path}]",
                        metadata={"source": self.file_path}
                    )]
            
            return SimpleExcelLoader(file_path)
    
    def _get_url_loader(self, url):
        """
        Obtiene un loader para URLs
        
        Args:
            url: URL a cargar
            
        Returns:
            Loader para URLs
        """
        try:
            # Intentar importar el loader de URLs
            try:
                from langchain.document_loaders import WebBaseLoader
                return WebBaseLoader(url)
            except ImportError:
                # Si no está disponible, crear un loader simple
                import requests
                from bs4 import BeautifulSoup
                from langchain.docstore.document import Document
                
                class SimpleWebLoader:
                    def __init__(self, url):
                        self.url = url
                    
                    def load(self):
                        try:
                            response = requests.get(self.url)
                            response.raise_for_status()
                            soup = BeautifulSoup(response.content, 'html.parser')
                            
                            # Eliminar scripts, estilos y contenido oculto
                            for script in soup(["script", "style", "meta", "link"]):
                                script.extract()
                            
                            # Extraer el texto
                            text = soup.get_text(separator=' ')
                            
                            # Limpiar el texto
                            lines = (line.strip() for line in text.splitlines())
                            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
                            text = ' '.join(chunk for chunk in chunks if chunk)
                            
                            return [Document(page_content=text, metadata={"source": self.url})]
                        except Exception as e:
                            logger.error(f"Error al cargar URL {self.url}: {e}")
                            return [Document(page_content=f"Error al cargar URL: {str(e)}", metadata={"source": self.url})]
                
                return SimpleWebLoader(url)
        except Exception as e:
            logger.error(f"Error al crear loader para URL: {e}")
            # Utilizar un loader muy simple como fallback
            from langchain.docstore.document import Document
            
            class VerySimpleWebLoader:
                def __init__(self, url):
                    self.url = url
                
                def load(self):
                    return [Document(
                        page_content=f"[Contenido de la URL: {self.url}]",
                        metadata={"source": self.url}
                    )]
            
            return VerySimpleWebLoader(url)
    
    def _get_html_loader(self, file_path):
        """
        Obtiene un loader para archivos HTML
        
        Args:
            file_path: Ruta al archivo HTML
            
        Returns:
            Loader para archivos HTML
        """
        try:
            # Intentar importar el loader de HTML
            from bs4 import BeautifulSoup
            from langchain.docstore.document import Document
            
            class SimpleHTMLLoader:
                def __init__(self, file_path):
                    self.file_path = file_path
                
                def load(self):
                    try:
                        with open(self.file_path, 'r', encoding='utf-8') as f:
                            soup = BeautifulSoup(f, 'html.parser')
                            
                            # Eliminar scripts, estilos y contenido oculto
                            for script in soup(["script", "style", "meta", "link"]):
                                script.extract()
                            
                            # Extraer el texto
                            text = soup.get_text(separator=' ')
                            
                            # Limpiar el texto
                            lines = (line.strip() for line in text.splitlines())
                            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
                            text = ' '.join(chunk for chunk in chunks if chunk)
                            
                            return [Document(page_content=text, metadata={"source": self.file_path})]
                    except Exception as e:
                        logger.error(f"Error al cargar HTML {self.file_path}: {e}")
                        return [Document(page_content=f"Error al cargar HTML: {str(e)}", metadata={"source": self.file_path})]
            
            return SimpleHTMLLoader(file_path)
        except Exception as e:
            logger.error(f"Error al crear loader para HTML: {e}")
            from langchain.docstore.document import Document
            
            class VerySimpleHTMLLoader:
                def __init__(self, file_path):
                    self.file_path = file_path
                
                def load(self):
                    return [Document(
                        page_content=f"[Contenido del archivo HTML: {self.file_path}]",
                        metadata={"source": self.file_path}
                    )]
            
            return VerySimpleHTMLLoader(file_path)

# Crear instancia singleton
knowledge_service = KnowledgeService()