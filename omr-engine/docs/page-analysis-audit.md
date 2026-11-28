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
