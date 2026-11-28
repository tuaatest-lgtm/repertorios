"""Evidencia vectorial local de plicas y haces para PDFs digitales.

Este detector complementa el análisis raster cuando el PDF conserva trazos
vectoriales. No sustituye el detector raster y nunca interpreta la pendiente
como valor rítmico: el número de polígonos paralelos conectados a plicas
determina únicamente una duración candidata.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
import math
from collections import defaultdict
from collections.abc import Mapping, Sequence
from typing import Any

from .beam_groups import BeamGroupCandidate
from .imaging import StaffCandidate
from .rhythm import RhythmCandidate
from .symbols import NoteheadCandidate


@dataclass(frozen=True)
class VectorStemCandidate:
    notehead_index: int
    staff_index: int
    direction: str
    x_px: float
    length_px: float
    confidence: float
    status: str = "candidate_from_pdf_vector"

    def to_dict(self) -> dict:
        return {
            "notehead_index": self.notehead_index,
            "staff_index": self.staff_index,
            "direction": self.direction,
            "x_px": round(self.x_px, 2),
            "length_px": round(self.length_px, 2),
            "confidence": self.confidence,
            "status": self.status,
        }


@dataclass(frozen=True)
class _VectorLine:
    x: float
    y_min: float
    y_max: float


@dataclass(frozen=True)
class _VectorBeam:
    x_min: float
    y_min: float
    x_max: float
    y_max: float
    points: tuple[tuple[float, float], ...]


@dataclass(frozen=True)
class _MatchedBeam:
    beam: _VectorBeam
    notehead_indices: tuple[int, ...]
    staff_index: int
    center_y: float


def _black(value: Any) -> bool:
    return isinstance(value, (tuple, list)) and len(value) >= 3 and all(
        isinstance(channel, (int, float)) and abs(float(channel)) <= 0.12
        for channel in value[:3]
    )


def _extract_vector_lines(drawings: Sequence[Mapping], scale: float) -> list[_VectorLine]:
    lines = []
    for drawing in drawings:
        if not isinstance(drawing, Mapping) or drawing.get("type") != "s":
            continue
        color = drawing.get("color")
        if color is not None and not _black(color):
            continue
        for item in drawing.get("items", ()):
            if not isinstance(item, (tuple, list)) or len(item) < 3 or item[0] != "l":
                continue
            first, second = item[1], item[2]
            try:
                x1, y1 = float(first.x) * scale, float(first.y) * scale
                x2, y2 = float(second.x) * scale, float(second.y) * scale
            except AttributeError:
                try:
                    x1, y1 = float(first[0]) * scale, float(first[1]) * scale
                    x2, y2 = float(second[0]) * scale, float(second[1]) * scale
                except (TypeError, ValueError, IndexError):
                    continue
            if abs(x1 - x2) <= 2.0 and abs(y1 - y2) >= 4.0:
                lines.append(_VectorLine(
                    x=(x1 + x2) / 2.0,
                    y_min=min(y1, y2),
                    y_max=max(y1, y2),
                ))
    return lines


def detect_vector_stem_candidates(
    drawings: Sequence[Mapping],
    staves: Sequence[StaffCandidate],
    noteheads: Sequence[NoteheadCandidate],
    *,
    dpi: int = 300,
) -> tuple[VectorStemCandidate, ...]:
    """Busca plicas verticales vectoriales conectadas a bordes de cabezas."""
    if not isinstance(dpi, int) or isinstance(dpi, bool) or not 72 <= dpi <= 600:
        raise ValueError("dpi debe estar entre 72 y 600")
    if not isinstance(drawings, (list, tuple)):
        raise ValueError("drawings debe ser una secuencia de trazos PDF")
    scale = dpi / 72.0
    lines = _extract_vector_lines(drawings, scale)
    results = []
    for head_index, head in enumerate(noteheads):
        if not 0 <= head.staff_index < len(staves):
            raise ValueError("Una cabeza referencia un pentagrama inexistente")
        if head.notehead_shape_score < 0.70:
            continue
        staff = staves[head.staff_index]
        spacing = float(staff.spacing_px)
        if spacing <= 1:
            continue
        x, _y, width, _height = head.bbox
        expected = (
            (float(x + width - 2), "up"),
            (float(x + 1), "down"),
        )
        options = []
        for anchor_x, direction in expected:
            for line in lines:
                x_error = abs(line.x - anchor_x)
                if x_error > spacing * 0.22:
                    continue
                if direction == "up":
                    length = head.center_y - line.y_min
                    connected = line.y_max >= head.center_y - spacing * 0.25
                else:
                    length = line.y_max - head.center_y
                    connected = line.y_min <= head.center_y + spacing * 0.25
                if not connected or not spacing * 1.35 <= length <= spacing * 6.0:
                    continue
                score = 0.62 + 0.12 * (1.0 - x_error / (spacing * 0.22)) + 0.04 * min(1.0, length / (spacing * 3.5))
                options.append((score, direction, line.x, length))
        if options:
            score, direction, stem_x, length = max(options, key=lambda item: item[0])
            results.append(VectorStemCandidate(
                notehead_index=head_index,
                staff_index=head.staff_index,
                direction=direction,
                x_px=stem_x,
                length_px=length,
                confidence=round(min(0.78, score), 3),
            ))
    return tuple(results)


def apply_vector_stem_candidates(
    rhythms: Sequence[RhythmCandidate],
    candidates: Sequence[VectorStemCandidate],
) -> tuple[RhythmCandidate, ...]:
    """Completa plicas ausentes sin sobrescribir una dirección raster existente."""
    by_index = {}
    for candidate in candidates:
        if candidate.notehead_index in by_index:
            previous = by_index[candidate.notehead_index]
            if previous.direction != candidate.direction:
                raise ValueError("Una cabeza tiene candidatos vectoriales de plica en conflicto")
            if candidate.confidence > previous.confidence:
                by_index[candidate.notehead_index] = candidate
        else:
            by_index[candidate.notehead_index] = candidate
    if any(index < 0 or index >= len(rhythms) for index in by_index):
        raise ValueError("Un candidato vectorial referencia una cabeza inexistente")

    updated = []
    for index, rhythm in enumerate(rhythms):
        candidate = by_index.get(index)
        if candidate is None or rhythm.stem_direction != "none":
            updated.append(rhythm)
            continue
        duration = rhythm.base_duration
        if rhythm.notehead_fill == "filled" and duration == "unknown" and rhythm.beam_count == 0:
            duration = "quarter"
        warning = (
            "Plica candidata recuperada desde trazos vectoriales del PDF; "
            "requiere revisión visual y no confirma la figura."
        )
        updated.append(replace(
            rhythm,
            stem_direction=candidate.direction,
            stem_length_px=int(round(candidate.length_px)),
            base_duration=duration,
            confidence=min(0.78, max(rhythm.confidence, candidate.confidence)),
            warnings=tuple(dict.fromkeys((*rhythm.warnings, warning))),
        ))
    return tuple(updated)


def _extract_vector_beams(drawings: Sequence[Mapping], scale: float) -> list[_VectorBeam]:
    beams = []
    for drawing in drawings:
        if not isinstance(drawing, Mapping) or drawing.get("type") not in {"f", "fs"}:
            continue
        fill = drawing.get("fill")
        if fill is not None and not _black(fill):
            continue
        rect = drawing.get("rect")
        try:
            x_min, y_min, x_max, y_max = (
                float(rect.x0) * scale, float(rect.y0) * scale,
                float(rect.x1) * scale, float(rect.y1) * scale,
            )
        except AttributeError:
            try:
                x_min, y_min, x_max, y_max = (float(value) * scale for value in rect)
            except (TypeError, ValueError):
                continue
        points = []
        valid = True
        for item in drawing.get("items", ()):
            if not isinstance(item, (tuple, list)) or len(item) < 3 or item[0] != "l":
                valid = False
                break
            for point in item[1:3]:
                try:
                    candidate = (float(point.x) * scale, float(point.y) * scale)
                except AttributeError:
                    try:
                        candidate = (float(point[0]) * scale, float(point[1]) * scale)
                    except (TypeError, ValueError, IndexError):
                        valid = False
                        break
                if not points or math.dist(candidate, points[-1]) > 0.2:
                    points.append(candidate)
            if not valid:
                break
        if not valid or len(points) < 4:
            continue
        if math.dist(points[0], points[-1]) <= 0.2:
            points.pop()
        beams.append(_VectorBeam(
            x_min=x_min, y_min=y_min, x_max=x_max, y_max=y_max,
            points=tuple(points),
        ))
    return beams


def _centerline_y(beam: _VectorBeam, x: float) -> float | None:
    intersections = []
    points = beam.points
    for first, second in zip(points, points[1:] + points[:1]):
        x1, y1 = first
        x2, y2 = second
        if abs(x2 - x1) < 1e-6:
            if abs(x - x1) <= 0.5:
                intersections.extend((y1, y2))
            continue
        if min(x1, x2) - 0.2 <= x <= max(x1, x2) + 0.2:
            ratio = (x - x1) / (x2 - x1)
            if -0.01 <= ratio <= 1.01:
                intersections.append(y1 + ratio * (y2 - y1))
    if len(intersections) < 2:
        return None
    return (min(intersections) + max(intersections)) / 2.0


def detect_vector_beam_group_candidates(
    drawings: Sequence[Mapping],
    staves: Sequence[StaffCandidate],
    noteheads: Sequence[NoteheadCandidate],
    *,
    dpi: int = 300,
) -> tuple[BeamGroupCandidate, ...]:
    """Agrupa polígonos de haces PDF mediante plicas vectoriales explícitas."""
    stems = detect_vector_stem_candidates(drawings, staves, noteheads, dpi=dpi)
    stems_by_head = {item.notehead_index: item for item in stems}
    beams = _extract_vector_beams(drawings, dpi / 72.0)
    matched: list[_MatchedBeam] = []

    for beam in beams:
        width = beam.x_max - beam.x_min
        height = beam.y_max - beam.y_min
        if width <= 0 or height <= 0:
            continue
        for staff_index, staff in enumerate(staves):
            spacing = float(staff.spacing_px)
            if spacing <= 1:
                continue
            if not (
                spacing * 1.2 <= width <= spacing * 10.0
                and height <= spacing * 1.2
                and width / max(height, 1.0) >= 4.0
            ):
                continue
            heads = []
            centers = []
            for head_index, head in enumerate(noteheads):
                if head.staff_index != staff_index:
                    continue
                stem = stems_by_head.get(head_index)
                if stem is None or not beam.x_min - spacing * 0.2 <= stem.x_px <= beam.x_max + spacing * 0.2:
                    continue
                beam_y = _centerline_y(beam, stem.x_px)
                if beam_y is None:
                    continue
                distance = beam_y - head.center_y
                if stem.direction == "up":
                    connected = (
                        -spacing * 4.5 <= distance <= -spacing * 0.8
                        and beam.y_min - spacing * 0.1 <= beam_y <= beam.y_max + spacing * 0.1
                    )
                else:
                    connected = (
                        spacing * 0.8 <= distance <= spacing * 4.5
                        and beam.y_min - spacing * 0.1 <= beam_y <= beam.y_max + spacing * 0.1
                    )
                if not connected:
                    continue
                heads.append(head_index)
                centers.append(beam_y)
            if heads:
                order = sorted(range(len(heads)), key=lambda index: noteheads[heads[index]].center_x)
                ordered_heads = tuple(heads[index] for index in order)
                matched.append(_MatchedBeam(
                    beam=beam,
                    notehead_indices=ordered_heads,
                    staff_index=staff_index,
                    center_y=float(sum(centers) / len(centers)),
                ))

    grouped: dict[tuple[int, tuple[int, ...]], list[_MatchedBeam]] = defaultdict(list)
    for item in matched:
        grouped[(item.staff_index, item.notehead_indices)].append(item)

    results = []
    for (staff_index, head_indices), items in sorted(grouped.items()):
        spacing = float(staves[staff_index].spacing_px)
        items.sort(key=lambda item: item.center_y)
        clusters: list[list[_MatchedBeam]] = []
        for item in items:
            if not clusters or item.center_y - clusters[-1][-1].center_y > spacing * 0.75:
                clusters.append([item])
            else:
                clusters[-1].append(item)
        for cluster in clusters:
            x_min = min(item.beam.x_min for item in cluster)
            y_min = min(item.beam.y_min for item in cluster)
            x_max = max(item.beam.x_max for item in cluster)
            y_max = max(item.beam.y_max for item in cluster)
            beam_count = min(4, len(cluster))
            partial = len(head_indices) == 1
            confidence = min(
                0.84,
                0.66 + 0.04 * max(0, len(head_indices) - 2) + 0.04 * (beam_count - 1),
            )
            results.append(BeamGroupCandidate(
                staff_index=staff_index,
                notehead_indices=list(head_indices),
                bbox=(
                    int(round(x_min)), int(round(y_min)),
                    int(round(x_max - x_min)), int(round(y_max - y_min)),
                ),
                beam_count_candidate=beam_count,
                confidence=round(confidence, 3),
                warning=(
                    "Haz parcial vectorial unido a una plica; puede ser bandera y requiere revisión."
                    if partial else
                    "Grupo de haces vectoriales unido a plicas; requiere revisión musical."
                ),
                connection_type_candidate="partial" if partial else "shared",
            ))
    results.sort(key=lambda item: (item.staff_index, item.bbox[0], item.bbox[1]))
    return tuple(results)


def merge_beam_group_candidates(
    raster_groups: Sequence[BeamGroupCandidate],
    vector_groups: Sequence[BeamGroupCandidate],
) -> tuple[BeamGroupCandidate, ...]:
    """Deduplica grupos raster/vector; conserva evidencia compartida más fuerte."""
    selected: dict[tuple[int, tuple[int, ...], int], BeamGroupCandidate] = {}
    for candidate in (*raster_groups, *vector_groups):
        key = (
            candidate.staff_index,
            tuple(sorted(candidate.notehead_indices)),
            candidate.beam_count_candidate,
        )
        previous = selected.get(key)
        if previous is None:
            selected[key] = candidate
            continue
        rank = (
            candidate.connection_type_candidate == "shared",
            candidate.confidence,
        )
        previous_rank = (
            previous.connection_type_candidate == "shared",
            previous.confidence,
        )
        if rank > previous_rank:
            selected[key] = candidate
    return tuple(sorted(
        selected.values(),
        key=lambda item: (item.staff_index, item.bbox[0], item.bbox[1]),
    ))
