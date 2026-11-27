# Estado y porcentaje de avance del motor OMR Palermo

**Corte:** 26 de noviembre de 2026  
**Rama:** `feature/omr-propio-palermo`  
**Objetivo medido:** motor OMR propio que convierta partituras en eventos musicales polifónicos estructurados y verificables.  
**Fuera del alcance:** integración con Sonoro, publicación, despliegue o cambios al reproductor; requieren autorización independiente.

## Indicador general

- **Avance estimado anterior:** 64%
- **Avance estimado actual:** 65%
- **Variación:** +1 punto porcentual
- **Trabajo restante estimado:** 35%

El indicador es una estimación de madurez del proyecto por hitos verificables. No representa porcentaje de código escrito ni precisión musical medida. El incremento de este corte reconoce que las etiquetas musicales disponibles en la capa de texto PDF y las marcas de agrupación recorren la CLI, se unifican como evidencia por página y llegan al paquete de revisión humana con referencias verificadas a pentagramas. No reconoce precisión musical nueva sobre partituras reales ni OCR de páginas escaneadas.

## Evolución por aspecto

| Aspecto | Anterior | Actual | Evidencia del cambio |
|---|---:|---:|---|
| Detección geométrica y símbolos | 56% | 57% | La CLI extrae también etiquetas impresas desde la capa de texto PDF, además de las marcas de agrupación. |
| Modelo rítmico y polifónico | 75% | 75% | Sin cambio: el modelo temporal existe, pero aún falta validarlo desde partituras reales completas. |
| Paquete de revisión humana | 93% | 95% | El paquete incorpora etiquetas impresas y evidencias combinadas de identidad, enlazadas con los pentagramas. |
| Evidencia visual y overlays | 88% | 88% | Sin cambio: se conservan overlays candidatos, pero no se añadió una nueva familia visual en este corte. |
| Corpus anotado y métricas reales | 25% | 25% | Sin cambio: no hay aún un corpus representativo anotado y medido. |
| Validación integral con partituras | 0% | 0% | Sin cambio: el motor todavía no se ha ejecutado y evaluado de extremo a extremo sobre el PDF coral de referencia en un entorno reproducible. |
| Modelo de identidad de pentagramas | 59% | 61% | Se unifican etiquetas impresas y marcas de agrupación en evidencia por página, sin crear asignaciones automáticas. |

Los porcentajes por aspecto son estimaciones independientes y no se deben sumar ni promediar directamente para reconstruir el indicador general.

## Trabajo verificado en este corte

- La CLI principal ejecuta `detect_staff_grouping_mark_candidates` para cada página y guarda `staff_grouping_mark_candidates` y su contador.
- El overlay geométrico representa las marcas candidatas como `BRACE?`, `BRACKET?` o `GROUP?`; no las presenta como relaciones musicales confirmadas.
- El paquete de revisión humana incluye la familia `staff_grouping_mark`, mantiene cada candidato pendiente y valida los índices de pentagrama asociados.
- `staff_grouping_adapter` convierte marcas curvas, corchetes y trazos verticales en evidencias de identidad ligadas a cada pentagrama. La evidencia mantiene `source=visual_candidate`; no crea partes, voces ni asignaciones.
- `identity_evidence.build_page_identity_evidence` combina la evidencia de etiquetas impresas y marcas de agrupación por página. La CLI incorpora etiquetas extraíbles desde el texto PDF y guarda candidatos y evidencias en `analysis.json`.
- El paquete de revisión conserva las etiquetas y evidencias de identidad, valida sus referencias a pentagramas y las mantiene pendientes.
- Se añadieron pruebas para la integración en overlay y paquete de revisión, incluidos índices inexistentes y duplicados.
- CI del recorrido CLI/overlay/revisión: ejecución [45903752937](https://github.com/tuaatest-lgtm/repertorios/actions/runs/45903752937), commit `45eee72cef309f49cc376594f57ef679afabf7c8`, resultado exitoso: **312 pruebas aprobadas**.
- CI del adaptador de evidencia: ejecución [45903872219](https://github.com/tuaatest-lgtm/repertorios/actions/runs/45903872219), commit `afb236bd3c109c766e6853c72d34d50303954826`, resultado exitoso: **317 pruebas aprobadas**.
- CI de evidencia combinada y paquete de revisión: ejecución [45933249039](https://github.com/tuaatest-lgtm/repertorios/actions/runs/45933249039), commit `0079fb041dcc65c3da2f7b601e8607418911bcf9`, resultado exitoso: **322 pruebas aprobadas** en ese corte. La integración de CLI quedó aprobada también en [45933208974](https://github.com/tuaatest-lgtm/repertorios/actions/runs/45933208974). Tras ampliar la validación de estados de etiqueta y corregir la expresión de una prueba, la rama completa volvió a pasar: ejecución [45933376574](https://github.com/tuaatest-lgtm/repertorios/actions/runs/45933376574), commit `27b349b96820452600d17db77757270aa70b10bb`, **325 pruebas aprobadas**.

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
