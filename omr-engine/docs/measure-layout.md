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
