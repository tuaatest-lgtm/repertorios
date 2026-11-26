# Revisión exploratoria de marcas de agrupación

Esta revisión comprueba el comportamiento geométrico en partituras reales. No es un conjunto de referencia anotado y no permite calcular precisión, exhaustividad ni una tasa de falsos positivos.

## Partituras revisadas

| Partitura | Páginas | Candidatos de llave curva | Observación |
|---|---:|---:|---|
| Brand New Hallelujah | 20 | 26 en 14 páginas | En las páginas 1, 2, 12 y 13 revisadas visualmente, los recuadros candidatos coinciden con llaves curvas impresas junto a pares de pentagramas. |
| Clamaré a Dios - Coro | 3 | 0 | No produjo candidatos de llave curva. |
| ACC-001 - PDF - CORO | 2 | 0 | No produjo candidatos de llave curva. |

El barrido se realizó con renderizado a 180 dpi y las reglas geométricas actuales de detección de cinco líneas, separación entre pares adyacentes y forma curva. Los conteos son propuestas visuales, no identificaciones confirmadas.

## Interpretación y límites

- La presencia de candidatos en la primera partitura y la ausencia en las dos partituras corales es compatible con la distinción visual entre llaves de sistemas de acompañamiento y pentagramas vocales separados.
- Esto no demuestra que los pentagramas candidatos sean de piano. Tampoco demuestra que todas las voces corales estén correctamente separadas o detectadas.
- Solo se revisaron visualmente algunos ejemplos positivos; no se anotaron manualmente todas las páginas ni todos los símbolos.
- No se midieron falsos negativos, por lo que la ausencia de candidatos no prueba que no existan llaves.
- La geometría puede variar según editorial, resolución, escaneo y tipografía. El umbral actual no debe considerarse universal.

Por estas razones, los resultados no se conectan todavía al CLI, no crean asignaciones automáticas de partes o voces y no se envían al reproductor.
