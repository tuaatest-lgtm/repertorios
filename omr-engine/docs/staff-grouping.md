# Marcas de agrupación de pentagramas

`palermo_omr.staff_grouping` propone formas gráficas situadas en el margen izquierdo de sistemas con dos o más pentagramas.

## Qué detecta

- `square_bracket_candidate`: trazo vertical con dos remates horizontales cortos, uno arriba y otro abajo.
- `curly_brace_candidate`: componente alto y estrecho cuyo centro se desplaza lateralmente respecto de sus tercios superior e inferior, una geometría compatible con una llave curva.
- `vertical_grouping_mark_candidate`: trazo vertical largo que no reúne evidencia suficiente para clasificarlo como corchete.

Los trazos verticales usan `max_interstaff_gap_spacing` (7.0 por defecto) para agrupar sistemas. Las llaves curvas se buscan por pares de pentagramas adyacentes, con `max_brace_gap_spacing` (8.0 por defecto). Esta búsqueda por pares evita que un tercer pentagrama cercano agrande el sistema y oculte una llave que solo abarca dos pentagramas. Ambos ajustes son locales a este detector y no modifican la agrupación general de sistemas del resto del motor.

## Qué no concluye

Ninguna etiqueta demuestra que los pentagramas pertenezcan al piano, al coro o a otra parte. La forma curva puede confundirse con otros trazos gráficos y las puntuaciones son heurísticas, no probabilidades calibradas. El detector no reconoce etiquetas impresas, no asigna instrumentos y no identifica voces SATB.

La detección depende de que los pentagramas previos sean razonables. Los candidatos requieren revisión visual y evaluación con partituras reales anotadas antes de usarse para proponer relaciones estructurales. No se conectan automáticamente con asignaciones de partes o voces.

## Recorrido en la canalización

La CLI principal ejecuta este detector sobre cada página y conserva los resultados en `staff_grouping_mark_candidates` y su contador. El overlay geométrico los dibuja con una etiqueta interrogativa (`BRACE?`, `BRACKET?` o `GROUP?`) y el paquete de revisión humana los incorpora como candidatos pendientes, relacionados con los índices de pentagrama detectados. Esta integración hace visible y revisable la evidencia; no cambia el estado de ninguna asignación de parte o voz.
