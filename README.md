CREDENCIALES PARA INICIAR:

CORREO: sebitasroja06@gmail.com
CONTRASEÑA: 1234567891112



# Generador de Gemelos de Negociación 

### Plataforma web para practicar negociaciones con un gemelo de inteligencia artificial y analizar el desempeño con evidencias

El **Generador de Gemelos de Negociación** es una plataforma web que permite crear escenarios de negociación, practicar conversaciones con un gemelo de IA, consultar el historial de cada negociación y obtener análisis estructurados sobre las estrategias utilizadas.

El proyecto utiliza una arquitectura cliente-servidor dividida en dos repositorios: un frontend desarrollado con Angular y un backend desarrollado con FastAPI. El backend coordina la persistencia, la autenticación, los servicios gRPC, los eventos en tiempo real y la comunicación con Groq. PostgreSQL se utiliza como base de datos en el despliegue de Railway y Redis apoya la distribución de eventos y el control compartido de solicitudes de IA.

La IA no se entrena automáticamente con cada conversación. El sistema construye el contexto de cada negociación y lo envía al proveedor configurado para producir respuestas o análisis. También existe una ruta opcional de inferencia local y un pipeline de preparación de datos y entrenamiento LoRA/QLoRA, pero **no hay actualmente un adaptador especializado entrenado y validado**.

---

# 1. Objetivos del proyecto

## Objetivo general

Desarrollar una plataforma de práctica de negociación que permita simular conversaciones con un gemelo de IA, administrar escenarios, conservar el historial de las interacciones y analizar habilidades de negociación mediante indicadores contextuales y evidencias extraídas de los mensajes.

## Objetivos específicos

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

---

# 2. Repositorios del proyecto

El proyecto se encuentra separado en dos repositorios independientes:

| Componente | Repositorio | Responsabilidad |
|---|---|---|
| Backend | [generador-gemelos-back](https://github.com/1081271746/generador-gemelos-back) | API, lógica de negocio, persistencia, autenticación, IA, gRPC y eventos. |
| Frontend | [generador-gemelos-front](https://github.com/1081271746/generador-gemelos-front) | Interfaz web, navegación, autenticación del cliente, chat, escenarios, análisis y conexión en tiempo real. |

El frontend consume la API existente del backend. No implementa una segunda lógica de negocio ni accede directamente a PostgreSQL, Redis o los servicios gRPC.

---

# 3. Tecnologías utilizadas

## 3.1. Frontend

| Tecnología | Función |
|---|---|
| Angular 22.2.5 | Framework principal para construir la aplicación web. |
| Angular CLI / Builder 22.2.6 | Herramientas de desarrollo, pruebas y compilación. |
| TypeScript 6 | Lenguaje principal del frontend. |
| HTML5 | Estructura de las páginas y componentes. |
| CSS3 | Estilos y presentación visual. |
| Tailwind CSS 4 | Utilidades de diseño y estilos de interfaz. |
| RxJS 7.8 | Manejo de operaciones asíncronas y flujos HTTP. |
| Angular Router | Navegación entre las secciones de la aplicación. |
| Angular Signals | Estado reactivo de sesión, conexión y componentes. |
| HttpClient | Comunicación HTTP con el backend. |
| Vitest | Pruebas unitarias del frontend. |
| jsdom | Entorno de navegador simulado para las pruebas. |
| Node.js 24.13 o superior | Entorno de ejecución de herramientas y servidor estático. |
| pnpm 10 | Instalación y administración de dependencias. |

La aplicación utiliza componentes standalone, rutas cargadas bajo demanda, formularios reactivos, guards de navegación e interceptores HTTP para adjuntar el JWT a las solicitudes dirigidas al backend configurado.

## 3.2. Backend

| Tecnología | Función |
|---|---|
| Python 3.13 | Lenguaje principal del backend. |
| FastAPI 0.162.2 | Construcción de la API REST y documentación OpenAPI. |
| Uvicorn 0.54.0 | Servidor ASGI que ejecuta FastAPI. |
| SQLAlchemy 2.1.8 | ORM y acceso a la base de datos. |
| Pydantic 2.14.3 | Validación de solicitudes, respuestas y estructuras generadas por IA. |
| Alembic 1.20.1 | Control de versiones y migraciones de la base de datos. |
| PyJWT 2.15.1 | Creación y validación de tokens JWT. |
| argon2-cffi 25.1.0 | Hashing seguro de contraseñas mediante Argon2. |
| python-dotenv 1.2.4 | Lectura de variables de entorno desde `.env`. |
| HTTPX 0.28.1 | Cliente HTTP y transporte de pruebas. |
| pytest 9.2.0 | Pruebas automatizadas del backend. |
| pytest-asyncio | Soporte para pruebas asíncronas. |

El backend se organiza mediante routers, servicios, repositorios, esquemas Pydantic, modelos SQLAlchemy y dependencias inyectables. FastAPI administra las solicitudes HTTP y coordina las operaciones con los servicios internos.

## 3.3. Base de datos

**PostgreSQL** es la base de datos utilizada en el despliegue de Railway. El backend utiliza SQLAlchemy y el controlador `psycopg[binary]` para conectarse a PostgreSQL.

Para desarrollo local, el proyecto conserva SQLite como configuración predeterminada (`sqlite:///./negotiation.db`). La URL se define mediante `DATABASE_URL`, por lo que se puede seleccionar la base de datos sin modificar la lógica de negocio.

Alembic administra las migraciones. El cambio de SQLite a PostgreSQL no copia automáticamente los registros: una migración de datos entre motores requiere respaldo, transferencia, revisión de claves y secuencias, y validación de integridad.

## 3.4. Redis

**Redis** (servidor probado con Redis 7.2.10) se utiliza como infraestructura de eventos y coordinación. El backend utiliza el cliente Python `redis` 8.1.0. Redis no reemplaza PostgreSQL.

Sus responsabilidades principales son:

- Distribuir avisos de eventos mediante Pub/Sub.
- Facilitar el fan-out de notificaciones a varios suscriptores autorizados.
- Mantener el contador compartido de solicitudes de IA por modelo y minuto.
- Coordinar procesos que participan en el flujo de eventos.

Los eventos de negocio se conservan en la base de datos. Redis transporta avisos para que los suscriptores consulten los eventos persistidos y los entreguen en orden.

## 3.5. gRPC y Protocol Buffers

| Tecnología | Función |
|---|---|
| gRPC 1.85.1 | Comunicación entre FastAPI y los servicios especializados. |
| grpcio-tools 1.85.1 | Generación de código cliente/servidor desde `.proto`. |
| Protocol Buffers 7.36.2 | Definición tipada de mensajes y contratos entre servicios. |
| `grpc.aio` | Servidores y clientes gRPC asíncronos. |

Los contratos están definidos en `app/rpc/negotiation.proto`. La arquitectura mantiene separados el gemelo, el análisis y la distribución central de eventos.

## 3.6. Inteligencia artificial

**Groq API** es el proveedor predeterminado de IA.

| Elemento | Configuración |
|---|---|
| Proveedor | Groq |
| SDK | `groq` 1.7.0 |
| Cliente | `AsyncGroq` |
| Modelo predeterminado | `openai/gpt-oss-20b` |
| Formato de respuesta | JSON Schema y validación Pydantic |
| Límite preventivo | 10 solicitudes por minuto por modelo, compartidas mediante Redis por defecto |
| Timeout predeterminado | 30 segundos para Groq |
| Configuración | Variables de entorno del backend |

El identificador `openai/gpt-oss-20b` corresponde al modelo servido por Groq. El sistema utiliza el SDK y la infraestructura de Groq; no utiliza la API de OpenAI para esta inferencia. Gemini fue retirado como proveedor activo.

También existe una opción local explícita mediante `AI_PROVIDER=local`, basada en un servidor `llama.cpp`. Esta ruta opcional utiliza como baseline documentado `Qwen/Qwen2.5-1.5B-Instruct` en formato GGUF. No es el proveedor predeterminado y no existe fallback automático entre proveedores.

## 3.7. Despliegue e infraestructura

| Tecnología / servicio | Función |
|---|---|
| Railway | Plataforma utilizada para desplegar frontend, backend y servicios administrados. |
| PostgreSQL en Railway | Persistencia de producción. |
| Redis en Railway | Mensajería Pub/Sub y cuotas compartidas. |
| Git y GitHub | Control de versiones y alojamiento de los repositorios. |
| Supervisor Python | Arranque, supervisión y apagado de los procesos del backend en el despliegue de un solo servicio. |

---

# 4. Integración de inteligencia artificial con Groq

La inteligencia artificial es uno de los componentes principales del Generador de Gemelos de Negociación. El sistema utiliza el proveedor para crear respuestas del gemelo y producir análisis estructurados de negociaciones finalizadas.

## 4.1. ¿Cómo funciona el gemelo?

1. El usuario crea un escenario y define el contexto de la negociación.
2. El usuario inicia una negociación a partir de ese escenario.
3. El backend crea una instantánea (`scenario_snapshot`) para conservar las condiciones originales de esa negociación.
4. El usuario envía una oferta, contraoferta, argumento o concesión.
5. FastAPI valida la solicitud, verifica la propiedad de la negociación y conserva el mensaje.
6. FastAPI prepara el contexto con el escenario, el historial de mensajes y el perfil disponible.
7. FastAPI solicita la generación al servicio gRPC del gemelo.
8. El servicio gRPC utiliza `TwinEngine` y el proveedor seleccionado.
9. Groq procesa el contexto y devuelve una respuesta estructurada.
10. El backend valida la respuesta mediante Pydantic y las reglas del motor.
11. La respuesta del gemelo se guarda y se devuelve al frontend.

La respuesta del gemelo contiene el texto y el tipo de intervención. Los tipos admitidos son `offer`, `counteroffer`, `argument` y `concession`.

## 4.2. ¿Cómo funciona el análisis?

1. El usuario finaliza una negociación con un resultado explícito.
2. El sistema verifica que la negociación esté cerrada y cuente con mensajes.
3. El backend reúne el escenario, el historial y el contexto permitido.
4. FastAPI solicita el análisis al servicio gRPC especializado.
5. `AnalysisEngine` prepara las instrucciones y el esquema de salida.
6. Groq genera el análisis estructurado.
7. Pydantic valida la estructura, los puntajes y las evidencias.
8. El backend verifica que las citas correspondan exactamente a mensajes del usuario.
9. El análisis válido se guarda en PostgreSQL o SQLite, según la configuración.
10. El frontend presenta el resumen, las dimensiones, las evidencias y las recomendaciones.

## 4.3. Dimensiones evaluadas

El análisis utiliza cinco dimensiones contextuales, cada una con un puntaje entre 0 y 100, explicación y evidencias:

| Dimensión | Qué representa en el análisis |
|---|---|
| `assertiveness` | Asertividad durante la negociación. |
| `cooperation` | Cooperación con la contraparte. |
| `flexibility` | Flexibilidad para considerar alternativas. |
| `argumentation` | Calidad de la argumentación. |
| `conflict_management` | Manejo de desacuerdos y conflictos. |

Cada evidencia contiene un identificador de mensaje y una cita literal. El backend rechaza estructuras inválidas o citas que no correspondan al contenido original.

El resultado también puede incluir resumen, estrategias, fortalezas, áreas de mejora, resultado de la negociación, evaluación del objetivo, recomendaciones, ejercicios y alertas.

Los indicadores son contextuales y sirven para reflexionar sobre una práctica concreta. No representan diagnósticos psicológicos ni etiquetas definitivas de personalidad.

## 4.4. Configuración del proveedor

La integración se configura desde el backend:

```env
AI_PROVIDER=groq
GROQ_API_KEY=tu_clave_de_groq
GROQ_MODEL=openai/gpt-oss-20b
GROQ_TIMEOUT_SECONDS=30
GROQ_REQUESTS_PER_MINUTE=10
```

La clave `GROQ_API_KEY` debe permanecer exclusivamente en el entorno del backend. No debe incluirse en Angular, en archivos públicos, en `public/config.json`, en GitHub ni en capturas de pantalla.

## 4.5. Validación y manejo de fallos

La respuesta del proveedor debe cumplir el esquema esperado y finalizar correctamente. Se controlan respuestas vacías, truncadas, bloqueadas, inválidas, errores de autenticación, cuota, conexión y timeout.

No existe fallback automático a otro proveedor. Si la IA falla, el sistema informa la indisponibilidad, conserva el mensaje del usuario y permite recuperar el flujo utilizando el mismo `request_id`. No se genera una respuesta ficticia para simular que Groq respondió.

El contexto enviado al proveedor incluye el escenario, el perfil contextual y el historial de la negociación. El sistema limita el contexto a 200.000 bytes UTF-8 y rechaza solicitudes que excedan ese tamaño en lugar de truncar silenciosamente los datos. Antes de utilizarlo con información real, se debe informar a los usuarios sobre el procesamiento externo y revisar los requisitos de privacidad y autorización aplicables.

## 4.6. Ruta opcional de IA local y entrenamiento

El backend conserva una implementación opcional de inferencia local mediante `llama.cpp` y el proveedor `AI_PROVIDER=local`.

La documentación del repositorio describe:

- Modelo base documentado: `Qwen/Qwen2.5-1.5B-Instruct`.
- Formato de inferencia: GGUF cuantizado.
- Servidor de inferencia: `llama.cpp`.
- Especialización prevista: LoRA / QLoRA mediante Transformers y PEFT.
- Preparación de datos: validación, deduplicación, división de conjuntos y manifiestos.

**Estado real de esta ruta:** se implementó el pipeline y se probó inferencia del modelo base en CPU, pero no se ha completado un adaptador especializado entrenado y evaluado. El corpus sintético documentado de 20 ejemplos es demostrativo y no constituye un conjunto suficiente para afirmar que existe un modelo experto en negociación. Groq continúa siendo el proveedor predeterminado.

---

# 5. Módulos principales del sistema

## 5.1. Autenticación y usuarios

Permite registrar usuarios, iniciar sesión, consultar y actualizar el perfil, cambiar la contraseña y cerrar sesión.

Incluye:

- Registro y login mediante correo y contraseña.
- Hashing de contraseñas con Argon2.
- Tokens JWT con expiración y validación de sesión.
- Versión de token para revocación de sesiones.
- Claves separadas para firmar tokens de usuario y tokens internos de servicio.
- Protección de rutas y verificación de propiedad de los recursos.

## 5.2. Dashboard

Es la pantalla principal de la aplicación. Presenta información de actividad y permite acceder a los módulos de escenarios, negociaciones, análisis y perfil.

Los contadores y listados se calculan a partir de datos reales y paginados del backend. El frontend no inventa estadísticas ni usa cifras de demostración para reemplazar respuestas de la API.

## 5.3. Escenarios de negociación

Permite crear, listar, consultar, editar y archivar escenarios propios.

Cada escenario contempla información como:

- Título y descripción.
- Contexto de la negociación.
- Objetivo del usuario.
- Rol de la contraparte.
- Objetivo de la contraparte.
- Límites de la contraparte.

Un escenario pertenece a un usuario. Al iniciar una negociación, el backend conserva una instantánea de su contenido; por tanto, editar posteriormente el escenario no altera las condiciones de conversaciones anteriores.

## 5.4. Negociaciones

Permite iniciar negociaciones a partir de escenarios, consultar el historial y finalizar o cancelar una negociación.

Estados principales:

| Estado | Significado |
|---|---|
| `active` | La negociación continúa abierta. |
| `completed` | La negociación terminó con un resultado registrado. |
| `cancelled` | La negociación fue cancelada. |

El cierre requiere un resultado explícito. Una negociación cerrada queda en modo de solo lectura y se utiliza como fuente para el análisis.

## 5.5. Chat y mensajes

El chat es el espacio donde el usuario intercambia mensajes con el gemelo.

Tipos de mensajes admitidos:

- `offer`: oferta.
- `counteroffer`: contraoferta.
- `argument`: argumento.
- `concession`: concesión.

Los mensajes quedan asociados a una negociación y conservan su historial. No se ofrecen operaciones para editar o eliminar mensajes desde la API.

Cada turno puede identificarse con un `request_id` UUID. Este identificador proporciona idempotencia para reintentos y evita duplicar el mismo turno cuando se produce un fallo temporal.

## 5.6. Análisis de negociación

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

## 5.7. Perfil del negociador

El perfil progresivo reúne indicadores contextuales derivados de los análisis disponibles. Puede presentar promedios, estrategias, fortalezas, oportunidades de mejora y evolución de indicadores.

El perfil se utiliza como contexto adicional para futuras prácticas y recomendaciones. No es un diagnóstico ni una clasificación fija de la personalidad del usuario.

## 5.8. Recomendaciones y ejercicios

El sistema puede ofrecer recomendaciones personalizadas y ejercicios construidos por la IA a partir del contexto del perfil y los resultados disponibles.

También existe un conjunto de ejercicios curados, servido desde `/resources/exercises`, que se presenta separado de las recomendaciones generadas por IA.

## 5.9. Eventos y comunicación en tiempo real

El módulo de eventos permite notificar cambios relevantes de una negociación, como el inicio, la creación de mensajes, la respuesta del gemelo, el cierre y la finalización de un análisis.

La comunicación utiliza un servicio central gRPC, Redis Pub/Sub y un puente WebSocket para los clientes web.

## 5.10. Rutas principales del frontend

| Ruta | Función |
|---|---|
| `/login`, `/register` | Inicio de sesión y registro. |
| `/dashboard` | Resumen de actividad y accesos principales. |
| `/scenarios` | Listado y búsqueda de escenarios. |
| `/scenarios/new` | Creación de un escenario. |
| `/scenarios/:id/edit` | Edición de un escenario propio. |
| `/scenarios/:id` | Detalle de un escenario. |
| `/negotiations/new` | Inicio de negociación a partir de un escenario. |
| `/negotiations` | Historial de negociaciones. |
| `/negotiations/:id` | Chat, historial, cierre y análisis de una negociación. |
| `/analyses` | Listado de análisis. |
| `/analyses/:id` | Detalle de un análisis y sus evidencias. |
| `/profile` | Perfil y evolución de indicadores. |
| `/training` | Recomendaciones y ejercicios. |
| `/settings` | Datos de cuenta y cambio de contraseña. |

Las rutas privadas requieren sesión. El JWT se conserva en `sessionStorage`, no se añade a URLs y se adjunta solo a solicitudes dirigidas al backend configurado. Los guards facilitan la navegación, pero la autorización efectiva corresponde al backend.

---

# 6. Comunicación en tiempo real: gRPC, Redis y WebSockets

El proyecto separa la comunicación entre componentes internos del backend de la comunicación con el navegador.

## 6.1. Servicios gRPC

Se implementan tres servicios especializados:

| Servicio gRPC | Método | Responsabilidad |
|---|---|---|
| `TwinNegotiationService` | `GenerateReply` | Generar la respuesta del gemelo de negociación. |
| `NegotiationAnalysisService` | `AnalyzeNegotiation` | Generar el análisis estructurado de una negociación. |
| `NegotiationEventService` | `PublishEvent` | Publicar un evento persistido mediante su identificador. |
| `NegotiationEventService` | `SubscribeEvents` | Entregar eventos mediante streaming del servidor. |

La comunicación se describe en `app/rpc/negotiation.proto`. Los servicios de IA validan el contexto, verifican el alcance de la identidad de servicio y devuelven estructuras JSON validadas.

Puertos locales predeterminados:

| Servicio | Dirección predeterminada |
|---|---|
| Gemelo | `127.0.0.1:50051` |
| Análisis | `127.0.0.1:50052` |
| Eventos | `127.0.0.1:50053` |

En la topología de producción de un solo servicio, los procesos gRPC se ejecutan en el mismo contenedor y se comunican por loopback. Para distribuirlos en máquinas o servicios distintos se deben configurar direcciones y certificados TLS válidos.

## 6.2. Redis Pub/Sub

El servicio central de eventos publica un aviso en un canal asociado al usuario, por ejemplo `negotiation:user:{id}`.

Redis transporta el aviso, mientras que el repositorio consulta los eventos persistidos y los entrega por secuencia. Así, Redis no es la fuente de verdad del historial.

## 6.3. Outbox transaccional

El backend registra el evento junto con la operación de negocio. Un dispatcher consulta los eventos pendientes, solicita su publicación al servicio gRPC central y marca el evento como entregado después de recibir confirmación.

Si un proceso falla después de publicar y antes de confirmar, puede volver a publicar el aviso. El diseño mantiene el evento persistido y utiliza identificadores y secuencias para controlar duplicados en el flujo.

## 6.4. WebSockets

El navegador no consume gRPC directamente. El frontend abre una conexión WebSocket con el backend y el puente WebSocket utiliza el servicio gRPC de eventos.

Dirección local:

```text
ws://127.0.0.1:8000/ws/events
```

Dirección de producción:

```text
wss://generador-gemelos-back-production.up.railway.app/ws/events
```

El primer mensaje de la conexión contiene el token y los parámetros de suscripción:

```json
{
  "token": "<JWT obtenido en el login>",
  "negotiation_id": 1,
  "after_sequence": 0
}
```

`negotiation_id: 0` permite suscribirse a todas las negociaciones propias. El cliente debe conservar la última secuencia confirmada y reconectar desde ese cursor cuando sea necesario. El token no se incluye en la URL.

Tipos de eventos documentados:

- `negotiation.started`
- `message.created`
- `twin.responded`
- `negotiation.completed`
- `negotiation.cancelled`
- `analysis.completed`
- `recommendation.created`
- `profile.updated`
- `twin.failed`

           
