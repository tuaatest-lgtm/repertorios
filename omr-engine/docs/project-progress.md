# Estado y porcentaje de avance del motor OMR Palermo

**Corte:** 26 de noviembre de 2026  
**Rama:** `feature/omr-propio-palermo`  
**Objetivo medido:** motor OMR propio que convierta partituras en eventos musicales polifónicos estructurados y verificables.  
**Fuera del alcance:** integración con Sonoro, publicación, despliegue o cambios al reproductor; requieren autorización independiente.

## Indicador general

- **Avance estimado anterior:** 62%
- **Avance estimado actual:** 63%
- **Variación:** +1 punto porcentual
- **Trabajo restante estimado:** 37%

El indicador es una estimación de madurez del proyecto por hitos verificables. No representa porcentaje de código escrito ni precisión musical medida. El incremento de este corte reconoce que las marcas de agrupación de pentagramas ya recorren la CLI, el overlay y el paquete de revisión humana, con pruebas automatizadas aprobadas. No reconoce precisión musical nueva sobre partituras reales.

## Evolución por aspecto

| Aspecto | Anterior | Actual | Evidencia del cambio |
|---|---:|---:|---|
| Detección geométrica y símbolos | 55% | 56% | Las marcas de agrupación ya se ejecutan desde la CLI y quedan en el análisis por página. |
| Modelo rítmico y polifónico | 75% | 75% | Sin cambio: el modelo temporal existe, pero aún falta validarlo desde partituras reales completas. |
| Paquete de revisión humana | 90% | 92% | El paquete incorpora marcas de agrupación pendientes y valida sus referencias a pentagramas. |
| Evidencia visual y overlays | 85% | 88% | El overlay ahora representa llaves, corchetes y marcas verticales con etiquetas explícitas de candidato. |
| Corpus anotado y métricas reales | 25% | 25% | Sin cambio: no hay aún un corpus representativo anotado y medido. |
| Validación integral con partituras | 0% | 0% | Sin cambio: el motor todavía no se ha ejecutado y evaluado de extremo a extremo sobre el PDF coral de referencia en un entorno reproducible. |

Los porcentajes por aspecto son estimaciones independientes y no se deben sumar ni promediar directamente para reconstruir el indicador general.

## Trabajo verificado en este corte

- La CLI principal ejecuta `detect_staff_grouping_mark_candidates` para cada página y guarda `staff_grouping_mark_candidates` y su contador.
- El overlay geométrico representa las marcas candidatas como `BRACE?`, `BRACKET?` o `GROUP?`; no las presenta como relaciones musicales confirmadas.
- El paquete de revisión humana incluye la familia `staff_grouping_mark`, mantiene cada candidato pendiente y valida los índices de pentagrama asociados.
- Se añadieron pruebas para la integración en overlay y paquete de revisión, incluidos índices inexistentes y duplicados.
- CI: ejecución [45903752937](https://github.com/tuaatest-lgtm/repertorios/actions/runs/45903752937), commit `45eee72cef309f49cc376594f57ef679afabf7c8`, resultado exitoso: **312 pruebas aprobadas**.

## Límites que siguen abiertos

- Una llave detectada no demuestra por sí sola que dos pentagramas sean piano ni identifica las manos.
- Un corchete o trazo vertical no confirma que los pentagramas pertenezcan a una parte instrumental o vocal.
- La extracción de etiquetas impresas y la geometría todavía requieren revisión conjunta; algunos PDF no contienen texto seleccionable.
- No se ha demostrado precisión/recall de cabezas, alturas, duraciones, silencios, ligaduras ni asignación SATB en un corpus real anotado.
- Las pruebas aprobadas son pruebas de software, no una certificación de transcripción musical.

## Proyección de hitos pendientes

| Próximo hito | Aporte estimado al avance global | Condición para reconocerlo |
|---|---:|---|
| Ejecutar el motor sobre partituras reales y revisar overlays | +2 a 3 pp | Ejecución reproducible, archivos de salida inspeccionados y errores documentados. |
| Crear anotaciones humanas de un conjunto representativo | +3 a 5 pp | Partituras, páginas, pentagramas, voces y eventos revisados; manifiestos validados. |
| Medir precisión y recuperación por familia de símbolos y eventos | +3 a 5 pp | Informes calculados contra referencias humanas, no pruebas sintéticas. |
| Corregir errores principales y repetir medición | +4 a 6 pp | Comparación antes/después en el mismo corpus y regresión independiente. |
| Integrar y validar la polifonía completa | +6 a 9 pp | Voces simultáneas con ataques y duraciones independientes, incluidos acordes y silencios, comprobados en partituras reales. |

Estas cifras son proyecciones, no trabajo ya completado, y pueden variar según los resultados. No se sumarán automáticamente: los hitos pueden compartir trabajo y sus resultados deben comprobarse.

## Reglas de control

- Todo el desarrollo permanece en `feature/omr-propio-palermo`.
- No modificar `main`, el reproductor funcional ni producción.
- No integrar con Sonoro sin autorización expresa.
- No añadir servicios OMR externos ni presentar candidatos heurísticos como transcripción fiable.
- No aumentar el avance por documentación o cantidad de código solamente.
- Cada incremento debe indicar el cambio verificable, su evidencia y los límites que permanecen.
