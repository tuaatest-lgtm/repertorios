# Flujo operativo de anotación humana

La utilidad `palermo-omr-dataset` hace ejecutable el ciclo de preparación y
control del corpus. No interpreta notas automáticamente y nunca declara que
una partitura está revisada sin una confirmación humana explícita.

## 1. Registrar un PDF

```bash
palermo-omr-dataset init "Clamare a Dios - Coro.pdf" \
  --manifest corpus/manifest.json \
  --score-id clamare-dios-coro \
  --split validation
```

El comando calcula SHA-256 del archivo, cuenta las páginas con PyMuPDF y crea
una entrada `draft` sin eventos. Si el mismo PDF o identificador ya existe,
rechaza la operación. El manifiesto se escribe de forma atómica.

## 2. Incorporar anotaciones

Editar `corpus/manifest.json` con eventos `ScoreEvent` de acuerdo con
`annotation-dataset.md`. Registrar cada ataque musical una sola vez por voz;
las notas simultáneas de un acorde forman un evento con varias alturas MIDI.
Las voces que sostienen notas mientras otras cambian conservan eventos y
duraciones independientes. Los silencios son eventos explícitos.

El formato actual registra alturas MIDI y tiempos en negras. La asignación
de pentagrama, compás y voz debe verificarse contra la partitura. No completar
por intuición los datos que no se puedan leer: primero se resuelve la anotación
o se deja el documento en borrador.

## 3. Validar

```bash
palermo-omr-dataset validate corpus/manifest.json --allow-drafts
```

La validación estricta, sin `--allow-drafts`, solo acepta documentos revisados
y es la que debe usarse antes de evaluar el motor.

## 4. Aprobar revisión humana

Después de contrastar visualmente todos los eventos de una partitura con el
PDF, ejecutar:

```bash
palermo-omr-dataset review corpus/manifest.json \
  --score-id clamare-dios-coro \
  --confirm-human-review
```

El comando exige el indicador explícito, no permite aprobar una partitura sin
eventos y modifica únicamente el estado de la partitura seleccionada. Esta
confirmación es una declaración del anotador; el programa no puede comprobar
que la revisión visual ocurrió.

## 5. Evaluar

El manifiesto revisado puede cargarse con `AnnotationDataset.from_dict` y
pasarse a `evaluate_annotation_dataset`, con las predicciones agrupadas por
`score_id` y una partición explícita. Consultar `dataset-evaluation.md`.

## Alcance y honestidad de resultados

Las pruebas verifican creación de manifiestos, integridad de hash, páginas,
rechazo de duplicados, aprobación explícita y validación. No constituyen
anotaciones musicales reales ni una medición de precisión OMR. La primera
partitura incorporada debe anotarse y revisarse antes de usarla como ground
truth.
