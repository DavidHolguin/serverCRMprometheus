# Servidor de Mensajería CRM con FastAPI y LangChain

Este servidor permite gestionar mensajes de diferentes canales (Messenger, Instagram, Telegram, WhatsApp, chat web, etc.) y responder utilizando la API de ChatGPT a través de LangChain.

## Características

- Integración con múltiples canales de comunicación
- Procesamiento de mensajes con ChatGPT
- Gestión de historial de conversaciones con LangChain
- Integración con Supabase para almacenamiento de datos
- Escalable y de alto rendimiento

## Requisitos

- Python 3.9+
- Supabase
- Cuenta de OpenAI con API key

## Instalación

1. Clonar el repositorio
2. Instalar dependencias:
   ```
   pip install -r requirements.txt
   ```
3. Configurar variables de entorno en un archivo `.env`
4. Ejecutar el servidor:
   ```
   uvicorn app.main:app --reload
   ```

## Despliegue en Railway

Este proyecto está configurado para ser desplegado fácilmente en [Railway](https://railway.app/):

1. Crea una cuenta en Railway si aún no tienes una
2. Instala la CLI de Railway (opcional):
   ```
   npm i -g @railway/cli
   ```
3. Inicia sesión en Railway:
   ```
   railway login
   ```
4. Conecta tu repositorio de GitHub a Railway o sube directamente el código:
   - Desde la interfaz web de Railway: Crea un nuevo proyecto → Desplegar desde GitHub
   - O usando la CLI: `railway init` y luego `railway up`
5. Configura las variables de entorno en Railway:
   - OPENAI_API_KEY
   - SUPABASE_URL
   - SUPABASE_KEY
   - Otras variables necesarias para tu proyecto
6. Railway detectará automáticamente que es una aplicación Python y la desplegará usando los archivos de configuración incluidos

El despliegue se realizará automáticamente cada vez que hagas push a tu repositorio si lo has conectado con GitHub.

## Estructura del Proyecto

```
servidorCRM/
├── app/
│   ├── api/          # Endpoints de la API
│   ├── core/         # Configuración central y constantes
│   ├── db/           # Conexión a la base de datos
│   ├── models/       # Modelos Pydantic
│   ├── services/     # Servicios de negocio
│   └── utils/        # Utilidades
├── .env              # Variables de entorno
├── requirements.txt  # Dependencias
└── README.md         # Documentación
```
## tablas de la base de datos en supabase

```

| table_name                 | column_name             |
| -------------------------- | ----------------------- |
| automatizacion_ejecuciones | id                      |
| automatizacion_ejecuciones | automatizacion_id       |
| automatizacion_ejecuciones | evento_id               |
| automatizacion_ejecuciones | resultado               |
| automatizacion_ejecuciones | mensaje                 |
| automatizacion_ejecuciones | detalles                |
| automatizacion_ejecuciones | created_at              |
| automatizaciones           | id                      |
| automatizaciones           | empresa_id              |
| automatizaciones           | nombre                  |
| automatizaciones           | descripcion             |
| automatizaciones           | evento_tipo             |
| automatizaciones           | condiciones             |
| automatizaciones           | acciones                |
| automatizaciones           | is_active               |
| automatizaciones           | created_at              |
| automatizaciones           | updated_at              |
| canales                    | id                      |
| canales                    | nombre                  |
| canales                    | tipo                    |
| canales                    | descripcion             |
| canales                    | logo_url                |
| canales                    | configuracion_requerida |
| canales                    | is_active               |
| canales                    | created_at              |
| canales                    | updated_at              |
| chatbot_canales            | id                      |
| chatbot_canales            | chatbot_id              |
| chatbot_canales            | canal_id                |
| chatbot_canales            | configuracion           |
| chatbot_canales            | webhook_url             |
| chatbot_canales            | webhook_secret          |
| chatbot_canales            | is_active               |
| chatbot_canales            | created_at              |
| chatbot_canales            | updated_at              |
| chatbot_contextos          | id                      |
| chatbot_contextos          | chatbot_id              |
| chatbot_contextos          | tipo                    |
| chatbot_contextos          | contenido               |
| chatbot_contextos          | orden                   |
| chatbot_contextos          | created_at              |
| chatbot_contextos          | updated_at              |
| chatbot_contextos          | welcome_message         |
| chatbot_contextos          | personality             |
| chatbot_contextos          | general_context         |
| chatbot_contextos          | communication_tone      |
| chatbot_contextos          | main_purpose            |
| chatbot_contextos          | key_points              |
| chatbot_contextos          | special_instructions    |
| chatbot_contextos          | prompt_template         |
| chatbot_contextos          | qa_examples             |
| chatbots                   | id                      |
| chatbots                   | empresa_id              |
| chatbots                   | nombre                  |
| chatbots                   | descripcion             |
| chatbots                   | avatar_url              |
| chatbots                   | tono                    |
| chatbots                   | personalidad            |
| chatbots                   | instrucciones           |
| chatbots                   | contexto                |
| chatbots                   | configuracion           |
| chatbots                   | pipeline_id             |
| chatbots                   | is_active               |
| chatbots                   | created_at              |
| chatbots                   | updated_at              |
| conversaciones             | id                      |
| conversaciones             | lead_id                 |
| conversaciones             | chatbot_id              |
| conversaciones             | canal_id                |
| conversaciones             | canal_identificador     |
| conversaciones             | estado                  |
| conversaciones             | ultimo_mensaje          |
| conversaciones             | metadata                |
| conversaciones             | created_at              |
| conversaciones             | updated_at              |
| conversaciones             | chatbot_activo          |
| empresa_faqs               | id                      |
| empresa_faqs               | empresa_id              |
| empresa_faqs               | pregunta                |
| empresa_faqs               | respuesta               |
| empresa_faqs               | orden                   |
| empresa_faqs               | created_at              |
| empresa_faqs               | updated_at              |
| empresa_productos          | id                      |
| empresa_productos          | empresa_id              |
| empresa_productos          | nombre                  |
| empresa_productos          | descripcion             |
| empresa_productos          | caracteristicas         |
| empresa_productos          | precio                  |
| empresa_productos          | imagen_url              |
| empresa_productos          | orden                   |
| empresa_productos          | is_active               |
| empresa_productos          | created_at              |
| empresa_productos          | updated_at              |
| empresas                   | id                      |
| empresas                   | created_at              |
| empresas                   | updated_at              |
| empresas                   | nombre                  |
| empresas                   | descripcion             |
| empresas                   | logo_url                |
| empresas                   | sitio_web               |
| empresas                   | telefono                |
| empresas                   | email                   |
| empresas                   | direccion               |
| empresas                   | ciudad                  |
| empresas                   | pais                    |
| empresas                   | codigo_postal           |
| empresas                   | configuracion           |
| empresas                   | is_active               |
| empresas                   | onboarding_completed    |
| empresas                   | created_by              |
| eventos                    | id                      |
| eventos                    | empresa_id              |
| eventos                    | tipo                    |
| eventos                    | entidad_tipo            |
| eventos                    | entidad_id              |
| eventos                    | datos                   |
| eventos                    | procesado               |
| eventos                    | created_at              |
| galeria_imagenes           | id                      |
| galeria_imagenes           | galeria_id              |
| galeria_imagenes           | url                     |
| galeria_imagenes           | titulo                  |
| galeria_imagenes           | descripcion             |
| galeria_imagenes           | palabras_clave          |
| galeria_imagenes           | orden                   |
| galeria_imagenes           | created_at              |
| galeria_imagenes           | updated_at              |
| galerias_imagenes          | id                      |
| galerias_imagenes          | empresa_id              |
| galerias_imagenes          | nombre                  |
| galerias_imagenes          | descripcion             |
| galerias_imagenes          | created_at              |
| galerias_imagenes          | updated_at              |
| lead_history               | id                      |
| lead_history               | lead_id                 |
| lead_history               | campo                   |
| lead_history               | valor_anterior          |
| lead_history               | valor_nuevo             |
| lead_history               | usuario_id              |
| lead_history               | created_at              |
| lead_tag_relation          | id                      |
| lead_tag_relation          | lead_id                 |
| lead_tag_relation          | tag_id                  |
| lead_tag_relation          | created_at              |
| lead_tags                  | id                      |
| lead_tags                  | empresa_id              |
| lead_tags                  | nombre                  |
| lead_tags                  | color                   |
| lead_tags                  | created_at              |
| lead_tags                  | updated_at              |
| leads                      | id                      |
| leads                      | empresa_id              |
| leads                      | canal_origen            |
| leads                      | canal_id                |
| leads                      | nombre                  |
| leads                      | apellido                |
| leads                      | email                   |
| leads                      | telefono                |
| leads                      | pais                    |
| leads                      | ciudad                  |
| leads                      | direccion               |
| leads                      | datos_adicionales       |
| leads                      | score                   |
| leads                      | pipeline_id             |
| leads                      | stage_id                |
| leads                      | asignado_a              |
| leads                      | ultima_interaccion      |
| leads                      | estado                  |
| leads                      | is_active               |
| leads                      | created_at              |
| leads                      | updated_at              |
| llm_configuraciones        | id                      |
| llm_configuraciones        | empresa_id              |
| llm_configuraciones        | nombre                  |
| llm_configuraciones        | proveedor               |
| llm_configuraciones        | modelo                  |
| llm_configuraciones        | configuracion           |
| llm_configuraciones        | api_key                 |
| llm_configuraciones        | is_default              |
| llm_configuraciones        | is_active               |
| llm_configuraciones        | created_at              |
| llm_configuraciones        | updated_at              |
| mensaje_plantillas         | id                      |
| mensaje_plantillas         | empresa_id              |
| mensaje_plantillas         | nombre                  |
| mensaje_plantillas         | contenido               |
| mensaje_plantillas         | categoria               |
| mensaje_plantillas         | variables               |
| mensaje_plantillas         | created_at              |
| mensaje_plantillas         | updated_at              |
| mensajes                   | id                      |
| mensajes                   | conversacion_id         |
| mensajes                   | origen                  |
| mensajes                   | remitente_id            |
| mensajes                   | contenido               |
| mensajes                   | tipo_contenido          |
| mensajes                   | metadata                |
| mensajes                   | score_impacto           |
| mensajes                   | created_at              |
| mensajes                   | leido                   |
| pipeline_stages            | id                      |
| pipeline_stages            | pipeline_id             |
| pipeline_stages            | nombre                  |
| pipeline_stages            | descripcion             |
| pipeline_stages            | color                   |
| pipeline_stages            | posicion                |
| pipeline_stages            | probabilidad            |
| pipeline_stages            | is_active               |
| pipeline_stages            | created_at              |
| pipeline_stages            | updated_at              |
| pipelines                  | id                      |
| pipelines                  | empresa_id              |
| pipelines                  | nombre                  |
| pipelines                  | descripcion             |
| pipelines                  | is_default              |
| pipelines                  | is_active               |
| pipelines                  | created_at              |
| pipelines                  | updated_at              |
| profiles                   | id                      |
| profiles                   | updated_at              |
| profiles                   | created_at              |
| profiles                   | email                   |
| profiles                   | full_name               |
| profiles                   | avatar_url              |
| profiles                   | role                    |
| profiles                   | empresa_id              |
| profiles                   | last_sign_in            |
| profiles                   | onboarding_completed    |
| profiles                   | onboarding_step         |
| profiles                   | is_active               |
| stage_automations          | id                      |
| stage_automations          | empresa_id              |
| stage_automations          | stage_id                |
| stage_automations          | evento                  |
| stage_automations          | accion                  |
| stage_automations          | configuracion           |
| stage_automations          | is_active               |
| stage_automations          | created_at              |
| stage_automations          | updated_at              |
