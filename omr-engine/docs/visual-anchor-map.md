# Anclajes geométricos para el cursor

`build_visual_anchor_map` conecta eventos fusionados con las cajas de las
cabezas de nota producidas por `detect_notehead_candidates`. Los acordes reciben
un rectángulo que cubre todas sus cabezas. El resultado usa el contrato
`page_index/system_index/measure_index/x/y/width/height` consumido por
`ScoreVisualCursor`.

La función exige mapas explícitos de pentagrama a sistema y evento a compás.
Para silencios u otros símbolos sin cabezas acepta una caja de glifo en
`event_geometry_by_id`. Si faltan coordenadas o contexto, devuelve el evento
en `unresolved`; nunca rellena posiciones por orden musical.

Las coordenadas se conservan en el sistema de píxeles de la página de análisis.
El host debe aplicar la misma transformación de escala/recorte al visor PDF
antes de dibujar los resaltados.
