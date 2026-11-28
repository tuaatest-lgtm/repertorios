# Adaptador directo del análisis de página

`build_visual_anchor_map_from_page_analysis` consume los arrays del JSON de
análisis (`staves`, `staff_system_candidates`, `measure_span_candidates` y
`notehead_candidates`). Reconstruye el `ScoreStructure` geométrico y traduce
índices de cabezas por página a IDs estables `p{page}-head-{index}`.

El llamador aporta el mapa evento -> índices de cabezas. Para silencios sin
cabezas debe aportar también el pentagrama y la caja geométrica del glifo.
Los acordes con cabezas en distintos pentagramas se reportan como
`cross_staff_event`; no se fuerza una caja común ni un sistema arbitrario.

Los resultados siguen siendo candidatos geométricos. La detección de sistemas
puede contener un sistema separado por pentagrama si no hay evidencia de
agrupación; este adaptador conserva esa incertidumbre en vez de inventar parejas.
