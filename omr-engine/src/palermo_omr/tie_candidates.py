"""Propuestas conservadoras para distinguir ligaduras de prolongación.

Combina arcos geométricos candidatos con eventos ya revisados en altura,
voz y tiempo. No confirma ligaduras ni modifica duraciones: toda propuesta
requiere revisión humana, incluida la grafía/enarmonía de las notas.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from fractions import Fraction
from collections.abc import Mapping, Sequence

from .duration_math import sum_tied_durations


@dataclass(frozen=True)
class TieNoteObservation:
    event_id: str
    voice_id: str
    staff_index: int
    onset_quarters: Fraction
    duration_quarters: Fraction
    pitch_midi: int
    notehead_bbox: tuple[int, int, int, int]
    staff_spacing: float
    measure_index: int


@dataclass(frozen=True)
class TieArcObservation:
    arc_id: str
    staff_index: int
    bbox: tuple[int, int, int, int]


@dataclass(frozen=True)
class TieLinkCandidate:
    arc_id: str
    source_event_id: str
    target_event_id: str
    status: str
    pitch_match: bool
    temporal_continuity: bool
    geometry_score: float
    warnings: tuple[str, ...]

    def to_dict(self) -> dict:
        return asdict(self)


def _as_fraction(value: Fraction | int | float) -> Fraction:
    if isinstance(value, bool):
        raise ValueError("Los tiempos no pueden ser booleanos")
    try:
        result = value if isinstance(value, Fraction) else Fraction(str(value))
    except (ValueError, TypeError, ZeroDivisionError) as exc:
        raise ValueError("Tiempo musical inválido") from exc
    return result


def _validate_bbox(bbox: tuple[int, int, int, int]) -> bool:
    return (
        isinstance(bbox, tuple)
        and len(bbox) == 4
        and all(isinstance(value, int) and not isinstance(value, bool) for value in bbox)
        and bbox[2] > 0
        and bbox[3] > 0
    )


def build_tie_link_candidates(
    notes: Sequence[TieNoteObservation],
    arcs: Sequence[TieArcObservation],
    *,
    horizontal_tolerance_spacing: float = 0.45,
    vertical_tolerance_spacing: float = 2.5,
) -> tuple[TieLinkCandidate, ...]:
    """Propone pares de notas que podrían estar unidos por un arco de tie.

    Requiere voice_id explícito y eventos ya ordenados en un tiempo global
    (también entre compases). Solo considera pares consecutivos de esa voz,
    en el mismo pentagrama, con alturas MIDI iguales y ataques contiguos.
    Las cajas y el espaciado deben proceder de la misma imagen rasterizada.
    """
    if horizontal_tolerance_spacing < 0 or vertical_tolerance_spacing <= 0:
        raise ValueError("Las tolerancias geométricas deben ser válidas")

    seen_notes: set[str] = set()
    normalized_notes: list[tuple[TieNoteObservation, Fraction, Fraction]] = []
    for note in notes:
        if not isinstance(note, TieNoteObservation):
            raise ValueError("Todos los elementos deben ser TieNoteObservation")
        if not isinstance(note.event_id, str) or not note.event_id.strip() or note.event_id in seen_notes:
            raise ValueError("event_id debe ser texto no vacío y único")
        seen_notes.add(note.event_id)
        if not isinstance(note.voice_id, str) or not note.voice_id.strip():
            raise ValueError("voice_id debe ser explícito y no vacío")
        if not isinstance(note.staff_index, int) or isinstance(note.staff_index, bool) or note.staff_index < 0:
            raise ValueError("staff_index debe ser entero no negativo")
        if not isinstance(note.measure_index, int) or isinstance(note.measure_index, bool) or note.measure_index < 0:
            raise ValueError("measure_index debe ser entero no negativo")
        if not isinstance(note.pitch_midi, int) or isinstance(note.pitch_midi, bool) or note.pitch_midi < 0:
            raise ValueError("pitch_midi debe ser entero no negativo")
        if not _validate_bbox(note.notehead_bbox):
            raise ValueError("notehead_bbox debe ser una caja xywh válida")
        if note.staff_spacing <= 1:
            raise ValueError("staff_spacing debe ser mayor que uno")
        onset = _as_fraction(note.onset_quarters)
        duration = _as_fraction(note.duration_quarters)
        if onset < 0 or duration <= 0:
            raise ValueError("El inicio no puede ser negativo y la duración debe ser positiva")
        normalized_notes.append((note, onset, duration))

    seen_arcs: set[str] = set()
    for arc in arcs:
        if not isinstance(arc, TieArcObservation):
            raise ValueError("Todos los arcos deben ser TieArcObservation")
        if not isinstance(arc.arc_id, str) or not arc.arc_id.strip() or arc.arc_id in seen_arcs:
            raise ValueError("arc_id debe ser texto no vacío y único")
        seen_arcs.add(arc.arc_id)
        if not isinstance(arc.staff_index, int) or isinstance(arc.staff_index, bool) or arc.staff_index < 0:
            raise ValueError("staff_index del arco debe ser entero no negativo")
        if not _validate_bbox(arc.bbox):
            raise ValueError("bbox del arco debe ser una caja xywh válida")

    # Solo se compara cada evento con el siguiente evento de la misma voz.
    by_voice: dict[str, list[tuple[TieNoteObservation, Fraction, Fraction]]] = {}
    for item in normalized_notes:
        by_voice.setdefault(item[0].voice_id, []).append(item)

    pairs: list[tuple[TieNoteObservation, TieNoteObservation]] = []
    for voice_events in by_voice.values():
        ordered = sorted(voice_events, key=lambda item: (item[1], item[0].event_id))
        for (source, source_onset, source_duration), (target, target_onset, _) in zip(ordered, ordered[1:]):
            if source.staff_index != target.staff_index:
                continue
            if source.pitch_midi != target.pitch_midi:
                continue
            if source_onset + source_duration != target_onset:
                continue
            pairs.append((source, target))

    raw: list[tuple[TieArcObservation, TieNoteObservation, TieNoteObservation, float]] = []
    for arc in arcs:
        ax, ay, aw, ah = arc.bbox
        arc_cx, arc_cy = ax + aw / 2, ay + ah / 2
        for source, target in pairs:
            if arc.staff_index != source.staff_index:
                continue
            sx, sy, sw, sh = source.notehead_bbox
            tx, ty, tw, th = target.notehead_bbox
            source_cx, source_cy = sx + sw / 2, sy + sh / 2
            target_cx, target_cy = tx + tw / 2, ty + th / 2
            if target_cx <= source_cx:
                continue
            spacing = (source.staff_spacing + target.staff_spacing) / 2
            gap_left, gap_right = sx + sw, tx
            if gap_right <= gap_left:
                continue
            tolerance = horizontal_tolerance_spacing * spacing
            if ax > gap_left + tolerance or ax + aw < gap_right - tolerance:
                continue
            if not (gap_left - tolerance <= arc_cx <= gap_right + tolerance):
                continue
            expected_y = (source_cy + target_cy) / 2
            vertical_distance = abs(arc_cy - expected_y) / spacing
            if vertical_distance > vertical_tolerance_spacing:
                continue
            horizontal_coverage = min(1.0, aw / max(1.0, gap_right - gap_left))
            vertical_score = max(0.0, 1.0 - vertical_distance / vertical_tolerance_spacing)
            raw.append((arc, source, target, round(0.65 * horizontal_coverage + 0.35 * vertical_score, 3)))

    # Si un arco o un par de notas admite más de una correspondencia, no elegir.
    arc_counts: dict[str, int] = {}
    pair_counts: dict[tuple[str, str], int] = {}
    for arc, source, target, _ in raw:
        arc_counts[arc.arc_id] = arc_counts.get(arc.arc_id, 0) + 1
        key = (source.event_id, target.event_id)
        pair_counts[key] = pair_counts.get(key, 0) + 1

    results = []
    for arc, source, target, score in raw:
        ambiguous = (
            arc_counts[arc.arc_id] > 1
            or pair_counts[(source.event_id, target.event_id)] > 1
        )
        warnings = [
            "Propuesta geométrica: requiere confirmación humana antes de sumar duraciones.",
            "La igualdad MIDI no garantiza igualdad de escritura musical; revisar nombre de nota y alteraciones.",
            "Un arco puede ser ligadura de expresión u otra marca editorial.",
            "La voz y el tiempo de entrada deben proceder de asignaciones revisadas.",
        ]
        if ambiguous:
            warnings.append("El arco o el par admite varias correspondencias; no se selecciona una.")
        results.append(TieLinkCandidate(
            arc_id=arc.arc_id,
            source_event_id=source.event_id,
            target_event_id=target.event_id,
            status="ambiguous_tie_candidate" if ambiguous else "proposed_tie",
            pitch_match=True,
            temporal_continuity=True,
            geometry_score=score,
            warnings=tuple(warnings),
        ))

    return tuple(sorted(results, key=lambda item: (item.source_event_id, item.arc_id)))


@dataclass(frozen=True)
class TieReviewConfirmation:
    candidate_index: int
    reviewer_confirmed: bool
    arc_is_tie_confirmed: bool
    same_notated_pitch_confirmed: bool


@dataclass(frozen=True)
class ReviewedTieDuration:
    source_event_id: str
    target_event_id: str
    combined_duration_quarters: Fraction


def build_reviewed_tie_durations(
    candidates: Sequence[TieLinkCandidate],
    confirmations: Sequence[TieReviewConfirmation],
    event_durations_quarters: Mapping[str, Fraction | int | float],
) -> tuple[ReviewedTieDuration, ...]:
    """Suma dos duraciones solo tras confirmar arco y misma nota escrita.

    Una propuesta ambigua nunca puede convertirse en ligadura confirmada.
    La confirmación humana debe verificar tanto que el arco sea una ligadura
    de prolongación como que ambas notas tengan la misma escritura musical.
    """
    seen_indices: set[int] = set()
    results: list[ReviewedTieDuration] = []
    for confirmation in confirmations:
        if not isinstance(confirmation, TieReviewConfirmation):
            raise ValueError("Todas las confirmaciones deben ser TieReviewConfirmation")
        index = confirmation.candidate_index
        if not isinstance(index, int) or isinstance(index, bool) or not 0 <= index < len(candidates):
            raise ValueError("candidate_index fuera del rango de candidatos")
        if index in seen_indices:
            raise ValueError("Una propuesta solo puede confirmarse una vez")
        seen_indices.add(index)
        candidate = candidates[index]
        if candidate.status != "proposed_tie":
            raise ValueError("Una propuesta ambigua no puede confirmarse")
        if confirmation.reviewer_confirmed is not True:
            raise ValueError("Se requiere revisión humana explícita")
        if confirmation.arc_is_tie_confirmed is not True:
            raise ValueError("El arco debe confirmarse como ligadura de prolongación")
        if confirmation.same_notated_pitch_confirmed is not True:
            raise ValueError("Debe confirmarse que ambas notas tienen la misma escritura")
        if candidate.source_event_id not in event_durations_quarters or candidate.target_event_id not in event_durations_quarters:
            raise ValueError("Faltan duraciones de uno o ambos eventos")
        combined = sum_tied_durations((
            event_durations_quarters[candidate.source_event_id],
            event_durations_quarters[candidate.target_event_id],
        ))
        results.append(ReviewedTieDuration(
            source_event_id=candidate.source_event_id,
            target_event_id=candidate.target_event_id,
            combined_duration_quarters=combined,
        ))
    return tuple(results)
