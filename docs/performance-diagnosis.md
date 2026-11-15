# Diagnóstico medido y etapas implementadas

## Alcance

Esta continuación entrega el plan técnico, diagnóstico de capacidad y mejoras
de observabilidad/preparación. **No entrega un modelo especializado entrenado**.
No se cambian frontend, Protocol Buffers, schemas públicos, persistencia ni
contratos de mensajes/negociaciones.

Se mantiene la separación API -> gRPC -> motores -> inferencia autohospedada.
No se incorporan reglas para generar respuestas supuestamente entrenadas.
Los guards existentes solo rechazan respuestas inválidas.

## Etapa 1: medición real del timeout

Hardware: Linux x86_64, 4 CPU, 8 GiB de límite de RAM, sin GPU NVIDIA.
llama.cpp 5311, Qwen2.5-1.5B-Instruct Q4_K_M oficial, un slot, tres hilos,
contexto 4096, sin desplazamiento del contexto. Modelo sin fine-tuning.

Primero se comparó el mismo caso sintético `comercial-analysis`, instrucciones,
semilla 42 y presupuesto de **64 tokens exclusivamente diagnóstico**:

| Gramática | Primer contenido | Total | Tokens/s de decodificación | Resultado |
|---|---:|---:|---:|---|
| Sin schema | 6.2204 s | 15.9977 s | 6.443 | length, incompleto |
| Estructural | 0.1692 s | 9.9325 s | 6.453 | length, incompleto |
| Completa | 0.1814 s | 10.0862 s | 6.361 | length, incompleto |

Las dos últimas aprovecharon contexto caliente: **no se puede atribuir la
diferencia respecto al primer caso a la gramática**. Entre completa y estructural
la diferencia es pequeña, sin evidencia de que expandir límites de schema
fuera el cuello de botella dominante. No se promueve la variante estructural
como una optimización demostrada.

Un primer intento durante carga devolvió 503; se descartó como medición de
inferencia y se añadió espera explícita de disponibilidad antes del diagnóstico.

Después se usó el caso exacto del fallo anterior, `precios-analysis`, conservando
su contexto completo, schema completo, semilla y **512 tokens diagnósticos**:

| Métrica | Resultado real |
|---|---:|
| Prompt | 381 tokens |
| Salida | 512 tokens |
| Primer contenido | 3.9135 s |
| Total | 91.2567 s |
| Decodificación aproximada | 5.85 tokens/s |
| Finalización | `length`: análisis incompleto |

Se observaron claves de las cinco dimensiones, pero no una respuesta completa
aprobada. La fracción de 4-gramas repetidos fue 0.384; repetir citas entre
dimensiones también la eleva: **no prueba por sí sola un bucle patológico**.

### Conclusión y límites del diagnóstico

La capacidad de CPU medida permite que un presupuesto de 2048 tokens supere
300 segundos. Con la muestra de precios, la extrapolación conservadora es
**353.83 segundos**, incluyendo el primer contenido observado. No es una nueva
medición de una respuesta de 2048 tokens, ni p95, ni SLA, ni demostración de la
causa única del registro antiguo (que no guardaba progreso ni uso de tokens).

Sí se identificó un desajuste de capacidad/presupuesto medido. No se encontró
evidencia de que la gramática fuera la causa dominante. El cambio de orden y la
muestra pequeña impiden conclusiones estadísticas más fuertes.

**No se bajó el presupuesto de producción ni se recortaron dimensiones, citas,
recomendaciones o historial para aparentar velocidad.** Los 64/512 tokens
solo sirven para medir capacidad; sus respuestas se marcan incompletas.

## Etapa 2: errores distinguibles y validación íntegra

Implementado y probado:

- Códigos internos diferentes para cola, timeout de generación, HTTP,
  transporte, límite de salida, protocolo, validación, memoria y cancelación.
- Métricas acotadas: tiempo, espera, status HTTP, finish reason normalizado,
  tokens reportados y modo de schema. Nunca texto de mensajes, perfil,
  credenciales, body de errores ni motivos arbitrarios enviados por el servidor.
- Los informes de evaluación conservan error y métricas por muestra, en vez de
  agrupar todo como un `ExternalServiceError` indistinguible.
- Al cancelar se libera el slot; la cancelación no se convierte en respuesta.
- Variante de gramática estructural para A/B mediante `AI_SCHEMA_MODE`, con
  **`full` aún por defecto**. Aunque se elija `structural`, se validan después
  todos los límites y campos con el schema Pydantic completo.
- La métrica `success` del proveedor solo significa validación de su salida,
  no calidad semántica, aprobación del guard o entrenamiento completado.

Reproducción:

```sh
python -m scripts.diagnose_inference --tokens 64 --deadline 60
python -m scripts.diagnose_inference --modes full --case-id precios-analysis \
  --tokens 512 --deadline 120 --output generated-artifacts/diagnostic-precios-512.json
python -m scripts.capacity_plan generated-artifacts/diagnostic-precios-512.json \
  --output-tokens 2048 --target-seconds 120
```

Los informes guardan cantidades y nombres de campos permitidos, no el texto
generado. La estimación no modifica configuración ni acepta respuestas parciales.

## Etapa 3: candidato y procedencia, sin inventar entrenamiento

El [plan](implementation-plan.md) compara las opciones. Candidato principal
para GPU: **Qwen3-4B-Instruct-2507**, Apache-2.0, non-thinking. Alternativa:
Qwen3-1.7B, desactivando thinking. Son selecciones documentales, **no modelos
probados o aprobados aquí para negociación**.

`training/qwen3-4b.candidate.json` fija revisión exacta, QLoRA y directorio
independiente. No cambia el baseline ni descarga pesos. Para planificar:
GPU CUDA 16–24 GiB VRAM, RAM 32 GiB, disco 50 GiB y contexto inicial 2048
para entrenamiento; estas cifras son estimaciones a validar en el host objetivo.

El registro de futuras corridas incorpora versiones reales de librerías,
runtime CUDA, parámetros entrenables/totales, pasos, checkpoints existentes e
historial del Trainer. **Es código preparado; no hay un registro nuevo de
entrenamiento, checkpoint ni adaptador generado en este trabajo**.

Faltan corpus autorizado con revisión experta verificable, infraestructura ML
compatible, smoke real de optimización, entrenamiento y comparación ciega
base/especializado. No se elude la revisión marcando los ejemplos como aprobados.
El corpus demostrativo anterior no es suficiente para producir una IA experta.

## Aprobación y despliegue

La mejora de calidad sigue sin aprobarse. Medir en GPU la latencia/memoria y
evaluar continuidad larga, objetivos, límites, concesiones, objeciones, citas y
recomendaciones antes de promover el modelo. No basta con JSON válido o pérdida
de entrenamiento menor. No se realizó despliegue ni cambio del backend del preview.

## Verificación del código de esta etapa

**113 pruebas automatizadas aprobadas**: las 95 previas y 18 nuevas de
observabilidad, validación íntegra, streaming diagnóstico, cancelación,
estimación de capacidad y procedencia de software. Continúa la advertencia
de deprecación conocida de Starlette/httpx, sin fallos en la suite.

Se ejecutó además el preflight del perfil Qwen3: rechazó correctamente el host
sin GPU antes de cargar pesos o generar checkpoints. Este rechazo no es una
prueba de entrenamiento; confirma que el control de recursos no se elude.
