# Evaluación agregada de un corpus

`palermo_omr.dataset_evaluation` aplica el evaluador de eventos a todas las
partituras revisadas de una partición y calcula métricas micro agregadas, además
de conservar el resultado individual de cada partitura.

## Uso

```python
from palermo_omr.annotation_dataset import AnnotationDataset
from palermo_omr.dataset_evaluation import evaluate_annotation_dataset

dataset = AnnotationDataset.from_dict(manifest_data)
result = evaluate_annotation_dataset(
    dataset,
    predictions_by_score,
    split="test",
)
print(result.f1, result.pitch_accuracy, result.per_score)
```

Cada clave de `predictions_by_score` es un `score_id`. Una partitura sin
predicciones se cuenta como cero eventos detectados. Se rechazan claves
desconocidas y predicciones de otra partición.

## Métricas

- Detección: TP, FP, FN, precisión, recall y F1 micro.
- Atributos de los eventos emparejados: tipo, conjunto completo de alturas,
  duración y voz.
- Inicio: error absoluto medio en negras.
- Desglose individual por partitura para detectar si una familia de partituras
  falla más que otra.

Las métricas micro se calculan sumando conteos antes de dividir; no se promedian
los F1 de cada partitura. Esto evita que una partitura pequeña tenga el mismo
peso que otra con muchos más eventos.

## Salvaguardas

- Solo acepta partituras con `review_status="reviewed"`.
- Solo evalúa una partición por llamada; por defecto, `test`.
- No permite mezclar por accidente predicciones de train/validation/test.
- No genera eventos ni completa datos ausentes.

Las pruebas actuales usan datos sintéticos. Hasta incorporar anotaciones reales,
los resultados de prueba solo validan el funcionamiento del evaluador, no la
precisión musical del motor.
