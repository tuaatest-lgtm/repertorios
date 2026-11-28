# Auditoría de análisis de página

El comando `palermo-omr-audit` resume la cobertura geométrica y las hipótesis
rítmicas de un `analysis.json` multipágina. No requiere ni inventa etiquetas
de verdad de terreno.

```bash
palermo-omr-audit analysis.json audit-report.json --low-confidence 0.60
```

El informe incluye por página:
- cabezas rellenas y huecas, pentagramas, sistemas y regiones de compás;
- cabezas con cero, una o varias regiones de compás compatibles;
- plicas, figuras, haces y estados de interpretación rítmica;
- candidatos de silencios, ligaduras/arcos y puntillos;
- candidatos rítmicos por debajo del umbral de confianza.

## Auditoría de referencia: «Clamaré a Dios - Coro»

La revisión local del `analysis.json` de tres páginas obtuvo:

| Medida geométrica/candidata | Resultado |
|---|---:|
| Cabezas rellenas candidatas | 564 |
| Ubicación única en intervalo de compás | 563 |
| Ambiguas en frontera entre dos intervalos | 1 |
| Sin intervalo compatible | 0 |
| Candidatos rítmicos sin dirección de plica | 112 |
| Candidatos con duración desconocida | 112 |
| Grupos de haces candidatos | 33 |
| Formas de silencio candidatas | 140 |
| Formas de ligadura/arco candidatas | 191 |

La cobertura de ubicación única es 99.82% (563/564). La única ambigüedad
ocurre exactamente en el límite entre dos intervalos geométricos. Los 112
casos sin plica explican los 112 valores de duración desconocida en este
análisis; son una oportunidad de revisión, no 112 errores confirmados.

**Límite fundamental:** estas cifras no miden precisión ni recall musical.
Las regiones, cabezas, plicas, haces, silencios y arcos siguen siendo candidatos.
No validan altura, clave, armadura, alteraciones, figura, voz ni ejecución.


## Evaluación de cabezas contra glifos embebidos del PDF

Además de la cobertura de compases, se ejecutó la evaluación geométrica
`palermo-omr-pdf-glyph-evaluate` con la fuente `RepriseStd`, el glifo
`œ` (cabeza rellena) y tolerancia de 3 puntos. El glifo se verificó en la
capa vectorial del documento y su posición coincide visualmente con las
cabezas negras de la partitura.

| Página | Candidatos (rellenos + huecos) | Glifos de referencia | TP | FP | FN |
|---|---:|---:|---:|---:|---:|
| 1 | 200 | 155 | 150 | 50 | 5 |
| 2 | 275 | 275 | 257 | 18 | 18 |
| 3 | 94 | 104 | 87 | 7 | 17 |
| **Total** | **569** | **534** | **494** | **75** | **40** |

- Precisión geométrica: **86.82 %**
- Recall geométrico: **92.51 %**
- F1 geométrico: **89.57 %**

La evaluación usa emparejamiento de máxima cardinalidad entre centros de
candidatos y centros de glifos, con tolerancia de 3 puntos. Los falsos
positivos y negativos son discrepancias de localización frente a ese glifo
de referencia. No indican por sí mismos si una nota musical fue interpretada
correctamente. Esta medición no valida alturas, alteraciones, figuras,
duraciones, silencios, voces, compases ni reproducción.


### Sensibilidad al umbral de confianza

La evaluación también calcula una curva de filtrado por confianza, sin cambiar
el detector ni descartar candidatos del JSON original. En este PDF, usando solo
cabezas rellenas y el mismo glifo de referencia, el umbral 0.70 conserva los
494 emparejamientos verdaderos, reduce los candidatos de 564 a 549 y eleva F1
de 89.98% a 91.23%. El umbral 0.75 reduce aún más los falsos positivos, pero
pierde seis emparejamientos y produce F1 91.47%.

Estos umbrales se muestran como análisis de sensibilidad para este documento,
no como un valor universal ni como una modificación automática del motor.
La evaluación de referencia sigue limitada al glifo de cabeza rellena.


## Filtro opcional en el análisis

El CLI principal mantiene todos los candidatos por defecto. Para explorar el
umbral evaluado en esta partitura sin alterar el valor predeterminado:

```bash
palermo-omr "Clamaré a Dios - Coro.pdf" --output omr-output --min-notehead-confidence 0.70
```

El filtro se aplica solo a cabezas rellenas y queda registrado en cada página
como `notehead_confidence_filter`. Los candidatos descartados no se convierten
en falsos negativos del análisis original: esta opción es una vista filtrada
para revisión y comparación. El umbral debe recalibrarse con otros documentos
antes de usarlo como valor general.


## Evidencia visual de ritmo

El análisis principal genera ahora `page-NNN-rhythm-overlay.png` además de
los overlays de cabezas y geometría. Muestra la dirección y longitud de plicas
propuestas, la figura base, el número de haces candidato y la confianza
heurística. Los casos sin plica o sin duración quedan señalados como pendientes.
El overlay es una ayuda de revisión: no convierte ninguna hipótesis en una
figura confirmada.
