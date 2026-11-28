# Palermo OMR Engine (desarrollo propio)

> **Relevo de trabajo:** antes de contribuir, lee [`AGENTS.md`](../AGENTS.md) y [`WORK_HANDOFF.md`](WORK_HANDOFF.md). El segundo archivo contiene el encargo concreto del siguiente turno y debe actualizarse al terminar cada intervención.

Motor OMR independiente para Palermo Music. Esta iteración implementa entrada PDF, preprocesamiento de páginas, detección geométrica inicial de pentagramas y propuestas de cabezas de nota.

**Estado:** prototipo geométrico 0.3.0. Incluye candidatos de cabezas, conversión de posición diatónica cuando la clave ya es conocida, análisis rítmico preliminar, grupos candidatos de barras compartidas, interpretación rítmica candidata y candidatos de puntillos, silencios, barras e intervalos de compás. Todo resultado requiere validación; no es una transcripción musical completa. No está integrado con el reproductor ni desplegado como servicio.


- **Ligaduras de prolongación candidatas**: `tie_candidates.py` cruza arcos geométricos con notas de igual altura, misma voz/pentagrama y continuidad temporal exacta. Solo propone; la suma de duraciones requiere confirmación humana de que el arco es tie y ambas notas tienen la misma escritura. No se conecta al reproductor. Ver `docs/tie-candidates.md`.


- **Silencios revisados por voz**: `rest_events.py` convierte candidatos geométricos en eventos temporales solo con confirmación humana de símbolo, duración, voz, compás y orden. Ver `docs/rest-events.md`.


- **Evaluación musical contra anotaciones humanas**: `event_evaluation.py` mide detección, inicio, tipo, alturas (incluidos acordes), duración y asignación de voz mediante emparejamiento uno a uno. Requiere anotaciones de referencia completas; las pruebas no miden precisión real del OMR. Ver `docs/event-evaluation.md`.
- **Corpus reproducible de anotaciones humanas**: `annotation_dataset.py` valida partituras, huellas SHA-256, particiones train/validation/test y eventos completos revisados; conserva fracciones exactas y bloquea borradores como ground truth. Ver `docs/annotation-dataset.md`.
- **Evaluación agregada del corpus**: `dataset_evaluation.py` calcula métricas micro por partición y conserva resultados por partitura; impide mezclar predicciones de train, validation y test. Ver `docs/dataset-evaluation.md`.
- **Flujo operativo de anotación**: `palermo-omr-dataset` registra PDFs, calcula SHA-256 y número de páginas, valida manifiestos y exige confirmación humana explícita para aprobar anotaciones. Ver `docs/annotation-workflow.md`.
- **Evaluación ejecutable desde CLI**: `palermo-omr-dataset evaluate` carga predicciones por partitura, aplica una partición revisada y escribe métricas agregadas y por documento. La CLI no inventa predicciones ni sustituye la revisión visual.
- **Paquete de revisión visual**: `palermo-omr-dataset prepare-review` transforma `analysis.json` en una lista de candidatos por página, enlaza hipótesis rítmicas y overlays, y mantiene todas las decisiones pendientes hasta revisión humana. Ver `docs/review-package.md`.
- **Revisión acotada por fragmento**: `palermo-omr-focus-review` extrae una página y pentagramas seleccionados de un paquete existente, conserva IDs y evidencia, y excluye relaciones que cruzan fuera del fragmento. El resultado permanece en borrador y nunca crea eventos ni ground truth. Ver `docs/focused-review.md`.


- **Seguimiento del proyecto**: `docs/project-progress.md` mantiene el porcentaje ponderado de avance, trabajo restante, alcance y criterios para actualizarlo.

## Integración con la aplicación

El contrato de integración HTTP v1, la separación entre navegador, worker Python y reproductor, y las puertas de seguridad están documentados en `docs/app-integration-contract.md`. Es una especificación; todavía no hay API desplegada ni conexión activa con Sonoro.

## Requisitos

- Python 3.11 o superior.
- Dependencias instalables con `pip install -e ".[dev]"`.

## Uso

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

pip install -e ".[dev]"
palermo-omr "partitura.pdf" --output "./omr-output" --dpi 300
```

El comando genera una imagen binarizada por página y un archivo `analysis.json` con:

- líneas horizontales candidatas;
- grupos geométricos de cinco líneas;\n- duración rítmica candidata por cabeza, con referencia al grupo de barras compartidas y estado explícito de ambigüedad o evidencia insuficiente;
- regiones propuestas como cabezas de nota;
- candidatos separados de cabezas huecas, guardados en `hollow_notehead_candidates` y no usados todavía para interpretar ritmo;
- posición diatónica relativa a la línea inferior del pentagrama (sin asignar todavía una letra o altura absoluta);
- puntuaciones heurísticas de confianza;
- hipótesis de relleno, plicas y barras horizontales de agrupación;
- candidatos de puntillos, formas que podrían corresponder a silencios (con sugerencias geométricas de familias de redonda/blanca y formas verticales), arcos candidatos a ligaduras y trazos verticales que podrían ser barras de compás;
- sistemas geométricos candidatos, separados por grandes saltos verticales entre pentagramas;
- agrupaciones de barras aproximadamente alineadas dentro de cada sistema candidato;
- clasificación visual preliminar de barras simples, dobles y finales candidatas;
- intervalos geométricos entre barras consecutivas del mismo pentagrama.

## Limitaciones conocidas

- Los trazos de barras, texto, ligaduras y otros símbolos pueden producir falsos positivos.
- Las cabezas de nota unidas a plicas o atravesadas por líneas pueden fragmentarse.
- La recuperación de dos cabezas desplazadas que se tocan aplica filtros de compacidad para no confundir vigas diagonales con notas; sigue siendo una hipótesis geométrica y requiere validación visual. Consulta `docs/notehead-detection.md`.
- La posición diatónica no equivale a una nota identificada: falta reconocer la clave y aplicar armadura y alteraciones desde la imagen.
- La sugerencia de familia de silencio es de confianza baja y no distingue todavía de forma fiable todos los tipos; cuartos, corcheas, semicorcheas, silencios compuestos y símbolos fragmentados requieren un clasificador más robusto.
- Los arcos detectados son candidatos visuales: no distinguen ligaduras de prolongación (tie) de ligaduras de expresión (slur), ni se enlazan todavía con cabezas de nota.
- Los grupos de barras compartidas son candidatos geométricos: requieren un trazo horizontal y plicas compatibles, pero no confirman por sí solos corcheas, semicorcheas, grupos irregulares, dirección de lectura ni voces. El análisis rítmico global sigue sin estar validado.
- La agrupación de sistemas es geométrica y heurística: no reconoce llaves, brackets, piano, coro SATB ni la función de cada pentagrama.
- La clasificación simple/doble/final es heurística y no reconoce aún puntos de repetición ni confirma la función musical de una barra.
- Los intervalos entre barras no incluyen los bordes externos que no fueron observados y no son compases musicales validados.
- Las partituras complejas deben evaluarse con ejemplos reales y anotaciones de referencia.
- No se debe enviar esta salida al reproductor.

## Próximas fases

1. Evaluación y calibración con partituras reales vectoriales y escaneadas.
2. Validar sistemas y barras simples/dobles/finales en partituras reales; después abordar puntos de repetición, saltos de sistema y continuidad entre páginas.
3. Calibrar los candidatos rítmicos con partituras reales anotadas y resolver grupos irregulares, barras parciales, ligaduras y puntillos.\n4. Clasificación robusta de símbolos: claves, armaduras, figuras y silencios.
5. Interpretación temporal polifónica y exportación MusicXML.
5. Revisión visual humana y, solo tras aviso y aprobación, diseño del adaptador aislado hacia el motor Sonoro de Palermo.

## Aritmética exacta de duraciones

Se añadió `palermo_omr.duration_math` para calcular valores de figuras, puntillos simples y múltiples, y sumar duraciones de notas cuya ligadura de prolongación ya haya sido confirmada. Utiliza fracciones exactas para evitar deriva de redondeo. No reconoce símbolos ni decide ligaduras a partir de imágenes; consulta `docs/duration-math.md`.

## Validación métrica preliminar

Se añadió `palermo_omr.measure_validation`, una capa matemática independiente que compara duraciones ya interpretadas con el valor esperado del indicador de compás. Distingue compases completos, incompletos, excedidos y posibles anacrusas. No reconoce figuras desde la imagen y todavía no se conecta al CLI ni al reproductor. Consulta `docs/measure-validation.md`.

## Conversión de geometría a estructura

El módulo score_geometry transforma sistemas y regiones candidatos en una estructura de página, conserva pentagramas no agrupados y deja las asignaciones de parte y voz sin resolver. No infiere piano, coro ni roles musicales. Consulta docs/score-geometry.md.

## Estructura musical explícita

Se añadió `palermo_omr.score_structure`, un modelo validable que separa sistemas, pentagramas, partes, voces, asignaciones y regiones de compás. Permite representar dos pentagramas de piano asociados a una misma parte y flujo, o varias voces sobre un pentagrama, sin deducir relaciones por posición. Las asignaciones pueden permanecer sin resolver o ambiguas. No detecta automáticamente estos elementos desde la imagen. Consulta `docs/score-structure.md`.

## Geometría de compases

Consulta `docs/measure-layout.md` para conocer cómo se detectan y agrupan las barras candidatas y qué limitaciones tienen los intervalos resultantes.


## Inferencia de una duración faltante

Se añadió `palermo_omr.duration_completion` para calcular el residuo métrico de un compás con fracciones exactas. Solo asigna ese residuo a una nota cuando exactamente un evento de la misma voz y compás permanece sin duración; si faltan varios, informa el residuo sin inventar cómo repartirlo. Requiere que silencios, puntillos, tresillos y ligaduras estén contabilizados previamente. No está conectado todavía al análisis de imágenes ni al CLI. Consulta `docs/duration-completion.md`.


## Balance rítmico por voz y compás

Se añadió `palermo_omr.voice_measure` para calcular el balance de cada voz o flujo rítmico por separado. Rechaza mezclar voces o compases, contabiliza silencios y solo asigna el residuo si queda exactamente un evento sin duración. No descubre todavía la voz ni el compás desde la imagen. Consulta `docs/voice-measure.md`.


## Documento multipágina y continuidad explícita

Se añadió `palermo_omr.score_document` para ordenar estructuras de página, enumerar sistemas en secuencia y registrar continuidades entre pentagramas solo cuando existan como propuestas, ambigüedades o confirmaciones con evidencia. La numeración global de compases también es explícita y opcional: no se deduce sumando intervalos geométricos locales. Consulta `docs/score-document.md`.


## Evidencia para identificar pentagramas

Se añadió `palermo_omr.staff_identity` para registrar etiquetas, claves, llaves, corchetes y otras evidencias, y formular propuestas de parte o voz. Las identidades solo pueden confirmarse con revisión humana explícita y evidencia asociada. El módulo no realiza todavía OCR ni reconocimiento automático de claves, llaves, piano o voces SATB. Consulta `docs/staff-identity.md`.


## Candidatos de marcas de agrupación

Se añadió `palermo_omr.staff_grouping` para proponer trazos verticales largos en el margen izquierdo de sistemas con varios pentagramas marcar corchetes rectos candidatos por sus dos remates horizontales y proponer llaves curvas por su contorno lateral. El agrupamiento vertical usa 7.0 veces el espaciado entre líneas por defecto; la búsqueda de llaves curvas se hace por pares adyacentes y admite hasta 8.0. Ninguna etiqueta confirma que los pentagramas pertenezcan al piano o al coro. Consulta `docs/staff-grouping.md` y la revisión exploratoria en `docs/staff-grouping-validation.md`.


## Etiquetas musicales impresas

El módulo `palermo_omr.printed_labels` extrae etiquetas conocidas desde la capa de texto PDF y propone una asociación geométrica con el pentagrama más cercano. Reconoce nombres completos y abreviaturas SATB aisladas (`S`, `A`, `T`, `B`), sin confirmar asignaciones de partes o voces. No realiza OCR de partituras escaneadas. Consulta `docs/printed-labels.md` y los resultados exploratorios, incluido MAR-007, en `docs/printed-labels-validation.md`.


## Regiones rasterizadas candidatas a texto

El módulo `palermo_omr.text_regions` propone cajas de regiones tipo texto en una franja estrecha del margen izquierdo y en la cabecera superior. No lee palabras ni las clasifica como voces o instrumentos; puede incluir títulos, letras y símbolos residuales. Las asociaciones son geométricas y pueden quedar sin asignar o ambiguas. Consulta `docs/text-regions.md`.


## Evaluación de regiones de texto

Se añadió `palermo_omr.text_region_evaluation` para comparar cajas geométricas del detector con anotaciones humanas mediante IoU y emparejamiento uno a uno. Calcula TP, FP, FN, precisión, cobertura, F1 e IoU media; no realiza OCR ni interpreta etiquetas. Todavía no existe un corpus real anotado, por lo que el módulo permite preparar la medición pero no demuestra el rendimiento del detector. Consulta `docs/text-region-evaluation.md`.


## Agrupación de ataques y acordes candidatos

El módulo `palermo_omr.rhythmic_event_groups` propone agrupar cabezas cercanas
del mismo pentagrama en posibles ataques/acordes, conserva ambigüedades cuando
las plicas o duraciones no concuerdan y nunca asigna voces por sí solo. La
posición horizontal solo sirve para proponer el agrupamiento; el tiempo musical
debe derivarse después a partir de duraciones conocidas por voz. Consulta
`docs/rhythmic-event-groups.md`.


## Propuestas de voces independientes en un pentagrama

El módulo `palermo_omr.staff_voice_layers` detecta zonas donde coexisten
cabezas con plicas hacia arriba y abajo dentro del mismo pentagrama. Solo
produce propuestas geométricas de posibles capas: no asigna voces ni genera
eventos temporales. Consulta `docs/staff-voice-layers.md`.


La construcción de eventos temporales también admite asignación explícita de
voz por evento mediante `build_reviewed_voice_events_by_voice`, de modo que
un mismo pentagrama pueda contener más de una voz sin forzar una identidad
global para todo el pentagrama. Consulta `docs/staff-voice-layers.md`.


## Continuidad melódica candidata

El módulo `palermo_omr.voice_continuity` propone enlaces entre eventos del
mismo pentagrama mediante alturas MIDI y tiempos musicales ya resueltos.
No asigna voces, omite acordes en esta primera versión y conserva como
ambiguos los sucesores competidores. Consulta `docs/voice-continuity.md`.


## Refinamiento de sistemas con evidencia de agrupación

La CLI combina los sistemas iniciales detectados por conectores con evidencia de llaves curvas y corchetes rectos candidatos entre pentagramas adyacentes. Las líneas verticales genéricas no bastan para fusionar sistemas. El resultado sigue siendo geométrico y requiere revisión humana; no identifica por sí solo piano, coro ni instrumentos. Consulta `docs/measure-layout.md`.
