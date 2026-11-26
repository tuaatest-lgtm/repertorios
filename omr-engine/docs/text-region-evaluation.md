# Evaluación de regiones de texto

El módulo `palermo_omr.text_region_evaluation` compara cajas detectadas con cajas de referencia dibujadas por una persona. Es una herramienta de evaluación geométrica: no hace OCR, no clasifica palabras y no confirma que una región sea una etiqueta musical.

## Formato de las cajas

Todas las coordenadas están en píxeles de la imagen evaluada y usan el orden:

`[x_min, y_min, x_max, y_max]`

El origen está en la esquina superior izquierda. `x_max` y `y_max` son límites exclusivos; el ancho y alto deben ser positivos. Las cajas anotadas y las predichas deben corresponder a la misma imagen, página, resolución y recorte.

## Métrica y emparejamiento

La intersección sobre unión (IoU) se calcula como el área de intersección dividida por el área de unión. Una pareja cuenta como acierto si su IoU alcanza el umbral configurado (por defecto, 0.5). El emparejamiento es uno a uno y maximiza el número de parejas válidas, para que dos detecciones no se acrediten contra una sola anotación.

- **TP (true positive):** detección emparejada con una anotación.
- **FP (false positive):** detección sin anotación emparejada.
- **FN (false negative):** anotación sin detección emparejada.
- **Precisión:** TP / (TP + FP).
- **Cobertura/recall:** TP / (TP + FN).
- **F1:** media armónica de precisión y cobertura.
- **IoU media:** promedio de IoU de las parejas emparejadas.

Si el denominador de una métrica es cero, el resultado es `None`, no cero ni uno. Así se evita presentar una página sin predicciones o sin anotaciones como una evaluación perfecta.

## Ejemplo de uso

```python
from palermo_omr.text_region_evaluation import evaluate_text_regions

predicted = [(32, 60, 90, 76), (18, 180, 75, 196)]
human_reference = [(30, 59, 92, 77)]

result = evaluate_text_regions(predicted, human_reference, iou_threshold=0.5)
print(result.to_dict())
```

## Formato recomendado para anotaciones

Cada página debe tener una imagen rasterizada de referencia y un archivo JSON independiente. Ejemplo ilustrativo:

```json
{
  "schema_version": 1,
  "image_id": "score-a-page-01",
  "source_file": "score-a.pdf",
  "page_number": 1,
  "image_width": 2550,
  "image_height": 3300,
  "render_dpi": 300,
  "annotations": [
    {
      "bbox": [32, 60, 90, 76],
      "category": "text_region",
      "text_content": null,
      "notes": "Etiqueta impresa sobre el primer pentagrama"
    }
  ]
}
```

Las anotaciones deben delimitar regiones visuales de texto, no interpretar el significado musical. El campo `text_content` puede permanecer `null` y no debe completarse por conjetura. Si luego se necesita clasificar etiquetas, esa tarea requiere una anotación semántica independiente.

## Protocolo para un corpus útil

1. Conservar el archivo original y registrar página, DPI y dimensiones del raster usado por el detector.
2. Anotar todas las regiones de texto dentro del alcance declarado del detector, incluidos títulos, indicaciones editoriales y texto que no sea una etiqueta de voz. Esto evita favorecer artificialmente al detector.
3. Registrar también páginas sin texto, que ayudan a medir falsos positivos.
4. Mantener un conjunto de ajuste y otro de evaluación final separados por partitura, no por página aleatoria de la misma partitura.
5. Definir una guía de anotación y revisar desacuerdos entre anotadores antes de calcular métricas.
6. Reportar resultados por partitura y en conjunto, junto con el umbral IoU y las resoluciones usadas.

Los ejemplos sintéticos sirven para probar el cálculo, pero no son evidencia de precisión en partituras reales. No existe todavía un corpus real anotado ni se reportan métricas de rendimiento del detector.
