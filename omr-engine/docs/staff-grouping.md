# Marcas de agrupación de pentagramas

`palermo_omr.staff_grouping` propone trazos verticales largos situados en el margen izquierdo de sistemas con dos o más pentagramas.

## Qué detecta

Busca segmentos verticales que cubren una parte sustancial de la altura del sistema geométrico. Si encuentra además dos remates horizontales cortos, uno por encima y otro por debajo del sistema, etiqueta la forma como `square_bracket_candidate`. Si no encuentra ambos remates, conserva la etiqueta genérica `vertical_grouping_mark_candidate`.

La detección de remates es intencionalmente estricta: busca evidencia fuera de las líneas superior e inferior del pentagrama para reducir confusiones con las propias líneas musicales.

## Qué no concluye

Un corchete recto candidato no demuestra que los pentagramas pertenezcan al piano ni que compartan una parte musical. Una marca vertical también puede ser parte de una llave u otro elemento gráfico. El módulo no reconoce llaves curvas, no distingue instrumentación y no identifica voces SATB.

La detección depende de que los sistemas geométricos previos sean razonables. Las puntuaciones son heurísticas y no están calibradas como probabilidades. Los candidatos no se convierten automáticamente en asignaciones de partes o voces; requieren revisión visual y evaluación con partituras reales anotadas.
