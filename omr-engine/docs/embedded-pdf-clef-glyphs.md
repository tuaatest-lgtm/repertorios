# Claves desde glifos embebidos en PDF

Para PDFs vectoriales Sibelius/Reprise, `pdf_clef_glyphs.py` extrae glifos de
la fuente `RepriseSpecialStd` y los ancla al pentagrama por la posición
vertical del glifo. El mapa inicial observado es:

| Glifo PDF | Candidato |
|---|---|
| `°` | clave de sol (treble) |
| `¢` | clave de fa (bass) |

Uso desde el CLI:

```bash
palermo-omr "partitura.pdf" --output omr-output --embedded-pdf-clef-glyphs
```

El resultado se guarda en cada página como `embedded_clef_candidates`.
Los candidatos incluyen pentagrama, glifo, caja PDF, distancia al centro del
pentagrama y estado. Todos quedan en `pending_human_review`; no se inyectan
automáticamente en `staff_clefs` ni resuelven alturas. El operador confirma
el contexto con `--staff-clefs`.

## Resultado en «Clamaré a Dios - Coro»

La capa vectorial de las tres páginas contiene 20 glifos de clave en
`RepriseSpecialStd`: 10 candidatos treble y 10 bass. Cada uno se asocia de
forma única a uno de los 20 pentagramas por proximidad vertical (distancia
observada aproximada de 0.9 a 19 puntos, con límite de 30). Esto valida el
anclaje geométrico para este PDF concreto, no el mapa tipográfico universal
ni la detección de claves en partituras escaneadas.
