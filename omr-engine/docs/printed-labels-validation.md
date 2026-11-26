# Validación exploratoria de etiquetas impresas

Esta revisión mide extracción de texto PDF y proximidad geométrica, no exactitud musical. No se preparó una anotación humana completa de cada pentagrama y no se calculan precisión ni exhaustividad.

## Resultados

Prueba realizada sobre los PDF disponibles, con renderizado a 180 dpi para obtener pentagramas y extracción de la capa de texto con PyMuPDF.

| Partitura | Páginas | Etiquetas reconocidas en la capa PDF | Asociación geométrica candidata |
|---|---:|---:|---:|
| Brand New Hallelujah | 20 | 22 | 21 asociadas, 1 sin asignar |
| ACC-001 - PDF - CORO | 2 | 0 | 0 |
| Clamaré a Dios - Coro | 3 | 0 | 0 |

En *Brand New Hallelujah* se encontraron indicaciones como `MALE SOLO`, `TENORS only`, `Add BASSES`, `LADIES unis.` y `Add LADIES`. Se normalizaron los calificadores editoriales y se comparó la posición vertical del texto con los pentagramas detectados.

## Qué significa y qué no

- Los 21 casos son asociaciones por proximidad vertical; no prueban que el texto corresponda semánticamente a ese pentagrama.
- Un caso quedó sin asignar porque estaba fuera del margen geométrico configurado.
- Que los otros dos PDF no produzcan etiquetas solo significa que no se encontraron coincidencias en su capa de texto PDF. No significa que no tengan rótulos visibles: podrían ser escaneos o imágenes sin texto seleccionable.
- El umbral de proximidad se amplió porque en la partitura real algunas etiquetas aparecen bastante por encima del pentagrama.
- La asociación no se conecta a `ScorePart`, `ScoreVoice` ni a las asignaciones de pentagramas. Sigue siendo evidencia candidata que requiere revisión humana.

El módulo no realiza OCR, no interpreta texto arbitrario y no se ha conectado al CLI. Para reconocer rótulos en partituras escaneadas hará falta una etapa visual propia adicional, con su validación independiente.
