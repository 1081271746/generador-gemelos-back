# Motor de IA local (actualización)

La inferencia predeterminada usa un **modelo abierto autohospedado mediante
llama.cpp**, no Gemini. Se mantienen los servicios gRPC y todos los contratos
existentes. Gemini queda disponible solo como reversión explícita.

- [Arquitectura, modelo, licencia e inferencia local](docs/local-ai.md).
- [Dataset, entrenamiento LoRA/QLoRA, evaluación y exportación](docs/training.md).
- [Resultados reales y límites de lo verificado](docs/local-ai-validation.md).
- [Plan técnico de continuación y modelos candidatos](docs/implementation-plan.md).
- [Diagnóstico medido del timeout y avances por etapa](docs/performance-diagnosis.md).
- [Diagnóstico de la GPU local en Windows sin instalaciones](docs/windows-hardware-diagnostic.md).

**Estado:** integración y pipeline implementados; inferencia del modelo base
probada en CPU; **sin adaptador especializado entrenado**. Los 20 ejemplos
sintéticos son demostrativos, no un corpus suficiente para una IA experta.
Las secciones históricas sobre Gemini que siguen describen el proveedor previo.
Para la ruta nueva siguen vigentes FastAPI, Redis, gRPC, autenticación y
persistencia; sustituye la configuración de proveedor como indica la guía local.

# Generador de Gemelos de Negociación — Backend

Backend universitario desarrollado sobre los archivos originales de `1081271746/generador-gemelos-back`. No incluye frontend. La API conserva los prefijos `/auth`, `/scenarios`, `/negotiations` y `/messages` y los amplía.

Se utiliza **Gemini**, no OpenAI. Las menciones a OpenAI y al repositorio `Copiloto-Duelo-Back` del documento original se consideran referencias desactualizadas frente a las instrucciones actuales.

## Requisitos

- Python 3.13, probado en este entorno.
- Redis Server, probado con Redis 7.2.10.
- Cuatro procesos Python: FastAPI, gemelo gRPC, análisis gRPC y eventos gRPC.
- Una clave de Google Gemini para generar respuestas y análisis reales. El modelo y las cuotas dependen de la cuenta; no se garantiza acceso gratuito por ser estudiante.

## Instalación local

Ejecutar desde la raíz de este repositorio:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python scripts/configure_local.py
python -m alembic upgrade head
```

En Windows, activar el entorno con `.venv\Scripts\activate`. Instalar Redis en un entorno compatible, por ejemplo WSL.

`configure_local.py` crea `.env` con dos secretos aleatorios independientes, sin mostrarlos y sin sobrescribir una configuración existente. `.env` está excluido de Git. Configurar `GEMINI_API_KEY` en el gestor de secretos o en el archivo local; nunca subirlo al repositorio. No pegar claves en chats ni capturas.

Arrancar Redis en una terminal:

```bash
redis-server --bind 127.0.0.1 --port 6379
```

En otras cuatro terminales, con el entorno activado y el directorio del repositorio:

```bash
python -m app.rpc.ai_server twin
```

```bash
python -m app.rpc.ai_server analysis
```

```bash
python -m app.rpc.event_server
```

```bash
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

API: `http://127.0.0.1:8000`. Swagger: `/docs`. Contrato OpenAPI: `/openapi.json`. `/health` comprueba la base de datos e indica si se configuró Gemini; **no certifica** disponibilidad de Google, Redis ni de los servicios gRPC.

Los procesos leen `.env` al iniciarse; reiniciarlos tras cambiar configuración.

## Variables de entorno

| Variable | Uso |
| --- | --- |
| `DATABASE_URL` | SQLite local por defecto: `sqlite:///./negotiation.db` |
| `SECRET_KEY` | Firma JWT de usuarios; al menos 32 caracteres |
| `SERVICE_SECRET` | Firma JWT entre servicios; distinto del anterior |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Duración de tokens; por defecto 30 minutos |
| `GEMINI_API_KEY` | Credencial de Google, nunca incluida en Git |
| `GEMINI_MODEL` | Modelo configurable; valor inicial `gemini-2.5-flash` |
| `GEMINI_TIMEOUT_SECONDS` | Tiempo máximo HTTP; por defecto 30 segundos |
| `GEMINI_REQUESTS_PER_MINUTE` | Límite preventivo compartido en Redis; por defecto 10 |
| `REDIS_URL` | Redis de eventos y control de uso de Gemini |
| `TWIN_GRPC_TARGET` | Servicio del gemelo, por defecto `127.0.0.1:50051` |
| `ANALYSIS_GRPC_TARGET` | Servicio de análisis, por defecto `127.0.0.1:50052` |
| `EVENT_GRPC_TARGET` | Servicio central de eventos, por defecto `127.0.0.1:50053` |
| `GRPC_TIMEOUT_SECONDS` | Límite de llamadas de IA; por defecto 40 segundos |
| `GRPC_TLS_CA` | Ruta al certificado CA para clientes gRPC |
| `GRPC_TLS_CERT` / `GRPC_TLS_KEY` | Certificado y clave privada del servidor |
| `CORS_ORIGINS` | Orígenes separados por comas; incluye `http://localhost:4200` |
| `SEED_PASSWORD` | Contraseña temporal del usuario ficticio al cargar ejemplos |

Los servicios no admiten conexiones gRPC sin TLS fuera de loopback. Para equipos distintos, usar DNS y certificados válidos, objetivos separados de las direcciones de escucha mediante configuración de despliegue o balanceador y revisar las reglas de red. Esta entrega está verificada en una sola máquina con procesos independientes.

## Datos ficticios y cuentas anteriores

Definir `SEED_PASSWORD` mediante un mecanismo local seguro, con un mínimo de 12 caracteres, y ejecutar:

```bash
python -m seed.load
```

Se crea `demo@example.com`, dos escenarios y una negociación de ejemplo. Es repetible y no modifica un usuario existente. No incluye resultados de IA inventados. Se puede analizar el historial ficticio con Gemini una vez configurado. Los ejercicios curados están disponibles en `/resources/exercises`, claramente separados de las recomendaciones de IA.

El código original utilizaba bcrypt. No es posible convertir un hash bcrypt a Argon2 sin conocer la contraseña. Esta implementación no conserva bcrypt como mecanismo de autenticación. Para cuentas locales anteriores, después de migrar la base:

```bash
python -m scripts.reset_password correo-del-usuario
```

El administrador introduce la nueva contraseña dos veces en un prompt oculto. El script requiere acceso a la base de datos, guarda solo Argon2 y revoca las sesiones previas. No es un endpoint público de recuperación.

## Arquitectura

```text
Cliente HTTP / futuro Angular
          |
       FastAPI -------- WebSocket /ws/events
          |                       |
    servicios de negocio          |
          |                       |
    repositorios SQLAlchemy       |
          |                       |
       SQLite                cliente gRPC
          |                       |
    eventos persistentes     servicio central de eventos
          |                       |
    dispatcher de outbox ------ Redis Pub/Sub

FastAPI -- gRPC autenticado --> servicio del gemelo -- HTTPS --> Gemini
FastAPI -- gRPC autenticado --> servicio de análisis -- HTTPS --> Gemini
```

- **Repository Pattern**: autorización y consultas de escenarios, negociaciones, mensajes y eventos.
- **Service Layer**: reglas, transacciones, estados, turnos, análisis y perfiles.
- **Dependency Injection**: sesiones, usuario autenticado, clientes y fábrica de aplicación sustituibles en pruebas.
- **Factory**: `create_app`, `make_engine` y construcción de canales.
- **Publish/Subscribe y Fan-Out**: un servicio central con Redis distribuye avisos a varios suscriptores.
- **Outbox transaccional**: los eventos se guardan con la operación de negocio y se publican con reintentos.
- No se añadió Strategy Pattern artificialmente: existe un proveedor Gemini concreto y esquemas de resultados separados.

Los servicios de IA no acceden a la base de datos ni ejecutan instrucciones arbitrarias. Solo reciben contexto y devuelven JSON validado. El servicio de eventos tiene acceso limitado mediante su repositorio a la autenticación, propiedad e historial de eventos. La API es responsable de persistir los datos de negocio.

### Organización

```text
app/core/           configuración, JWT, dependencias y errores
app/database/       motor, sesiones y base declarativa
app/models/         modelos originales ampliados y relaciones ORM
app/schemas/        contratos de entrada, salida y análisis
app/repositories/   acceso y aislamiento de datos
app/services/       lógica de negocio y outbox
app/ai/             cliente Gemini, cuotas y prompts
app/rpc/            contratos Protobuf, clientes y servidores
app/routers/        API HTTP
app/websocket/      puente WebSocket a gRPC Streaming
migrations/        versiones Alembic
seed/              ejemplos ficticios
scripts/           generación Protobuf y herramientas locales
tests/             pruebas unitarias y de integración real
```

## Funcionalidades y reglas

- Registro, login, perfil, edición y cambio de contraseña. JWT con emisor, audiencia, vencimiento y versión de sesión. Logout y cambio de contraseña revocan **todas** las sesiones del usuario.
- Escenarios privados: contexto, objetivos, rol, intereses y límites de la contraparte. Eliminación lógica para conservar historial.
- Cada negociación conserva una copia del escenario al iniciarse. Editar el escenario no altera conversaciones anteriores.
- Estados: `active`, `completed`, `cancelled`. Cerrar exige un resultado explícito y no se permite mientras hay un turno en proceso.
- Mensajes sin endpoints de edición ni borrado; ofertas, contraofertas, argumentos y concesiones.
- `request_id` UUID hace idempotente un turno. Para reintentar tras un 503, reutilizar **el mismo UUID y contenido**. Si se omite, el servidor lo genera; para reintentos fiables debe enviarlo el cliente.
- El mensaje del usuario queda persistido aunque falle la IA. No se genera una respuesta de sustitución presentada como Gemini.
- Bloqueo temporal por negociación impide turnos simultáneos y permite recuperar operaciones interrumpidas. Un reintento antiguo incompleto no se acepta después de mensajes posteriores.
- Análisis de negociaciones cerradas, una versión persistida por negociación. Las cinco dimensiones tienen puntajes de 0 a 100, explicación y citas exactas de mensajes del usuario.
- Evidencia inventada, estructuras inválidas o respuestas bloqueadas no se almacenan como análisis válidos.
- Perfil progresivo: medias de indicadores contextuales, estrategias, fortalezas, oportunidades, recomendaciones, ejercicios e historial de evolución. Nunca diagnóstico ni etiqueta definitiva de personalidad.
- El contexto completo viaja a Gemini, incluyendo perfil e historial. Si supera el límite preventivo de 200.000 caracteres se devuelve un error controlado en lugar de truncarlo silenciosamente.

## Endpoints

Salvo registro, login, raíz, documentación y salud, se requiere `Authorization: Bearer <token>`. Las rutas con barra final se conservan del proyecto original.

| Método | Ruta | Operación |
| --- | --- | --- |
| POST | `/auth/register` | Crear usuario |
| POST | `/auth/login` | Obtener JWT con correo y contraseña |
| GET / PUT | `/auth/me` | Consultar o actualizar perfil |
| POST | `/auth/password` | Cambiar contraseña y revocar sesiones |
| POST | `/auth/logout` | Revocar todas las sesiones |
| POST / GET | `/scenarios/` | Crear o listar escenarios |
| GET / PUT / DELETE | `/scenarios/{id}` | Consultar, editar o archivar |
| POST / GET | `/negotiations/` | Iniciar o listar negociaciones |
| GET / PATCH | `/negotiations/{id}` | Consultar o cerrar con estado y resultado |
| POST | `/messages/` | Enviar mensaje y obtener turno usuario/gemelo |
| GET | `/messages/{negotiation_id}` | Historial íntegro paginado |
| POST | `/negotiations/{id}/analysis` | Generar o recuperar análisis |
| GET | `/analyses` | Historial de análisis paginado |
| GET | `/analyses/{id}` | Consultar análisis propio |
| GET | `/profile` | Perfil y evolución |
| GET | `/recommendations` | Recomendaciones y ejercicios personalizados |
| GET | `/resources/exercises` | Ejercicios curados sin IA |
| GET | `/events` | Historial con cursor `after` y filtro `negotiation_id` |
| WS | `/ws/events` | Eventos privados en tiempo real |
| GET | `/health` | Estado de la base y configuración de IA |

Listados generales: `offset` y `limit`, con límites máximos validados. Mensajes se ordenan por ID y eventos por secuencia, evitando ambigüedad por marcas temporales iguales.

Ejemplo del cuerpo de un mensaje:

```json
{
  "negotiation_id": 1,
  "request_id": "346d82d8-fc8a-4c8b-afbe-8f0b5aa63e92",
  "content": "Propongo aumentar el volumen a cambio de un descuento.",
  "kind": "offer"
}
```

Consultar en `/docs` los cuerpos completos de escenarios y las respuestas Pydantic. Errores: 401 autenticación, 404 recurso inexistente o ajeno, 409 estado/conflicto/idempotencia, 422 validación, 503 IA temporalmente no disponible.

## gRPC y eventos

Contrato: `app/rpc/negotiation.proto`. Para regenerar clientes y servidores:

```bash
python scripts/generate_proto.py
```

Los archivos generados se incluyen en Git; los comentarios de esos archivos son producidos por el compilador, no código manual.

| Servicio | Método | Comportamiento |
| --- | --- | --- |
| `TwinNegotiationService` | `GenerateReply` | Rol, límites, objetivos, perfil e historial completo |
| `NegotiationAnalysisService` | `AnalyzeNegotiation` | Análisis estructurado con cinco dimensiones |
| `NegotiationEventService` | `PublishEvent` | Publica un evento ya persistido mediante su UUID |
| `NegotiationEventService` | `SubscribeEvents` | Server Streaming privado con cursor de reanudación |

Publicaciones y operaciones IA exigen JWT de servicio de corta duración, con alcance y usuario. Las suscripciones exigen JWT normal y verifican actividad, versión de sesión y propiedad de negociación. La identidad no procede de un `user_id` libre del frontend. Los canales gRPC se reutilizan y cierran al apagar cada proceso.

El servicio central publica avisos en `negotiation:user:{id}`. Los suscriptores consultan los eventos persistidos en orden, no confían en cargas arbitrarias recibidas por Redis. Un mismo evento llega a varias conexiones autorizadas. La secuencia elimina duplicados por publicación repetida y facilita reanudación.

El dispatcher marca el evento como entregado solo después de recibir confirmación. Una caída entre publicación y confirmación puede provocar otro aviso de Redis, pero no otra fila de evento ni una entrega duplicada dentro de un flujo. El cliente debe guardar su última secuencia y también deduplicar al reconectar.

Si Redis se desconecta, el streaming devuelve un estado controlado y el puente WebSocket intenta reconectar tres veces. Los eventos siguen guardados en SQLite. Hay consulta periódica para recuperar avisos perdidos y reproducción desde un cursor después de reinicios. Las suscripciones activas no sustituyen la persistencia.

### WebSocket desde Angular

Abrir `ws://127.0.0.1:8000/ws/events` y enviar como **primer mensaje**, en menos de diez segundos:

```json
{
  "token": "<JWT obtenido en login>",
  "negotiation_id": 1,
  "after_sequence": 0
}
```

`negotiation_id: 0` suscribe a todas las negociaciones propias. El token no se pone en la URL. El servidor verifica el origen cuando está presente. Guardar `sequence` de cada evento; reconectar desde el último valor para recuperar pendientes. En producción usar HTTPS/WSS y no registrar cuerpos de autenticación.

Tipos de eventos: `negotiation.started`, `message.created`, `twin.responded`, `negotiation.completed`, `negotiation.cancelled`, `analysis.completed`, `recommendation.created`, `profile.updated`, `twin.failed`.

## Pruebas y alcance verificado

Con Redis Server disponible como ejecutable:

```bash
python -m pytest -q
git diff --check
```

Las pruebas arrancan Redis temporal en puertos locales y bases SQLite aisladas. No usan claves reales ni consumen cuota de Gemini. Incluyen:

- Registro, login, JWT, revocación, contraseñas y protección de endpoints.
- Escenarios, estados, propiedad e historial inmutable.
- Idempotencia, concurrencia por negociación y conservación de mensajes ante fallos.
- Validación de análisis, citas exactas, perfiles, ejercicios y recomendaciones.
- Gemini con HTTP controlado: respuestas válidas, inválidas, cuotas, errores y timeout.
- Canales gRPC reales para gemelo, análisis y eventos; solo el proveedor de IA está sustituido.
- Redis real, Fan-Out, aislamiento, duplicados, reconexión y reinicio del servicio de eventos.
- Dos aplicaciones FastAPI reales compartiendo el servicio central gRPC/Redis, con eventos recibidos por WebSocket.
- Cuotas compartidas entre clientes independientes.
- Migraciones, conservación de registros anteriores y herramientas de configuración.

No se afirma que Gemini haya sido probado contra una cuenta real. El uso real requiere clave, acceso al modelo y cuota. PostgreSQL y TLS remoto no se han certificado mediante despliegues reales.

## Migraciones y futura base PostgreSQL

Base nueva: `python -m alembic upgrade head`.

Una base que ya contiene exactamente las cuatro tablas del proyecto original debe respaldarse y revisarse antes de marcar la versión existente:

```bash
python -m alembic stamp 0001
python -m alembic upgrade head
```

No ejecutar `stamp` sobre un esquema diferente: no realiza cambios ni verifica equivalencia. La migración 0002 añade campos y tablas y copia el escenario de negociaciones anteriores sin borrar sus mensajes. La API no ejecuta `create_all` ni migra automáticamente al arrancar.

Para PostgreSQL, instalar un controlador compatible, configurar `DATABASE_URL` con el dialecto correspondiente, crear una base propia y ejecutar Alembic. Los modelos utilizan SQLAlchemy, claves foráneas y JSON portable; no hay SQL específico de SQLite en la lógica de negocio. Las opciones de SQLite solo están en la fábrica de motor.

Cambiar `DATABASE_URL` **no copia los datos**. Trasladar registros y claves, ajustar secuencias y verificar integridad en un proceso de migración con respaldo. No se incluye ni se afirma haber probado ese traslado.

Todas las instancias locales de FastAPI y el servicio de eventos deben apuntar al mismo archivo SQLite usando ruta absoluta si se inician desde directorios distintos. SQLite es apropiado para esta primera etapa, no para réplicas en máquinas diferentes. Para ese caso usar una base PostgreSQL compartida y validar la migración.

## Seguridad y límites conocidos

- Contraseñas nuevas con Argon2id; JWT de usuario y de servicio con claves distintas.
- No se almacenan claves de Gemini, tokens ni contraseñas en tablas o eventos.
- El historial es inmutable por API; un administrador con acceso directo a la base puede modificarlo. No se promete un registro criptográficamente inalterable.
- La IA no garantiza veracidad de las conclusiones: se validan estructura, rangos y citas, y se mantienen indicadores contextuales.
- Mantener Redis en red privada. Para producción añadir políticas de respaldo, rotación de claves, límites por IP y usuario en el acceso público, observabilidad sin información sensible y pruebas de carga.
- Una instancia central de eventos es la topología verificada. No se presenta gRPC como replicación de datos ni se promete entrega exactamente una vez.
- Gemini puede rechazar un modelo, agotar cuota o no estar disponible; las operaciones de cuenta, escenarios, historial y recursos continúan funcionando.
- Este proyecto no implementa frontend, despliegue productivo, recuperación de contraseña por correo ni migración automática de datos a PostgreSQL.

## Git y entrega

Trabajo realizado en una rama separada, sin reemplazar `main`. Se verificó la identidad existente en los commits del propietario antes de configurar la copia local. Los commits están escritos en español y separados por módulos y verificaciones.

Consultar los cambios:

```bash
git log --reverse --oneline main..feature/backend-completo
git diff --stat main...feature/backend-completo
```

El pull request permite revisar y decidir la integración. No se fusiona ni se despliega automáticamente. El frontend debe permanecer pendiente hasta recibir su repositorio e instrucciones.
