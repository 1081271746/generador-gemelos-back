# Migración del proveedor a Groq

## Arquitectura inspeccionada y alcance

FastAPI llama a `ServiceClients`, que conserva gRPC y Protocol Buffers.
Los servicios gRPC construyen el proveedor mediante `model_manager`.
`TwinEngine` y `AnalysisEngine` mantienen los prompts y validaciones de
límites, contexto y citas. El proveedor devuelve el mismo modelo Pydantic.
Los servicios de negocio siguen siendo responsables de las transacciones,
idempotencia, recuperación de turnos fallidos y almacenamiento del análisis.

Se sustituyó el transporte Gemini por `GroqService` en `app/ai/groq.py`,
basado en el SDK oficial `groq==1.7.0`, `AsyncGroq` y HTTP asíncrono.
Groq es el valor predeterminado. Se conserva `local` como opción explícita,
sin fallback. `AI_PROVIDER=gemini` produce un error claro de configuración.
No hay SDK de Google que retirar de requirements: Gemini usaba `httpx`
directamente. `httpx` se conserva porque otros módulos y el SDK lo usan.

No se modificaron modelos SQLAlchemy, tablas, migraciones, autenticación,
Redis como infraestructura, gRPC, WebSockets, rutas de negocio ni Angular.
No se ejecutan seeds, migraciones o limpiezas como parte de esta migración.
No se descargan modelos/datasets ni se inicia entrenamiento.

## Configuración de una instalación existente

No reemplazar el `.env` existente ni ejecutar `configure_local.py`.
Añadir/ajustar **solo** estas variables en el gestor de secretos o configuración
local. Nunca compartir la clave por chat ni subirla al repositorio:

```dotenv
AI_PROVIDER=groq
GROQ_API_KEY=<tu-clave-local-no-versionada>
GROQ_MODEL=openai/gpt-oss-20b
GROQ_TIMEOUT_SECONDS=30
GROQ_REQUESTS_PER_MINUTE=10
```

Mantener `DATABASE_URL`, `REDIS_URL`, `SECRET_KEY`, `SERVICE_SECRET` y demás
configuración existentes. Las variables `GEMINI_*` dejan de leerse; se pueden
retirar manualmente cuando se haya verificado la migración en la cuenta real.
Si ya existe `AI_PROVIDER=local`, cambiarlo explícitamente a `groq` en los
procesos de API, gemelo y análisis; no se sobrescribe automáticamente el entorno.
No enviar claves al navegador. El contexto, perfil e historial se procesan
en Groq: revisar las autorizaciones de privacidad correspondientes.

Mantener el timeout gRPC por encima del de Groq (valores por defecto 40 y
30 segundos). El límite por minuto es preventivo, compartido por los procesos
que usan el mismo modelo y Redis; no sustituye los límites reales de la cuenta,
que también pueden incluir tokens diarios o por minuto.

## Modelo y formato

La documentación oficial consultada el 16 de noviembre de 2026 publica
`openai/gpt-oss-20b` como modelo de producción con Structured Outputs:

- https://console.groq.com/docs/models
- https://console.groq.com/docs/structured-outputs
- https://github.com/groq/groq-python

El cliente envía `json_schema` con `strict=false`, conservando los esquemas
Pydantic existentes, incluidos sus campos opcionales, sin transformarlos ni
debilitar la validación local. Siempre valida la respuesta completa, después
se aplican los guards de negociación y la comprobación de evidencias.
Se rechazan respuestas vacías, truncadas, bloqueadas, mal formadas o inválidas.
El presupuesto máximo de salida es 8192 tokens, incluido el razonamiento del
modelo; una respuesta que agota ese presupuesto no se almacena como válida.
No se reintenta con otro modelo/proveedor ni se habilitan herramientas.

Publicación en el catálogo no garantiza acceso o cuota en una cuenta concreta.
Para consultar los modelos accesibles sin generar respuestas (clave local
configurada; no imprime la clave):

```powershell
python -c "from groq import Groq; from app.core.config import settings; c=Groq(api_key=settings.GROQ_API_KEY, timeout=settings.GROQ_TIMEOUT_SECONDS, max_retries=0); print([m.id for m in c.models.list().data]); c.close()"
```

Este comando realiza solo una consulta del catálogo; no demuestra la calidad
del gemelo o del análisis. No se ha ejecutado contra una cuenta real durante
las pruebas con mocks.

## Instalación y arranque local

Desde el repositorio backend, activar su entorno habitual (no el entorno
independiente de entrenamiento) e instalar:

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m pip check
```

No crear otro `.env` ni ejecutar Alembic para cambiar de proveedor.
Con PostgreSQL/Redis y los servicios existentes configurados, reiniciar en
sus terminales habituales:

```powershell
python -m app.rpc.ai_server twin
python -m app.rpc.ai_server analysis
python -m app.rpc.event_server
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Cada línea representa un proceso independiente. Los comandos y los contratos
gRPC no cambiaron; el servicio de eventos no depende del proveedor de IA.
En Linux, activar el entorno con `source .venv/bin/activate`.

## Salud y errores

`GET /health` conserva `database`, `ai_provider`, `ai_readiness` y el campo
obsoleto `gemini_configured`, siempre `false`. Añade `groq_configured`.
`groq_configured=true` solo indica clave no vacía, no credencial válida.
`ai_readiness=not_probed` evita afirmar conexión real, cuota o calidad.
El endpoint no envía negociaciones ni realiza peticiones al proveedor.

Una clave ausente no impide arrancar los procesos, pero la generación devuelve
indisponibilidad real. Clave inválida/permisos, timeout, 429, errores de conexión,
errores HTTP, fallo de Redis y respuesta inválida se convierten en errores
controlados sin exponer cuerpos del proveedor o credenciales. El SDK usa
`max_retries=0`; el plazo total incluye la reserva de cuota en Redis.

Ante fallo se conserva el mensaje del usuario, se libera el turno y no se
inventa una respuesta. Reintentar con el mismo `request_id` y contenido.
Un análisis no validado no se guarda. La cuota usa un nuevo prefijo `groq:quota:`
sin borrar ni modificar las claves de eventos o la configuración de Redis.

## Pruebas y límites de la evidencia

`tests/test_groq.py` utiliza el SDK real sobre `httpx.MockTransport`, sin
conexión con Groq. Comprueba configuración, prompts/contexto, esquema,
errores, cancelación, cuota y conservación de datos en SQLite temporal.
Las pruebas existentes cubren los contratos gRPC, eventos, WebSockets,
autenticación e idempotencia; las pruebas de procesos verifican arranque
con Groq sin clave y errores 503 sin respuestas inventadas.

Ejecutar las pruebas solo sobre bases temporales, nunca sobre la base real.
Las pruebas de migraciones que hacen downgrade se excluyen de la comprobación
de este cambio; no son necesarias para sustituir el proveedor.

Pendiente con credencial real: catálogo accesible a la cuenta, turno completo,
análisis con citas, cuota y latencias reales. Aprobar mocks no valida eso.

### Resultado de esta implementación

- **167 pruebas aprobadas**, sin fallos, en la suite backend excluyendo
  `tests/test_migrations.py` (no se ejecutaron downgrades).
- Dentro de ellas, **40 casos** específicos de Groq, con el SDK oficial real
  y transporte HTTP simulado.
- El test de cuatro procesos aplicó el esquema únicamente en su SQLite
  temporal para verificar el arranque; ninguna migración se aplicó a las
  bases existentes del proyecto.
- Un aviso de deprecación de Starlette sobre su uso de `httpx` en TestClient;
  no se cambiaron dependencias del framework ajenas a esta migración.
- Conexión, clave y generación reales en Groq: **pendientes**, no simuladas
  como éxito. El frontend de referencia no cambió ni se redirigió a este backend.

### Archivos

Creados:

- `app/ai/groq.py`
- `tests/test_groq.py`
- `docs/groq-migration.md`

Modificados:

- `app/ai/model_manager.py`
- `app/core/config.py`
- `app/main.py`
- `requirements.txt`
- `.env.example`
- `README.md`
- `docs/local-ai.md`
- `tests/test_grpc_events.py`
- `tests/test_local_inference.py`
- `tests/test_local_tools.py`
- `tests/test_process_startup.py`

Retirados después de sustituir su cobertura:

- `app/ai/gemini.py`
- `tests/test_gemini.py`

Las únicas referencias activas restantes al nombre anterior son el campo
obsoleto de salud y la prueba que rechaza explícitamente `AI_PROVIDER=gemini`.
Las referencias históricas de documentos de entrenamiento se conservan como
registro de trabajos anteriores, no como configuración vigente.
