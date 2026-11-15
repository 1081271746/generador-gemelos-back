# Validación real del motor local

## Evidencia disponible

- **95 pruebas automatizadas aprobadas**: se conservaron las 48 anteriores y se
  añadieron 47 de cliente local, motores, gRPC, privacidad y pipeline.
- Sintaxis de 24 módulos Python de IA/entrenamiento/launchers comprobada.
- Pruebas de gRPC con transporte TCP real: autenticación y contrato de respuesta.
  Las pruebas automatizadas del adaptador HTTP usan respuestas controladas,
  claramente distintas de las mediciones del modelo real.
- Datos sintéticos: 20 targets validados, 10 familias, reparto reproducible
  16/2/2 sin compartir familias entre subconjuntos.
- El entrenamiento completo se rechazó correctamente antes de descargar pesos
  por ausencia de GPU. No se crearon checkpoints ni adaptadores ficticios.
- Sin cambios en `.proto`, schemas públicos, modelos SQLAlchemy o migraciones.
- Sin modificaciones al repositorio del frontend.

La suite muestra una advertencia de deprecación de Starlette/httpx del entorno
existente; no un fallo de pruebas.

## Inferencia verdaderamente ejecutada

Se descargó el GGUF oficial y se cargó en llama.cpp 5311 sobre CPU:

- Qwen2.5-1.5B-Instruct Q4_K_M, **sin fine-tuning**.
- Tamaño del archivo: 1 117 320 736 bytes.
- SHA-256: `6a1a2eb6d15622bf3c96857206351ba97e1af16c30d7a74ee38970e434e9407e`.
- Revisión oficial GGUF: `91cad51170dc346986eccefdc2dd33a9da36ead9`.
- Proceso observado alrededor de 1.47 GiB RSS durante la evaluación; es una
  observación puntual, no pico máximo ni garantía para todos los contextos.
- `/v1/models` confirmó el modelo cargado. Esto por sí solo no demuestra calidad.

La primera generación real, antes del guard numérico, tardó **13.68 segundos**.
Devolvió JSON válido pero aceptó un precio de 80 cuando el escenario exigía no
vender por debajo de 90. **Eso fue un fallo de negociación**, no una prueba
exitosa de calidad. Motivó el control posterior que bloquea esas respuestas.
No se ocultó el fallo ni se sustituyó la respuesta por una plantilla.

La evaluación ampliada del modelo base produjo estos resultados reales:

| Caso | Resultado | Tiempo |
|---|---|---|
| `precios-twin` | JSON válido, pero la revisión semántica detectó que revelaba un precio mínimo privado | 9.631 s |
| `precios-analysis` | `ExternalServiceError` al agotar la espera; sin análisis válido | 300.107 s |

Hubo 1/2 respuestas válidas en formato, **no 1/2 aprobadas en calidad**. Después
se reforzó el guard para rechazar cifras etiquetadas como límites privados.
Se comprobó esa corrección con pruebas deterministas, sin repetir la evaluación
larga ni convertir una respuesta rechazada en un éxito semántico.

El smoke autenticado con modelo real devolvió `UNAVAILABLE` en 6.35 segundos
después de los controles. No produjo una respuesta aprobada. La autenticación y
el transporte se verifican aparte con las pruebas de integración controladas.
**El recorrido completo con respuesta local útil no está aprobado para producción.**

Los informes están en `generated-artifacts/`. No se versionan automáticamente
porque pueden contener conversaciones. El smoke aislado usa únicamente el
caso sintético incluido, sin cuentas ni DB reales:

```sh
python -m scripts.smoke_local_rpc
python -m training.evaluate training/prepared/test.jsonl \
  --allow-unreviewed-synthetic --output generated-artifacts/evaluation-base.json
```

La evaluación del pequeño conjunto sintético se usa para detectar fallos de
integración, no para certificar generalización. No representa una evaluación
ciega independiente de los ejemplos diseñados en este trabajo.

## Entrenamiento: no ejecutado

El host observado tiene 4 CPU, unos 8 GiB RAM y no dispone de GPU NVIDIA
detectable. La instalación opcional de torch/Transformers/PEFT/accelerate no
pudo resolverse: el instalador informó que no había una versión de accelerate
disponible en su resolución. Se conservaron las dependencias base originales.

Por tanto:

- Pipeline LoRA/QLoRA, checkpoints, evaluación y exportación: **código implementado**.
- Tokenización/padding con librerías ML reales: **pendiente de ejecución** en host compatible.
- Prueba pequeña de optimización: **no ejecutada**.
- Entrenamiento completo: **no ejecutado**.
- Adaptador especializado: **no existe todavía**.
- Comparación real base vs especializado y mejora de calidad: **no demostradas**.
- Pruebas sostenidas con GPU, consumo VRAM y concurrencia multiusuario:
  **no ejecutadas**.

No deben confundirse las pruebas unitarias de preflight/formato con una corrida
de entrenamiento. Ver `docs/training.md` para el procedimiento GPU y el smoke
pequeño obligatorio antes de cualquier entrenamiento completo.

## Límites pendientes antes de producción

Hace falta ampliar y revisar el corpus con especialistas, validar calidad en
español y adversarialmente, entrenar en infraestructura compatible y comparar
contra el base. Los límites narrativos complejos y las cifras de magnitudes
mezcladas no están resueltos por el guard conservador de precios.

El push del código no despliega ni configura un host GPU, no publica un backend
nuevo y no cambia la conexión del frontend existente.
