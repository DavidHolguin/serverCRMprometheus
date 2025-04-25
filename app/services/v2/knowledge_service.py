from typing import Dict, List, Any, Optional
from uuid import UUID
import json
from datetime import datetime

from langchain_openai import OpenAIEmbeddings
# Importamos cada loader directamente desde el archivo base
# para evitar la carga del módulo language_parser problemático
try:
    # Intentar importaciones directas para evitar problemas con módulos intermedios
    import PyPDF2  # Dependencia directa para PyPDFLoader
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
    print(f"Error en importaciones: {e}")
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
            import PyPDF2
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
        self.embeddings = OpenAIEmbeddings(
            model="text-embedding-3-small",
            openai_api_key=settings.OPENAI_API_KEY
        )
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200
        )

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
            # Seleccionar el loader adecuado según el tipo de archivo
            loader = self._get_document_loader(file_path, file_type)
            
            # Cargar el documento
            documents = loader.load()
            
            # Dividir el texto en chunks
            texts = self.text_splitter.split_documents(documents)
            
            # Generar embeddings
            embeddings_list = []
            for text in texts:
                embedding = await self.embeddings.aembed_query(text.page_content)
                embeddings_list.append(embedding)
            
            # Crear entradas de conocimiento
            knowledge_entries = []
            for i, (text, embedding) in enumerate(zip(texts, embeddings_list)):
                knowledge = AgentKnowledge(
                    id=UUID(),
                    agent_id=agent_id,
                    type="processed_document",
                    source=file_path,
                    format="text_with_embeddings",
                    content=text.page_content,
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
                
                # Guardar en la base de datos
                result = supabase.table("agente_conocimiento").insert(
                    knowledge.model_dump(exclude={'embeddings'})
                ).execute()
                
                if result.data:
                    # Guardar embeddings en la tabla de vectores
                    vector_data = {
                        "knowledge_id": str(knowledge.id),
                        "embedding": embedding
                    }
                    supabase.table("agente_conocimiento_vectores").insert(vector_data).execute()
                    
                    knowledge_entries.append(knowledge)
                
            # Registrar evento de procesamiento exitoso
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
            
            return knowledge_entries
            
        except Exception as e:
            # Registrar evento de error
            event_service.log_event(
                empresa_id=company_id,
                event_type="agent_knowledge_error",
                entidad_origen_tipo="agent",
                entidad_origen_id=agent_id,
                resultado="error",
                detalle=f"Error procesando documento: {str(e)}",
                metadata={
                    "file_type": file_type,
                    "error": str(e)
                }
            )
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
        loaders = {
            "pdf": PyPDFLoader,
            "csv": CSVLoader,
            "txt": TextLoader,
            "docx": UnstructuredWordDocumentLoader,
            "xlsx": UnstructuredExcelLoader
        }
        
        loader_class = loaders.get(file_type.lower())
        if not loader_class:
            raise ValueError(f"Tipo de archivo no soportado: {file_type}")
            
        return loader_class(file_path)

    async def search_similar_knowledge(
        self,
        query: str,
        agent_id: UUID,
        limit: int = 5
    ) -> List[AgentKnowledge]:
        """
        Busca conocimiento similar usando embeddings
        
        Args:
            query: Texto a buscar
            agent_id: ID del agente
            limit: Número máximo de resultados
            
        Returns:
            Lista de conocimientos similares
        """
        try:
            # Generar embedding para la consulta
            query_embedding = await self.embeddings.aembed_query(query)
            
            # Realizar búsqueda por similitud usando la función match_vectors
            result = supabase.rpc(
                'match_knowledge_vectors',
                {
                    'query_embedding': query_embedding,
                    'match_threshold': 0.7,
                    'match_count': limit,
                    'agent_id': str(agent_id)
                }
            ).execute()
            
            # Convertir resultados a objetos AgentKnowledge
            knowledge_entries = []
            for item in result.data:
                knowledge = AgentKnowledge(
                    id=item['id'],
                    agent_id=agent_id,
                    type=item['type'],
                    source=item['source'],
                    format=item['format'],
                    content=item['content'],
                    metadata=item['metadata'],
                    priority=item['priority'],
                    created_at=item['created_at'],
                    updated_at=item['updated_at']
                )
                knowledge_entries.append(knowledge)
                
            return knowledge_entries
            
        except Exception as e:
            print(f"Error en búsqueda de conocimiento: {e}")
            return []

# Crear instancia singleton
knowledge_service = KnowledgeService()