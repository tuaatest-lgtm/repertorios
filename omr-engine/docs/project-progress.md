# Estado y porcentaje de avance del motor OMR Palermo

**Corte:** 27 de noviembre de 2026  
**Rama:** `feature/omr-propio-palermo`  
**Objetivo medido:** motor OMR propio que convierta partituras en eventos musicales polifónicos estructurados y verificables.  
**Fuera del alcance:** integración con Sonoro, publicación, despliegue o cambios al reproductor; requieren autorización independiente.

## Indicador general

- **Avance estimado anterior:** 69%
- **Avance estimado actual:** 70%
- **Variación:** +1 punto porcentual
- **Trabajo restante estimado:** 30%

El indicador es una estimación de madurez del proyecto por hitos verificables. No representa porcentaje de código escrito ni precisión musical medida. El incremento de este corte reconoce la continuidad de rangos de sección entre páginas, su exportación global y su conservación en el paquete de revisión. La prueba de continuidad es sintética; no equivale a validación musical real. Esta ejecución no equivale a una evaluación contra anotación humana ni demuestra exactitud de transcripción.

## Evolución por aspecto

| Aspecto | Anterior | Actual | Evidencia del cambio |
|---|---:|---:|---|
| Detección geométrica y símbolos | 58% | 59% | La ejecución real reveló demasiados candidatos a silencio; se añadieron filtros y el conteo bajó de 680 a 140 sin cambiar los demás detectores. |
| Modelo rítmico y polifónico | 75% | 75% | Sin cambio: el modelo temporal existe, pero aún falta validarlo desde partituras reales completas. |
| Paquete de revisión humana | 93% | 95% | El paquete incorpora etiquetas impresas y evidencias combinadas de identidad, enlazadas con los pentagramas. |
| Evidencia visual y overlays | 91% | 92% | Se inspeccionaron los overlays generados en las tres páginas reales y se documentaron las principales confusiones visuales. |
| Corpus anotado y métricas reales | 25% | 25% | Sin cambio: no hay aún un corpus representativo anotado y medido. |
| Validación integral con partituras | 0% | 10% | Primera ejecución reproducible sobre tres páginas reales y revisión visual de salidas; aún no hay anotación de referencia ni métricas de precisión/recuperación. |
| Modelo de identidad de pentagramas | 59% | 61% | Se unifican etiquetas impresas y marcas de agrupación en evidencia por página, sin crear asignaciones automáticas. |
| Estructura de secciones musicales | 20% | 35% | Los rangos candidatos ya se enlazan entre páginas y se conservan en el paquete de revisión; los límites exactos de compás siguen pendientes. |

Los porcentajes por aspecto son estimaciones independientes y no se deben sumar ni promediar directamente para reconstruir el indicador general.

## Trabajo verificado en este corte

- La CLI principal ejecuta `detect_staff_grouping_mark_candidates` para cada página y guarda `staff_grouping_mark_candidates` y su contador.
- El overlay geométrico representa las marcas candidatas como `BRACE?`, `BRACKET?` o `GROUP?`; no las presenta como relaciones musicales confirmadas.
- El overlay también delimita las etiquetas de texto PDF con `LABEL?`, convirtiendo `bbox_pdf` a píxeles mediante el DPI de renderizado. Se añadieron pruebas para DPI 72 y 144.
- Se añadió una prueba de integración de CLI con un PDF sintético generado en la propia prueba: detecta una etiqueta `Soprano`, exporta su evidencia y comprueba que el paquete de revisión la conserve. Esto verifica el recorrido del software, no la precisión sobre partituras reales.
- La inspección de la capa de texto del PDF `Clamaré a Dios - Coro` (3 páginas) encontró 21 líneas con la letra aislada `B` en posiciones propias de cifrado/partitura y un marcador editorial `[B]`. Se cambió el detector para aceptar `S/A/T/B` solo si el texto es literalmente esa letra y está dentro del 12% izquierdo de la página; se añadieron pruebas para `[B]` y `B` en zona de acordes.
- Se ejecutó el motor Palermo completo sobre `Clamaré a Dios - Coro.pdf` a 300 DPI, usando una copia del código de la rama obtenida desde un artefacto de CI. La salida contiene 3 páginas y 20 pentagramas candidatos (8 + 8 + 4), coincidentes con el recuento geométrico inspeccionado previamente.
- Primera ejecución: 564 cabezas rellenas, 5 huecas, 33 grupos de vigas, 14 puntillos, 680 formas candidatas a silencio, 191 arcos, 400 barras de compás y 373 intervalos entre barras. La inspección visual reveló demasiados candidatos de silencio sobre texto y otros trazos.
- Tras aplicar filtros conservadores (centro dentro del pentagrama, compactación mínima y exclusión de componentes superpuestos con cabezas detectadas), se repitió la ejecución: las formas candidatas a silencio bajaron de 680 a 140 (reducción del 79,4% en cantidad de candidatos); 85 de las 140 recibieron solo una familia geométrica sugerida. No es una medición de precisión: algunas formas válidas pueden haberse descartado y aún hay candidatos falsos.
- En este PDF la CLI no encontró etiquetas del vocabulario actual ni marcas de agrupación de pentagramas; palabras como `Coro` y `Voz` no están en el vocabulario, por lo que no se identificaron automáticamente partes o voces.
- El paquete de revisión humana incluye la familia `staff_grouping_mark`, mantiene cada candidato pendiente y valida los índices de pentagrama asociados.
- `staff_grouping_adapter` convierte marcas curvas, corchetes y trazos verticales en evidencias de identidad ligadas a cada pentagrama. La evidencia mantiene `source=visual_candidate`; no crea partes, voces ni asignaciones.
- `identity_evidence.build_page_identity_evidence` combina la evidencia de etiquetas impresas y marcas de agrupación por página. La CLI incorpora etiquetas extraíbles desde el texto PDF y guarda candidatos y evidencias en `analysis.json`.
- El paquete de revisión conserva las etiquetas y evidencias de identidad, valida sus referencias a pentagramas y las mantiene pendientes.
- Se añadieron pruebas para la integración en overlay y paquete de revisión, incluidos índices inexistentes y duplicados.
- CI del recorrido CLI/overlay/revisión: ejecución [45903752937](https://github.com/tuaatest-lgtm/repertorios/actions/runs/45903752937), commit `45eee72cef309f49cc376594f57ef679afabf7c8`, resultado exitoso: **312 pruebas aprobadas**.
- CI del adaptador de evidencia: ejecución [45903872219](https://github.com/tuaatest-lgtm/repertorios/actions/runs/45903872219), commit `afb236bd3c109c766e6853c72d34d50303954826`, resultado exitoso: **317 pruebas aprobadas**.
- CI de evidencia combinada y paquete de revisión: ejecución [45933249039](https://github.com/tuaatest-lgtm/repertorios/actions/runs/45933249039), commit `0079fb041dcc65c3da2f7b601e8607418911bcf9`, resultado exitoso: **322 pruebas aprobadas** en ese corte. La integración de CLI quedó aprobada también en [45933208974](https://github.com/tuaatest-lgtm/repertorios/actions/runs/45933208974). Tras ampliar la validación de estados de etiqueta y corregir la expresión de una prueba, la rama completa volvió a pasar: ejecución [45933376574](https://github.com/tuaatest-lgtm/repertorios/actions/runs/45933376574), commit `27b349b96820452600d17db77757270aa70b10bb`, **325 pruebas aprobadas**. La nueva visualización de etiquetas pasó también en ejecución [45933685409](https://github.com/tuaatest-lgtm/repertorios/actions/runs/45933685409), commit `333484f815051bdb8aea7011c490b5abc6069271`, con **327 pruebas aprobadas**. La prueba de integración CLI con PDF sintético pasó en [45933805391](https://github.com/tuaatest-lgtm/repertorios/actions/runs/45933805391), commit `fa608b216d1035ea835f75aeeee3299e997e1871`, elevando la suite a **328 pruebas aprobadas**. La corrección de abreviaturas SATB pasó en [45934028737](https://github.com/tuaatest-lgtm/repertorios/actions/runs/45934028737), commit `4ba76e0ae20f6de5b6105db33d3c94a1221e589a`, con **330 pruebas aprobadas**. Los filtros de silencios y la prueba de integración pasaron en [45934441387](https://github.com/tuaatest-lgtm/repertorios/actions/runs/45934441387), commit `5ae2eb2c6b5e8bcd909d9e1c848fe99802edb934`, con **333 pruebas aprobadas**.

- Se incorporó `section_structure.py`: extrae rótulos como CORO, ESTROFA, PUENTE, FINAL, INTRO y CODA desde la capa de texto PDF; reconoce letras aisladas a no más de un ancho medio de compás candidato y conserva la relación como identificador posible, no como voz SATB.
- La CLI exporta `section_marker_candidates`, `section_identifier_candidates` y `section_range_candidates`; las letras ya relacionadas con una sección se excluyen de la lista duplicada de etiquetas SATB. El paquete de revisión humana conserva las tres familias como pendientes.
- Los rangos locales se proponen entre marcas sucesivas y permiten límites dentro de sistemas. Se añadió `link_section_ranges_across_pages`: una marca en la página siguiente cierra el rango anterior, incluso si hay páginas intermedias sin marcas. El último rango queda abierto hasta el final de la partitura; el final de página no cierra la sección.
- La CLI exporta `global_section_range_candidates` y el paquete de revisión conserva esos rangos para revisión humana. Cada rango contiene página/posición de inicio, página/posición de final, extensión en páginas y estado pendiente.
- Límite explícito: el enlace global usa el orden de páginas y el orden de marcas detectadas; no reconstruye todavía los compases globales ni sus límites exactos. La asociación letra-marca sigue basada en anchos geométricos candidatos. Los rótulos deben estar en la capa de texto PDF; no hay OCR.
- Se añadieron pruebas de continuidad entre páginas, páginas intermedias sin marcas, ordenación independiente del orden de entrada y rangos abiertos. CI exacta de la rama: ejecución [45937522902](https://github.com/tuaatest-lgtm/repertorios/actions/runs/45937522902), commit `617870de9fe35193b36ef8ee59ee729e76457521`, resultado exitoso: **338 pruebas aprobadas**.

## Límites que siguen abiertos

- Una llave detectada no demuestra por sí sola que dos pentagramas sean piano ni identifica las manos.
- Un corchete o trazo vertical no confirma que los pentagramas pertenezcan a una parte instrumental o vocal.
- La extracción de etiquetas impresas y la geometría todavía requieren revisión conjunta; algunos PDF no contienen texto seleccionable.
- No se ha demostrado precisión/recall de cabezas, alturas, duraciones, silencios, ligaduras ni asignación SATB en un corpus real anotado.
- Las pruebas aprobadas son pruebas de software, no una certificación de transcripción musical. La ejecución real tampoco es todavía una validación cuantitativa: no hay eventos anotados de referencia para medir precisión/recuperación.

## Proyección de hitos pendientes

| Próximo hito | Aporte estimado al avance global | Condición para reconocerlo |
|---|---:|---|
| Delimitar compases y posiciones de inicio/final de cada sección | +1 a 2 pp | Vincular marcas con intervalos de compás por pentagrama/sistema y revisar límites parciales. |
| Ejecutar el motor sobre más partituras reales y revisar overlays | +1 a 2 pp | Ampliar el análisis a partituras de distinta edición y calidad; revisar los overlays y documentar fallos por familia. |
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
