# Adaptador de eventos desde análisis de página

`build_event_candidates_from_page_analysis` reconstruye las estructuras
tipadas de pentagramas, cabezas, ritmo, interpretación y grupos de haces a
partir del JSON de una página. Luego usa el agrupador conservador y fusiona
cada grupo con la lista de candidatos de altura ya alineada por índice.

Los IDs de evento se prefijan con el número de página para evitar colisiones
en documentos multipágina. Si la altura no está resuelta, la figura es
ambigua o las plicas no concuerdan, el evento permanece incompleto. La voz
no se inventa: se asigna después mediante el flujo de contexto revisado.

El adaptador requiere un ID de procedencia por cada cabeza; no intenta
reconstruir IDs a partir de coordenadas ni ordenar candidatos de forma implícita.
