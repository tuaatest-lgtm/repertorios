# Validación métrica de compases

## Objetivo

La validación métrica es una capa matemática posterior a la interpretación de
figuras. No reconoce símbolos en la imagen, no detecta barras de compás y no
convierte candidatos OMR en notas confirmadas.

## Unidad de duración

Las duraciones se expresan en unidades de negra:

- redonda: 4
- blanca: 2
- negra: 1
- corchea: 0.5
- semicorchea: 0.25

El puntillo y las ligaduras deben resolverse antes de sumar las duraciones.

## Indicadores de compás

La duración esperada se calcula como:

`numerador × 4 / denominador`

Por tanto, 4/4 espera cuatro negras, 3/4 espera tres negras y 6/8 espera tres
negras (seis corcheas). Esta equivalencia comprueba la duración total, no el
agrupamiento de acentos propio de un compás compuesto.

## Estados

- `complete`: la suma coincide con el valor esperado dentro de la tolerancia.
- `underfull`: la suma es menor que el compás y no se marcó como anacrusa.
- `overfull`: la suma supera el valor esperado.
- `pickup_incomplete`: compás menor que el esperado marcado explícitamente
  como posible anacrusa.

Una anacrusa no se confirma automáticamente: requiere contexto musical y
editorial. Los silencios, repeticiones, cambios de compás y compases irregulares
también necesitan tratamiento específico.

## Uso desde Python

```python
from palermo_omr.measure_validation import validate_measure_duration

result = validate_measure_duration([1, 1, 1, 1], 4, 4)
print(result.status)  # complete
```

## Límite actual

Esta capa todavía no está conectada al CLI ni al reproductor. La detección de
compases y la interpretación fiable de figuras siguen pendientes. No debe
usarse para validar automáticamente una partitura completa hasta que esas
etapas produzcan eventos musicales revisados.
