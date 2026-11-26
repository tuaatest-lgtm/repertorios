# Marcas de agrupación de pentagramas

`palermo_omr.staff_grouping` propone formas gráficas situadas en el margen izquierdo de sistemas con dos o más pentagramas.

## Qué detecta

- `square_bracket_candidate`: trazo vertical con dos remates horizontales cortos, uno arriba y otro abajo.
- `curly_brace_candidate`: componente alto y estrecho cuyo centro se desplaza lateralmente respecto de sus tercios superior e inferior, una geometría compatible con una llave curva.
- `vertical_grouping_mark_candidate`: trazo vertical largo que no reúne evidencia suficiente para clasificarlo como corchete.

El umbral de separación entre pentagramas se puede ajustar con `max_interstaff_gap_spacing`. Su valor predeterminado en este detector es 8.0 veces el espaciado entre líneas. Este ajuste es local al detector de marcas y no modifica la agrupación general de sistemas del resto del motor.

## Qué no concluye

Ninguna etiqueta demuestra que los pentagramas pertenezcan al piano, al coro o a otra parte. La forma curva puede confundirse con otros trazos gráficos y las puntuaciones son heurísticas, no probabilidades calibradas. El detector no reconoce etiquetas impresas, no asigna instrumentos y no identifica voces SATB.

La detección depende de que los pentagramas previos sean razonables. Los candidatos requieren revisión visual y evaluación con partituras reales anotadas antes de usarse para proponer relaciones estructurales. No se conectan automáticamente con asignaciones de partes o voces.
