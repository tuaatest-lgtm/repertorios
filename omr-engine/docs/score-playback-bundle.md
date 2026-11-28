# Paquete integrado de reproducción por documento

`build_score_playback_bundle` reúne en una sola respuesta:
- proyección temporal provisional,
- comandos polifónicos note_on/note_off,
- anclajes visuales multipágina derivados de `ScoreDocument`.

La página de cada evento debe estar declarada en `event_page_numbers`. La
estructura de cada página aporta los sistemas y regiones de compás; las cajas
de cabezas proceden de la detección geométrica. Eventos sin página, sistema,
compás o caja verificable quedan en `visual_anchor_map.unresolved`.

El campo `coverage` permite detectar eventos reproducibles que no tienen
posición visual y anclajes que no corresponden a un evento de reproducción.
Este paquete no se conecta aún al visor de producción ni convierte candidatos
OMR en notas confirmadas.


Para unir páginas sin reiniciar el reloj, se puede pasar `page_measure_global_indices` a `build_score_playback_bundle_from_page_analyses`. El mapa declara cada índice local de compás y su índice global continuo. Si falta una asignación o hay un salto, el paquete conserva solo el prefijo contiguo y deja las medidas posteriores sin programar; nunca comprime un compás ausente y adelanta la música.
