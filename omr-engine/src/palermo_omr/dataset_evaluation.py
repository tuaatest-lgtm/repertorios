"""Evaluación agregada por partición de un corpus anotado.

Calcula métricas micro sobre partituras completas y conserva resultados por
partitura. No produce predicciones ni permite evaluar borradores como verdad
de referencia.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from fractions import Fraction

from .annotation_dataset import AnnotationDataset
from .event_evaluation import ScoreEvent, ScoreEventEvaluation, evaluate_score_events


@dataclass(frozen=True)
class ScoreDatasetResult:
    score_id: str
    evaluation: ScoreEventEvaluation


@dataclass(frozen=True)
class DatasetEvaluation:
    split: str
    score_count: int
    predicted_count: int
    reference_count: int
    true_positive: int
    false_positive: int
    false_negative: int
    precision: float | None
    recall: float | None
    f1: float | None
    event_type_correct: int
    event_type_accuracy: float | None
    pitch_correct: int
    pitch_accuracy: float | None
    duration_correct: int
    duration_accuracy: float | None
    voice_correct: int
    voice_accuracy: float | None
    mean_onset_error_quarters: float | None
    per_score: tuple[ScoreDatasetResult, ...]


def _ratio(correct: int, total: int) -> float | None:
    return correct / total if total else None


def evaluate_annotation_dataset(
    dataset: AnnotationDataset,
    predictions_by_score: Mapping[str, Sequence[ScoreEvent]],
    *,
    split: str = "test",
    onset_tolerance_quarters: Fraction | int | float = Fraction(1, 8),
) -> DatasetEvaluation:
    """Evalúa todas las partituras revisadas de una partición.

    Las partituras sin una entrada en predictions_by_score se evalúan como
    cero predicciones. Las claves desconocidas o pertenecientes a otra
    partición se rechazan para evitar mezclar resultados por accidente.
    """
    if split not in {"train", "validation", "test"}:
        raise ValueError("split debe ser train, validation o test")
    dataset.validate(require_reviewed=True)
    selected = tuple(score for score in dataset.scores if score.split == split)
    if not selected:
        raise ValueError(f"No hay partituras revisadas en la partición {split}")

    selected_ids = {score.score_id for score in selected}
    all_ids = {score.score_id for score in dataset.scores}
    unknown = set(predictions_by_score) - all_ids
    if unknown:
        raise ValueError(f"Hay predicciones para partituras desconocidas: {sorted(unknown)}")
    wrong_split = set(predictions_by_score) - selected_ids
    if wrong_split:
        raise ValueError(
            f"Las predicciones incluyen partituras fuera de {split}: {sorted(wrong_split)}"
        )

    results = tuple(
        ScoreDatasetResult(
            score_id=score.score_id,
            evaluation=evaluate_score_events(
                score.events,
                predictions_by_score.get(score.score_id, ()),
                onset_tolerance_quarters=onset_tolerance_quarters,
            ),
        )
        for score in selected
    )

    evaluations = tuple(result.evaluation for result in results)
    predicted_count = sum(item.predicted_count for item in evaluations)
    reference_count = sum(item.reference_count for item in evaluations)
    tp = sum(item.true_positive for item in evaluations)
    fp = sum(item.false_positive for item in evaluations)
    fn = sum(item.false_negative for item in evaluations)
    precision = tp / (tp + fp) if tp + fp else None
    recall = tp / (tp + fn) if tp + fn else None
    f1 = (
        2 * precision * recall / (precision + recall)
        if precision is not None and recall is not None and precision + recall > 0
        else (0.0 if precision == 0 or recall == 0 else None)
    )
    type_correct = sum(item.event_type_correct for item in evaluations)
    pitch_correct = sum(item.pitch_correct for item in evaluations)
    duration_correct = sum(item.duration_correct for item in evaluations)
    voice_correct = sum(item.voice_correct for item in evaluations)
    onset_error_sum = sum(
        (
            match.onset_error_quarters
            for item in evaluations
            for match in item.matches
        ),
        Fraction(0),
    )

    return DatasetEvaluation(
        split=split,
        score_count=len(selected),
        predicted_count=predicted_count,
        reference_count=reference_count,
        true_positive=tp,
        false_positive=fp,
        false_negative=fn,
        precision=precision,
        recall=recall,
        f1=f1,
        event_type_correct=type_correct,
        event_type_accuracy=_ratio(type_correct, tp),
        pitch_correct=pitch_correct,
        pitch_accuracy=_ratio(pitch_correct, tp),
        duration_correct=duration_correct,
        duration_accuracy=_ratio(duration_correct, tp),
        voice_correct=voice_correct,
        voice_accuracy=_ratio(voice_correct, tp),
        mean_onset_error_quarters=float(onset_error_sum / tp) if tp else None,
        per_score=results,
    )
