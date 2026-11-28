# Conjunto de anotaciones musicales

El módulo `palermo_omr.annotation_dataset` define el formato reproducible para
un corpus de partituras con eventos musicales revisados por una persona. Es
infraestructura de datos: **no detecta notas ni genera ground truth**.

## Qué registra cada partitura

- `score_id`: identificador estable dentro del corpus.
- `source_sha256`: huella SHA-256 del PDF original, para identificar exactamente
  la fuente y evitar duplicados o filtraciones entre particiones.
- `page_count`: número total de páginas del PDF.
- `split`: `train`, `validation` o `test`.
- `annotation_version`: versión del criterio/formato de anotación.
- `review_status`: `draft` o `reviewed`.
- `events`: eventos `ScoreEvent` completos, con página, pentagrama, compás,
  inicio y duración en negras, tipo, alturas MIDI y voz. Pueden incluir
  `source_candidate_ids`, lista de IDs del paquete visual que sustentan el evento.
- `source_review_package_sha256`: SHA-256 del archivo JSON exacto de `prepare-review`;
  es obligatorio si algún evento conserva `source_candidate_ids`.

Los acordes se anotan como una tupla de alturas MIDI en un mismo evento. Los
silencios llevan `event_type="rest"` y `pitches_midi=[]`. Cada voz mantiene un
identificador explícito. Los tiempos se serializan como fracciones exactas
(por ejemplo `"1/3"`) para no introducir redondeos. La evidencia visual se conserva
como IDs, por ejemplo `p1-filled_notehead-3` y `p1-staff-1`; estos vínculos no
confirman por sí mismos la nota ni sustituyen la revisión humana. Cuando se usan,
las nuevas importaciones exigen la huella SHA-256 del paquete completo para impedir que IDs
similares de otra revisión se interpreten como la misma evidencia. Los manifiestos
heredados sin esa huella siguen siendo legibles; su evidencia queda identificada
como histórica/no vinculada y no debe confundirse con una referencia verificada.

## Reglas de validación

- Una referencia humana debe tener inicio, duración, tipo, alturas cuando es
  nota, y voz confirmados.
- Los eventos deben apuntar a páginas existentes.
- Los identificadores de partitura y las huellas de PDF deben ser únicos.
- Un PDF no puede aparecer en más de una partición.
- Para aceptar el conjunto como ground truth de evaluación, todas las partituras
  deben tener `review_status="reviewed"`.
- Los borradores pueden guardarse y recargarse, pero no pasan la validación
  estricta por defecto.

## Ejemplo mínimo

```python
from fractions import Fraction
from palermo_omr.annotation_dataset import AnnotatedScore, AnnotationDataset
from palermo_omr.event_evaluation import ScoreEvent

score = AnnotatedScore(
    score_id="coral-001",
    source_sha256="a" * 64,  # sustituir por SHA-256 real del PDF
    page_count=1,
    split="train",
    annotation_version="1.0",
    review_status="reviewed",
    events=(
        ScoreEvent(
            event_id="p1-s0-m1-e1",
            page_number=1,
            staff_index=0,
            measure_index=0,
            onset_quarters=Fraction(0),
            event_type="note",
            pitches_midi=(60, 64, 67),
            duration_quarters=Fraction(1),
            voice_id="soprano",
        ),
    ),
)
dataset = AnnotationDataset("0.1", (score,))
dataset.validate()
```

El ejemplo ilustra el formato; no representa una anotación de una partitura
real. El corpus no se considera existente ni validado hasta incorporar PDFs
reales, calcular sus huellas y revisar manualmente sus eventos.

## Separación de particiones

Asignar partituras completas a train, validation o test antes de ajustar
detectores. Nunca dividir páginas de un mismo PDF entre particiones. Mantener
el conjunto test reservado para la evaluación final y no usarlo para calibrar
umbrales. Las métricas deben informarse por tipo de partitura (por ejemplo,
SATB y piano), además de la cifra agregada.

## Alcance actual

El módulo valida y serializa el manifiesto, pero aún no existe un corpus real
anotado ni una interfaz de anotación. Las pruebas son sintéticas y verifican
integridad de datos; no son métricas de precisión del motor OMR.
