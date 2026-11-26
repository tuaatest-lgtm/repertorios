# Etiquetas musicales impresas

`palermo_omr.printed_labels` extrae etiquetas conocidas desde la capa de texto de un PDF y propone una asociación geométrica con el pentagrama más cercano.

## Etiquetas contempladas

La primera versión reconoce coincidencias exactas normalizadas para etiquetas frecuentes:

- Voces o grupos vocales: `MALE SOLO`, `FEMALE SOLO`, `LADIES`, `WOMEN`, `MEN`, `SOPRANO(S)`, `ALTO(S)`, `CONTRALTO`, `TENOR(S)`, `BASS(ES)`, `BARITONE`.
- Instrumentos: `PIANO`, `KEYBOARD`, `ORGAN`.

La normalización ignora mayúsculas, acentos y puntuación. También admite calificadores editoriales frecuentes como `Add`, `only` y `unis.` alrededor de una etiqueta reconocida. No reconoce frases libres ni variantes que no estén en el vocabulario explícito.

## Asociación a pentagramas

La función recibe los pentagramas geométricos detectados para esa página. Convierte la caja de texto PDF a la escala de renderizado y compara el centro vertical de la etiqueta con el centro de cada pentagrama. El margen predeterminado admite hasta 8 veces el espaciado entre líneas porque algunas editoriales imprimen la indicación bastante por encima del pentagrama correspondiente.

Los resultados pueden quedar como:

- `associated_candidate`: un pentagrama es claramente el más cercano.
- `ambiguous`: dos o más pentagramas están a distancias similares.
- `unassigned`: no hay un pentagrama suficientemente cercano.

Incluso una asociación candidata es solo proximidad geométrica; no demuestra que la etiqueta describa exclusivamente ese pentagrama. La revisión humana sigue siendo necesaria para crear una identidad confirmada.

## Límites importantes

- Funciona con texto disponible en la capa interna del PDF. No realiza OCR.
- Si la partitura es un escaneo o una imagen incrustada sin texto seleccionable, no encontrará estas etiquetas.
- No interpreta etiquetas desconocidas, abreviaturas no incluidas ni instrucciones musicales generales.
- No decide por sí sola la asignación de partes, piano/manos ni voces SATB.
- El CLI no incorpora todavía este detector; primero debe validarse con partituras reales y compararse con una anotación humana.

No se añade ninguna dependencia: se reutiliza PyMuPDF, que ya forma parte del motor.
