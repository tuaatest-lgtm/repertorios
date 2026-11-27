# Estado y porcentaje de avance del motor OMR Palermo

**Corte:** 27 de noviembre de 2026  
**Rama:** `feature/omr-propio-palermo`  
**Objetivo medido:** motor OMR propio que convierta partituras en eventos musicales polifónicos estructurados y verificables.  
**Fuera del alcance:** integración con Sonoro, publicación, despliegue o cambios al reproductor; requieren autorización independiente.

## Indicador general

- **Avance estimado anterior:** 73%
- **Avance estimado actual:** 74%
- **Variación:** +1 punto porcentual
- **Trabajo restante estimado:** 26%

El indicador es una estimación de madurez del proyecto por hitos verificables. No representa porcentaje de código escrito ni precisión musical medida. El incremento de este corte reconoce la continuidad de rangos de sección entre páginas, su exportación global y su conservación en el paquete de revisión. La prueba de continuidad es sintética; no equivale a validación musical real. Esta ejecución no equivale a una evaluación contra anotación humana ni demuestra exactitud de transcripción.

## Evolución por aspecto

| Aspecto | Anterior | Actual | Evidencia del cambio |
|---|---:|---:|---|
| Detección geométrica y símbolos | 58% | 59% | La ejecución real reveló demasiados candidatos a silencio; se añadieron filtros y el conteo bajó de 680 a 140 sin cambiar los demás detectores. |
| Modelo rítmico y polifónico | 75% | 75% | Sin cambio: el modelo temporal existe, pero aún falta validarlo desde partituras reales completas. |
| Paquete de revisión humana | 97% | 98% | El resumen del paquete contabiliza explícitamente compases globales y rangos de sección pendientes, además de conservar sus coordenadas y referencias. |
| Evidencia visual y overlays | 91% | 92% | Se inspeccionaron los overlays generados en las tres páginas reales y se documentaron las principales confusiones visuales. |
| Corpus anotado y métricas reales | 25% | 25% | Sin cambio: no hay aún un corpus representativo anotado y medido. |
| Validación integral con partituras | 0% | 10% | Primera ejecución reproducible sobre tres páginas reales y revisión visual de salidas; aún no hay anotación de referencia ni métricas de precisión/recuperación. |
| Modelo de identidad de pentagramas | 59% | 61% | Se unifican etiquetas impresas y marcas de agrupación en evidencia por página, sin crear asignaciones automáticas. |
| Estructura de secciones musicales | 62% | 63% | La construcción de rangos globales excluye encabezados superiores repetidos entre páginas y rótulos del margen superior sin ancla musical geométrica. |

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
- Se añadió una primera ancla local entre cada marca de sección y el intervalo geométrico entre barras más cercano del pentagrama candidato. Se conserva el índice de compás local al pentagrama, la posición relativa dentro del intervalo y la distancia; aún no se trata como numeración global ni como compás confirmado.
- La suite completa pasó en [45937807139](https://github.com/tuaatest-lgtm/repertorios/actions/runs/45937807139), commit `1fada1449e67c680f7fc12c922a0da10a8282246`, con **340 pruebas aprobadas**. La integración de la CLI también pasó en [45937789485](https://github.com/tuaatest-lgtm/repertorios/actions/runs/45937789485), commit `b730937a2156337238767cf2cd766dd83e4c9069`, con el mismo total.
- Límite explícito: el enlace global usa el orden de páginas y el orden de marcas detectadas; no reconstruye todavía los compases globales ni sus límites exactos. La asociación letra-marca sigue basada en anchos geométricos candidatos. Los rótulos deben estar en la capa de texto PDF; no hay OCR.
- Se añadieron pruebas de continuidad entre páginas, páginas intermedias sin marcas, ordenación independiente del orden de entrada y rangos abiertos. CI exacta de la rama: ejecución [45937522902](https://github.com/tuaatest-lgtm/repertorios/actions/runs/45937522902), commit `617870de9fe35193b36ef8ee59ee729e76457521`, resultado exitoso: **338 pruebas aprobadas**.


- Se endureció la conciliación de intervalos globales: un mismo pentagrama ya no puede aportar dos intervalos al mismo clúster de compás candidato. Esto evita fusionar intervalos locales próximos del mismo pentagrama por tolerancias geométricas; una prueba sintética verifica que dos pentagramas paralelos formen dos compases globales distintos con soporte de ambos.
- El paquete de revisión ahora resume por separado la cantidad total y pendiente de compases globales candidatos y rangos globales de sección. El contador general de cabezas/otros candidatos mantiene su significado anterior. Se añadió una prueba que distingue rangos pendientes de rangos ya aceptados.
- Se añadió `build_global_measure_sequence`: ordena intervalos geométricos por página, sistema y posición horizontal; agrupa intervalos de pentagramas distintos cuando sus centros se alinean dentro de una tolerancia proporcional a su anchura. Exporta ordinal global provisional, soporte de pentagramas y mapa de referencias local→global.
- La CLI incorpora `global_measure_sequence` en `analysis.json` y adjunta a cada ancla de sección su ordinal global candidato. Las referencias locales siguen disponibles para rastrear el origen.
- La secuencia no fuerza intervalos sin barras detectadas y separa sistemas geométricos; no reconoce aún anacrusas, compases parciales, barras omitidas ni compases métricos reales. Los ordinales son coordenadas de revisión, no números de compás definitivos.
- Pruebas sintéticas verifican conciliación de pentagramas alineados, separación de sistemas, orden de páginas fuera de secuencia y exclusión de intervalos sin sistema. CI de la rama: ejecución [45938579297](https://github.com/tuaatest-lgtm/repertorios/actions/runs/45938579297), commit `52ce0812bb6c737063c3400d7800f7e055c0ae7f`, **342 pruebas aprobadas**.
- El paquete de revisión valida ahora la estructura de los datos globales antes de entregarlos: exige objetos para cada compás y rango, referencias locales/globales con forma válida y extremos de inicio/final coherentes. Se añadieron casos negativos para impedir que un paquete incompleto se presente como revisable.
- Se añadieron validaciones de integridad para la secuencia global: no acepta números de página duplicados, identificadores de sistema repetidos ni un mismo pentagrama asignado simultáneamente a dos sistemas. Las pruebas verifican que esos datos ambiguos se rechacen en vez de generar ordinales globales engañosos.
CI de endurecimiento de anclas y límites: ejecución [45940100932](https://github.com/tuaatest-lgtm/repertorios/actions/runs/45940100932), commit `ec3dcad29125e854f2bb9f29bea12e9b243d54c3`, **354 pruebas aprobadas**. Una primera prueba usó una distancia vertical dentro del umbral definido; se corrigió el dato de prueba para representar un rótulo realmente lejano y la ejecución completa pasó.
CI de robustez de agrupación por pentagrama: ejecución [45939428989](https://github.com/tuaatest-lgtm/repertorios/actions/runs/45939428989), commit `9bfbb1d916e2c309b1a0b2af07fbafaad2c2a84a`, **345 pruebas aprobadas**. CI de resumen de revisión humana: ejecución [45939505336](https://github.com/tuaatest-lgtm/repertorios/actions/runs/45939505336), commit `3e53dfbedecb0e44f8b6d49bd51791a3f7065351`, **346 pruebas aprobadas**. CI de integridad de páginas/sistemas: ejecución [45939606630](https://github.com/tuaatest-lgtm/repertorios/actions/runs/45939606630), commit `93041688d942adb78491924d7f6d6e218fbaeabd`, **348 pruebas aprobadas**. La validación estructural del paquete global y sus fixtures quedó aprobada en [45939770977](https://github.com/tuaatest-lgtm/repertorios/actions/runs/45939770977), commit `cc9edf7145209fe63e813366582bc8043b0fd499`, **351 pruebas aprobadas**. Dos ejecuciones intermedias detectaron que una prueba de resumen no incluía los extremos obligatorios del rango; el fixture se corrigió y la suite completa pasó. La primera ejecución intermedia del cambio de resumen detectó una expectativa de prueba desactualizada; se corrigió en el commit de prueba posterior y la suite completa pasó.
\n\n- El análisis real de `Clamaré a Dios - Coro` mostró que la palabra `Coro` repetida en la franja superior de las páginas 2 y 3 se estaba interpretando como nuevas secciones, y que un rótulo superior sin ancla podía abrir un rango falso. Se añadieron dimensiones de página a las marcas y una regla conservadora: encabezados repetidos en la misma posición superior y rótulos del margen superior sin ancla se conservan como candidatos locales, pero no dividen los rangos globales.
- La nueva ejecución de `Clamaré a Dios - Coro.pdf` a 300 DPI completó las tres páginas sin error. Los marcadores locales siguen siendo 6, pero los rangos globales bajan de 6 a 3 al retirar tres falsos límites de encabezado. Se conservan 373 intervalos globales candidatos y los límites de sección resultantes incluyen referencias de compás global y posiciones fraccionales. Esto es una comprobación de comportamiento en una partitura real, no una confirmación de precisión musical; las posiciones siguen pendientes de revisión humana.
- CI de filtrado conservador de encabezados: ejecución [45940705719](https://github.com/tuaatest-lgtm/repertorios/actions/runs/45940705719), commit `a2d6cba1dc3154d44a44e416c7901a83d8216df9`, **361 pruebas aprobadas**.
- `build_global_measure_sequence` valida ahora cada intervalo local antes de agruparlo: exige índices válidos, coordenadas finitas, límites ordenados y anchura positiva; rechaza duplicados del mismo pentagrama/compás para no inventar compases globales a partir de entradas repetidas. Pruebas negativas cubren intervalos duplicados, `NaN`, anchura cero y límites invertidos.
- CI de validación geométrica de intervalos: ejecución [45940192821](https://github.com/tuaatest-lgtm/repertorios/actions/runs/45940192821), commit `e3681415e97dc41aced6a2f4f12de7100db28e1c`, **358 pruebas aprobadas**.
- La asociación de rótulos con intervalos ahora impone también una distancia vertical máxima de 12 espacios del pentagrama. Así evita vincular encabezados o textos alejados al pentagrama más cercano por el solo hecho de que sea el único candidato disponible. La tolerancia es conservadora y requiere validación con partituras anotadas.
- `resolve_section_range_boundaries` trabaja ahora sobre copias independientes de los rangos, por lo que no modifica las estructuras recibidas. También descarta posiciones fraccionales no finitas y valida la estructura básica del mapa de compases globales. Pruebas específicas cubren la distancia vertical, la ausencia de mutaciones y valores `NaN`.
- Se añadió `resolve_section_range_boundaries`: para cada inicio y final de sección selecciona la mejor ancla disponible, vincula el intervalo con el ordinal global provisional y conserva la fracción horizontal. Distingue posición dentro del compás candidato, antes/después y coincidencia con sus extremos; no confunde una marca textual con una barra musical.
- La CLI incorpora estas coordenadas en `global_section_range_candidates`. El paquete de revisión humana ahora conserva también `global_measure_sequence`, para que el revisor pueda consultar el mapa global y las referencias locales originales.
- Las pruebas verifican posiciones parciales, extremos exactos, límites sin ancla y conservación de la secuencia en el paquete de revisión. CI de la rama: ejecución [45939141059](https://github.com/tuaatest-lgtm/repertorios/actions/runs/45939141059), commit `e32775b625c34525bbfdf5466d9f26d1b7827fcd`, **344 pruebas aprobadas**.
- Precaución: la posición se deriva del centro del rótulo y del intervalo geométrico candidato. No demuestra el punto musical exacto donde comienza o termina la sección. La revisión humana sigue siendo obligatoria.
\n## Límites que siguen abiertos

- Una llave detectada no demuestra por sí sola que dos pentagramas sean piano ni identifica las manos.
- Un corchete o trazo vertical no confirma que los pentagramas pertenezcan a una parte instrumental o vocal.
- La extracción de etiquetas impresas y la geometría todavía requieren revisión conjunta; algunos PDF no contienen texto seleccionable.
- No se ha demostrado precisión/recall de cabezas, alturas, duraciones, silencios, ligaduras ni asignación SATB en un corpus real anotado.
- Las pruebas aprobadas son pruebas de software, no una certificación de transcripción musical. La ejecución real tampoco es todavía una validación cuantitativa: no hay eventos anotados de referencia para medir precisión/recuperación.

## Proyección de hitos pendientes

| Próximo hito | Aporte estimado al avance global | Condición para reconocerlo |
|---|---:|---|
| Validar ordinales globales contra compases musicales anotados y resolver límites parciales | +1 a 2 pp | Comparar la secuencia geométrica con referencias humanas; corregir anacrusas, barras omitidas y cambios de sistema. |
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
