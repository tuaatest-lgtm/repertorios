# Reconstrucción geométrica preliminar de compases

El módulo `palermo_omr.measure_layout` realiza tres operaciones:

1. `detect_barline_candidates`: propone trazos verticales largos dentro de cada pentagrama.
2. `group_system_barlines`: agrupa candidatos alineados en distintos pentagramas; requiere apoyo de al menos dos pentagramas por defecto.
3. `infer_measure_spans`: propone intervalos entre barras consecutivas dentro de un mismo pentagrama.

## Límites importantes

- Una barra detectada no demuestra que sea una barra de compás.
- La agrupación por alineación horizontal no identifica por sí sola el sistema musical.
- Los intervalos no incluyen bordes de página o de sistema no observados.
- No se asigna un número editorial definitivo de compás.
- La validación métrica requiere figuras y duraciones ya interpretadas; no se infieren de estos trazos.
- No se deben enviar estos candidatos al motor Sonoro.

Las pruebas son geométricas y sintéticas. Se requiere validación posterior con partituras reales, incluyendo escaneos inclinados, barras dobles, sistemas de piano y partituras corales.


## Conciliación conservadora ante barras omitidas

La secuencia global compara los intervalos de cada pentagrama dentro de un mismo sistema. Si un intervalo de un pentagrama contiene los centros de dos o más intervalos consecutivos de otro pentagrama y su anchura respalda que abarca varios, se clasifica como:

- `ambiguous_spans_multiple_measure_candidates`

Ese intervalo no recibe un ordinal global propio ni se fuerza a uno de los compases. El mapa local conserva la referencia del pentagrama y los ordinales candidatos que podría abarcar, con estado pendiente de revisión. Así se evita contar una barra omitida como un compás adicional falso.

La continuidad de ordinales entre sistemas y páginas conserva el orden documental, pero sigue siendo provisional. Esta regla no reconstruye por sí sola una barra ausente ni demuestra la métrica musical; requiere comprobación visual y, para medir exactitud, anotación humana de referencia.
