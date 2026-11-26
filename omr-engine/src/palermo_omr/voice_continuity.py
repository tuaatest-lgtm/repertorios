"""Enlaces melódicos candidatos entre eventos ya situados en el tiempo.

Este módulo no asigna eventos a voces. Solo propone transiciones plausibles
usando alturas MIDI, tiempos musicales y pertenencia al mismo pentagrama.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from fractions import Fraction
from collections.abc import Sequence


@dataclass(frozen=True)
class VoiceEventObservation:
    event_id: str
    staff_index: int
    onset_quarters: Fraction
    duration_quarters: Fraction
    pitches_midi: tuple[int, ...]
    stem_direction: str = "unknown"


@dataclass(frozen=True)
class MelodicTransitionCandidate:
    source_event_id: str
    target_event_id: str
    staff_index: int
    pitch_interval_semitones: int
    temporal_gap_quarters: Fraction
    overlaps_source: bool
    stem_direction_match: bool | None
    score: float
    status: str
    warnings: tuple[str, ...]

    def to_dict(self) -> dict:
        result = asdict(self)
        result["temporal_gap_quarters"] = str(self.temporal_gap_quarters)
        return result


def _fraction(value: Fraction | int | float) -> Fraction:
    if isinstance(value, bool):
        raise ValueError("Los tiempos no pueden ser booleanos")
    try:
        result = value if isinstance(value, Fraction) else Fraction(str(value))
    except (ValueError, TypeError, ZeroDivisionError) as exc:
        raise ValueError("Tiempo musical inválido") from exc
    return result


def build_melodic_transition_candidates(
    events: Sequence[VoiceEventObservation],
    *,
    max_pitch_interval_semitones: int = 12,
    max_temporal_gap_quarters: Fraction | int | float = 2,
    ambiguity_margin: float = 0.12,
) -> tuple[MelodicTransitionCandidate, ...]:
    """Propone enlaces temporales y melódicos, sin decidir la voz.

    Solo compara eventos monódicos (una altura MIDI) del mismo pentagrama.
    El orden temporal procede de onset_quarters, nunca de coordenadas x.
    """
    if not isinstance(max_pitch_interval_semitones, int) or isinstance(max_pitch_interval_semitones, bool) or max_pitch_interval_semitones < 0:
        raise ValueError("max_pitch_interval_semitones debe ser entero no negativo")
    max_gap = _fraction(max_temporal_gap_quarters)
    if max_gap < 0:
        raise ValueError("max_temporal_gap_quarters no puede ser negativo")
    if not 0 <= ambiguity_margin <= 1:
        raise ValueError("ambiguity_margin debe estar entre 0 y 1")

    seen: set[str] = set()
    normalized: list[tuple[VoiceEventObservation, Fraction, Fraction]] = []
    for event in events:
        if not isinstance(event, VoiceEventObservation):
            raise ValueError("Todos los elementos deben ser VoiceEventObservation")
        if not isinstance(event.event_id, str) or not event.event_id.strip():
            raise ValueError("event_id debe ser texto no vacío")
        if event.event_id in seen:
            raise ValueError("event_id debe ser único")
        seen.add(event.event_id)
        if not isinstance(event.staff_index, int) or isinstance(event.staff_index, bool) or event.staff_index < 0:
            raise ValueError("staff_index debe ser entero no negativo")
        onset = _fraction(event.onset_quarters)
        duration = _fraction(event.duration_quarters)
        if onset < 0 or duration <= 0:
            raise ValueError("El inicio no puede ser negativo y la duración debe ser positiva")
        if len(event.pitches_midi) != 1:
            if len(event.pitches_midi) == 0:
                raise ValueError("Cada evento debe incluir una altura MIDI")
            if any(not isinstance(p, int) or isinstance(p, bool) or p < 0 for p in event.pitches_midi):
                raise ValueError("Las alturas MIDI deben ser enteros no negativos")
        elif not isinstance(event.pitches_midi[0], int) or isinstance(event.pitches_midi[0], bool) or event.pitches_midi[0] < 0:
            raise ValueError("Las alturas MIDI deben ser enteros no negativos")
        if event.stem_direction not in {"up", "down", "none", "unknown"}:
            raise ValueError("stem_direction no reconocido")
        normalized.append((event, onset, duration))

    ordered = sorted(normalized, key=lambda item: (item[1], item[0].staff_index, item[0].event_id))
    raw: list[tuple[VoiceEventObservation, VoiceEventObservation, int, Fraction, bool, bool | None, float]] = []
    for source, source_onset, source_duration in ordered:
        if len(source.pitches_midi) != 1:
            continue
        source_pitch = source.pitches_midi[0]
        source_end = source_onset + source_duration
        for target, target_onset, _ in ordered:
            if target.staff_index != source.staff_index or target_onset <= source_onset:
                continue
            if len(target.pitches_midi) != 1:
                continue
            gap = target_onset - source_end
            if gap > max_gap:
                continue
            interval = target.pitches_midi[0] - source_pitch
            if abs(interval) > max_pitch_interval_semitones:
                continue
            overlap = gap < 0
            direction_match = (
                source.stem_direction == target.stem_direction
                if source.stem_direction in {"up", "down"}
                and target.stem_direction in {"up", "down"}
                else None
            )
            pitch_score = 1.0 - abs(interval) / max(1, max_pitch_interval_semitones + 1)
            gap_score = 1.0 - min(abs(float(gap)), float(max_gap) + 1) / (float(max_gap) + 1)
            score = 0.75 * pitch_score + 0.25 * gap_score
            if overlap:
                score *= 0.65
            if direction_match is False:
                score *= 0.9
            raw.append((source, target, interval, gap, overlap, direction_match, max(0.0, min(1.0, score))))

    # Mark close competing successors as ambiguous rather than selecting one.
    by_source: dict[str, list[int]] = {}
    for index, item in enumerate(raw):
        by_source.setdefault(item[0].event_id, []).append(index)
    statuses = ["proposed_transition"] * len(raw)
    for indices in by_source.values():
        ranked = sorted(indices, key=lambda i: (-raw[i][6], raw[i][1].event_id))
        if len(ranked) > 1 and raw[ranked[0]][6] - raw[ranked[1]][6] < ambiguity_margin:
            for index in ranked:
                statuses[index] = "ambiguous_competing_successors"

    results = []
    for index, (source, target, interval, gap, overlap, direction_match, score) in enumerate(raw):
        warnings = [
            "Enlace melódico candidato; no confirma que ambos eventos pertenezcan a la misma voz.",
            "La altura MIDI debe proceder de una clave y alteraciones revisadas o confirmadas.",
        ]
        if len(source.pitches_midi) != 1 or len(target.pitches_midi) != 1:
            warnings.append("Los acordes no se enlazan automáticamente con esta versión.")
        if overlap:
            warnings.append("Los eventos se solapan; el enlace requiere revisión musical.")
        if direction_match is False:
            warnings.append("Las direcciones de plica difieren; no se usa como regla de separación.")
        if statuses[index] == "ambiguous_competing_successors":
            warnings.append("Hay varios sucesores de puntuación similar; no se elige uno.")
        results.append(MelodicTransitionCandidate(
            source_event_id=source.event_id,
            target_event_id=target.event_id,
            staff_index=source.staff_index,
            pitch_interval_semitones=interval,
            temporal_gap_quarters=gap,
            overlaps_source=overlap,
            stem_direction_match=direction_match,
            score=round(score, 3),
            status=statuses[index],
            warnings=tuple(warnings),
        ))
    return tuple(results)
