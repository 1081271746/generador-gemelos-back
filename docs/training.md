# Especialización LoRA/QLoRA

## Estado y requisitos

Este repositorio incluye un pipeline ejecutable, **no un adaptador entrenado**.
No hay pesos especializados publicados. Descargar Qwen o cargar GGUF no entrena
el modelo. El entrenamiento completo se bloquea antes de descargar pesos si no
se detecta GPU NVIDIA. Existe una excepción explícita para un smoke de 1–5 pasos
con un modelo pequeño en CPU; sigue necesitando las librerías ML.

En una máquina GPU compatible, instala Python y las dependencias base más las
opcionales de `training/requirements.txt` con su gestor de paquetes. Para QLoRA
añade bitsandbytes en una versión compatible con CUDA. No son dependencias de
FastAPI y no se importan al arrancar los servicios.

```sh
python -m training.hardware
python -c "import torch; print(torch.__version__, torch.cuda.is_available())"
```

Comprueba memoria VRAM, disco, CUDA, licencia del modelo y acceso al almacenamiento
antes de proceder. Las APIs de referencia son Transformers 4.x, PEFT y Trainer;
la compatibilidad de ese conjunto debe verificarse y bloquearse en el host GPU.

## Datos autorizados y separación

1. Reúne un corpus autorizado con casos variados y revisión de especialistas.
2. Adapta los registros al schema `training.data.Example`, mantén familia,
   procedencia, licencia, consentimiento/autorización y justificación.
3. Elimina PII y secretos fuera de línea. La detección automática es parcial.
4. Valida los targets contra los schemas Pydantic existentes. Las citas deben
   existir literalmente en mensajes del usuario.
5. Prepara los subconjuntos:

```sh
python -m training.prepare training/private/authorized.jsonl --output training/prepared
```

El reparto determinista por familia evita que turnos del mismo escenario se
mezclen entre entrenamiento, validación y prueba. Se rechazan duplicados aunque
cambien sus IDs. Esto no detecta todas las paráfrasis: auditar similitudes antes
de aprobar un corpus. El manifiesto guarda hashes y cantidades.

Para un smoke de formato, sin afirmar revisión experta:

```sh
python -m training.seed
python -m training.prepare training/datasets/synthetic.jsonl --allow-unreviewed-synthetic
```

Ese permiso **no permite un entrenamiento completo con datos sin revisar**.
No usar el conjunto de prueba para escoger prompts o hiperparámetros y luego
reportarlo como una evaluación independiente.

## Primera prueba pequeña

Copia `training/config.example.json` a un archivo propio. En GPU:

- `smoke: true`, `max_steps: 2`, `max_length: 2048`.
- `output_dir: models/smoke_adapter`, modo `lora` o `qlora` según hardware.
- Para CPU usa un modelo diagnóstico pequeño, revisión exacta de 40 caracteres,
  `cpu_smoke: true`, `mode: lora`, `max_length <= 1024`.
- Si un ejemplo excede la longitud, preparar ejemplos más breves o aumentar la
  ventana en hardware compatible; no truncar evidencia ni respuestas.

```sh
python -m training.train training/smoke-config.json
```

Se enmascara el prompt con `-100`, entrenando únicamente tokens del asistente.
El padding también se excluye de la pérdida. La plantilla chat debe conservar
el prefijo; de lo contrario se rechaza el tokenizer en vez de entrenar etiquetas
desalineadas. Se comprueban hashes y separación antes de cargar los pesos.

Solo un retorno correcto de `trainer.train()` seguido de evaluación y guardado
produce `run.json` con `smoke_completed`. No hay un marcador de éxito anticipado.
Un smoke comprueba la mecánica, **no especialización útil**.

## Entrenamiento completo

Después de revisar datos, smoke y recursos:

```sh
python -m training.train training/config.example.json
# Reanudar una corrida explícita:
python -m training.train training/config.example.json --resume models/negotiation_adapter/checkpoint-25
```

LoRA ajusta `q_proj` y `v_proj`, rango 8, alpha 16, microbatch 1 y acumulación 8
por defecto. QLoRA carga base NF4 4-bit con doble cuantización. Se usa BF16 donde
la GPU lo soporta, gradiente checkpointing y un máximo de dos checkpoints.
No se envían datos ni métricas a servicios de seguimiento externos.

El directorio no puede sobrescribirse accidentalmente: si contiene archivos,
elige uno nuevo o proporciona un checkpoint. Guarda respaldos del adaptador,
tokenizer, manifiesto, revisión base y métricas. No hay entrenamiento automático
con cada conversación ni acceso del pipeline a PostgreSQL.

## Evaluación base frente a especializado

El comando siguiente solo compara si **ambos modelos existen y están cargados**
en servidores diferentes. Si no existe adaptador, omite `--adapter-url`; el
informe contendrá solo el modelo base y no inventará la comparación.

```sh
python -m training.evaluate training/prepared/test.jsonl \
  --base-url http://127.0.0.1:8090/v1 \
  --adapter-url http://127.0.0.1:8091/v1 \
  --output generated-artifacts/comparison.json
```

Resultados automáticos: validez de schema, evidencia exacta, guard numérico,
latencia por ejemplo y RSS del **cliente**. Para análisis hay MAE de puntuaciones
contra etiquetas; si las etiquetas son provisionales, ese MAE no mide calidad.
La memoria del modelo se mide en el proceso llama-server, no con el RSS del cliente.

Revisión humana obligatoria, sobre el mismo conjunto ciego para ambos modelos:

| Criterio | 0 | 1 | 2 |
|---|---|---|---|
| Rol y escenario | contradictorio | parcial | consistente |
| Objetivos y límites | incumple | ambiguo | respeta |
| Contraofertas | inviables | débiles | viables y justificadas |
| Objeciones | ignora/escala | parcial | atiende con argumentos |
| Continuidad | contradice historia | parcial | coherente |
| Análisis | inventa hechos | superficial | fundamentado |
| Recomendaciones | genéricas | parciales | accionables y justificadas |
| Español y seguridad | incomprensible/riesgoso | mejorable | claro y seguro |

No aprobar una versión por schema válido únicamente. Registrar fallos de límites
y evidencia por separado; bloquear el despliegue si persisten fallos críticos.
No afirmar “experta” a partir de veinte casos ni de una pérdida de entrenamiento.

## Exportación y carga

```sh
python -m training.export models/negotiation_adapter models/merged
python /ruta/llama.cpp/convert_hf_to_gguf.py models/merged \
  --outfile models/negotiation-f16.gguf --outtype f16
llama-quantize models/negotiation-f16.gguf models/negotiation-q4.gguf Q4_K_M
python scripts/serve_local_model.py models/negotiation-q4.gguf
```

La fusión se hace con pesos base FP32, no con una base cuantizada en memoria, y
requiere RAM suficiente. Un adaptador smoke solo se exporta con permiso
`--allow-smoke` y no debe convertirse en candidato de producción.

Como alternativa avanzada, convierte el adaptador PEFT con la utilidad
`convert_lora_to_gguf.py` de una versión compatible de llama.cpp y cárgalo con
`scripts/serve_local_model.py BASE.gguf --adapter ADAPTER.gguf`.
No pases una carpeta PEFT al argumento `--adapter`: son formatos diferentes.

Cada actualización requiere nuevas métricas base/especializado, revisión ciega,
manifiesto de hashes, respaldo del modelo anterior y reinicio de inferencia.
No sustituir pesos durante una negociación activa sin un procedimiento controlado.
