# Plan técnico de especialización verificable

## Estado de partida

El modelo Qwen2.5-1.5B Q4_K_M no está aprobado: hubo aceptación fuera del
límite, revelación de un mínimo y timeout de análisis a 300 s. Esos resultados
no equivalen a un entrenamiento ni a un modelo especializado. El registro
antiguo no separa generación, compilación de gramática, cola y validación:
la causa precisa del timeout todavía debe medirse.

No se reescribe el backend. Se mantienen FastAPI, SQLAlchemy, Pydantic, gRPC,
Protocol Buffers, autenticación, eventos y contratos de negociaciones/mensajes.
Los guards pueden rechazar salidas, pero no generan respuestas y **no son
evidencia de IA entrenada**.

## Decisión de arquitectura

```text
FastAPI / servicios existentes
    -> cliente gRPC autenticado
    -> Twin Engine / Analysis Engine
    -> proveedor Python asíncrono, acotado y observable
    -> llama.cpp autohospedado (proceso/host separado)
    -> validación Pydantic completa + citas exactas antes de persistir

Corpus autorizado y revisado (offline)
    -> normalización/deduplicación/splits por familia
    -> SFT con LoRA/QLoRA
    -> smoke + checkpoints + validación + comparación ciega
    -> exportación y candidato versionado, NO promoción automática
```

No se conecta el modelo a SQL ni se entrena globalmente con conversaciones de
usuarios. El contexto de perfil sigue filtrado por propietario en el servicio
existente. No se añaden dependencias de Gemini/OpenAI a la ruta local.

## Modelos comparados documentalmente

Son candidatos, no un ranking medido de negociación.

| Modelo | Idiomas y seguimiento | Licencia | Inferencia estimada | Especialización |
|---|---|---|---|---|
| Qwen2.5-1.5B-Instruct | Español documentado; falló casos reales de este proyecto | Apache-2.0 | Q4 ~1.1 GB de pesos; CPU viable pero calidad insuficiente observada | PEFT; se conserva como baseline diagnóstico |
| Qwen3-1.7B | Familia con 100+ idiomas y diálogo multiturno; probar español de dominio | Apache-2.0 | Q4 ~1–1.5 GB de pesos, más KV/runtime; thinking debe desactivarse explícitamente | LoRA/QLoRA; alternativa pequeña por validar |
| Qwen3-4B-Instruct-2507 | 4B multilingüe, mejoras declaradas de instrucciones/razonamiento; solo non-thinking | Apache-2.0 | Q4 ~2.5–3 GB de pesos, más KV/runtime; preferir GPU | Candidato principal a evaluación; PEFT Qwen3 con Transformers >=4.51 |
| Gemma-3-4B-it | Alternativa multilingüe; no se ejecutó aquí | Gemma, términos específicos y acceso condicionado | 4B; cuantización posible, medir en host objetivo | Posible PEFT, pero no elegida por licencia/acceso y falta de comparación local |

No existe evidencia aquí de superioridad en negociación para Qwen3. Se elige
4B non-thinking como **hipótesis técnica** por capacidad/latencia potencial,
sin chain-of-thought adicional y licencia permisiva. La selección final depende
de benchmark español, límites, continuidad, citas, latencia y memoria.

Fuentes primarias consultadas:
- https://huggingface.co/Qwen/Qwen3-4B-Instruct-2507
- https://huggingface.co/Qwen/Qwen3-1.7B
- https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct
- https://huggingface.co/google/gemma-3-4b-it (acceso a pesos/ficha raw restringido)
- https://github.com/ggml-org/llama.cpp/tree/master/tools/server

Las cifras de RAM/VRAM son **estimaciones de planificación**, no benchmarks:
para QLoRA 4B empezar con GPU CUDA de 16–24 GiB VRAM, RAM 32 GiB y disco
libre 50 GiB; para inferencia Q4, GPU 8–12 GiB, RAM 16 GiB y contexto inicial
8192, midiendo el pico real. Para LoRA sin cuantizar reservar más VRAM. El
contexto nativo de 256K de un modelo no implica que deba reservarse aquí.

Este host no tiene GPU NVIDIA detectada y cuenta con 4 CPU / 8 GiB RAM. No se
descargarán pesos 4B ni se iniciará entrenamiento completo en estas condiciones.
Una inferencia pequeña en CPU sirve como diagnóstico, no como garantía de SLA.

## Etapas y criterios de salida

1. **Diagnóstico reproducible.** Comparar contexto/semilla idénticos con
   schema completo, estructural y sin schema. Registrar tiempo a primer token,
   tokens/s, finish reason, deadline y memoria sin registrar conversaciones.
   Un límite pequeño de tokens en este diagnóstico no modifica producción ni
   acredita calidad. Preservar el resultado anterior de 300 s.
2. **Inferencia observable y validación íntegra.** Errores diferenciados,
   métricas sin texto sensible y gramática de transporte optimizada solo si
   el diagnóstico la justifica. Mantener todos los campos/dimensiones/citas y
   los límites Pydantic finales; no aceptar salidas truncadas ni llenar campos.
3. **Datos y entrenamiento profesional.** Auditoría humana verificable,
   licencia/autorización, revisión de escalas, conversaciones multivuelta,
   separación por familia y manifiestos reproducibles. Smoke de 1–5 pasos
   en host compatible antes de SFT. No marcar revisión humana inexistente.
4. **Especialización y evaluación.** Dataset/configuración/hardware/logs/
   checkpoints/adapter reales. Comparar base vs adapter sobre casos ciegos,
   con límites, concesiones, objeciones, continuidad, análisis y evidencias.
   No sustituir la evaluación de especialistas por un score de schema.
5. **Integración y promoción controlada.** Tests de regresión gRPC/persistencia,
   concurrencia y cancelación; verificar p95/memoria y calidad en host objetivo.
   Ningún despliegue, cambio del frontend o gasto de GPU sin autorización.

La API ya es asíncrona y la inferencia ya está separada. Añadir `async` no acelera
el muestreo. Una cola de trabajos persistente para análisis largos es una
posibilidad posterior si el SLA medido lo exige; no se introduce cambiando
silenciosamente el contrato síncrono actual.

Cada etapa debe reportar por separado: código implementado, pruebas de contrato,
pruebas de modelo real, calidad aprobada/rechazada y entrenamiento ejecutado.
