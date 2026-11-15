# Datos de demostración, no un corpus experto

`synthetic.jsonl` contiene **20 ejemplos sintéticos originales**, dos tareas por
cada una de diez familias: comercial, salarial, vehículos, precios, empresarial,
contratos, conflictos, colaborativa, competitiva y objeciones.

Procedencia: casos diseñados para este proyecto en `training/seed.py`, sin
conversaciones de usuarios ni material copiado de terceros. Se ofrecen bajo
CC0-1.0. `authorized=true` se refiere a este uso del material sintético.
`reviewed=false`: **no existe validación por especialistas en negociación**.

Los análisis muestran el formato, citas verificables y limitaciones de una
observación aislada. Sus puntuaciones 50 son etiquetas pedagógicas provisionales,
NO mediciones expertas, y no sirven para aprender una escala fiable.

Cada registro conserva escenario, objetivos, límites, roles, historial,
resultado esperado, estrategia/justificación y procedencia. Las familias se
separan juntas: las variantes de una conversación no deben aparecer en distintos
subconjuntos. El reparto actual es 16 entrenamiento / 2 validación / 2 prueba,
demasiado pequeño para concluir calidad o generalización.

```sh
python -m training.seed
python -m training.prepare training/datasets/synthetic.jsonl --allow-unreviewed-synthetic
```

La excepción anterior es solo diagnóstica. Un entrenamiento completo exige
registros revisados. Para corpus reales: documentar derechos, autorización,
revisión humana, diversidad, deduplicación y ausencia de información privada.
No cambiar `reviewed` en bloque para saltarse la revisión. Las reglas automáticas
detectan algunos correos/credenciales; no garantizan anonimización completa.

No se lee la base de datos ni se exportan conversaciones privadas automáticamente.
Almacena datos privados autorizados fuera de Git en una ubicación controlada.
