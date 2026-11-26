# Reconstrucción temporal por secuencia de voz

El módulo `voice_sequence_timing.py` asigna inicios exactos a eventos rítmicos ordenados dentro de una voz y un compás.

## Criterio

1. Una etapa visual previa determina qué evento aparece antes y después dentro del mismo flujo (orden de lectura).
2. Cada evento debe tener una duración musical candidata o quedar explícitamente desconocida.
3. El inicio del primer evento es cero; los siguientes se calculan acumulando duraciones exactas.
4. Las cabezas que forman un acorde se agrupan en un solo evento de ataque mediante `notehead_ids`.
5. Cada voz o flujo independiente se calcula por separado; luego sus eventos pueden combinarse en la línea temporal común.

**La separación horizontal en píxeles no se interpreta como duración ni como escala temporal.** Solo el orden visual se usa para ordenar eventos. Esto evita asumir que una partitura distribuye el espacio de manera lineal.

## Incertidumbre

Si una duración es desconocida, el inicio de ese evento aún puede conocerse por los eventos anteriores, pero los inicios posteriores de esa secuencia quedan pendientes. El módulo no inventa duraciones para recuperar el alineamiento.

El cálculo presupone que la secuencia de entrada ya está separada por voz y compás, que los acordes ya se han agrupado y que las ligaduras de prolongación ya se han consolidado. No identifica esas estructuras en la imagen.

## Piano y SATB

- Piano: se procesa cada flujo independiente de mano/voz por separado. No se equiparan automáticamente mano derecha e izquierda.
- SATB: soprano, alto, tenor y bajo se procesan como secuencias distintas y después se combinan. Los ataques que coinciden en tiempo quedan con el mismo inicio exacto.
- Una partitura con dos voces independientes en un mismo pentagrama requiere dos secuencias separadas; no se debe asumir que un pentagrama equivale siempre a una voz.

Este módulo no se conecta al CLI ni a Sonoro.
