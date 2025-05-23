from typing import Dict, List, Any, Optional
from uuid import UUID, uuid4
import json
from datetime import datetime
import logging
import sys
import importlib.util
import traceback
import re
import os

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
    
    # En LangChain 0.3, los loaders se han movido a paquetes específicos
    try:
        # Importaciones para LangChain 0.3
        from langchain_text_splitters import RecursiveCharacterTextSplitter
        from langchain_community.document_loaders.csv_loader import CSVLoader
        # Corrección en la ruta de importación del TextLoader
        from langchain_community.document_loaders import TextLoader
        from langchain_community.document_loaders.unstructured import UnstructuredFileLoader
        from langchain_community.document_loaders.pdf import PyPDFLoader
        
        # Definimos clases personalizadas basadas en UnstructuredFileLoader
        class UnstructuredWordDocumentLoader(UnstructuredFileLoader):
            """Loader para documentos de Word usando Unstructured"""
            def __init__(self, file_path: str, **kwargs):
                super().__init__(file_path, **kwargs)
                
        class UnstructuredExcelLoader(UnstructuredFileLoader):
            """Loader para archivos Excel usando Unstructured"""
            def __init__(self, file_path: str, **kwargs):
                super().__init__(file_path, **kwargs)
    except ImportError as e:
        # Fallback - utilizar implementaciones más simples si las importaciones fallan
        logger.error(f"Error en importaciones de loaders: {e}")
        # Implementaciones mínimas que pueden funcionar para casos básicos
        from langchain_core.documents import Document
        
        class CSVLoader:
            def __init__(self, file_path: str):
                self.file_path = file_path
                
            def load(self):
                import csv
                documents = []
                with open(self.file_path, 'r', encoding='utf-8') as f:
                    csv_reader = csv.reader(f)
                    headers = next(csv_reader)
                    for i, row in enumerate(csv_reader):
                        # Combine headers and row values into a single string
                        content = "\n".join([f"{headers[i]}: {value}" for i, value in enumerate(row) if i < len(headers)])
                        document = Document(page_content=content, metadata={"source": self.file_path, "row": i})
                        documents.append(document)
                return documents
                
        class PyPDFLoader:
            def __init__(self, file_path: str):
                self.file_path = file_path
                
            def load(self):
                documents = []
                with open(self.file_path, 'rb') as f:
                    pdf_reader = PyPDF2.PdfReader(f)
                    for i, page in enumerate(pdf_reader.pages):
                        text = page.extract_text()
                        if text.strip():  # Solo añadir si hay texto
                            document = Document(page_content=text, metadata={"source": self.file_path, "page": i})
                            documents.append(document)
                return documents
                
        class TextLoader:
            def __init__(self, file_path: str):
                self.file_path = file_path
                
            def load(self):
                with open(self.file_path, 'r', encoding='utf-8') as f:
                    text = f.read()
                return [Document(page_content=text, metadata={"source": self.file_path})]
                
        class UnstructuredFileLoader:
            def __init__(self, file_path: str, **kwargs):
                self.file_path = file_path
                
            def load(self):
                # Implementación básica que lee el archivo como texto
                with open(self.file_path, 'r', encoding='utf-8') as f:
                    text = f.read()
                return [Document(page_content=text, metadata={"source": self.file_path})]
                
        class UnstructuredWordDocumentLoader(UnstructuredFileLoader):
            pass
            
        class UnstructuredExcelLoader(UnstructuredFileLoader):
            pass
            
        class RecursiveCharacterTextSplitter:
            def __init__(self, chunk_size=1000, chunk_overlap=200):
                self.chunk_size = chunk_size
                self.chunk_overlap = chunk_overlap
                
            def split_documents(self, documents):
                # Implementación básica para dividir documentos
                split_docs = []
                for doc in documents:
                    text = doc.page_content
                    # Dividir texto en fragmentos de tamaño aproximado chunk_size con superposición chunk_overlap
                    start = 0
                    while start < len(text):
                        end = start + self.chunk_size
                        if end > len(text):
                            end = len(text)
                        # Crear un nuevo documento con el fragmento
                        split_docs.append(Document(
                            page_content=text[start:end],
                            metadata=doc.metadata
                        ))
                        start = end - self.chunk_overlap
                return split_docs
except Exception as e:
    logger.error(f"Error importando las dependencias requeridas: {e}")
    # Definiciones mínimas para evitar errores de importación
    
    class Document:
        def __init__(self, page_content, metadata=None):
            self.page_content = page_content
            self.metadata = metadata or {}
            
    class CSVLoader:
        def __init__(self, file_path):
            self.file_path = file_path
        def load(self):
            return []
            
    class PyPDFLoader:
        def __init__(self, file_path):
            self.file_path = file_path
        def load(self):
            return []
            
    class TextLoader:
        def __init__(self, file_path):
            self.file_path = file_path
        def load(self):
            return []
            
    class UnstructuredFileLoader:
        def __init__(self, file_path, **kwargs):
            self.file_path = file_path
        def load(self):
            return []
            
    class UnstructuredWordDocumentLoader:
        def __init__(self, file_path, **kwargs):
            self.file_path = file_path
        def load(self):
            return []
            
    class UnstructuredExcelLoader:
        def __init__(self, file_path, **kwargs):
            self.file_path = file_path
        def load(self):
            return []
            
    class RecursiveCharacterTextSplitter:
        def __init__(self, chunk_size=1000, chunk_overlap=200):
            self.chunk_size = chunk_size
            self.chunk_overlap = chunk_overlap
        def split_documents(self, documents):
            return []

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
            # Verificar que el tipo de archivo sea válido
            file_type = file_type.lower()
            logger.info(f"Obteniendo loader para archivo de tipo: {file_type}")
            
            # Si es un PDF, intentar primero con el loader de LangChain Community
            if file_type == "pdf":
                try:
                    # Importar explícitamente pypdf para verificar que esté disponible
                    try:
                        import pypdf
                        logger.info(f"pypdf importado correctamente: {pypdf.__version__}")
                        from langchain_community.document_loaders.pdf import PyPDFLoader
                        return PyPDFLoader(file_path)
                    except ImportError:
                        # Si pypdf falla, intentar con PyPDF2 (anterior)
                        import PyPDF2
                        logger.info(f"PyPDF2 importado como alternativa: {PyPDF2.__version__}")
                        
                        # Implementar un loader personalizado con PyPDF2
                        from langchain_core.documents import Document
                        
                        class CustomPyPDF2Loader:
                            def __init__(self, file_path):
                                self.file_path = file_path
                                
                            def load(self):
                                with open(self.file_path, 'rb') as f:
                                    pdf = PyPDF2.PdfReader(f)
                                    documents = []
                                    for i, page in enumerate(pdf.pages):
                                        text = page.extract_text()
                                        if text.strip():  # Solo añadir si hay texto
                                            doc = Document(
                                                page_content=text,
                                                metadata={"source": self.file_path, "page": i}
                                            )
                                            documents.append(doc)
                                return documents
                                
                        return CustomPyPDF2Loader(file_path)
                except Exception as pdf_error:
                    logger.error(f"Error al intentar cargar PDF usando ambos métodos: {pdf_error}")
                    raise ValueError(f"Error al obtener loader para pdf: {str(pdf_error)}")
            
            # Mapa de tipos de archivo a loaders
            loaders = {
                "csv": CSVLoader,
                "txt": TextLoader,
                "docx": UnstructuredWordDocumentLoader,
                "xlsx": self._get_excel_loader,
                "xls": self._get_excel_loader,
                "url": self._get_url_loader,
                "html": self._get_html_loader
            }
            
            loader_func_or_class = loaders.get(file_type)
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
            logger.error(traceback.format_exc())
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
        Obtiene un loader para URLs utilizando Playwright para una mejor extracción de contenido
        
        Args:
            url: URL a cargar
            
        Returns:
            Loader para URLs
        """
        try:
            # Intentar cargar con Playwright para mejor compatibilidad
            try:
                # Importar dependencias necesarias
                import nest_asyncio
                from playwright.async_api import async_playwright
                from langchain_core.documents import Document
                import asyncio
                
                # Aplicar nest_asyncio para permitir bucles anidados (necesario si se ejecuta desde un notebook o entorno interactivo)
                try:
                    nest_asyncio.apply()
                except:
                    logger.warning("Error al aplicar nest_asyncio, podría causar problemas en algunos entornos")
                
                # Crear una clase loader personalizada con Playwright
                class PlaywrightURLLoader:
                    def __init__(self, url):
                        self.url = url
                    
                    async def _load_with_playwright(self):
                        try:
                            documents = []
                            async with async_playwright() as p:
                                browser = await p.chromium.launch(headless=True)
                                page = await browser.new_page()
                                
                                # Agregar logger para depuración
                                logger.info(f"Navegando a URL: {self.url}")
                                
                                # Navegar a la página con timeout adecuado
                                await page.goto(self.url, wait_until="domcontentloaded", timeout=30000)
                                
                                # Esperar a que la página cargue completamente
                                await page.wait_for_load_state("networkidle", timeout=10000)
                                
                                # Extraer el contenido y metadatos
                                content = await page.content()
                                title = await page.title()
                                
                                # Obtener el texto principal de la página
                                text = await page.evaluate('''() => {
                                    // Seleccionar el contenido principal, excluyendo elementos de navegación, etc.
                                    // Primero intentar con article, main o #content
                                    const mainContent = document.querySelector('article, main, #content, .content, .article, .post');
                                    
                                    if (mainContent) {
                                        return mainContent.innerText;
                                    }
                                    
                                    // Si no encontramos contenido principal, usar el body pero excluir elementos típicos de navegación
                                    const body = document.body;
                                    const excludeElements = document.querySelectorAll('nav, header, footer, aside, .sidebar, .menu, .ad, .advertisement');
                                    
                                    // Clonar el body para no modificar la página original
                                    const bodyClone = body.cloneNode(true);
                                    
                                    // Eliminar elementos a excluir
                                    excludeElements.forEach(el => {
                                        const elInClone = bodyClone.querySelector(`#${el.id}`) || 
                                                        bodyClone.querySelector(`.${Array.from(el.classList).join('.')}`);
                                        if (elInClone) {
                                            elInClone.remove();
                                        }
                                    });
                                    
                                    return bodyClone.innerText;
                                }''')
                                
                                # Limpiar el texto
                                cleaned_text = self._clean_text(text)
                                
                                # Crear metadata útil
                                metadata = {
                                    "source": self.url,
                                    "title": title,
                                    "content_type": "url"
                                }
                                
                                # Crear documento
                                documents.append(Document(
                                    page_content=cleaned_text,
                                    metadata=metadata
                                ))
                                
                                # Cerrar el navegador
                                await browser.close()
                                
                            return documents
                        except Exception as e:
                            logger.error(f"Error en PlaywrightURLLoader: {e}")
                            # Retornar un documento con un mensaje de error
                            return [Document(
                                page_content=f"Error al cargar URL con Playwright: {str(e)}",
                                metadata={"source": self.url, "error": True}
                            )]
                    
                    def _clean_text(self, text):
                        """Limpia el texto extraído"""
                        import re
                        
                        # Eliminar espacios en blanco extra
                        text = re.sub(r'\s+', ' ', text)
                        
                        # Eliminar líneas vacías
                        text = re.sub(r'\n\s*\n', '\n', text)
                        
                        # Eliminar espacios al inicio y fin
                        text = text.strip()
                        
                        return text
                    
                    def load(self):
                        """Carga la URL usando Playwright"""
                        try:
                            # Ejecutar la función asíncrona en el bucle de eventos
                            loop = asyncio.get_event_loop()
                            return loop.run_until_complete(self._load_with_playwright())
                        except Exception as e:
                            logger.error(f"Error al ejecutar PlaywrightURLLoader: {e}")
                            # Retornar un documento con mensaje de error
                            return [Document(
                                page_content=f"Error al cargar URL: {str(e)}",
                                metadata={"source": self.url, "error": True}
                            )]
                
                # Retornar el loader personalizado
                logger.info(f"Usando PlaywrightURLLoader para URL: {url}")
                return PlaywrightURLLoader(url)
                
            except ImportError as e:
                logger.warning(f"No se pudo importar Playwright: {e}. Intentando método alternativo...")
                
                # Si Playwright no está disponible, intentar con BeautifulSoup y requests
                import requests
                from bs4 import BeautifulSoup
                from langchain_core.documents import Document
                
                class BeautifulSoupURLLoader:
                    def __init__(self, url):
                        self.url = url
                    
                    def load(self):
                        try:
                            # Configurar headers para simular un navegador
                            headers = {
                                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                            }
                            
                            # Realizar la solicitud HTTP
                            response = requests.get(self.url, headers=headers, timeout=30)
                            response.raise_for_status()
                            
                            # Parsear el contenido HTML
                            soup = BeautifulSoup(response.content, 'html.parser')
                            
                            # Eliminar tags no deseados
                            for tag in soup(["script", "style", "noscript", "iframe", "head", "meta", "link"]):
                                tag.decompose()
                            

                            # Intentar extraer el contenido principal
                            main_content = None
                            
                            # Buscar por tags comunes para contenido principal
                            for selector in ['article', 'main', '#content', '.content', '.article', '.post']:
                                content = soup.select_one(selector)
                                if content:
                                    main_content = content
                                    break
                            
                            # Si no encontramos contenido principal, usar el body
                            if not main_content:
                                main_content = soup.body
                            
                            # Extraer el texto
                            if main_content:
                                text = main_content.get_text(separator=' ')
                            else:
                                text = soup.get_text(separator=' ')
                            
                            # Limpiar el texto
                            lines = (line.strip() for line in text.splitlines())
                            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
                            text = ' '.join(chunk for chunk in chunks if chunk)
                            
                            # Obtener título
                            title = soup.title.string if soup.title else ""
                            
                            # Crear documento
                            return [Document(
                                page_content=text,
                                metadata={
                                    "source": self.url,
                                    "title": title,
                                    "content_type": "url"
                                }
                            )]
                        except Exception as e:
                            logger.error(f"Error al cargar URL {self.url} con BeautifulSoup: {e}")
                            return [Document(
                                page_content=f"Error al cargar URL: {str(e)}",
                                metadata={"source": self.url, "error": True}
                            )]
                
                logger.info(f"Usando BeautifulSoupURLLoader para URL: {url}")
                return BeautifulSoupURLLoader(url)
                
        except Exception as e:
            logger.error(f"Error al crear loader para URL: {e}")
            
            # Utilizar un loader muy simple como último recurso
            from langchain_core.documents import Document
            
            class SimpleURLLoader:
                def __init__(self, url):
                    self.url = url
                    
                def load(self):
                    try:
                        import requests
                        response = requests.get(self.url)
                        text = f"[Contenido extraído de {self.url}]\n\n{response.text[:10000]}..."  # Limitar tamaño
                        return [Document(
                            page_content=text,
                            metadata={"source": self.url}
                        )]
                    except:
                        return [Document(
                            page_content=f"No se pudo cargar el contenido de {self.url}",
                            metadata={"source": self.url, "error": True}
                        )]
            
            logger.info(f"Usando SimpleURLLoader para URL como último recurso: {url}")
            return SimpleURLLoader(url)
        
    def _get_html_loader(self, file_path_or_html):
        """
        Obtiene un loader para archivos HTML o contenido HTML
        
        Args:
            file_path_or_html: Ruta al archivo HTML o contenido HTML
            
        Returns:
            Loader para HTML
        """
        try:
            # Determinar si es una ruta a archivo o contenido HTML
            is_file = os.path.isfile(file_path_or_html) if isinstance(file_path_or_html, str) else False
            from langchain_core.documents import Document
            
            # Crear clase personalizada para cargar HTML
            class CustomHTMLLoader:
                def __init__(self, source):
                    self.source = source
                    self.is_file = os.path.isfile(source) if isinstance(source, str) else False
                
                def load(self):
                    try:
                        html_content = ""
                        if self.is_file:
                            # Leer el archivo HTML
                            with open(self.source, 'r', encoding='utf-8') as f:
                                html_content = f.read()
                        else:
                            # Usar directamente si ya es contenido HTML
                            html_content = self.source
                        
                        # Usar BeautifulSoup para parsear HTML
                        from bs4 import BeautifulSoup
                        
                        # Parsear el HTML
                        soup = BeautifulSoup(html_content, 'html.parser')
                        
                        # Eliminar tags no deseados
                        for tag in soup(['script', 'style', 'meta', 'noscript', 'header', 'footer', 'nav']):
                            tag.decompose()
                        
                        # Extraer texto del contenido principal
                        main_content = soup.find('main') or soup.find('article') or soup.find('div', {'class': 'content'})
                        if main_content:
                            text = main_content.get_text(separator=' ')
                        else:
                            # Si no hay contenido principal, usar el body completo
                            text = soup.body.get_text(separator=' ') if soup.body else soup.get_text(separator=' ')
                        
                        # Limpiar el texto
                        import re
                        text = re.sub(r'\s+', ' ', text)  # Reemplazar múltiples espacios por uno solo
                        text = text.strip()  # Eliminar espacios al inicio y al final
                        
                        # Obtener título
                        title = soup.title.string if soup.title else ""
                        
                        # Crear un documento con el texto extraído
                        return [Document(
                            page_content=text,
                            metadata={
                                "source": self.source if self.is_file else "html_content",
                                "title": title,
                                "content_type": "html"
                            }
                        )]
                    except Exception as e:
                        logger.error(f"Error al procesar HTML: {e}")
                        # Devolver un documento con mensaje de error
                        return [Document(
                            page_content="Error al procesar contenido HTML",
                            metadata={"source": self.source if self.is_file else "html_content", "error": True}
                        )]
                        
            # Crear y devolver el loader
            return CustomHTMLLoader(file_path_or_html)
            
        except Exception as e:
            logger.error(f"Error al crear loader HTML: {e}")
            from langchain_core.documents import Document
            
            # Crear un loader simple como fallback
            class SimpleHTMLLoader:
                def __init__(self, source):
                    self.source = source
                
                def load(self):
                    return [Document(
                        page_content="No se pudo procesar el contenido HTML",
                        metadata={"source": self.source}
                    )]
            
            return SimpleHTMLLoader(file_path_or_html)

# Crear instancia singleton
knowledge_service = KnowledgeService()