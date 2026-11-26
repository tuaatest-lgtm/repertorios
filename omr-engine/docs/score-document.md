# Modelo de documento multipágina

El módulo `score_document.py` reúne estructuras de página en un documento y conserva el orden de lectura sin convertir similitudes geométricas en identidades musicales.

## Orden de páginas y sistemas

- Las páginas deben ser únicas y estar ordenadas por su número original.
- `ordered_system_refs` expone referencias a sistemas en orden de página y en el orden en que aparecen dentro de cada estructura de página.
- Los identificadores de pentagrama y de región de compás deben ser únicos en todo el documento.

## Continuidad entre páginas

`StaffContinuation` registra una posible relación entre un pentagrama de una página y otro de una página posterior. Sus estados son:

- `proposed`: existe una hipótesis pendiente de revisión.
- `confirmed`: la continuidad fue confirmada y debe incluir evidencia.
- `ambiguous`: se detectó una relación posible, pero no puede resolverse.

El modelo no crea estas relaciones automáticamente, no las deduce por altura vertical y no asigna por ello una parte o voz. Una continuidad entre pentagramas no demuestra por sí sola que se trate del mismo instrumento o voz; esa identidad musical permanece en las asignaciones explícitas del modelo de página.

## Numeración de compases

Los números de compás de `MeasureRegion` siguen siendo locales a la geometría de cada pentagrama. `GlobalMeasureNumber` permite registrar un número global solo cuando otra etapa o una revisión lo haya establecido explícitamente. La numeración global es opcional; el modelo no suma compases entre páginas ni supone que todos los pentagramas tengan idénticos límites.

## Límites

Esta capa organiza y valida referencias. No detecta saltos de sistema, no reconoce llaves o etiquetas de instrumentos, no decide continuidad musical y no resuelve anacrusas, repeticiones, compases omitidos ni numeración editorial. No se conecta al reproductor Sonoro ni cambia el análisis visual.
