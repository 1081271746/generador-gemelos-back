CREDENCIALES PARA INICIAR:

CORREO: sebitasroja06@gmail.com
CONTRASEÑA: 1234567891112



Generador de Gemelos de Negociación 



Plataforma web para practicar negociaciones con un gemelo de inteligencia artificial y analizar el desempeño con evidencias
El Generador de Gemelos de Negociación es una plataforma web que permite crear escenarios de negociación, practicar conversaciones con un gemelo de IA, consultar el historial de cada negociación y obtener análisis estructurados sobre las estrategias utilizadas.

El proyecto utiliza una arquitectura cliente-servidor dividida en dos repositorios: un frontend desarrollado con Angular y un backend desarrollado con FastAPI. El backend coordina la persistencia, la autenticación, los servicios gRPC, los eventos en tiempo real y la comunicación con Groq. PostgreSQL se utiliza como base de datos en el despliegue de Railway y Redis apoya la distribución de eventos y el control compartido de solicitudes de IA.

La IA no se entrena automáticamente con cada conversación. El sistema construye el contexto de cada negociación y lo envía al proveedor configurado para producir respuestas o análisis. También existe una ruta opcional de inferencia local y un pipeline de preparación de datos y entrenamiento LoRA/QLoRA, pero no hay actualmente un adaptador especializado entrenado y validado.
1. Objetivos del proyecto
Objetivo general
Desarrollar una plataforma de práctica de negociación que permita simular conversaciones con un gemelo de IA, administrar escenarios, conservar el historial de las interacciones y analizar habilidades de negociación mediante indicadores contextuales y evidencias extraídas de los mensajes.
Objetivos específicos
- Permitir el registro, autenticación y administración de cuentas de usuario.
- Crear escenarios configurables con objetivos, contexto, rol de la contraparte e información sobre sus límites.
- Iniciar y administrar negociaciones individuales a partir de escenarios.
- Generar respuestas del gemelo de IA considerando el escenario, los mensajes anteriores y el perfil contextual del usuario.
- Conservar los mensajes y estados de cada negociación.
- Analizar negociaciones finalizadas mediante cinco dimensiones de desempeño.
- Asociar las conclusiones del análisis con citas verificables de mensajes del usuario.
- Construir un perfil progresivo con indicadores de desempeño, fortalezas y oportunidades de mejora.
- Generar recomendaciones y ejercicios de práctica.
- Distribuir eventos en tiempo real mediante gRPC Streaming, Redis Pub/Sub y WebSockets.
- Mantener una arquitectura modular, con validaciones, pruebas automatizadas y despliegue separado del frontend y backend.
2. Repositorios del proyecto
El proyecto se encuentra separado en dos repositorios independientes:
Componente	Repositorio	Responsabilidad
Backend	generador-gemelos-back	API, lógica de negocio, persistencia, autenticación, IA, gRPC y eventos.
Frontend	generador-gemelos-front	Interfaz web, navegación, autenticación del cliente, chat, escenarios, análisis y conexión en tiempo real.


El frontend consume la API existente del backend. No implementa una segunda lógica de negocio ni accede directamente a PostgreSQL, Redis o los servicios gRPC.
3. Tecnologías utilizadas
3.1. Frontend
Tecnología	Función
Angular 22.2.5	Framework principal para construir la aplicación web.
Angular CLI / Builder 22.2.6	Herramientas de desarrollo, pruebas y compilación.
TypeScript 6	Lenguaje principal del frontend.
HTML5	Estructura de las páginas y componentes.
CSS3	Estilos y presentación visual.
Tailwind CSS 4	Utilidades de diseño y estilos de interfaz.
RxJS 7.8	Manejo de operaciones asíncronas y flujos HTTP.
Angular Router	Navegación entre las secciones de la aplicación.
Angular Signals	Estado reactivo de sesión, conexión y componentes.
HttpClient	Comunicación HTTP con el backend.
Vitest	Pruebas unitarias del frontend.
jsdom	Entorno de navegador simulado para las pruebas.
Node.js 24.13 o superior	Entorno de ejecución de herramientas y servidor estático.
pnpm 10	Instalación y administración de dependencias.


La aplicación utiliza componentes standalone, rutas cargadas bajo demanda, formularios reactivos, guards de navegación e interceptores HTTP para adjuntar el JWT a las solicitudes dirigidas al backend configurado.
3.2. Backend
Tecnología	Función
Python 3.13	Lenguaje principal del backend.
FastAPI 0.162.2	Construcción de la API REST y documentación OpenAPI.
Uvicorn 0.54.0	Servidor ASGI que ejecuta FastAPI.
SQLAlchemy 2.1.8	ORM y acceso a la base de datos.
Pydantic 2.14.3	Validación de solicitudes, respuestas y estructuras generadas por IA.
Alembic 1.20.1	Control de versiones y migraciones de la base de datos.
PyJWT 2.15.1	Creación y validación de tokens JWT.
argon2-cffi 25.1.0	Hashing seguro de contraseñas mediante Argon2.
python-dotenv 1.2.4	Lectura de variables de entorno desde .env.
HTTPX 0.28.1	Cliente HTTP y transporte de pruebas.
pytest 9.2.0	Pruebas automatizadas del backend.
pytest-asyncio	Soporte para pruebas asíncronas.


El backend se organiza mediante routers, servicios, repositorios, esquemas Pydantic, modelos SQLAlchemy y dependencias inyectables. FastAPI administra las solicitudes HTTP y coordina las operaciones con los servicios internos.
3.3. Base de datos
PostgreSQL es la base de datos utilizada en el despliegue de Railway. El backend utiliza SQLAlchemy y el controlador psycopg[binary] para conectarse a PostgreSQL.

Para desarrollo local, el proyecto conserva SQLite como configuración predeterminada (sqlite:///./negotiation.db). La URL se define mediante DATABASE_URL, por lo que se puede seleccionar la base de datos sin modificar la lógica de negocio.

Alembic administra las migraciones. El cambio de SQLite a PostgreSQL no copia automáticamente los registros: una migración de datos entre motores requiere respaldo, transferencia, revisión de claves y secuencias, y validación de integridad.
3.4. Redis
Redis (servidor probado con Redis 7.2.10) se utiliza como infraestructura de eventos y coordinación. El backend utiliza el cliente Python redis 8.1.0. Redis no reemplaza PostgreSQL.

Sus responsabilidades principales son:
- Distribuir avisos de eventos mediante Pub/Sub.
- Facilitar el fan-out de notificaciones a varios suscriptores autorizados.
- Mantener el contador compartido de solicitudes de IA por modelo y minuto.
- Coordinar procesos que participan en el flujo de eventos.
Los eventos de negocio se conservan en la base de datos. Redis transporta avisos para que los suscriptores consulten los eventos persistidos y los entreguen en orden.
3.5. gRPC y Protocol Buffers
Tecnología	Función
gRPC 1.85.1	Comunicación entre FastAPI y los servicios especializados.
grpcio-tools 1.85.1	Generación de código cliente/servidor desde .proto.
Protocol Buffers 7.36.2	Definición tipada de mensajes y contratos entre servicios.
grpc.aio	Servidores y clientes gRPC asíncronos.


Los contratos están definidos en app/rpc/negotiation.proto. La arquitectura mantiene separados el gemelo, el análisis y la distribución central de eventos.
3.6. Inteligencia artificial
Groq API es el proveedor predeterminado de IA.
Elemento	Configuración
Proveedor	Groq
SDK	groq 1.7.0
Cliente	AsyncGroq
Modelo predeterminado	openai/gpt-oss-20b
Formato de respuesta	JSON Schema y validación Pydantic
Límite preventivo	10 solicitudes por minuto por modelo, compartidas mediante Redis por defecto
Timeout predeterminado	30 segundos para Groq
Configuración	Variables de entorno del backend


El identificador openai/gpt-oss-20b corresponde al modelo servido por Groq. El sistema utiliza el SDK y la infraestructura de Groq; no utiliza la API de OpenAI para esta inferencia. Gemini fue retirado como proveedor activo.

También existe una opción local explícita mediante AI_PROVIDER=local, basada en un servidor llama.cpp. Esta ruta opcional utiliza como baseline documentado Qwen/Qwen2.5-1.5B-Instruct en formato GGUF. No es el proveedor predeterminado y no existe fallback automático entre proveedores.
3.7. Despliegue e infraestructura
Tecnología / servicio	Función
Railway	Plataforma utilizada para desplegar frontend, backend y servicios administrados.
PostgreSQL en Railway	Persistencia de producción.
Redis en Railway	Mensajería Pub/Sub y cuotas compartidas.
Git y GitHub	Control de versiones y alojamiento de los repositorios.
Supervisor Python	Arranque, supervisión y apagado de los procesos del backend en el despliegue de un solo servicio.


4. Integración de inteligencia artificial con Groq
La inteligencia artificial es uno de los componentes principales del Generador de Gemelos de Negociación. El sistema utiliza el proveedor para crear respuestas del gemelo y producir análisis estructurados de negociaciones finalizadas.
4.1. ¿Cómo funciona el gemelo?
1. El usuario crea un escenario y define el contexto de la negociación.
2. El usuario inicia una negociación a partir de ese escenario.
3. El backend crea una instantánea (scenario_snapshot) para conservar las condiciones originales de esa negociación.
4. El usuario envía una oferta, contraoferta, argumento o concesión.
5. FastAPI valida la solicitud, verifica la propiedad de la negociación y conserva el mensaje.
6. FastAPI prepara el contexto con el escenario, el historial de mensajes y el perfil disponible.
7. FastAPI solicita la generación al servicio gRPC del gemelo.
8. El servicio gRPC utiliza TwinEngine y el proveedor seleccionado.
9. Groq procesa el contexto y devuelve una respuesta estructurada.
10. El backend valida la respuesta mediante Pydantic y las reglas del motor.
11. La respuesta del gemelo se guarda y se devuelve al frontend.
La respuesta del gemelo contiene el texto y el tipo de intervención. Los tipos admitidos son offer, counteroffer, argument y concession.
4.2. ¿Cómo funciona el análisis?
1. El usuario finaliza una negociación con un resultado explícito.
2. El sistema verifica que la negociación esté cerrada y cuente con mensajes.
3. El backend reúne el escenario, el historial y el contexto permitido.
4. FastAPI solicita el análisis al servicio gRPC especializado.
5. AnalysisEngine prepara las instrucciones y el esquema de salida.
6. Groq genera el análisis estructurado.
7. Pydantic valida la estructura, los puntajes y las evidencias.
8. El backend verifica que las citas correspondan exactamente a mensajes del usuario.
9. El análisis válido se guarda en PostgreSQL o SQLite, según la configuración.
10. El frontend presenta el resumen, las dimensiones, las evidencias y las recomendaciones.
4.3. Dimensiones evaluadas
El análisis utiliza cinco dimensiones contextuales, cada una con un puntaje entre 0 y 100, explicación y evidencias:
Dimensión	Qué representa en el análisis
assertiveness	Asertividad durante la negociación.
cooperation	Cooperación con la contraparte.
flexibility	Flexibilidad para considerar alternativas.
argumentation	Calidad de la argumentación.
conflict_management	Manejo de desacuerdos y conflictos.


Cada evidencia contiene un identificador de mensaje y una cita literal. El backend rechaza estructuras inválidas o citas que no correspondan al contenido original.

El resultado también puede incluir resumen, estrategias, fortalezas, áreas de mejora, resultado de la negociación, evaluación del objetivo, recomendaciones, ejercicios y alertas.

Los indicadores son contextuales y sirven para reflexionar sobre una práctica concreta. No representan diagnósticos psicológicos ni etiquetas definitivas de personalidad.
4.4. Configuración del proveedor
La integración se configura desde el backend:
AI_PROVIDER=groq
GROQ_API_KEY=tu_clave_de_groq
GROQ_MODEL=openai/gpt-oss-20b
GROQ_TIMEOUT_SECONDS=30
GROQ_REQUESTS_PER_MINUTE=10
La clave GROQ_API_KEY debe permanecer exclusivamente en el entorno del backend. No debe incluirse en Angular, en archivos públicos, en public/config.json, en GitHub ni en capturas de pantalla.
4.5. Validación y manejo de fallos
La respuesta del proveedor debe cumplir el esquema esperado y finalizar correctamente. Se controlan respuestas vacías, truncadas, bloqueadas, inválidas, errores de autenticación, cuota, conexión y timeout.

No existe fallback automático a otro proveedor. Si la IA falla, el sistema informa la indisponibilidad, conserva el mensaje del usuario y permite recuperar el flujo utilizando el mismo request_id. No se genera una respuesta ficticia para simular que Groq respondió.

El contexto enviado al proveedor incluye el escenario, el perfil contextual y el historial de la negociación. El sistema limita el contexto a 200.000 bytes UTF-8 y rechaza solicitudes que excedan ese tamaño en lugar de truncar silenciosamente los datos. Antes de utilizarlo con información real, se debe informar a los usuarios sobre el procesamiento externo y revisar los requisitos de privacidad y autorización aplicables.
4.6. Ruta opcional de IA local y entrenamiento
El backend conserva una implementación opcional de inferencia local mediante llama.cpp y el proveedor AI_PROVIDER=local.

La documentación del repositorio describe:
- Modelo base documentado: Qwen/Qwen2.5-1.5B-Instruct.
- Formato de inferencia: GGUF cuantizado.
- Servidor de inferencia: llama.cpp.
- Especialización prevista: LoRA / QLoRA mediante Transformers y PEFT.
- Preparación de datos: validación, deduplicación, división de conjuntos y manifiestos.
Estado real de esta ruta: se implementó el pipeline y se probó inferencia del modelo base en CPU, pero no se ha completado un adaptador especializado entrenado y evaluado. El corpus sintético documentado de 20 ejemplos es demostrativo y no constituye un conjunto suficiente para afirmar que existe un modelo experto en negociación. Groq continúa siendo el proveedor predeterminado.
5. Módulos principales del sistema
5.1. Autenticación y usuarios
Permite registrar usuarios, iniciar sesión, consultar y actualizar el perfil, cambiar la contraseña y cerrar sesión.

Incluye:
- Registro y login mediante correo y contraseña.
- Hashing de contraseñas con Argon2.
- Tokens JWT con expiración y validación de sesión.
- Versión de token para revocación de sesiones.
- Claves separadas para firmar tokens de usuario y tokens internos de servicio.
- Protección de rutas y verificación de propiedad de los recursos.
5.2. Dashboard
Es la pantalla principal de la aplicación. Presenta información de actividad y permite acceder a los módulos de escenarios, negociaciones, análisis y perfil.

Los contadores y listados se calculan a partir de datos reales y paginados del backend. El frontend no inventa estadísticas ni usa cifras de demostración para reemplazar respuestas de la API.
5.3. Escenarios de negociación
Permite crear, listar, consultar, editar y archivar escenarios propios.

Cada escenario contempla información como:
- Título y descripción.
- Contexto de la negociación.
- Objetivo del usuario.
- Rol de la contraparte.
- Objetivo de la contraparte.
- Límites de la contraparte.
Un escenario pertenece a un usuario. Al iniciar una negociación, el backend conserva una instantánea de su contenido; por tanto, editar posteriormente el escenario no altera las condiciones de conversaciones anteriores.
5.4. Negociaciones
Permite iniciar negociaciones a partir de escenarios, consultar el historial y finalizar o cancelar una negociación.

Estados principales:
Estado	Significado
active	La negociación continúa abierta.
completed	La negociación terminó con un resultado registrado.
cancelled	La negociación fue cancelada.


El cierre requiere un resultado explícito. Una negociación cerrada queda en modo de solo lectura y se utiliza como fuente para el análisis.
5.5. Chat y mensajes
El chat es el espacio donde el usuario intercambia mensajes con el gemelo.

Tipos de mensajes admitidos:
- offer: oferta.
- counteroffer: contraoferta.
- argument: argumento.
- concession: concesión.
Los mensajes quedan asociados a una negociación y conservan su historial. No se ofrecen operaciones para editar o eliminar mensajes desde la API.

Cada turno puede identificarse con un request_id UUID. Este identificador proporciona idempotencia para reintentos y evita duplicar el mismo turno cuando se produce un fallo temporal.
5.6. Análisis de negociación
El módulo genera análisis sobre negociaciones cerradas. Cada negociación conserva una versión persistida de su análisis.

El contenido puede incluir:
- Resumen de la negociación.
- Estrategias observadas.
- Fortalezas.
- Áreas de mejora.
- Puntajes de las cinco dimensiones.
- Explicaciones y citas de evidencia.
- Resultado y evaluación del objetivo.
- Recomendaciones.
- Ejercicios de práctica.
- Alertas contextuales.
El sistema valida la estructura y las evidencias antes de aceptar un resultado como análisis válido.
5.7. Perfil del negociador
El perfil progresivo reúne indicadores contextuales derivados de los análisis disponibles. Puede presentar promedios, estrategias, fortalezas, oportunidades de mejora y evolución de indicadores.

El perfil se utiliza como contexto adicional para futuras prácticas y recomendaciones. No es un diagnóstico ni una clasificación fija de la personalidad del usuario.
5.8. Recomendaciones y ejercicios
El sistema puede ofrecer recomendaciones personalizadas y ejercicios construidos por la IA a partir del contexto del perfil y los resultados disponibles.

También existe un conjunto de ejercicios curados, servido desde /resources/exercises, que se presenta separado de las recomendaciones generadas por IA.
5.9. Eventos y comunicación en tiempo real
El módulo de eventos permite notificar cambios relevantes de una negociación, como el inicio, la creación de mensajes, la respuesta del gemelo, el cierre y la finalización de un análisis.

La comunicación utiliza un servicio central gRPC, Redis Pub/Sub y un puente WebSocket para los clientes web.
5.10. Rutas principales del frontend
Ruta	Función
/login, /register	Inicio de sesión y registro.
/dashboard	Resumen de actividad y accesos principales.
/scenarios	Listado y búsqueda de escenarios.
/scenarios/new	Creación de un escenario.
/scenarios/:id/edit	Edición de un escenario propio.
/scenarios/:id	Detalle de un escenario.
/negotiations/new	Inicio de negociación a partir de un escenario.
/negotiations	Historial de negociaciones.
/negotiations/:id	Chat, historial, cierre y análisis de una negociación.
/analyses	Listado de análisis.
/analyses/:id	Detalle de un análisis y sus evidencias.
/profile	Perfil y evolución de indicadores.
/training	Recomendaciones y ejercicios.
/settings	Datos de cuenta y cambio de contraseña.


Las rutas privadas requieren sesión. El JWT se conserva en sessionStorage, no se añade a URLs y se adjunta solo a solicitudes dirigidas al backend configurado. Los guards facilitan la navegación, pero la autorización efectiva corresponde al backend.
6. Comunicación en tiempo real: gRPC, Redis y WebSockets
El proyecto separa la comunicación entre componentes internos del backend de la comunicación con el navegador.
6.1. Servicios gRPC
Se implementan tres servicios especializados:
Servicio gRPC	Método	Responsabilidad
TwinNegotiationService	GenerateReply	Generar la respuesta del gemelo de negociación.
NegotiationAnalysisService	AnalyzeNegotiation	Generar el análisis estructurado de una negociación.
NegotiationEventService	PublishEvent	Publicar un evento persistido mediante su identificador.
NegotiationEventService	SubscribeEvents	Entregar eventos mediante streaming del servidor.


La comunicación se describe en app/rpc/negotiation.proto. Los servicios de IA validan el contexto, verifican el alcance de la identidad de servicio y devuelven estructuras JSON validadas.

Puertos locales predeterminados:
Servicio	Dirección predeterminada
Gemelo	127.0.0.1:50051
Análisis	127.0.0.1:50052
Eventos	127.0.0.1:50053


En la topología de producción de un solo servicio, los procesos gRPC se ejecutan en el mismo contenedor y se comunican por loopback. Para distribuirlos en máquinas o servicios distintos se deben configurar direcciones y certificados TLS válidos.
6.2. Redis Pub/Sub
El servicio central de eventos publica un aviso en un canal asociado al usuario, por ejemplo negotiation:user:{id}.

Redis transporta el aviso, mientras que el repositorio consulta los eventos persistidos y los entrega por secuencia. Así, Redis no es la fuente de verdad del historial.
6.3. Outbox transaccional
El backend registra el evento junto con la operación de negocio. Un dispatcher consulta los eventos pendientes, solicita su publicación al servicio gRPC central y marca el evento como entregado después de recibir confirmación.

Si un proceso falla después de publicar y antes de confirmar, puede volver a publicar el aviso. El diseño mantiene el evento persistido y utiliza identificadores y secuencias para controlar duplicados en el flujo.
6.4. WebSockets
El navegador no consume gRPC directamente. El frontend abre una conexión WebSocket con el backend y el puente WebSocket utiliza el servicio gRPC de eventos.

Dirección local:
ws://127.0.0.1:8000/ws/events
Dirección de producción:
wss://generador-gemelos-back-production.up.railway.app/ws/events
El primer mensaje de la conexión contiene el token y los parámetros de suscripción:
{
  "token": "<JWT obtenido en el login>",
  "negotiation_id": 1,
  "after_sequence": 0
}
negotiation_id: 0 permite suscribirse a todas las negociaciones propias. El cliente debe conservar la última secuencia confirmada y reconectar desde ese cursor cuando sea necesario. El token no se incluye en la URL.

Tipos de eventos documentados:
- negotiation.started
- message.created
- twin.responded
- negotiation.completed
- negotiation.cancelled
- analysis.completed
- recommendation.created
- profile.updated
- twin.failed
7. Arquitectura general del sistema
El sistema utiliza una arquitectura modular con separación entre interfaz, API, servicios internos, persistencia y proveedor de IA.
                         USUARIO
                            |
                            v
                 ANGULAR 22 / TYPESCRIPT
                   INTERFAZ WEB
                            |
                 HTTP / REST + WEBSOCKET
                            |
                            v
                    FASTAPI / UVICORN
                   API Y LÓGICA DE NEGOCIO
                            |
            +---------------+----------------+
            |               |                |
            v               v                v
       SQLALCHEMY       CLIENTES gRPC    WEBSOCKET BRIDGE
            |               |                |
            v       +-------+-------+        |
     POSTGRESQL    |       |       |        |
     (PRODUCCIÓN)  v       v       v        |
       SQLITE    TWIN   ANALYSIS  EVENTS     |
      (LOCAL)    ENGINE ENGINE   SERVICE     |
                  |       |       |          |
                  +---+---+       v          |
                      |         REDIS <------+ 
                      v        PUB/SUB
                  GROQ API
              GPT-OSS-20B
                      |
                      v
             RESPUESTA / ANÁLISIS
                      |
                      v
              VALIDACIÓN PYDANTIC
                      |
                      v
                PERSISTENCIA
Responsabilidades por componente
Frontend Angular
- Renderizar la interfaz y administrar la navegación.
- Capturar y validar formularios del lado del cliente.
- Gestionar la sesión y adjuntar el JWT a solicitudes autorizadas.
- Consultar escenarios, negociaciones, mensajes, análisis y perfil.
- Mostrar estados de conexión y eventos WebSocket.
Backend FastAPI
- Autenticar usuarios y validar permisos.
- Ejecutar las reglas de negocio y transacciones.
- Consultar y guardar información mediante SQLAlchemy.
- Coordinar los servicios gRPC.
- Administrar la cola de eventos/outbox.
- Validar respuestas de IA y conservar resultados válidos.
Servicios gRPC
- Separar la generación del gemelo.
- Separar el análisis de negociación.
- Centralizar la publicación y suscripción de eventos.
PostgreSQL / SQLite
- Conservar usuarios, escenarios, negociaciones, mensajes, análisis, perfiles y eventos.
Redis
- Distribuir notificaciones y coordinar límites compartidos de IA.
Groq
- Generar respuestas contextuales del gemelo.
- Producir análisis estructurados.
8. Estructura de la base de datos
SQLAlchemy define los modelos y Alembic administra las migraciones.
Tabla	Función
users	Usuarios, credenciales cifradas mediante hash y versión de token.
scenarios	Escenarios de negociación creados por cada usuario.
negotiations	Negociaciones, estado, resultado e instantánea del escenario.
messages	Mensajes del usuario y del gemelo, tipo e identificador idempotente.
analyses	Análisis estructurado persistido por negociación.
negotiator_profiles	Perfil progresivo e indicadores contextuales del negociador.
events	Eventos persistidos, secuencia y estado de entrega.


Relaciones principales
- Un usuario puede crear varios escenarios.
- Un usuario puede tener varias negociaciones.
- Un escenario puede originar varias negociaciones.
- Cada negociación contiene mensajes ordenados.
- Una negociación puede tener un análisis persistido.
- El perfil del negociador se relaciona con el usuario.
- Los eventos se asocian al usuario y a la negociación correspondiente.
Migraciones
Comando para actualizar la base de datos:
python -m alembic upgrade head
En producción, scripts/start_production.py ejecuta la migración después de comprobar Redis y antes de iniciar los servicios gRPC y FastAPI. En una base existente, se debe revisar el estado de Alembic y respaldar la información antes de aplicar cambios. No se debe ejecutar stamp sobre un esquema cuya equivalencia no haya sido verificada.
9. API REST
FastAPI expone las operaciones del sistema mediante una API REST con solicitudes y respuestas JSON.
Endpoints principales
Salvo registro, login, raíz, documentación y salud, las rutas protegidas requieren el encabezado:
Authorization: Bearer <JWT>
Método	Ruta	Operación
POST	/auth/register	Registrar usuario.
POST	/auth/login	Iniciar sesión y obtener JWT.
GET / PUT	/auth/me	Consultar o actualizar el perfil.
POST	/auth/password	Cambiar contraseña y revocar sesiones.
POST	/auth/logout	Cerrar sesión y revocar sesiones activas.
POST / GET	/scenarios/	Crear y listar escenarios.
GET / PUT / DELETE	/scenarios/{id}	Consultar, editar o archivar escenario.
POST / GET	/negotiations/	Iniciar y listar negociaciones.
GET / PATCH	/negotiations/{id}	Consultar, cerrar o cancelar negociación.
POST	/messages/	Enviar un mensaje y procesar el turno del gemelo.
GET	/messages/{negotiation_id}	Consultar historial de mensajes.
POST	/negotiations/{id}/analysis	Generar o recuperar el análisis.
GET	/analyses	Listar análisis propios.
GET	/analyses/{id}	Consultar un análisis propio.
GET	/profile	Consultar perfil y evolución de indicadores.
GET	/recommendations	Consultar recomendaciones personalizadas.
GET	/resources/exercises	Consultar ejercicios curados.
GET	/events	Consultar eventos con cursor y filtros.
WS	/ws/events	Suscribirse a eventos privados en tiempo real.
GET	/health	Verificar base de datos y configuración del proveedor de IA.


Los listados utilizan paginación mediante offset y limit. El historial de mensajes se ordena por identificador y los eventos por secuencia.
Ejemplo de envío de un mensaje
{
  "negotiation_id": 1,
  "request_id": "346d82d8-fc8a-4c8b-afbe-8f0b5aa63e92",
  "content": "Propongo aumentar el volumen a cambio de un descuento.",
  "kind": "offer"
}
El request_id se conserva cuando se reintenta una solicitud que pudo haber sido interrumpida. Para reintentos idempotentes se debe reutilizar el mismo UUID y el mismo contenido.
Códigos de respuesta habituales
Código	Significado
200	Operación consultada o completada correctamente.
201	Recurso creado.
401	Falta autenticación o el token no es válido.
404	Recurso inexistente o no perteneciente al usuario.
409	Conflicto de estado, concurrencia o idempotencia.
422	Error de validación de los datos enviados.
503	Proveedor de IA o servicio externo temporalmente no disponible.


Documentación interactiva
En local:
http://127.0.0.1:8000/docs
En producción:
https://generador-gemelos-back-production.up.railway.app/docs
10. Seguridad del sistema
El proyecto incorpora controles de seguridad en la autenticación, las llamadas internas y el acceso a los recursos.
10.1. Autenticación JWT
Los tokens de usuario se utilizan para autenticar operaciones protegidas. También existe una clave distinta para firmar tokens internos de servicio utilizados en operaciones gRPC.
10.2. Protección de contraseñas
Las contraseñas se almacenan mediante hashing con Argon2. No se guarda la contraseña original.
10.3. Control de sesiones
La versión de token del usuario permite revocar sesiones anteriores, por ejemplo cuando se cambia la contraseña o se cierra sesión.
10.4. Autorización por propietario
Los repositorios y servicios validan que el usuario autenticado sea propietario del recurso solicitado. Los servicios internos no confían en un user_id arbitrario enviado por el navegador.
10.5. Tokens de servicio gRPC
Las operaciones internas requieren JWT de servicio con alcance y usuario. Las suscripciones de eventos vuelven a verificar la sesión y la propiedad durante la conexión.
10.6. Variables de entorno
Las claves y credenciales se administran mediante variables de entorno. .env está excluido del control de versiones.
10.7. Comunicación segura
Para producción se deben usar HTTPS y WSS en las comunicaciones públicas. Los servicios gRPC se mantienen en loopback en la topología de un solo servicio; una topología distribuida debe protegerse con TLS y reglas de red adecuadas.
10.8. Manejo de información de IA
El contexto de negociación, el perfil contextual y el historial se transmiten al proveedor de IA para generar respuestas o análisis. Se debe informar de este tratamiento y evitar incluir información personal que no sea necesaria.
11. Variables de entorno
El backend utiliza un archivo .env en desarrollo y variables de servicio en Railway.
Backend
Variable	Función	Valor predeterminado / ejemplo
DATABASE_URL	Conexión a la base de datos.	sqlite:///./negotiation.db local.
SECRET_KEY	Firma de JWT de usuario.	Secreto aleatorio de al menos 32 caracteres.
SERVICE_SECRET	Firma de JWT de servicio.	Secreto distinto de SECRET_KEY, al menos 32 caracteres.
ACCESS_TOKEN_EXPIRE_MINUTES	Duración del token.	30
AI_PROVIDER	Selección explícita de proveedor.	groq
GROQ_API_KEY	Clave privada de Groq.	Se configura en backend.
GROQ_MODEL	Modelo usado por Groq.	openai/gpt-oss-20b
GROQ_TIMEOUT_SECONDS	Timeout de Groq.	30
GROQ_REQUESTS_PER_MINUTE	Límite preventivo compartido.	10
REDIS_URL	Conexión a Redis.	redis://127.0.0.1:6379/0 local.
TWIN_GRPC_TARGET	Dirección del servicio del gemelo.	127.0.0.1:50051
ANALYSIS_GRPC_TARGET	Dirección del servicio de análisis.	127.0.0.1:50052
EVENT_GRPC_TARGET	Dirección del servicio de eventos.	127.0.0.1:50053
GRPC_TIMEOUT_SECONDS	Timeout de llamadas gRPC.	40
GRPC_TLS_CA	Certificado CA para gRPC TLS.	Ruta opcional.
GRPC_TLS_CERT	Certificado del servidor gRPC.	Ruta opcional.
GRPC_TLS_KEY	Clave privada del servidor gRPC.	Ruta opcional.
CORS_ORIGINS	Orígenes autorizados separados por coma.	http://localhost:4200
SEED_PASSWORD	Contraseña temporal para los datos de ejemplo.	Se define localmente.


Para la ruta local opcional de IA también pueden configurarse AI_BASE_URL, AI_MODEL, AI_TIMEOUT_SECONDS, AI_MAX_TOKENS, AI_MAX_CONTEXT_BYTES, AI_CONCURRENCY, AI_QUEUE_TIMEOUT_SECONDS y AI_SCHEMA_MODE.
Frontend
Variable	Función
API_BASE_URL	URL pública del backend, sin añadir rutas de endpoints.
WEBSOCKET_URL	URL opcional del WebSocket. Si no se define y se configura API_BASE_URL, se deriva como <API_BASE_URL>/ws/events.
PORT	Puerto del servidor frontend.
BASE_PATH	Prefijo opcional de la aplicación.


La configuración de runtime del frontend solo publica las direcciones de conexión necesarias. No deben añadirse GROQ_API_KEY, SECRET_KEY, SERVICE_SECRET, contraseñas o tokens como variables públicas del navegador.
12. Pruebas y validaciones
Backend
La validación documentada para la integración de Groq registró 167 pruebas aprobadas, sin fallos, excluyendo tests/test_migrations.py para no ejecutar pruebas de downgrade sobre bases que no corresponden a ese ensayo.

Dentro de esa validación se documentan 40 casos específicos del proveedor Groq utilizando el SDK oficial con transporte HTTP simulado. Las pruebas de integración cubren, entre otros aspectos:
- Registro, login, JWT y revocación de sesiones.
- Protección de rutas y propiedad de los recursos.
- Creación, edición y archivo de escenarios.
- Estados de negociación e historial.
- Idempotencia y concurrencia de turnos.
- Conservación de mensajes ante fallos del proveedor.
- Validación de análisis, dimensiones y citas exactas.
- Perfiles, recomendaciones y ejercicios.
- Servicios gRPC del gemelo, análisis y eventos.
- Redis real para Pub/Sub, fan-out, aislamiento, deduplicación y recuperación.
- WebSockets, reanudación por cursor y reconexión.
- Migraciones y herramientas de configuración.
- Errores, cuotas, respuestas inválidas y timeout de Groq.
Las pruebas de Groq utilizan un transporte controlado y no consumen cuota ni prueban la calidad de una cuenta real. La disponibilidad, cuota, latencia y calidad del proveedor deben verificarse de forma independiente con credenciales válidas.

Comandos:
python -m pytest -q
git diff --check
Redis debe estar disponible para las pruebas que lo requieren. Las pruebas utilizan bases temporales y no deben ejecutarse apuntando a la base de datos de producción.
Frontend
La validación documentada del frontend registra 55 pruebas aprobadas, además de compilación de tipos y build de producción correctos.

También se documentaron verificaciones de:
- Configuración de la URL de API y WebSocket.
- Autenticación y protección de rutas.
- Escenarios, negociaciones, chat e historial.
- Consumo de análisis y perfil.
- Conexión WebSocket y gestión de eventos.
- Respuestas de error y estados de disponibilidad.
- Integración HTTP contra el backend a través del proxy.
Comandos:
pnpm test
pnpm typecheck
pnpm build
13. Despliegue en Railway
El despliegue de producción utiliza Railway para alojar los componentes principales.
Servicios del proyecto
Servicio	Responsabilidad
generador-gemelos-front	Aplicación Angular.
generador-gemelos-back	API FastAPI, servicios gRPC y supervisor.
Postgres	Base de datos persistente de producción.
Redis	Pub/Sub y límites compartidos del proveedor de IA.


El proyecto de Railway se ha identificado como adaptable-respect.
Dominios de producción
Frontend:

https://generador-gemelos-front-production.up.railway.app

Backend:

https://generador-gemelos-back-production.up.railway.app

Documentación de API:

https://generador-gemelos-back-production.up.railway.app/docs

Health check:

https://generador-gemelos-back-production.up.railway.app/health
Backend en Railway
El backend se ejecuta con el supervisor:
python scripts/start_production.py
El supervisor realiza las siguientes tareas:
1. Valida las claves de seguridad y la configuración de los servicios.
2. Comprueba la conexión con Redis.
3. Ejecuta python -m alembic upgrade head.
4. Inicia el servicio gRPC del gemelo.
5. Espera a que el servicio gRPC del gemelo esté disponible.
6. Inicia el servicio gRPC de análisis.
7. Inicia el servicio gRPC de eventos.
8. Inicia FastAPI/Uvicorn en el puerto proporcionado por Railway (PORT).
9. Comprueba el endpoint /health.
10. Supervisa los procesos y los detiene correctamente cuando recibe una señal de apagado.
Los tres servicios gRPC usan direcciones loopback dentro del mismo contenedor. PostgreSQL y Redis se conectan mediante sus respectivas variables de entorno.
Frontend en Railway
El frontend se compila con Angular y utiliza un servidor Node para servir los archivos compilados y la configuración pública.

Para conectarlo al backend desplegado se utilizan:
API_BASE_URL=https://generador-gemelos-back-production.up.railway.app
WEBSOCKET_URL=wss://generador-gemelos-back-production.up.railway.app/ws/events
El backend debe incluir el dominio del frontend en CORS_ORIGINS. Al usar HTTPS, la conexión WebSocket debe utilizar WSS.
Verificación posterior al despliegue
1. Abrir /health en el backend.
2. Comprobar /docs.
3. Confirmar en los logs que Redis conecta y que los servicios gRPC están listos.
4. Abrir el frontend y comprobar login, navegación y consulta de escenarios.
5. Crear una negociación de prueba.
6. Enviar un mensaje y comprobar que se conserva en el historial.
7. Comprobar la conexión de eventos WebSocket.
8. Finalizar una negociación y probar el análisis.
9. Confirmar que el análisis válido se persiste y que el perfil se actualiza.
La respuesta /health informa el estado de la base de datos, si hay clave de Groq configurada, el proveedor seleccionado y el estado ai_readiness. groq_configured=true solo indica que la variable no está vacía; ai_readiness=not_probed no certifica por sí solo una generación real ni la calidad de las respuestas.
14. Ejecución en entorno local
14.1. Requisitos
- Python 3.13.
- Node.js 24.13 o superior.
- pnpm 10.
- Redis Server 7 o superior; el repositorio se validó con Redis 7.2.10.
- PostgreSQL opcional para desarrollo con ese motor; SQLite está disponible como valor local predeterminado.
- Clave de Groq para generar respuestas y análisis reales.
- Git.
En Windows, Redis puede ejecutarse mediante WSL u otro entorno compatible.
14.2. Backend
Clonar el repositorio:
git clone https://github.com/1081271746/generador-gemelos-back.git
cd generador-gemelos-back
Crear y activar el entorno virtual:
python -m venv .venv
.venv\Scripts\Activate.ps1
Instalar dependencias:
python -m pip install -r requirements.txt
Crear la configuración inicial:
python scripts/configure_local.py
configure_local.py está pensado para instalaciones nuevas. Crea .env sin sobrescribir uno que ya exista. Si el entorno ya está configurado, no se debe ejecutar para reemplazar credenciales o variables; se deben conservar las existentes y ajustar únicamente las variables necesarias.

Aplicar migraciones:
python -m alembic upgrade head
Iniciar Redis en una terminal:
redis-server --bind 127.0.0.1 --port 6379
Iniciar los servicios en terminales separadas, con el entorno virtual activo:

Terminal 1 — Gemelo:
python -m app.rpc.ai_server twin
Terminal 2 — Análisis:
python -m app.rpc.ai_server analysis
Terminal 3 — Eventos:
python -m app.rpc.event_server
Terminal 4 — API:
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
La API estará disponible en:
http://127.0.0.1:8000
Swagger:
http://127.0.0.1:8000/docs
Health check:
http://127.0.0.1:8000/health
14.3. Datos ficticios de demostración
Para cargar datos ficticios en una base local nueva, definir SEED_PASSWORD con una contraseña temporal segura (mínimo 12 caracteres) y ejecutar:
python -m seed.load
El seed crea el usuario de demostración demo@example.com, dos escenarios y una negociación de ejemplo. La operación es repetible y no modifica un usuario existente. No crea resultados de IA ficticios.

No ejecutar el seed contra producción salvo que se haya autorizado expresamente y se haya revisado el impacto.
14.4. Frontend
Clonar el repositorio:
git clone https://github.com/1081271746/generador-gemelos-front.git
cd generador-gemelos-front
Instalar dependencias:
pnpm install --frozen-lockfile
Iniciar Angular:
pnpm dev
Abrir:
http://localhost:4200
El proxy de desarrollo está definido en proxy.conf.json. El prefijo /api/backend se reenvía a http://127.0.0.1:8000, se elimina dicho prefijo y se admite WebSocket.

Compilar:
pnpm build
Ejecutar pruebas y verificación de tipos:
pnpm test
pnpm typecheck
Servir el build local:
pnpm serve
14.5. Configuración del frontend
La configuración pública se encuentra en public/config.json:
{
  "apiBaseUrl": "/api/backend",
  "websocketUrl": "/api/backend/ws/events"
}
Para conectarse directamente a un backend desplegado, configurar las direcciones públicas antes de construir el frontend:
$env:API_BASE_URL="https://generador-gemelos-back-production.up.railway.app"
$env:WEBSOCKET_URL="wss://generador-gemelos-back-production.up.railway.app/ws/events"
pnpm build
API_BASE_URL y WEBSOCKET_URL son direcciones públicas, no secretos. No deben contener credenciales, contraseñas, tokens, query strings ni fragmentos.
15. Estructura general de los repositorios
Las rutas siguientes representan la organización principal de cada repositorio. Algunos módulos auxiliares pueden cambiar conforme evoluciona el código.
15.1. Backend
generador-gemelos-back/
│
├── app/
│   ├── ai/
│   │   ├── inference/       # Interfaz y motor de inferencia local opcional
│   │   ├── groq.py          # Cliente oficial asíncrono de Groq
│   │   ├── model_manager.py # Selección explícita del proveedor
│   │   ├── twin_engine.py   # Generación de respuestas del gemelo
│   │   ├── analysis_engine.py # Análisis estructurado
│   │   └── prompts.py       # Instrucciones de los motores
│   │
│   ├── core/                # Configuración, seguridad, errores y dependencias
│   ├── database/            # Motor, sesiones y base declarativa
│   ├── models/              # Modelos SQLAlchemy
│   ├── repositories/        # Consultas y aislamiento de datos
│   ├── routers/             # Endpoints HTTP de FastAPI
│   ├── schemas/             # Esquemas Pydantic
│   ├── services/            # Lógica de negocio, outbox y coordinación
│   ├── rpc/                 # .proto, clientes, servidores y clases generadas
│   ├── websocket/           # Bridge WebSocket para eventos
│   └── main.py              # Creación de la aplicación FastAPI
│
├── migrations/              # Versiones Alembic
├── seed/                    # Datos ficticios para desarrollo
├── scripts/                 # Configuración, generación Protobuf y supervisor
├── tests/                   # Pruebas unitarias e integración
├── training/                # Preparación de datos y pipeline LoRA/QLoRA opcional
├── docs/                    # Arquitectura, IA, validación y guías técnicas
├── .env.example             # Variables de ejemplo sin secretos
├── alembic.ini
├── requirements.txt
└── README.md
15.2. Frontend
generador-gemelos-front/
│
├── src/
│   ├── app/
│   │   ├── core/
│   │   │   ├── auth/        # Sesión, login, logout y guards
│   │   │   ├── config/      # Configuración runtime
│   │   │   ├── http/        # Interceptor y manejo de errores
│   │   │   └── services/    # Servicios HTTP, WebSocket y notificaciones
│   │   ├── features/        # Funcionalidades y páginas bajo demanda
│   │   ├── layouts/         # Estructuras de navegación
│   │   └── shared/          # Modelos y componentes reutilizables
│   ├── main.ts
│   └── styles.css
│
├── public/
│   ├── config.json         # Configuración pública por defecto
│   └── config.example.json
├── scripts/
│   ├── dev.mjs
│   ├── serve.mjs
│   └── runtime-config.mjs
├── docs/                   # Arquitectura, contrato y validación
├── proxy.conf.json
├── angular.json
├── package.json
├── pnpm-lock.yaml
└── README.md
16. Patrones y prácticas de ingeniería utilizados
- Arquitectura cliente-servidor: separación entre frontend y backend.
- Repository Pattern: encapsula consultas y acceso a datos, incluyendo el control de propiedad de recursos.
- Service Layer: concentra reglas de negocio, estados, turnos, análisis y perfiles.
- Dependency Injection: permite sustituir sesiones, clientes y dependencias en pruebas.
- Factory Pattern: creación de la aplicación, motores y canales de comunicación.
- Publish/Subscribe: distribución de eventos mediante Redis Pub/Sub.
- Fan-Out: entrega de avisos a múltiples suscriptores autorizados.
- Transactional Outbox: persistencia de eventos junto con operaciones de negocio y publicación con reintentos.
- Idempotencia: UUID request_id para controlar reintentos de turnos.
- Validación por esquemas: Pydantic para solicitudes, respuestas de IA y análisis.
- JWT y Argon2: autenticación y protección de credenciales.
- Migraciones versionadas: evolución controlada del esquema mediante Alembic.
- Pruebas automatizadas: verificación de lógica, contratos, servicios, eventos y errores.
17. Estado actual y límites conocidos
Implementado
- Frontend Angular y backend FastAPI en repositorios separados.
- Gestión de usuarios, autenticación y sesiones JWT.
- Creación, edición y archivo de escenarios.
- Inicio y seguimiento de negociaciones.
- Chat con el gemelo y persistencia de mensajes.
- Análisis estructurado con cinco dimensiones y citas de evidencia.
- Perfil progresivo, recomendaciones y ejercicios.
- Servicios gRPC para gemelo, análisis y eventos.
- Redis Pub/Sub, outbox y WebSockets.
- Integración de Groq como proveedor predeterminado.
- Ruta local opcional con llama.cpp.
- Pipeline de preparación y entrenamiento LoRA/QLoRA.
- Pruebas automatizadas en backend y frontend.
- Despliegue del frontend y backend en Railway, con PostgreSQL y Redis.
Limitaciones que deben quedar claras
- No existe un adaptador LoRA/QLoRA especializado y entrenado listo para producción.
- Los ejemplos sintéticos documentados son demostrativos y no equivalen a un dataset experto.
- Las pruebas automatizadas de Groq utilizan transporte simulado; no demuestran por sí solas la disponibilidad, latencia, cuota ni calidad de una cuenta externa real.
- El endpoint /health no ejecuta una generación de IA; informa la presencia de configuración y el estado de la base de datos.
- Las dimensiones del análisis son indicadores contextuales, no diagnósticos ni mediciones psicológicas validadas.
- El guard numérico del motor local es conservador y no resuelve todos los límites narrativos complejos.
- Redis es un componente de coordinación y eventos; no es la base de datos persistente.
- Cambiar DATABASE_URL no migra automáticamente los registros entre SQLite y PostgreSQL.
18. Conclusión
El Generador de Gemelos de Negociación integra desarrollo web, servicios distribuidos, bases de datos, comunicación en tiempo real e inteligencia artificial para crear un entorno de práctica de negociación.

Angular proporciona la interfaz de usuario; FastAPI administra la lógica y la API; SQLAlchemy y PostgreSQL conservan la información; gRPC divide las responsabilidades del gemelo, el análisis y los eventos; Redis distribuye notificaciones y controla cuotas; y Groq genera respuestas y análisis estructurados.

La separación por módulos permite mantener el sistema, probar sus componentes y ampliar sus funcionalidades. La ruta de IA local y el pipeline de entrenamiento dejan una base para experimentación futura, sin afirmar que exista ya un modelo especializado entrenado.
