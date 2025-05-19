# Este archivo permite importaciones lazy para evitar dependencias circulares

# Importar servicios de manera lazy
from app.services.conversation_service import ConversationService
from app.services.lead_evaluation_service import LeadEvaluationService
from app.services.data_capture_service import DataCaptureService

# Instancias de servicios
conversation_service = ConversationService()
lead_evaluation_service = LeadEvaluationService()
data_capture_service = DataCaptureService()