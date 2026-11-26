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


## Caso adicional: MAR-007 - PARTITURA

Se revisó el PDF de tres páginas generado mediante Quartz PDFContext de iOS. El documento contiene objetos de imagen incrustados en las tres páginas, pero también conserva texto seleccionable para los nombres de las voces y otros elementos musicales.

La detección geométrica existente propuso 8 pentagramas en la página 1, 8 en la página 2 y 4 en la página 3 (20 en total). La extracción de texto permitió identificar 20 rótulos vocales:

- Página 1, primer sistema: `Soprano`, `Alto`, `Tenor`, `Bass`.
- Página 1, segundo sistema: `S`, `A`, `T`, `B`.
- Página 2: dos sistemas con `S`, `A`, `T`, `B`.
- Página 3: un sistema con `S`, `A`, `T`, `B`.

En esta revisión exploratoria, los centros verticales de los 20 rótulos quedaron próximos a un pentagrama distinto, de acuerdo con la geometría detectada. Esto representa 20 asociaciones geométricas candidatas observadas, no 20 identidades musicales confirmadas ni una medición de precisión/recall. No existe una anotación humana independiente completa para calcular esas métricas.

El caso motivó la incorporación de las abreviaturas aisladas `S`, `A`, `T`, `B` al vocabulario del módulo. La regla es exacta por línea: no se reconocen esas letras dentro de palabras. Las asociaciones siguen siendo candidatas y no crean partes, voces ni asignaciones confirmadas.

La prueba del módulo usa PDFs sintéticos generados durante los tests; no incorpora el PDF de usuario al repositorio. El caso MAR-007 se conserva como validación exploratoria documentada, no como fixture binario versionado.
