# Balance rítmico por voz y compás

El módulo `voice_measure.py` organiza eventos ya reconocidos en una sola voz (o flujo rítmico independiente) y un solo compás, y utiliza `duration_completion.py` para calcular el residuo exacto.

## Reglas

- Cada análisis recibe explícitamente `voice_id` y `measure_index`.
- No permite mezclar eventos de otra voz ni de otro compás.
- Notas y silencios cuentan como eventos; los silencios conocidos consumen tiempo.
- Un evento con duración `None` se considera pendiente.
- Solo se asigna el residuo cuando queda exactamente un evento pendiente.
- Los identificadores deben ser únicos dentro del compás.
- Las notas enlazadas por ligadura de prolongación deben llegar con su duración total ya consolidada. Una continuación ligada no debe contarse como un nuevo ataque.

## Alcance actual

Este módulo no descubre voces, compases ni eventos en la imagen. La asignación de `voice_id` y `measure_index` es responsabilidad de una etapa posterior de reconocimiento estructural. En partituras de piano, cada flujo rítmico de mano/pentagrama se analiza de forma independiente; en SATB, cada voz se analiza separadamente cuando la partitura permite identificarla.

La inferencia es matemática y condicional: no convierte por sí sola una duración restante en una figura gráfica única. Por ejemplo, 3/2 negras puede representarse de varias maneras según el contexto notacional.
