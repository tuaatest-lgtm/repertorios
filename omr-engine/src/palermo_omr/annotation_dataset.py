"""Conjunto reproducible de partituras con anotaciones musicales humanas.

El manifiesto conserva la identidad del PDF mediante SHA-256, separa los
conjuntos train/validation/test y exige anotaciones completas revisadas antes
de usarlas como referencia de evaluación. No realiza reconocimiento OMR.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from fractions import Fraction
import re
from typing import Any

from .event_evaluation import ScoreEvent, evaluate_score_events


_DATASET_SPLITS = {"train", "validation", "test"}
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True)
class AnnotatedScore:
    score_id: str
    source_sha256: str
    page_count: int
    split: str
    annotation_version: str
    review_status: str
    events: tuple[ScoreEvent, ...]
    source_review_package_sha256: str | None = None

    def validate(self) -> None:
        if not isinstance(self.score_id, str) or not self.score_id.strip():
            raise ValueError("score_id debe ser texto no vacío")
        if not isinstance(self.source_sha256, str) or not _SHA256_RE.fullmatch(self.source_sha256):
            raise ValueError("source_sha256 debe contener 64 caracteres hexadecimales minúsculos")
        if not isinstance(self.page_count, int) or isinstance(self.page_count, bool) or self.page_count < 1:
            raise ValueError("page_count debe ser un entero positivo")
        if self.split not in _DATASET_SPLITS:
            raise ValueError("split debe ser train, validation o test")
        if not isinstance(self.annotation_version, str) or not self.annotation_version.strip():
            raise ValueError("annotation_version debe ser texto no vacío")
        if self.review_status not in {"draft", "reviewed"}:
            raise ValueError("review_status debe ser draft o reviewed")
        if not isinstance(self.events, tuple):
            raise ValueError("events debe ser una tupla de ScoreEvent")
        if self.source_review_package_sha256 is not None and (
            not isinstance(self.source_review_package_sha256, str)
            or not _SHA256_RE.fullmatch(self.source_review_package_sha256)
        ):
            raise ValueError("source_review_package_sha256 debe ser SHA-256 hexadecimal o null")
        # Legacy manifests may contain candidate IDs without a package digest.
        # New imports enforce the digest in import_score_events; do not reject old data.

        # Reutiliza la validación estricta de las referencias del evaluador.
        evaluate_score_events(self.events, ())
        for event in self.events:
            if event.page_number > self.page_count:
                raise ValueError(
                    f"El evento {event.event_id} apunta a una página fuera del PDF"
                )


@dataclass(frozen=True)
class AnnotationDataset:
    dataset_version: str
    scores: tuple[AnnotatedScore, ...]

    def validate(self, *, require_reviewed: bool = True) -> None:
        if not isinstance(self.dataset_version, str) or not self.dataset_version.strip():
            raise ValueError("dataset_version debe ser texto no vacío")
        if not isinstance(self.scores, tuple):
            raise ValueError("scores debe ser una tupla de AnnotatedScore")

        score_ids: set[str] = set()
        source_hashes: set[str] = set()
        for score in self.scores:
            if not isinstance(score, AnnotatedScore):
                raise ValueError("Todos los elementos deben ser AnnotatedScore")
            score.validate()
            if score.score_id in score_ids:
                raise ValueError("score_id debe ser único en el conjunto")
            if score.source_sha256 in source_hashes:
                raise ValueError("Un mismo PDF no puede aparecer más de una vez ni cruzar particiones")
            if require_reviewed and score.review_status != "reviewed":
                raise ValueError(f"La partitura {score.score_id} aún no está revisada")
            score_ids.add(score.score_id)
            source_hashes.add(score.source_sha256)

    def to_dict(self) -> dict[str, Any]:
        self.validate(require_reviewed=False)
        return {
            "dataset_version": self.dataset_version,
            "scores": [
                {
                    "score_id": score.score_id,
                    "source_sha256": score.source_sha256,
                    "page_count": score.page_count,
                    "split": score.split,
                    "annotation_version": score.annotation_version,
                    "review_status": score.review_status,
                    "source_review_package_sha256": score.source_review_package_sha256,
                    "events": [
                        {
                            "event_id": event.event_id,
                            "page_number": event.page_number,
                            "staff_index": event.staff_index,
                            "measure_index": event.measure_index,
                            "onset_quarters": _number_string(event.onset_quarters),
                            "event_type": event.event_type,
                            "pitches_midi": (
                                list(event.pitches_midi)
                                if event.pitches_midi is not None else None
                            ),
                            "duration_quarters": _number_string(event.duration_quarters),
                            "voice_id": event.voice_id,
                            "source_candidate_ids": list(event.source_candidate_ids),
                        }
                        for event in score.events
                    ],
                }
                for score in self.scores
            ],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AnnotationDataset":
        if not isinstance(data, dict) or set(data) != {"dataset_version", "scores"}:
            raise ValueError("El manifiesto requiere dataset_version y scores")
        if not isinstance(data["scores"], list):
            raise ValueError("scores debe ser una lista")
        scores = []
        for score_data in data["scores"]:
            expected_score_keys = {
                "score_id", "source_sha256", "page_count", "split",
                "annotation_version", "review_status", "events",
            }
            optional_score_keys = expected_score_keys | {"source_review_package_sha256"}
            if not isinstance(score_data, dict) or set(score_data) not in (expected_score_keys, optional_score_keys):
                raise ValueError("Cada partitura debe contener exactamente los campos definidos")
            if not isinstance(score_data["events"], list):
                raise ValueError("events debe ser una lista")
            events = []
            for event_data in score_data["events"]:
                expected_event_keys = {
                    "event_id", "page_number", "staff_index", "measure_index",
                    "onset_quarters", "event_type", "pitches_midi",
                    "duration_quarters", "voice_id",
                }
                optional_event_keys = expected_event_keys | {"source_candidate_ids"}
                if (not isinstance(event_data, dict)
                        or set(event_data) not in (expected_event_keys, optional_event_keys)):
                    raise ValueError("Cada evento debe contener los campos definidos y evidencia opcional")
                candidate_ids = event_data.get("source_candidate_ids", [])
                if not isinstance(candidate_ids, list):
                    raise ValueError("source_candidate_ids debe ser una lista")
                pitches = event_data["pitches_midi"]
                if pitches is not None and not isinstance(pitches, list):
                    raise ValueError("pitches_midi debe ser una lista o null")
                events.append(ScoreEvent(
                    event_id=event_data["event_id"],
                    page_number=event_data["page_number"],
                    staff_index=event_data["staff_index"],
                    measure_index=event_data["measure_index"],
                    onset_quarters=_parse_fraction(event_data["onset_quarters"]),
                    event_type=event_data["event_type"],
                    pitches_midi=tuple(pitches) if pitches is not None else None,
                    duration_quarters=_parse_fraction(event_data["duration_quarters"]),
                    voice_id=event_data["voice_id"],
                    source_candidate_ids=tuple(candidate_ids),
                ))
            scores.append(AnnotatedScore(
                score_id=score_data["score_id"],
                source_sha256=score_data["source_sha256"],
                page_count=score_data["page_count"],
                split=score_data["split"],
                annotation_version=score_data["annotation_version"],
                review_status=score_data["review_status"],
                events=tuple(events),
                source_review_package_sha256=score_data.get("source_review_package_sha256"),
            ))
        result = cls(dataset_version=data["dataset_version"], scores=tuple(scores))
        result.validate(require_reviewed=False)
        return result


def _number_string(value: Fraction | int | float | None) -> str | None:
    if value is None:
        return None
    if isinstance(value, bool):
        raise ValueError("Los valores musicales no pueden ser booleanos")
    try:
        exact = value if isinstance(value, Fraction) else Fraction(str(value))
    except (ValueError, TypeError, ZeroDivisionError) as exc:
        raise ValueError("Valor musical no válido para serialización") from exc
    return str(exact)


def _parse_fraction(value: Any) -> Fraction | None:
    if value is None:
        return None
    if not isinstance(value, (str, int, float)) or isinstance(value, bool):
        raise ValueError("Los tiempos y duraciones deben ser números o fracciones como texto")
    try:
        return Fraction(str(value))
    except (ValueError, ZeroDivisionError) as exc:
        raise ValueError("Fracción musical no válida") from exc
