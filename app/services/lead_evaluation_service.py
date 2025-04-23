from typing import Dict, Any, List, Optional, Union, Tuple
from uuid import UUID
import json
import re
import math
import unidecode
from datetime import datetime, timedelta

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.pydantic_v1 import BaseModel, Field

from app.core.config import settings
from app.db.supabase_client import supabase
from app.services.langchain_service import langchain_service
from app.services.event_service import event_service

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

class EvaluationWeights(BaseModel):
    """Modelo para los pesos utilizados en evaluaciones"""
    recency_factor: float = Field(0.7, description="Factor de peso para mensajes recientes vs históricos")
    sentiment_weight: float = Field(0.3, description="Peso para análisis de sentimiento")
    intent_weight: float = Field(0.3, description="Peso para intenciones detectadas")
    product_interest_weight: float = Field(0.2, description="Peso para interés en productos")
    engagement_weight: float = Field(0.2, description="Peso para nivel de engagement")

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
        result = supabase.table("llm_configuraciones").select("*").eq("empresa_id", str(empresa_id)).eq("is_default", True).execute()
        
        if not result.data or len(result.data) == 0:
            return {
                "model": settings.DEFAULT_MODEL,
                "temperature": 0.1,
                "max_tokens": 1000,
                "api_key": settings.OPENAI_API_KEY
            }
        
        config = result.data[0]
        
        return {
            "model": config["modelo"],
            "temperature": 0.1,
            "max_tokens": 1000,
            "api_key": config["api_key"] or settings.OPENAI_API_KEY
        }
    
    def _get_evaluation_config(self, empresa_id: UUID) -> Dict[str, Any]:
        """
        Obtiene configuración específica para evaluaciones de una empresa
        
        Args:
            empresa_id: El ID de la empresa
            
        Returns:
            Dict con la configuración para evaluaciones
        """
        result = supabase.table("evaluacion_configuraciones").select("*").eq("empresa_id", str(empresa_id)).limit(1).execute()
        
        if result.data and len(result.data) > 0:
            return result.data[0]
        
        return {
            "version": "1.0.0",
            "recency_factor": 0.7,
            "sentiment_weight": 0.3,
            "intent_weight": 0.3,
            "product_interest_weight": 0.3,
            "engagement_weight": 0.2,
            "min_satisfaction_threshold": 4,
            "drastic_change_threshold": 3,
            "normalize_keywords": True,
            "product_match_algorithm": "hybrid",
            "temperature_calculation_enabled": True
        }
    
    def _normalize_keywords(self, keywords: List[str]) -> List[str]:
        """
        Normaliza palabras clave: elimina duplicados, stopwords, 
        convierte a minúsculas y normaliza acentos
        
        Args:
            keywords: Lista de palabras clave a normalizar
            
        Returns:
            Lista de palabras clave normalizadas
        """
        stop_words = {
            'el', 'la', 'los', 'las', 'un', 'una', 'y', 'o', 'de', 'del', 'a', 'en', 
            'que', 'por', 'con', 'para', 'como', 'pero', 'si', 'no', 'más', 'este', 
            'esta', 'estos', 'estas', 'ese', 'esa', 'esos', 'esas'
        }
        normalized = []
        
        for keyword in keywords:
            kw = keyword.lower()
            kw = re.sub(r'[^\w\s]', '', kw)
            kw = unidecode.unidecode(kw)
            
            if kw not in stop_words and len(kw) > 2:
                normalized.append(kw)
        
        return list(set(normalized))
    
    def _get_company_products_with_keywords(self, empresa_id: UUID) -> List[Dict[str, Any]]:
        """
        Obtiene los productos de una empresa con palabras clave generadas
        
        Args:
            empresa_id: El ID de la empresa
            
        Returns:
            Lista de productos con palabras clave generadas
        """
        products = self._get_company_products(empresa_id)
        
        product_synonyms = {}
        result = supabase.table("producto_sinonimos").select("*").eq("empresa_id", str(empresa_id)).execute()
        
        if result.data:
            for synonym in result.data:
                if synonym["producto_id"] not in product_synonyms:
                    product_synonyms[synonym["producto_id"]] = []
                product_synonyms[synonym["producto_id"]].append(synonym["palabra_clave"])
        
        for product in products:
            keywords = set()
            if product.get("nombre"):
                keywords.update(self._extract_keywords(product["nombre"]))
            if product.get("descripcion"):
                keywords.update(self._extract_keywords(product["descripcion"]))
            if product.get("caracteristicas") and isinstance(product.get("caracteristicas"), list):
                for caracteristica in product["caracteristicas"]:
                    keywords.update(self._extract_keywords(caracteristica))
            
            if product.get("id") in product_synonyms:
                keywords.update(product_synonyms[product["id"]])
                
            product["keywords_generadas"] = list(keywords)
        
        return products
    
    def _extract_keywords(self, text: str) -> List[str]:
        """
        Extrae palabras clave de un texto
        
        Args:
            text: Texto del cual extraer palabras clave
            
        Returns:
            Lista de palabras clave extraídas
        """
        if not text:
            return []
            
        text = text.lower()
        text = re.sub(r'[^\w\s]', ' ', text)
        words = text.split()
        words = [word for word in words if len(word) > 2]
        
        stop_words = {
            'el', 'la', 'los', 'las', 'un', 'una', 'y', 'o', 'de', 'del', 'a', 'en', 
            'que', 'por', 'con', 'para', 'como', 'pero', 'si', 'no', 'más', 'este', 
            'esta', 'estos', 'estas', 'ese', 'esa', 'esos', 'esas'
        }
        
        words = [word for word in words if word not in stop_words]
        
        bigramas = []
        for i in range(len(words) - 1):
            bigramas.append(f"{words[i]} {words[i+1]}")
        
        keywords = words + bigramas
        keywords = [unidecode.unidecode(kw) for kw in keywords]
        
        return list(set(keywords))
    
    def _match_products(self, keywords: List[str], products: List[Dict[str, Any]], 
                       mensaje_texto: str) -> List[Dict[str, float]]:
        """
        Algoritmo para vincular palabras clave con productos específicos
        
        Args:
            keywords: Lista de palabras clave detectadas
            products: Lista de productos de la empresa
            mensaje_texto: Texto completo del mensaje
            
        Returns:
            Lista de productos coincidentes con sus scores
        """
        matched_products = []
        norm_keywords = self._normalize_keywords(keywords)
        
        for product in products:
            match_score = 0.0
            product_keywords = product.get("keywords_generadas", [])
            
            direct_matches = 0
            for kw in norm_keywords:
                if kw in product_keywords:
                    direct_matches += 1
                    match_score += 1.0
            
            if product.get("nombre") and mensaje_texto:
                product_name_lower = product.get("nombre", "").lower()
                cleaned_message = mensaje_texto.lower()
                
                if product_name_lower in cleaned_message:
                    match_score += 5.0
            
            if match_score > 0.5:
                matched_products.append({
                    "id": product.get("id", ""),
                    "nombre": product.get("nombre", ""),
                    "score": min(match_score, 10)
                })
        
        return sorted(matched_products, key=lambda x: x.get("score", 0), reverse=True)
    
    def _calculate_lead_score(self, 
                           lead_id: UUID, 
                           current_evaluation: EvaluacionLead,
                           historical_evaluations: List[Dict[str, Any]],
                           interactions: List[Dict[str, Any]],
                           lead_info: Dict[str, Any],
                           empresa_id: UUID) -> Dict[str, Any]:
        """
        Algoritmo mejorado para calcular score de lead
        
        Args:
            lead_id: El ID del lead
            current_evaluation: La evaluación actual
            historical_evaluations: Lista de evaluaciones históricas
            interactions: Lista de interacciones del lead
            lead_info: Información del lead
            empresa_id: ID de la empresa
            
        Returns:
            Dict con el nuevo score y sus componentes
        """
        config = self._get_evaluation_config(empresa_id)
        
        current_score = lead_info.get("score", 0)
        recency_weight = config.get("recency_factor", 0.6)
        history_weight = 0.2
        interaction_weight = 0.2
        
        potential_contribution = current_evaluation.score_potencial * 8
        satisfaction_contribution = current_evaluation.score_satisfaccion * 2
        current_eval_score = (potential_contribution + satisfaction_contribution) / 10
        
        historical_trend = 0
        if historical_evaluations:
            weights_sum = 0
            weighted_scores = 0
            
            for i, eval in enumerate(historical_evaluations):
                weight = math.exp(-0.5 * i)
                weighted_scores += eval.get("score_potencial", 5) * weight
                weights_sum += weight
            
            if weights_sum > 0:
                historical_trend = weighted_scores / weights_sum
        
        interaction_value = 0
        if interactions:
            total_value = sum(interaction.get("valor_score", 0) for interaction in interactions)
            interaction_value = min(total_value / len(interactions), 10)
        
        combined_score = (
            current_eval_score * recency_weight +
            historical_trend * history_weight +
            interaction_value * interaction_weight
        ) * 10
        
        final_score = max(0, min(int(combined_score), 100))
        
        return {
            "nuevo_score": final_score,
            "componentes": {
                "evaluacion_actual": current_eval_score * 10,
                "tendencia_historica": historical_trend * 10 if historical_evaluations else None,
                "valor_interacciones": interaction_value * 10 if interactions else None
            },
            "calculado_en": datetime.now().isoformat()
        }
    
    def _get_lead_info(self, lead_id: UUID) -> Dict[str, Any]:
        """
        Obtiene información del lead desde la base de datos
        
        Args:
            lead_id: El ID del lead a consultar
            
        Returns:
            Dict con la información del lead
        """
        try:
            result = supabase.table("leads").select("*").eq("id", str(lead_id)).limit(1).execute()
            
            if not result.data or len(result.data) == 0:
                return {
                    "score": 0,
                    "canal_origen": "desconocido"
                }
            
            return result.data[0]
        except Exception as e:
            print(f"Error al obtener información del lead: {e}")
            return {
                "score": 0,
                "canal_origen": "desconocido"
            }
    
    def _get_conversation_messages(self, conversacion_id: UUID) -> List[Dict[str, Any]]:
        """
        Obtiene todos los mensajes de una conversación
        
        Args:
            conversacion_id: El ID de la conversación
            
        Returns:
            Lista de mensajes de la conversación
        """
        try:
            result = supabase.table("mensajes").select("*").eq("conversacion_id", str(conversacion_id)).order("created_at").execute()
            
            return result.data if result.data else []
        except Exception as e:
            print(f"Error al obtener mensajes de la conversación: {e}")
            return []
    
    def _get_lead_intentions(self, empresa_id: UUID) -> List[Dict[str, Any]]:
        """
        Obtiene las intenciones configuradas para una empresa
        
        Args:
            empresa_id: El ID de la empresa
            
        Returns:
            Lista de intenciones configuradas
        """
        try:
            result = supabase.table("lead_intentions").select("*").eq("empresa_id", str(empresa_id)).execute()
            
            return result.data if result.data else []
        except Exception as e:
            print(f"Error al obtener intenciones de la empresa: {e}")
            return []
            
    def _get_company_products(self, empresa_id: UUID) -> List[Dict[str, Any]]:
        """
        Obtiene los productos de una empresa
        
        Args:
            empresa_id: El ID de la empresa
            
        Returns:
            Lista de productos de la empresa
        """
        try:
            result = supabase.table("empresa_productos").select("*").eq("empresa_id", str(empresa_id)).execute()
            
            return result.data if result.data else []
        except Exception as e:
            print(f"Error al obtener productos de la empresa: {e}")
            return []
            
    def _get_interaction_types(self, empresa_id: UUID) -> List[Dict[str, Any]]:
        """
        Obtiene los tipos de interacción configurados para una empresa
        
        Args:
            empresa_id: El ID de la empresa
            
        Returns:
            Lista de tipos de interacción configurados
        """
        try:
            result = supabase.table("lead_interaction_types").select("*").eq("empresa_id", str(empresa_id)).execute()
            
            return result.data if result.data else []
        except Exception as e:
            print(f"Error al obtener tipos de interacción: {e}")
            return []
            
    def _get_lead_interactions(self, lead_id: UUID) -> List[Dict[str, Any]]:
        """
        Obtiene las interacciones de un lead
        
        Args:
            lead_id: El ID del lead
            
        Returns:
            Lista de interacciones del lead
        """
        try:
            result = supabase.table("lead_interactions").select("*").eq("lead_id", str(lead_id)).order("created_at", desc=True).limit(50).execute()
            
            return result.data if result.data else []
        except Exception as e:
            print(f"Error al obtener interacciones del lead: {e}")
            return []
            
    def _get_historical_evaluations(self, lead_id: UUID) -> List[Dict[str, Any]]:
        """
        Obtiene evaluaciones históricas para un lead
        
        Args:
            lead_id: El ID del lead
            
        Returns:
            Lista de evaluaciones históricas
        """
        try:
            result = supabase.table("evaluaciones_llm").select("*").eq("lead_id", str(lead_id)).order("fecha_evaluacion", desc=True).limit(10).execute()
            
            return result.data if result.data else []
        except Exception as e:
            print(f"Error al obtener evaluaciones históricas: {e}")
            return []
            
    def _create_evaluation_prompt(self, 
                               messages: List[Dict[str, Any]], 
                               lead_info: Dict[str, Any],
                               intentions: List[Dict[str, Any]],
                               products: List[Dict[str, Any]],
                               interaction_types: List[Dict[str, Any]]) -> str:
        """
        Crea el prompt para evaluación de lead
        
        Args:
            messages: Lista de mensajes de la conversación
            lead_info: Información del lead
            intentions: Intenciones configuradas
            products: Productos de la empresa
            interaction_types: Tipos de interacción
            
        Returns:
            Prompt para evaluación de lead
        """
        # Identificar mensajes del usuario y del sistema
        conversation_text = ""
        for msg in messages:
            if msg.get("role") == "user":
                conversation_text += f"Usuario: {msg.get('contenido', '')}\n"
            else:
                conversation_text += f"Chatbot: {msg.get('contenido', '')}\n"
        
        # Formatear los últimos 5 mensajes para darles mayor peso
        recent_messages = messages[-5:] if len(messages) > 5 else messages
        recent_messages_text = ""
        for msg in recent_messages:
            if msg.get("role") == "user":
                recent_messages_text += f"Usuario: {msg.get('contenido', '')}\n"
            else:
                recent_messages_text += f"Chatbot: {msg.get('contenido', '')}\n"
        
        # Formatear intenciones configuradas
        intentions_text = "\n".join([f"- {i.get('nombre')}: {i.get('descripcion')}" for i in intentions])
        
        # Formatear productos
        products_text = "\n".join([f"- {p.get('nombre')}: {p.get('descripcion', 'Programa innovadores')}" for p in products])
        
        # Formatear tipos de interacción
        interaction_types_text = "\n".join([
            f"- {i.get('nombre')}: {i.get('descripcion')} (Valor score: {i.get('valor_score', 0)})"
            for i in interaction_types
        ])
        
        prompt = f"""
        Eres un evaluador experto de leads para un CRM. Tu tarea es analizar la conversación entre un usuario y un chatbot
        para determinar el valor potencial del lead, su nivel de satisfacción, y otros indicadores importantes.
        
        # Información del Lead
        - ID: {lead_info.get('id')}
        - Canal de origen: {lead_info.get('canal_origen')}
        - Score actual: {lead_info.get('score')}
        
        # Conversación Completa
        {conversation_text}
        
        # Mensajes Más Recientes (PRESTA ESPECIAL ATENCIÓN A ESTOS)
        {recent_messages_text}
        
        # Intenciones Configuradas
        {intentions_text}
        
        
        # Productos de la Empresa
        {products_text}
        
        # Tipos de Interacción
        {interaction_types_text}
        
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
        Registra las intenciones detectadas para un lead
        
        Args:
            lead_id: ID del lead
            conversacion_id: ID de la conversación
            mensaje_id: ID del mensaje actual
            empresa_id: ID de la empresa
            evaluation: Resultado de la evaluación
            
        Returns:
            None
        """
        try:
            intentions = self._get_lead_intentions(empresa_id)
            
            # Detectar intenciones basado en palabras clave y evaluación
            detected_intentions = []
            
            for intention in intentions:
                keywords = intention.get("palabras_clave", [])
                if not keywords:
                    continue
                    
                for kw in keywords:
                    if any(kw.lower() in k.lower() for k in evaluation.palabras_clave):
                        detected_intentions.append({
                            "lead_id": str(lead_id),
                            "conversacion_id": str(conversacion_id),
                            "mensaje_id": str(mensaje_id),
                            "intencion_id": intention.get("id"),
                            "fecha_deteccion": datetime.now().isoformat(),
                            "confianza": 0.8,
                            "metodo_deteccion": "keywords"
                        })
                        break
            
            if detected_intentions:
                supabase.table("intenciones_detectadas").insert(detected_intentions).execute()
                
        except Exception as e:
            print(f"Error al registrar intenciones del lead: {e}")
    
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
            # Registrar evento de inicio de evaluación detallada
            event_service.log_event(
                empresa_id=empresa_id,
                event_type=event_service.EVENT_LEAD_QUALIFIED,
                entidad_origen_tipo="lead",
                entidad_origen_id=lead_id,
                lead_id=lead_id,
                conversacion_id=conversacion_id,
                mensaje_id=mensaje_id,
                resultado="processing",
                detalle="Iniciando evaluación LLM del lead",
                async_processing=False
            )
            
            # Tiempo de inicio para medir duración
            start_time = datetime.now()
            
            evaluation_config = self._get_evaluation_config(empresa_id)
            lead_info = self._get_lead_info(lead_id)
            messages = self._get_conversation_messages(conversacion_id)
            mensaje_actual = next((m for m in messages if m["id"] == str(mensaje_id)), None)
            mensaje_texto = mensaje_actual.get("contenido", "") if mensaje_actual else ""
            intentions = self._get_lead_intentions(empresa_id)
            products = self._get_company_products_with_keywords(empresa_id)
            interaction_types = self._get_interaction_types(empresa_id)
            lead_interactions = self._get_lead_interactions(lead_id)
            
            prompt = self._create_evaluation_prompt(
                messages, 
                lead_info,
                intentions,
                products,
                interaction_types
            )
            
            llm_config = self._get_llm_config(empresa_id)
            
            llm = ChatOpenAI(
                model=llm_config["model"],
                temperature=llm_config["temperature"],
                openai_api_key=llm_config["api_key"],
                max_tokens=llm_config["max_tokens"]
            )
            
            parser = JsonOutputParser(pydantic_object=EvaluacionLead)
            
            prompt_template = ChatPromptTemplate.from_messages([
                ("system", prompt)
            ])
            
            chain = prompt_template | llm | parser
            
            evaluation_result = chain.invoke({})
            
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
            
            if evaluation_config.get("normalize_keywords", True):
                evaluation.palabras_clave = self._normalize_keywords(evaluation.palabras_clave)
                
            if mensaje_texto:
                matched_products = self._match_products(
                    evaluation.palabras_clave, 
                    products, 
                    mensaje_texto
                )
                if matched_products:
                    evaluation.interes_productos = [p["nombre"] for p in matched_products]
            
            historical_evaluations = self._get_historical_evaluations(lead_id)
            
            score_calculation = self._calculate_lead_score(
                lead_id, 
                evaluation, 
                historical_evaluations, 
                lead_interactions,
                lead_info,
                empresa_id
            )
            
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
                
                self._register_lead_intentions(lead_id, conversacion_id, mensaje_id, empresa_id, evaluation)
                
                # Actualizar score del lead
                supabase.table("leads").update({"score": score_calculation["nuevo_score"]}).eq("id", str(lead_id)).execute()
                
                # Calcular duración del proceso completo
                duration_seconds = (datetime.now() - start_time).total_seconds()
                
                # Registrar evento de cambio de score
                event_service.log_event(
                    empresa_id=empresa_id,
                    event_type=event_service.EVENT_LEAD_STATUS_CHANGED,
                    entidad_origen_tipo="sistema",
                    entidad_destino_tipo="lead",
                    entidad_destino_id=lead_id,
                    lead_id=lead_id,
                    conversacion_id=conversacion_id,
                    mensaje_id=mensaje_id,
                    valor_score=score_calculation["nuevo_score"],
                    resultado="success",
                    detalle=f"Score actualizado: {score_calculation['nuevo_score']}",
                    metadata={
                        "score_anterior": lead_info.get("score", 0),
                        "score_nuevo": score_calculation["nuevo_score"],
                        "evaluacion_id": evaluation_id,
                        "score_potencial": evaluation.score_potencial,
                        "score_satisfaccion": evaluation.score_satisfaccion
                    },
                    async_processing=False
                )
                
                # Registrar evento de interés en productos si se detectaron
                if evaluation.interes_productos:
                    event_service.log_event(
                        empresa_id=empresa_id,
                        event_type=event_service.EVENT_INFO_REQUEST,
                        entidad_origen_tipo="lead",
                        entidad_origen_id=lead_id,
                        lead_id=lead_id,
                        conversacion_id=conversacion_id,
                        mensaje_id=mensaje_id,
                        resultado="success",
                        detalle=f"Interés en productos detectado: {', '.join(evaluation.interes_productos)}",
                        metadata={
                            "productos": evaluation.interes_productos,
                            "evaluacion_id": evaluation_id
                        },
                        async_processing=False
                    )
                
                # Registrar evento de evaluación completada
                event_service.log_event(
                    empresa_id=empresa_id,
                    event_type=event_service.EVENT_LEAD_QUALIFIED,
                    entidad_origen_tipo="lead",
                    entidad_origen_id=lead_id,
                    lead_id=lead_id,
                    conversacion_id=conversacion_id,
                    mensaje_id=mensaje_id,
                    valor_score=score_calculation["nuevo_score"],
                    duracion_segundos=duration_seconds,
                    resultado="completed",
                    detalle=f"Evaluación completada con score {score_calculation['nuevo_score']}",
                    metadata={
                        "evaluacion_id": evaluation_id,
                        "potencial": evaluation.score_potencial,
                        "satisfaccion": evaluation.score_satisfaccion,
                        "comentario": evaluation.comentario[:100] if evaluation.comentario else None,
                        "palabras_clave_count": len(evaluation.palabras_clave),
                        "productos_detectados": len(evaluation.interes_productos)
                    },
                    async_processing=False
                )
                
                result_data = {
                    "id": evaluation_id,
                    "lead_id": str(lead_id),
                    "conversacion_id": str(conversacion_id),
                    "mensaje_id": str(mensaje_id),
                    "fecha_evaluacion": datetime.now().isoformat(),
                    "score_potencial": evaluation.score_potencial,
                    "score_satisfaccion": evaluation.score_satisfaccion,
                    "interes_productos": evaluation.interes_productos,
                    "comentario": evaluation.comentario,
                    "palabras_clave": evaluation.palabras_clave,
                    "nuevo_score": score_calculation["nuevo_score"],
                    "created_at": datetime.now().isoformat(),
                    "updated_at": None,
                    "details": score_calculation
                }
                
                return result_data
            
            # Si fallamos al guardar la evaluación, registrar el evento de error
            event_service.log_event(
                empresa_id=empresa_id,
                event_type=event_service.EVENT_ERROR_OCCURRED,
                entidad_origen_tipo="lead",
                entidad_origen_id=lead_id,
                lead_id=lead_id,
                conversacion_id=conversacion_id,
                mensaje_id=mensaje_id,
                resultado="error",
                detalle="Error al guardar la evaluación",
                async_processing=False
            )
            
            raise ValueError("Error al guardar la evaluación")
        except Exception as e:
            # Registrar error en la evaluación
            event_service.log_event(
                empresa_id=empresa_id,
                event_type=event_service.EVENT_ERROR_OCCURRED,
                entidad_origen_tipo="sistema",
                entidad_destino_tipo="lead",
                entidad_destino_id=lead_id,
                lead_id=lead_id,
                conversacion_id=conversacion_id,
                mensaje_id=mensaje_id if mensaje_id else None,
                resultado="error",
                detalle=f"Error en evaluate_message: {str(e)}",
                metadata={"error": str(e)},
                async_processing=False
            )
            
            print(f"Error en evaluate_message: {e}")
            raise

# Crear instancia singleton
lead_evaluation_service = LeadEvaluationService()
