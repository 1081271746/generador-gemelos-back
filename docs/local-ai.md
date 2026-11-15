# Motor de negociación autohospedado

## Qué se implementó y qué no

La ruta predeterminada ahora es `AI_PROVIDER=local`. FastAPI conserva sus rutas,
schemas y persistencia; los dos servicios gRPC conservan el `.proto` y delegan
en `TwinEngine` y `AnalysisEngine`, mediante una interfaz de inferencia Python.
El motor llama a un servidor **llama.cpp propio** por HTTP con salida JSON Schema.
No usa una API comercial ni necesita una clave de Gemini por respuesta.

**No se entrenó todavía un adaptador especializado.** El modelo base abierto
puede cargarse y generar de verdad, pero no es un experto en negociación.
El corpus de 20 ejemplos es una demostración sintética pendiente de revisión.
Las pruebas de contratos no demuestran calidad semántica ni de entrenamiento.

## Modelo y licencia

Seleccionado: **Qwen/Qwen2.5-1.5B-Instruct**, 1.54B parámetros, Apache-2.0.
Su ficha declara español entre más de 29 idiomas, seguimiento de instrucciones,
role-play y salidas JSON. No se entrenan pesos aleatorios: se especializan pesos
preentrenados mediante LoRA/QLoRA cuando existe infraestructura y datos adecuados.

- Pesos HF: revisión `989aa7980e4cf806f80c7fef2b1adb7bc71aa306`.
- GGUF oficial: `Qwen/Qwen2.5-1.5B-Instruct-GGUF`, revisión
  `91cad51170dc346986eccefdc2dd33a9da36ead9`,
  archivo `qwen2.5-1.5b-instruct-q4_k_m.gguf`.
- [Ficha y licencia](https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct).
- [GGUF oficial](https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF).
- [Servidor llama.cpp y JSON Schema](https://github.com/ggml-org/llama.cpp/tree/master/tools/server).
- [PEFT LoRA](https://huggingface.co/docs/peft/developer_guides/lora).

La familia Llama pequeña es alternativa viable, pero se prefirió Qwen por
licencia permisiva y soporte multilingüe documentado. Modelos 7B+ requieren
mayor memoria; 0.5B reduce recursos a costa de capacidad. Estas son decisiones
de ingeniería, no una comparación de calidad medida entre familias.

## Recursos

Comprueba siempre la máquina de destino:

```sh
python -m training.hardware
```

El entorno observado tiene 4 CPU, límite de unos 8 GiB de RAM y ninguna GPU
NVIDIA detectada. Se ejecutó inferencia Q4_K_M en CPU. Como estimación orientativa,
reserva 2–4 GiB para el proceso de inferencia y su KV cache, más la aplicación.
Los pesos FP32 del modelo de 1.54B ya requieren unos 6 GiB antes de gradientes,
optimizador y activaciones: no se recomienda entrenamiento completo aquí.

Para QLoRA del 1.5B: planificar inicialmente GPU CUDA con 8–12 GiB VRAM y al
menos 16 GiB RAM, secuencias 2048 y microbatch 1; **es una estimación, no un
benchmark ejecutado**. Medir uso y reducir longitud antes de una corrida larga.
La inspección `nvidia-smi` es preliminar; PyTorch/CUDA deben funcionar también.

## Inferencia local

Instala llama.cpp en el host de inferencia; `llama-server` debe estar en PATH.
La validación de este trabajo usó el paquete llama-cpp 5311. No se inicia ni se
descarga un modelo al arrancar FastAPI.

1. Descarga el GGUF oficial de la revisión indicada a `models/` o almacenamiento
   externo. Conserva la licencia y un SHA-256 local del archivo.
2. Arranca:

```sh
python scripts/serve_local_model.py models/qwen2.5-1.5b-instruct-q4_k_m.gguf
python -m scripts.probe_local_ai
```

El launcher usa loopback, 8192 tokens de contexto, una ranura, tres hilos, CPU
por defecto, sin desplazamiento del contexto y sin logs de prompts. No actives
herramientas, MCP, SQL ni acceso al sistema de archivos del modelo.

3. Configura **los dos procesos de IA gRPC** y FastAPI con la misma selección:

```sh
export AI_PROVIDER=local
export AI_BASE_URL=http://127.0.0.1:8090/v1
export AI_MODEL=negotiation-local
export AI_TIMEOUT_SECONDS=300
export GRPC_TIMEOUT_SECONDS=320
python -m app.rpc.ai_server twin
# En otro proceso con el mismo entorno:
python -m app.rpc.ai_server analysis
```

Conserva los procesos de eventos, Redis y FastAPI documentados en el README.
Mantén también las variables de seguridad existentes; no desactives su validación.
Para GPU cambia `AI_GPU_LAYERS` del launcher según la capacidad disponible.
Los valores de timeout de 300/320 son para CPU lenta, no una promesa de latencia.

El endpoint remoto debe ser autohospedado, HTTPS y accesible solo por los
servicios autorizados (red privada o túnel). No publiques llama-server sin
autenticación/red restringida. El cliente no sigue redirecciones y no toma una
URL del usuario. La configuración rechaza credenciales incrustadas.

## Límites y seguridad

- Máximo de contexto en bytes, salida en bytes, tokens de salida, timeout total,
  concurrencia y espera de cola; fallos devuelven UNAVAILABLE/503, no texto falso.
- `AI_MAX_CONTEXT_BYTES` no representa tokens. Si la ventana real se excede,
  llama.cpp rechaza la solicitud; no se recorta silenciosamente el historial.
- Análisis: cinco dimensiones 0–100, citas exactas de mensajes del usuario y
  sus IDs. Se comprueban antes de devolver gRPC y otra vez antes de persistir.
- Gemelo: conserva escenario y límites en cada turno; el perfil ya filtrado por
  propietario se transmite solo como contexto, sin entrenar globalmente.
- Guard numérico conservador para límites explícitos de precio, salario,
  gasto y descuento. Rechaza cifras incompatibles y separadores ambiguos.
  También rechaza cifras que se etiqueten como el mínimo/máximo privado.
  Puede rechazar mensajes válidos que repitan una cifra rechazada o incluyan
  otras magnitudes. **No resuelve límites narrativos o contratos complejos**:
  estos requieren reglas estructuradas y evaluación humana adicional.
- Las instrucciones previenen revelación de límites e inyección de prompts,
  pero no constituyen una garantía formal contra todas las respuestas dañinas.
- Logs del cliente: solo duración y éxito. No se registran mensajes, perfiles,
  credenciales ni respuestas. Los informes offline pueden contener muestras:
  son privados/ignorados por Git y no se publican automáticamente.

`/health` mantiene `gemini_configured` por compatibilidad y añade `ai_provider`
y `ai_readiness=not_probed`. No afirma que el modelo esté cargado ni que genere
correctamente: usa el probe y la evaluación explícita para comprobarlo.

## Compatibilidad y reversión

No se cambiaron Protocol Buffers, endpoints, modelos SQLAlchemy ni migraciones.
No hay fallback automático. `AI_PROVIDER=gemini` permite volver explícitamente
al proveedor anterior si se configura; no es necesario para la ruta local.
El despliegue existente no se actualiza automáticamente con un push.

## Pesos y datos

No versionar `models/`, checkpoints, `.gguf`, `.safetensors`, `.bin` ni corpus
privados. Usar almacenamiento controlado, respaldos cifrados y manifiestos con
revisión base, hash de dataset, versión de librerías, configuración y evaluación.
Ver [entrenamiento](training.md) y [validación real](local-ai-validation.md).
