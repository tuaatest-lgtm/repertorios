# Marcas verticales de agrupación de pentagramas

`palermo_omr.staff_grouping` propone trazos verticales largos situados en el margen izquierdo de sistemas con dos o más pentagramas.

## Qué detecta

Busca segmentos verticales que cubren una parte sustancial de la altura del sistema geométrico. La salida se denomina `vertical_grouping_mark_candidate`.

## Qué no concluye

El trazo puede corresponder a un corchete, a una parte de una llave o a otro elemento gráfico. No distingue todavía llaves curvas de corchetes rectos, no confirma que dos pentagramas pertenezcan al piano y no identifica voces SATB. La detección depende de que los sistemas geométricos previos sean razonables.

Los candidatos se limitan al margen izquierdo y llevan advertencia explícita. No se convierten automáticamente en asignaciones de partes o voces. Para avanzar será necesario reconocer la forma completa (incluidos remates o curvatura), contrastarla con partituras reales y medir precisión y falsos positivos.
