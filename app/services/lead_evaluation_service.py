from typing import Dict, Any, List, Optional
from uuid import UUID
import json
from datetime import datetime

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.pydantic_v1 import BaseModel, Field

from app.core.config import settings
from app.db.supabase_client import supabase
from app.services.langchain_service import langchain_service

class EvaluacionLead(BaseModel):
    """Modelo para la evaluación de un lead basado en sus mensajes"""
    score_potencial: int = Field(
        description="Puntuación de 1 a 10 que indica el potencial del lead como cliente. 10 es el máximo potencial."
    )
    score_satisfaccion: int = Field(
        description="Puntuación de 1 a 10 que indica la satisfacción del lead con la conversación. 10 es la máxima satisfacción."
    )
    interes_productos: List[str] = Field(
        description="Lista de productos en los que el lead ha mostrado interés."
    )
    comentario: str = Field(
        description="Comentario o análisis breve sobre el valor del lead y su comportamiento."
    )
    palabras_clave: List[str] = Field(
        description="Palabras clave identificadas en la conversación que indican intenciones o intereses."
    )

class LeadEvaluationService:
    """Servicio para evaluar leads basado en sus mensajes y conversaciones"""
    
    def __init__(self):
        """Inicializa el servicio de evaluación de leads"""
        pass
    
    def _get_llm_config(self, empresa_id: UUID) -> Dict[str, Any]:
        """
        Obtiene la configuración del LLM para una empresa específica
        
        Args:
            empresa_id: El ID de la empresa
            
        Returns:
            Dict con la configuración del LLM
        """
        # Obtener configuración del LLM desde la base de datos
        result = supabase.table("llm_configuraciones").select("*").eq("empresa_id", str(empresa_id)).eq("is_default", True).execute()
        
        if not result.data or len(result.data) == 0:
            # Usar configuración predeterminada si no se encuentra
            return {
                "model": settings.DEFAULT_MODEL,
                "temperature": 0.1,  # Temperatura baja para evaluaciones más consistentes
                "max_tokens": 1000,
                "api_key": settings.OPENAI_API_KEY
            }
        
        config = result.data[0]
        
        return {
            "model": config["modelo"],
            "temperature": 0.1,  # Temperatura baja para evaluaciones más consistentes
            "max_tokens": 1000,
            "api_key": config["api_key"] or settings.OPENAI_API_KEY
        }
    
    def _get_lead_intentions(self, empresa_id: UUID) -> List[Dict[str, Any]]:
        """
        Obtiene las intenciones de lead configuradas para una empresa
        
        Args:
            empresa_id: El ID de la empresa
            
        Returns:
            Lista de intenciones de lead
        """
        result = supabase.table("lead_intentions").select("*").eq("empresa_id", str(empresa_id)).eq("is_active", True).execute()
        
        return result.data if result.data else []
    
    def _get_company_products(self, empresa_id: UUID) -> List[Dict[str, Any]]:
        """
        Obtiene los productos de una empresa
        
        Args:
            empresa_id: El ID de la empresa
            
        Returns:
            Lista de productos de la empresa
        """
        result = supabase.table("empresa_productos").select("*").eq("empresa_id", str(empresa_id)).eq("is_active", True).execute()
        
        return result.data if result.data else []
    
    def _get_conversation_messages(self, conversation_id: UUID, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Obtiene los mensajes de una conversación
        
        Args:
            conversation_id: El ID de la conversación
            limit: Número máximo de mensajes a recuperar
            
        Returns:
            Lista de mensajes en la conversación
        """
        result = supabase.table("mensajes").select("*").eq("conversacion_id", str(conversation_id)).order("created_at", desc=False).limit(limit).execute()
        
        return result.data if result.data else []
    
    def _get_lead_info(self, lead_id: UUID) -> Dict[str, Any]:
        """
        Obtiene información sobre un lead
        
        Args:
            lead_id: El ID del lead
            
        Returns:
            Información del lead
        """
        result = supabase.table("leads").select("*").eq("id", str(lead_id)).limit(1).execute()
        
        if not result.data or len(result.data) == 0:
            raise ValueError(f"Lead con ID {lead_id} no encontrado")
        
        return result.data[0]
    
    def _get_lead_interactions(self, lead_id: UUID) -> List[Dict[str, Any]]:
        """
        Obtiene las interacciones previas de un lead
        
        Args:
            lead_id: El ID del lead
            
        Returns:
            Lista de interacciones del lead
        """
        result = supabase.table("lead_interactions").select("*").eq("lead_id", str(lead_id)).order("created_at", desc=False).execute()
        
        return result.data if result.data else []
    
    def _get_interaction_types(self, empresa_id: UUID) -> List[Dict[str, Any]]:
        """
        Obtiene los tipos de interacción configurados para una empresa
        
        Args:
            empresa_id: El ID de la empresa
            
        Returns:
            Lista de tipos de interacción
        """
        result = supabase.table("lead_interaction_types").select("*").eq("empresa_id", str(empresa_id)).eq("is_active", True).execute()
        
        return result.data if result.data else []
    
    def _create_evaluation_prompt(self, 
                                 messages: List[Dict[str, Any]], 
                                 lead_info: Dict[str, Any],
                                 intentions: List[Dict[str, Any]],
                                 products: List[Dict[str, Any]],
                                 interaction_types: List[Dict[str, Any]]) -> str:
        """
        Crea el prompt para la evaluación del lead
        
        Args:
            messages: Lista de mensajes de la conversación
            lead_info: Información del lead
            intentions: Lista de intenciones configuradas
            products: Lista de productos de la empresa
            interaction_types: Lista de tipos de interacción
            
        Returns:
            Prompt para la evaluación
        """
        # Formatear mensajes para el prompt
        formatted_messages = []
        for msg in messages:
            origen = "Usuario" if msg["origen"] == "user" else "Chatbot"
            formatted_messages.append(f"{origen}: {msg['contenido']}")
        
        # Destacar los últimos 3 mensajes como los más recientes
        recent_messages = []
        if len(formatted_messages) > 3:
            conversation_text = "\n".join(formatted_messages[:-2])
            recent_messages = formatted_messages[-2:]
            recent_messages_text = "\n".join(recent_messages)
        else:
            conversation_text = "\n".join(formatted_messages)
            recent_messages_text = ""
        
        # Formatear intenciones para el prompt
        intentions_text = []
        for intention in intentions:
            keywords = ", ".join(intention["palabras_clave"]) if intention["palabras_clave"] else "N/A"
            intentions_text.append(f"- {intention['nombre']}: {intention['descripcion']} (Palabras clave: {keywords})")
        
        intentions_formatted = "\n".join(intentions_text)
        
        # Formatear productos para el prompt
        products_text = []
        for product in products:
            products_text.append(f"- {product['nombre']}: {product['descripcion']}")
        
        products_formatted = "\n".join(products_text)
        
        # Formatear tipos de interacción para el prompt
        interaction_types_text = []
        for it in interaction_types:
            interaction_types_text.append(f"- {it['nombre']}: {it['descripcion']} (Valor score: {it['valor_score']})")
        
        interaction_types_formatted = "\n".join(interaction_types_text)
        
        # Crear prompt
        prompt = f"""
        Eres un evaluador experto de leads para un CRM. Tu tarea es analizar la conversación entre un usuario y un chatbot
        para determinar el valor potencial del lead, su nivel de satisfacción, y otros indicadores importantes.
        
        # Información del Lead
        - Nombre: {lead_info.get('nombre', 'No disponible')}
        - Email: {lead_info.get('email', 'No disponible')}
        - Teléfono: {lead_info.get('telefono', 'No disponible')}
        - Score actual: {lead_info.get('score', 0)}
        
        # Conversación Completa
        {conversation_text}
        
        # Mensajes Más Recientes (PRESTA ESPECIAL ATENCIÓN A ESTOS)
        {recent_messages_text}
        
        # Intenciones Configuradas
        {intentions_formatted}
        
        # Productos de la Empresa
        {products_formatted}
        
        # Tipos de Interacción
        {interaction_types_formatted}
        
        Analiza cuidadosamente la conversación completa, pero da MAYOR PESO a los mensajes más recientes, ya que representan el estado actual del lead. Evalúa:
        
        1. El potencial del lead como cliente (score_potencial) en una escala de 1 a 10
           - Si los mensajes recientes contienen señales negativas (cancelaciones, quejas, problemas personales graves), reduce significativamente esta puntuación
           - Si hay un cambio drástico de tono positivo a negativo en los mensajes recientes, esto debe reflejarse en la puntuación
        
        2. La satisfacción del lead con la conversación (score_satisfaccion) en una escala de 1 a 10
           - Considera principalmente los mensajes más recientes para esta puntuación
           - Detecta cambios de humor o tono en la conversación
        
        3. Los productos en los que el lead ha mostrado interés (interes_productos)
           - Incluye productos mencionados en toda la conversación
        
        4. Un comentario breve sobre el valor del lead y su comportamiento (comentario)
           - Menciona explícitamente cualquier cambio importante en el tono o intención del lead
        
        5. Palabras clave identificadas en la conversación que indican intenciones o intereses (palabras_clave)
           - Incluye palabras clave de toda la conversación, pero prioriza las de los mensajes recientes
        
        Responde con un objeto JSON que contenga estos campos.
        """
        
        return prompt
    
    def _register_lead_intentions(self, 
                                 lead_id: UUID, 
                                 conversacion_id: UUID, 
                                 mensaje_id: UUID,
                                 empresa_id: UUID,
                                 evaluation: EvaluacionLead) -> None:
        """
        Registra las intenciones identificadas en la evaluación como interacciones del lead
        
        Args:
            lead_id: El ID del lead
            conversacion_id: El ID de la conversación
            mensaje_id: El ID del mensaje evaluado
            empresa_id: El ID de la empresa
            evaluation: La evaluación generada
        """
        # Obtener intenciones configuradas
        intentions = self._get_lead_intentions(empresa_id)
        
        # Mapear palabras clave a intenciones
        matched_intentions = []
        for keyword in evaluation.palabras_clave:
            for intention in intentions:
                if not intention.get("palabras_clave"):
                    continue
                    
                if keyword.lower() in [kw.lower() for kw in intention["palabras_clave"]]:
                    matched_intentions.append(intention)
        
        # Eliminar duplicados
        unique_intentions = {intention["id"]: intention for intention in matched_intentions}.values()
        
        # Obtener tipos de interacción
        interaction_types = self._get_interaction_types(empresa_id)
        default_interaction_type = None
        
        # Buscar tipo de interacción para "intención identificada"
        for it in interaction_types:
            if it["nombre"].lower() == "intención identificada":
                default_interaction_type = it
                break
        
        # Si no existe, usar el primero disponible
        if not default_interaction_type and interaction_types:
            default_interaction_type = interaction_types[0]
        
        # Registrar interacciones
        for intention in unique_intentions:
            interaction_data = {
                "lead_id": str(lead_id),
                "interaction_type_id": default_interaction_type["id"] if default_interaction_type else None,
                "conversacion_id": str(conversacion_id),
                "mensaje_id": str(mensaje_id),
                "intencion_id": intention["id"],
                "valor_score": intention.get("prioridad", 5),
                "metadata": {
                    "evaluacion_id": None,  # Se actualizará después de guardar la evaluación
                    "palabras_clave_detectadas": evaluation.palabras_clave
                },
                "notas": f"Intención detectada automáticamente: {intention['nombre']}"
            }
            
            # Guardar interacción
            supabase.table("lead_interactions").insert(interaction_data).execute()
    
    def _update_lead_score(self, lead_id: UUID, evaluation: EvaluacionLead) -> None:
        """
        Actualiza el score del lead basado en la evaluación
        
        Args:
            lead_id: El ID del lead
            evaluation: La evaluación generada
        """
        # Obtener información actual del lead
        lead_info = self._get_lead_info(lead_id)
        
        # Obtener evaluaciones previas
        result = supabase.table("evaluaciones_llm").select("*").eq("lead_id", str(lead_id)).order("fecha_evaluacion", desc=True).limit(2).execute()
        previous_evaluations = result.data if result.data else []
        
        # Calcular nuevo score
        current_score = lead_info.get("score", 0)
        
        # Verificar si hay un cambio drástico en la evaluación
        drastic_change = False
        
        # Si hay evaluaciones previas, comparar con la anterior
        if len(previous_evaluations) > 1:
            # Ignorar la evaluación actual (que ya está en la BD)
            prev_eval = previous_evaluations[1]  # La segunda evaluación más reciente
            
            # Detectar cambios drásticos en el potencial o satisfacción
            if prev_eval.get("score_potencial", 5) - evaluation.score_potencial >= 3:
                drastic_change = True
            if prev_eval.get("score_satisfaccion", 5) - evaluation.score_satisfaccion >= 3:
                drastic_change = True
        
        # Fórmula de score:
        if len(previous_evaluations) == 0:
            # Primera evaluación: asignar directamente el score potencial como base
            new_score = evaluation.score_potencial * 10
        elif drastic_change:
            # Si hay un cambio drástico negativo, dar más peso a la nueva evaluación
            # 40% score actual + 60% score potencial de la evaluación
            new_score = int(current_score * 0.4 + evaluation.score_potencial * 6)
        else:
            # 70% score actual + 30% score potencial de la evaluación
            new_score = int(current_score * 0.7 + evaluation.score_potencial * 3)
        
        # Limitar el score a un máximo de 100
        new_score = min(new_score, 100)
        
        # Si el score potencial es muy bajo (1-3), asegurar que el score total también baje significativamente
        if evaluation.score_potencial <= 3:
            new_score = min(new_score, current_score - 10)  # Forzar una reducción de al menos 10 puntos
            
        # Asegurar que el score no sea negativo
        new_score = max(new_score, 0)
        
        # Actualizar lead
        supabase.table("leads").update({"score": new_score}).eq("id", str(lead_id)).execute()
    
    def evaluate_message(self, 
                        lead_id: UUID, 
                        conversacion_id: UUID, 
                        mensaje_id: UUID,
                        empresa_id: UUID) -> Dict[str, Any]:
        """
        Evalúa un mensaje específico y actualiza la información del lead
        
        Args:
            lead_id: El ID del lead
            conversacion_id: El ID de la conversación
            mensaje_id: El ID del mensaje a evaluar
            empresa_id: El ID de la empresa
            
        Returns:
            Resultado de la evaluación
        """
        try:
            # Obtener información del lead
            lead_info = self._get_lead_info(lead_id)
            
            # Obtener mensajes de la conversación
            messages = self._get_conversation_messages(conversacion_id)
            
            # Obtener intenciones configuradas
            intentions = self._get_lead_intentions(empresa_id)
            
            # Obtener productos de la empresa
            products = self._get_company_products(empresa_id)
            
            # Obtener tipos de interacción
            interaction_types = self._get_interaction_types(empresa_id)
            
            # Crear prompt para la evaluación
            prompt = self._create_evaluation_prompt(
                messages, 
                lead_info,
                intentions,
                products,
                interaction_types
            )
            
            # Obtener configuración del LLM
            llm_config = self._get_llm_config(empresa_id)
            
            # Crear LLM
            llm = ChatOpenAI(
                model=llm_config["model"],
                temperature=llm_config["temperature"],
                openai_api_key=llm_config["api_key"],
                max_tokens=llm_config["max_tokens"]
            )
            
            # Crear parser para la salida JSON
            parser = JsonOutputParser(pydantic_object=EvaluacionLead)
            
            # Crear prompt template
            prompt_template = ChatPromptTemplate.from_messages([
                ("system", prompt)
            ])
            
            # Crear chain
            chain = prompt_template | llm | parser
            
            # Generar evaluación
            evaluation_result = chain.invoke({})
            
            # Asegurarse de que la evaluación sea un objeto EvaluacionLead
            if isinstance(evaluation_result, dict):
                evaluation = EvaluacionLead(
                    score_potencial=evaluation_result.get("score_potencial", 5),
                    score_satisfaccion=evaluation_result.get("score_satisfaccion", 5),
                    interes_productos=evaluation_result.get("interes_productos", []),
                    comentario=evaluation_result.get("comentario", ""),
                    palabras_clave=evaluation_result.get("palabras_clave", [])
                )
            else:
                evaluation = evaluation_result
            
            # Guardar evaluación en la base de datos
            evaluation_data = {
                "lead_id": str(lead_id),
                "conversacion_id": str(conversacion_id),
                "mensaje_id": str(mensaje_id),
                "fecha_evaluacion": datetime.now().isoformat(),
                "score_potencial": evaluation.score_potencial,
                "score_satisfaccion": evaluation.score_satisfaccion,
                "interes_productos": evaluation.interes_productos,
                "comentario": evaluation.comentario,
                "palabras_clave": evaluation.palabras_clave,
                "llm_configuracion_id": llm_config.get("id"),
                "prompt_utilizado": prompt
            }
            
            result = supabase.table("evaluaciones_llm").insert(evaluation_data).execute()
            
            if result.data and len(result.data) > 0:
                evaluation_id = result.data[0]["id"]
                
                # Registrar intenciones como interacciones
                self._register_lead_intentions(lead_id, conversacion_id, mensaje_id, empresa_id, evaluation)
                
                # Actualizar score del lead
                self._update_lead_score(lead_id, evaluation)
                
                return {
                    "id": evaluation_id,
                    "lead_id": str(lead_id),
                    "conversacion_id": str(conversacion_id),
                    "mensaje_id": str(mensaje_id),
                    "score_potencial": evaluation.score_potencial,
                    "score_satisfaccion": evaluation.score_satisfaccion,
                    "interes_productos": evaluation.interes_productos,
                    "comentario": evaluation.comentario,
                    "palabras_clave": evaluation.palabras_clave
                }
            
            raise ValueError("Error al guardar la evaluación")
        except Exception as e:
            print(f"Error en evaluate_message: {e}")
            raise

# Crear instancia singleton
lead_evaluation_service = LeadEvaluationService()
