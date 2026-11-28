# Adaptador de alturas desde el análisis de página

`build_pitch_candidates_from_page_analysis` convierte las posiciones
diatónicas de `notehead_candidates` en candidatos MIDI mediante
`build_pitch_candidates`. Solo permite resolver una altura cuando tanto la
clave como la armadura de ese pentagrama están en estado `human_confirmed`.

Una armadura vacía debe declararse confirmada explícitamente. Si la clave o la
armadura siguen pendientes, el adaptador conserva el candidato sin MIDI y
explica qué contexto falta. Las alteraciones explícitas aceptadas se pueden
pasar alineadas por índice; el motor de pitch mantiene su propagación dentro
del compás y reinicia al cambiar de compás.

No detecta claves, armaduras ni alteraciones a partir de píxeles y no confirma
la posición de las cabezas: integra resultados revisados con la geometría.
