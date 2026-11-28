# Cursor visual sincronizado

`ScoreVisualCursor` une una proyección temporal provisional con anclajes
geométricos explícitos de cada evento. No detecta ni inventa coordenadas.

El host puede consultar `positionAt(player.current_seconds)` desde el ciclo de
renderizado y usar `page_index`, `system_index` y `highlights` para seleccionar
la página/sistema y resaltar simultáneamente las notas activas. El reloj de audio
sigue siendo la fuente de tiempo; cambiar de página no reinicia la reproducción.

Los anclajes requieren `event_id`, índices de página/sistema/compás y un rectángulo
`x,y,width,height`. Los eventos sin anclaje quedan enumerados en `unresolved`.
Si eventos activos se ubican en páginas o sistemas distintos, la posición se marca
ambigua y no se elige una página arbitrariamente.

Este módulo no está conectado a `index.html`, Sonoro ni a un renderizador de PDF.
La geometría debe ser suministrada por la capa de análisis visual del documento.
