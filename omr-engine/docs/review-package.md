# Paquete de revisión visual humana

El módulo `review_package.py` convierte el `analysis.json` de la CLI OMR en
un paquete de trabajo para revisar candidatos visuales. Conserva la referencia
a los overlays PNG creados durante el análisis, la página, el pentagrama,
la caja y posición de cada cabeza, y las hipótesis rítmicas relacionadas.

## Generar el paquete

```bash
palermo-omr-dataset prepare-review omr-output/analysis.json \
  --score-id score-01 \
  --output review/score-01-review.json
```

La CLI produce tres overlays PNG por página: cabezas rellenas, cabezas huecas y
un overlay geométrico combinado para silencios/arcos, puntillos, vigas, barras,
sistemas e intervalos de compás. El overlay geométrico diferencia familias por
color y etiqueta las formas como candidatas; los colores no son puntuaciones
de confianza ni validaciones. El paquete incluye sus nombres para abrirlos junto
al PDF original.

El paquete agrupa por página:
- cabezas rellenas y huecas como familias independientes;
- hipótesis rítmicas e interpretaciones candidatas relacionadas por índice;
- candidatos de silencios, ligaduras/arcos, puntillos y barras;
- grupos de vigas, agrupaciones de barras y barras compartidas entre pentagramas;
- sistemas de pentagramas e intervalos geométricos entre barras que podrían ser compases;
- etiquetas musicales impresas extraídas de la capa de texto PDF, conservando asociaciones ambiguas/no asignadas;
- evidencias de identidad que combinan etiquetas y llaves/corchetes, vinculadas a los pentagramas correspondientes y aún pendientes de revisión.
- nombres de los overlays para consultar la evidencia visual original.

Las relaciones geométricas se guardan como candidatos independientes dentro de
`other_candidates`, con su familia, datos originales y `related_candidate_ids`
cuando la relación se puede resolver con índices válidos. Los pentagramas se
exponen en `staff_candidates`; las referencias usan IDs como
`p1-staff-1` y `p1-filled_notehead-1`. Los puntillos se vinculan a la cabeza
rellena que el detector propone como asociada y a su pentagrama; los silencios,
arcos y barras se vinculan al pentagrama indicado por su candidato geométrico. Los índices fuera de rango o booleanos
se rechazan, en lugar de crear vínculos rotos. Las etiquetas asociadas y las
observaciones de identidad se vinculan a los IDs de pentagrama; las etiquetas
ambiguas o sin asignar se conservan sin inventar una relación. No se interpretan como
agrupaciones musicales confirmadas ni como numeración definitiva de compases.
Las etiquetas PDF extraídas también se delimitan en el overlay geométrico como `LABEL?`; sus coordenadas de texto PDF se escalan al DPI de renderizado. El recuadro identifica la región textual, no certifica su asociación con un pentagrama.
Las evidencias de identidad mantienen el origen `visual_candidate`: no crean
partes, instrumentos, manos de piano ni voces SATB confirmadas.
Cada elemento conserva `review_status: pending` y `decision: null` y no se
confirma automáticamente ninguna relación.

Cada candidato empieza con `review_status: pending` y `decision: null`.
La herramienta no convierte una posición diatónica en altura MIDI, no decide
clave ni armadura, no asigna voces ni duraciones confirmadas y no crea eventos
ScoreEvent. Las hipótesis de duración se conservan como evidencia, nunca como
verdad musical.

## Paso siguiente de la revisión

El revisor consulta el PDF y los overlays y registra sus decisiones en el
paquete de trabajo. Los eventos de referencia se importan por separado al
manifiesto del corpus mediante `import-events`, con compás, voz, altura MIDI,
ataque y duración explícitos. Solo después de revisar cada evento se puede
solicitar la aprobación humana del documento.

Este paquete es una interfaz de intercambio JSON, no una interfaz gráfica
interactiva. Los PNG referenciados deben permanecer junto al `analysis.json`
o copiarse conservando sus nombres para que los pueda abrir la herramienta
de revisión elegida. El overlay geométrico es una guía de localización, no
sustituye la inspección de los píxeles originales ni el PDF.
