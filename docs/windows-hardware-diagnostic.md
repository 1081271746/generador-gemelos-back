# Diagnóstico local en Windows sin instalaciones

Este script recoge datos de **la computadora donde se ejecuta**, no de una GPU remota.
Funciona con la biblioteca estándar de Python 3.10 o posterior, incluido el
Python 3.14 que el usuario tiene instalado. No requiere instalar el backend,
activar servicios, configurar `.env`, conectarse a Replit ni iniciar sesión.

## Ejecutar ahora

Desde PowerShell, ubicado en la raíz de `generador-gemelos-back`:

```powershell
py -3 scripts\diagnose_local_hardware.py --output generated-artifacts\hardware-local.json
```

Si el lanzador `py` no está disponible, utilizar:

```powershell
python scripts\diagnose_local_hardware.py --output generated-artifacts\hardware-local.json
```

Ejecutar **una sola variante**. El JSON también se imprime en la terminal.
El script rechaza sobrescribir un archivo existente: para repetirlo, elegir
otro nombre, por ejemplo `hardware-local-2.json`.

Para revisar el archivo antes de compartirlo:

```powershell
Get-Content generated-artifacts\hardware-local.json
```

Compartir únicamente ese JSON, no `.env`, credenciales, inventarios completos,
rutas personales ni capturas de otras ventanas. El informe no incluye nombre de
usuario/equipo, UUID/serial de GPU, variables de entorno, claves ni lista de
procesos. Solo escribe un archivo cuando se indica `--output`; sus resultados
quedan excluidos de Git por la regla existente `generated-artifacts/`.

## Qué comprueba

- Windows/arquitectura, bits del intérprete, versión de Python y cantidad de CPU.
- RAM física total/disponible mediante la API nativa de Windows.
- Espacio libre de la unidad del directorio actual, sin guardar la ruta.
- Nombre de cada GPU, VRAM total/libre y controlador mediante `nvidia-smi`.
- Versión CUDA anunciada por el controlador, si está disponible; **no prueba**
  que el Toolkit esté instalado o que PyTorch funcione.
- Versiones instaladas en **el Python que ejecuta el script**, leyendo metadatos
  sin importar PyTorch, Transformers, PEFT, Accelerate o bitsandbytes.

Una dependencia ausente aparece como `null`. Un `nvidia-smi` ausente, lento,
fallido o con una respuesta inválida se informa explícitamente. No se considera
que la GPU funcione en CUDA por el mero hecho de que aparezca su nombre.
El diagnóstico no modifica el preflight del entrenamiento existente.

## Comprobación CUDA opcional, solo después de autorizar una instalación

Cuando PyTorch ya esté instalado en el intérprete elegido:

```powershell
py -3.11 scripts\diagnose_local_hardware.py --check-cuda --output generated-artifacts\hardware-cuda.json
```

Esta opción inicia un proceso separado, con límite de 60 segundos, y ejecuta
una multiplicación de tensores **8 × 8 en FP32**, sin gradientes. No carga un
modelo, no calcula un paso de optimización y no entrena. Comprueba acceso real a
CUDA y consulta capacidad de cómputo y soporte BF16 reportado por PyTorch.
Ese indicador **no equivale a una prueba aritmética BF16**.
Los errores del proceso se resumen sin imprimir rutas o trazas personales.
Los demás comandos externos tienen un límite de 10 segundos.

Incluso si esta operación pasa, `training_readiness` sigue siendo `not_verified`:
no se han comprobado un backward NF4, el presupuesto de memoria durante
entrenamiento, la recarga de adaptadores ni la calidad del modelo.

## Configuración propuesta para 6 GB

Propuesta, **no instalación aprobada ni combinación probada en esa laptop**:

| Componente | Objetivo |
| --- | --- |
| Python | 3.11, 64 bits, en paralelo al Python existente |
| PyTorch | 2.10.0, distribución CUDA 12.6 |
| Transformers / PEFT | 4.57.6 / 0.18.1 |
| Accelerate / bitsandbytes | 1.12.0 / 0.49.2 |
| Primera prueba | Qwen2.5-0.5B-Instruct; revisión fijada antes de descargar |
| Adaptación | QLoRA NF4, doble cuantización, rango 8 / alpha 16 |
| Módulos / dropout | `q_proj`, `v_proj` / 0.05 |
| Batch / pasos iniciales | 1 / 3 pasos de optimización |
| Longitud diagnóstica | Hasta 512 tokens totales; ejemplos breves completos |
| Memoria | Medir; objetivo conservador de proceso ≤4.5 GiB, no garantía |

Los 16 GB de RAM y 135 GB libres reportados por el usuario cubren las
recomendaciones iniciales, pero este script debe medir los recursos donde se
ejecute. No elimina Python 3.14 ni lo declara incompatible con todo el conjunto.
Las versiones propuestas no son un lockfile validado. No instalar el
`requirements.txt` completo del backend para obtener este inventario.

La configuración de entrenamiento anterior de 4B **no es el punto de partida
para esta GPU de 6 GB**. Este inventario no selecciona ni ejecuta ninguna
configuración de entrenamiento. Los 512 tokens no cambian los límites de la
API ni permiten truncar datos o análisis existentes.

Antes de autorizar el smoke: comprobar CUDA real, kernels NF4 con gradientes,
precisión elegida y longitud completa de los ejemplos. Antes de entrenamiento
completo: revisar el dataset y comparar base/adaptador con casos reservados.

## Evidencia y límites

El script y sus casos de error pueden probarse en el entorno Linux del
repositorio. La API de memoria de Windows se cubre con una prueba simulada;
**eso no equivale a haberlo ejecutado en Windows o en la RTX local**.
No se han instalado dependencias ni descargado pesos mediante este diagnóstico.
La suite del backend aprobó **136 pruebas** en Linux tras incorporar el
diagnóstico, incluidas 23 pruebas nuevas de inventario, errores y escritura
segura del informe.

Fuentes:

- [Capacidad CUDA de NVIDIA](https://developer.nvidia.com/cuda-gpus).
- [Binarios oficiales de PyTorch](https://pytorch.org/get-started/previous-versions/).
- [bitsandbytes 0.49.2: Windows, CUDA y NF4](https://huggingface.co/docs/bitsandbytes/v0.49.2/en/installation).
- [Qwen2.5-0.5B-Instruct](https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct).
