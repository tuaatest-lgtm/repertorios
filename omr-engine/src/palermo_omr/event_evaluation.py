"""Evaluación de eventos musicales predichos contra anotaciones humanas.

Empareja eventos uno a uno por página, pentagrama, compás e inicio temporal
dentro de una tolerancia. Después mide por separado tipo, alturas, duración
y voz. No modifica predicciones ni infiere datos faltantes.
"""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import asdict, dataclass
from fractions import Fraction
from math import isfinite


@dataclass(frozen=True)
class ScoreEvent:
    event_id: str
    page_number: int
    staff_index: int
    measure_index: int
    onset_quarters: Fraction | int | float | None
    event_type: str
    pitches_midi: tuple[int, ...] | None
    duration_quarters: Fraction | int | float | None
    voice_id: str | None


@dataclass(frozen=True)
class ScoreEventMatch:
    predicted_index: int
    reference_index: int
    onset_error_quarters: Fraction


@dataclass(frozen=True)
class ScoreEventEvaluation:
    onset_tolerance_quarters: Fraction
    predicted_count: int
    reference_count: int
    matches: tuple[ScoreEventMatch, ...]
    unmatched_predicted_indices: tuple[int, ...]
    unmatched_reference_indices: tuple[int, ...]
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

    def to_dict(self) -> dict:
        result = asdict(self)
        result["onset_tolerance_quarters"] = str(self.onset_tolerance_quarters)
        for match in result["matches"]:
            match["onset_error_quarters"] = str(match["onset_error_quarters"])
        return result


def _fraction(value: Fraction | int | float, field: str) -> Fraction:
    if isinstance(value, bool):
        raise ValueError(f"{field} no puede ser booleano")
    try:
        result = value if isinstance(value, Fraction) else Fraction(str(value))
    except (ValueError, TypeError, ZeroDivisionError) as exc:
        raise ValueError(f"{field} debe ser un número válido") from exc
    return result


def _validate_events(
    events: Sequence[ScoreEvent],
    *,
    reference: bool,
) -> tuple[ScoreEvent, ...]:
    validated = tuple(events)
    seen_ids: set[str] = set()
    for index, event in enumerate(validated):
        if not isinstance(event, ScoreEvent):
            raise ValueError("Todos los elementos deben ser ScoreEvent")
        if not isinstance(event.event_id, str) or not event.event_id.strip():
            raise ValueError(f"event_id[{index}] debe ser texto no vacío")
        if event.event_id in seen_ids:
            raise ValueError("event_id debe ser único dentro de cada conjunto")
        seen_ids.add(event.event_id)
        if not isinstance(event.page_number, int) or isinstance(event.page_number, bool) or event.page_number < 1:
            raise ValueError("page_number debe ser entero positivo")
        if not isinstance(event.staff_index, int) or isinstance(event.staff_index, bool) or event.staff_index < 0:
            raise ValueError("staff_index debe ser entero no negativo")
        if not isinstance(event.measure_index, int) or isinstance(event.measure_index, bool) or event.measure_index < 0:
            raise ValueError("measure_index debe ser entero no negativo")
        if event.event_type not in {"note", "rest", "unknown"}:
            raise ValueError("event_type debe ser note, rest o unknown")
        if reference and event.event_type == "unknown":
            raise ValueError("Las anotaciones humanas deben tener event_type confirmado")
        if event.onset_quarters is None:
            if reference:
                raise ValueError("Las anotaciones humanas deben tener onset conocido")
            onset = None
        else:
            onset = _fraction(event.onset_quarters, "onset_quarters")
            if onset < 0:
                raise ValueError("onset_quarters no puede ser negativo")
        if event.duration_quarters is None:
            if reference:
                raise ValueError("Las anotaciones humanas deben tener duración conocida")
        else:
            duration = _fraction(event.duration_quarters, "duration_quarters")
            if duration <= 0:
                raise ValueError("duration_quarters debe ser mayor que cero")
        if event.pitches_midi is not None:
            if not isinstance(event.pitches_midi, tuple):
                raise ValueError("pitches_midi debe ser una tupla o None")
            if any(
                not isinstance(pitch, int) or isinstance(pitch, bool) or pitch < 0
                for pitch in event.pitches_midi
            ):
                raise ValueError("Cada altura MIDI debe ser un entero no negativo")
            if len(set(event.pitches_midi)) != len(event.pitches_midi):
                raise ValueError("pitches_midi no puede repetir alturas")
        if reference:
            if event.event_type == "note" and not event.pitches_midi:
                raise ValueError("Una nota de referencia requiere alturas MIDI")
            if event.event_type == "rest" and event.pitches_midi != ():
                raise ValueError("Un silencio de referencia debe tener pitches_midi vacío")
            if not isinstance(event.voice_id, str) or not event.voice_id.strip():
                raise ValueError("La anotación humana requiere voice_id")
        elif event.voice_id is not None and (
            not isinstance(event.voice_id, str) or not event.voice_id.strip()
        ):
            raise ValueError("voice_id debe ser texto no vacío o None")
    return validated


def _accuracy(correct: int, total: int) -> float | None:
    return correct / total if total else None


def evaluate_score_events(
    reference_events: Sequence[ScoreEvent],
    predicted_events: Sequence[ScoreEvent],
    *,
    onset_tolerance_quarters: Fraction | int | float = Fraction(1, 8),
) -> ScoreEventEvaluation:
    """Evalúa detección y atributos mediante emparejamiento 1 a 1.

    El emparejamiento usa solo página, pentagrama, compás e inicio (dentro de
    tolerancia); no usa tipo, altura, duración ni voz, para que los errores de
    esos campos aparezcan en sus métricas y no se oculten como eventos ausentes.
    Predicciones sin inicio conocido no se emparejan y permanecen como falsos
    positivos; la anotación correspondiente permanece como falso negativo.
    """
    tolerance = _fraction(onset_tolerance_quarters, "onset_tolerance_quarters")
    if tolerance < 0:
        raise ValueError("onset_tolerance_quarters no puede ser negativo")
    reference = _validate_events(reference_events, reference=True)
    predicted = _validate_events(predicted_events, reference=False)

    eligible: list[list[tuple[Fraction, int]]] = []
    for prediction in predicted:
        options: list[tuple[Fraction, int]] = []
        if prediction.onset_quarters is not None:
            pred_onset = _fraction(prediction.onset_quarters, "onset_quarters")
            for reference_index, annotation in enumerate(reference):
                if (
                    prediction.page_number != annotation.page_number
                    or prediction.staff_index != annotation.staff_index
                    or prediction.measure_index != annotation.measure_index
                ):
                    continue
                delta = abs(
                    pred_onset - _fraction(annotation.onset_quarters, "onset_quarters")
                )
                if delta <= tolerance:
                    options.append((delta, reference_index))
        options.sort(key=lambda item: (item[0], item[1]))
        eligible.append(options)

    reference_to_prediction: dict[int, tuple[int, Fraction]] = {}

    def assign(prediction_index: int, visited: set[int]) -> bool:
        for error, reference_index in eligible[prediction_index]:
            if reference_index in visited:
                continue
            visited.add(reference_index)
            previous = reference_to_prediction.get(reference_index)
            if previous is None or assign(previous[0], visited):
                reference_to_prediction[reference_index] = (prediction_index, error)
                return True
        return False

    order = sorted(range(len(predicted)), key=lambda i: (len(eligible[i]), i))
    for prediction_index in order:
        assign(prediction_index, set())

    matches = tuple(sorted(
        (
            ScoreEventMatch(prediction_index, reference_index, error)
            for reference_index, (prediction_index, error)
            in reference_to_prediction.items()
        ),
        key=lambda match: (match.predicted_index, match.reference_index),
    ))
    matched_predictions = {match.predicted_index for match in matches}
    matched_references = {match.reference_index for match in matches}
    unmatched_predictions = tuple(i for i in range(len(predicted)) if i not in matched_predictions)
    unmatched_references = tuple(i for i in range(len(reference)) if i not in matched_references)

    tp = len(matches)
    fp = len(unmatched_predictions)
    fn = len(unmatched_references)
    precision = tp / (tp + fp) if tp + fp else None
    recall = tp / (tp + fn) if tp + fn else None
    f1 = (
        2 * precision * recall / (precision + recall)
        if precision is not None and recall is not None and precision + recall > 0
        else (0.0 if precision == 0 or recall == 0 else None)
    )

    type_correct = sum(
        predicted[m.predicted_index].event_type == reference[m.reference_index].event_type
        for m in matches
    )
    # La exactitud de alturas se calcula solo sobre eventos cuya referencia
    # es una nota. Los silencios no tienen altura y no deben inflar la métrica.
    reference_note_matches = tuple(
        m for m in matches
        if reference[m.reference_index].event_type == "note"
    )
    pitch_correct = sum(
        predicted[m.predicted_index].pitches_midi == reference[m.reference_index].pitches_midi
        for m in reference_note_matches
    )
    duration_correct = sum(
        predicted[m.predicted_index].duration_quarters is not None
        and _fraction(predicted[m.predicted_index].duration_quarters, "duration_quarters")
        == _fraction(reference[m.reference_index].duration_quarters, "duration_quarters")
        for m in matches
    )
    voice_correct = sum(
        predicted[m.predicted_index].voice_id == reference[m.reference_index].voice_id
        for m in matches
    )
    mean_onset_error = (
        float(sum((m.onset_error_quarters for m in matches), Fraction(0)) / tp)
        if tp else None
    )

    return ScoreEventEvaluation(
        onset_tolerance_quarters=tolerance,
        predicted_count=len(predicted),
        reference_count=len(reference),
        matches=matches,
        unmatched_predicted_indices=unmatched_predictions,
        unmatched_reference_indices=unmatched_references,
        true_positive=tp,
        false_positive=fp,
        false_negative=fn,
        precision=precision,
        recall=recall,
        f1=f1,
        event_type_correct=type_correct,
        event_type_accuracy=_accuracy(type_correct, tp),
        pitch_correct=pitch_correct,
        pitch_accuracy=_accuracy(pitch_correct, len(reference_note_matches)),
        duration_correct=duration_correct,
        duration_accuracy=_accuracy(duration_correct, tp),
        voice_correct=voice_correct,
        voice_accuracy=_accuracy(voice_correct, tp),
        mean_onset_error_quarters=mean_onset_error,
    )
