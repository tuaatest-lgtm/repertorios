"""Detección y agrupación preliminar de barras y regiones de compás.

Los resultados son candidatos geométricos. La segmentación de sistemas usa
separaciones verticales relativas al espaciado de los pentagramas; no intenta
inferir llaves, instrumentación ni la función musical de cada pentagrama.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass

import cv2
import numpy as np

from .imaging import StaffCandidate


@dataclass(frozen=True)
class StaffSystemCandidate:
    system_index: int
    staff_indices: list[int]
    y_top: float
    y_bottom: float
    confidence: float
    warning: str

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class BarlineCandidate:
    x: float
    y_top: int
    y_bottom: int
    width_px: int
    staff_index: int
    coverage: float
    confidence: float
    warning: str

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class SystemBarlineCandidate:
    x: float
    staff_indices: list[int]
    support_count: int
    confidence: float
    warning: str
    system_index: int = 0

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class MeasureSpanCandidate:
    staff_index: int
    measure_index: int
    x_start: float
    x_end: float
    width_px: float
    left_boundary_observed: bool
    right_boundary_observed: bool
    confidence: float
    warning: str

    def to_dict(self) -> dict:
        return asdict(self)


def detect_staff_systems(
    staves: list[StaffCandidate],
    *,
    max_interstaff_gap_spacing: float = 5.5,
) -> list[StaffSystemCandidate]:
    """Agrupa pentagramas consecutivos en sistemas geométricos candidatos.

    La distancia se mide desde la última línea del pentagrama superior hasta
    la primera línea del siguiente, normalizada por el espaciado típico.
    Un salto vertical grande inicia otro sistema. Es una heurística: no
    sustituye el reconocimiento de llaves, brackets ni la estructura musical.
    """
    if max_interstaff_gap_spacing <= 0:
        raise ValueError("max_interstaff_gap_spacing debe ser positivo")
    if not staves:
        return []

    valid = [
        (index, staff)
        for index, staff in enumerate(staves)
        if len(staff.lines_y) == 5 and staff.spacing_px > 1
    ]
    if not valid:
        return []

    valid.sort(key=lambda pair: pair[1].lines_y[0])
    typical_spacing = float(np.median([staff.spacing_px for _, staff in valid]))
    groups: list[list[tuple[int, StaffCandidate]]] = [[valid[0]]]

    for item in valid[1:]:
        previous = groups[-1][-1][1]
        current = item[1]
        gap = float(current.lines_y[0] - previous.lines_y[-1])
        if gap / typical_spacing > max_interstaff_gap_spacing:
            groups.append([item])
        else:
            groups[-1].append(item)

    systems: list[StaffSystemCandidate] = []
    for system_index, group in enumerate(groups):
        indices = [index for index, _ in group]
        y_top = float(min(staff.lines_y[0] for _, staff in group))
        y_bottom = float(max(staff.lines_y[-1] for _, staff in group))
        systems.append(
            StaffSystemCandidate(
                system_index=system_index,
                staff_indices=indices,
                y_top=round(y_top, 2),
                y_bottom=round(y_bottom, 2),
                confidence=0.65,
                warning=(
                    "Sistema candidato por proximidad vertical; debe verificarse "
                    "visualmente. No identifica piano, coro, llaves ni voces."
                ),
            )
        )
    return systems


def detect_barline_candidates(
    binary: np.ndarray,
    staves: list[StaffCandidate],
) -> list[BarlineCandidate]:
    """Propone barras verticales que atraviesan la mayor parte del pentagrama."""
    if binary is None or binary.ndim != 2 or binary.size == 0:
        raise ValueError("Se requiere una imagen binaria monocroma no vacía")

    ink = cv2.bitwise_not(binary)
    results: list[BarlineCandidate] = []
    for staff_index, staff in enumerate(staves):
        if len(staff.lines_y) != 5 or staff.spacing_px <= 1:
            continue

        top = int(round(staff.lines_y[0]))
        bottom = int(round(staff.lines_y[-1]))
        staff_height = bottom - top
        if staff_height <= 0 or top < 0 or bottom >= binary.shape[0]:
            continue

        kernel_height = max(3, int(round(staff.spacing_px * 3.2)))
        vertical = cv2.morphologyEx(
            ink,
            cv2.MORPH_OPEN,
            cv2.getStructuringElement(cv2.MORPH_RECT, (1, kernel_height)),
        )
        roi = vertical[top:bottom + 1, :]
        count, _, stats, centroids = cv2.connectedComponentsWithStats(roi, 8)

        for label in range(1, count):
            _, y, width, height, _ = (int(v) for v in stats[label])
            if width > max(2, int(round(staff.spacing_px * 0.35))):
                continue
            coverage = height / max(staff_height, 1)
            if coverage < 0.78:
                continue
            center_x = float(centroids[label][0])
            results.append(
                BarlineCandidate(
                    x=round(center_x, 2),
                    y_top=top + y,
                    y_bottom=top + y + height - 1,
                    width_px=width,
                    staff_index=staff_index,
                    coverage=round(min(1.0, coverage), 3),
                    confidence=round(min(0.9, 0.55 + 0.35 * min(1.0, coverage)), 3),
                    warning=(
                        "Candidato geométrico no confirmado: debe distinguirse de "
                        "trazos verticales, límites de sistema y otros símbolos."
                    ),
                )
            )

    results.sort(key=lambda item: (item.staff_index, item.x))
    return results


def group_system_barlines(
    candidates: list[BarlineCandidate],
    staves: list[StaffCandidate],
    *,
    x_tolerance_spacing: float = 0.8,
    min_staff_support: int = 2,
    max_interstaff_gap_spacing: float = 5.5,
) -> list[SystemBarlineCandidate]:
    """Agrupa barras alineadas, sin mezclar sistemas separados verticalmente."""
    if x_tolerance_spacing <= 0:
        raise ValueError("x_tolerance_spacing debe ser positivo")
    if min_staff_support < 1:
        raise ValueError("min_staff_support debe ser al menos 1")
    if max_interstaff_gap_spacing <= 0:
        raise ValueError("max_interstaff_gap_spacing debe ser positivo")
    if not candidates or not staves:
        return []

    systems = detect_staff_systems(
        staves, max_interstaff_gap_spacing=max_interstaff_gap_spacing
    )
    staff_to_system = {
        staff_index: system.system_index
        for system in systems
        for staff_index in system.staff_indices
    }
    typical_spacing = float(np.median([s.spacing_px for s in staves if s.spacing_px > 1]))
    tolerance = max(2.0, typical_spacing * x_tolerance_spacing)

    by_system: dict[int, list[BarlineCandidate]] = {}
    for candidate in candidates:
        system_index = staff_to_system.get(candidate.staff_index)
        if system_index is not None:
            by_system.setdefault(system_index, []).append(candidate)

    results: list[SystemBarlineCandidate] = []
    for system_index, system_candidates in sorted(by_system.items()):
        ordered = sorted(system_candidates, key=lambda item: item.x)
        clusters: list[list[BarlineCandidate]] = []
        for candidate in ordered:
            if (
                not clusters
                or candidate.x - float(np.mean([v.x for v in clusters[-1]])) > tolerance
            ):
                clusters.append([candidate])
            else:
                clusters[-1].append(candidate)

        for cluster in clusters:
            by_staff: dict[int, BarlineCandidate] = {}
            for candidate in cluster:
                current = by_staff.get(candidate.staff_index)
                if current is None or candidate.confidence > current.confidence:
                    by_staff[candidate.staff_index] = candidate
            staff_indices = sorted(by_staff)
            if len(staff_indices) < min_staff_support:
                continue
            mean_x = float(np.mean([item.x for item in by_staff.values()]))
            confidence = float(np.mean([item.confidence for item in by_staff.values()]))
            results.append(
                SystemBarlineCandidate(
                    x=round(mean_x, 2),
                    staff_indices=staff_indices,
                    support_count=len(staff_indices),
                    confidence=round(confidence, 3),
                    warning=(
                        "Alineación probable dentro de un sistema geométrico candidato; "
                        "no confirma por sí sola el límite métrico."
                    ),
                    system_index=system_index,
                )
            )
    return sorted(results, key=lambda item: (item.system_index, item.x))


def infer_measure_spans(
    candidates: list[BarlineCandidate],
    *,
    min_width_px: float = 8.0,
) -> list[MeasureSpanCandidate]:
    """Crea intervalos entre barras consecutivas dentro de cada pentagrama."""
    if min_width_px <= 0:
        raise ValueError("min_width_px debe ser positivo")

    by_staff: dict[int, list[BarlineCandidate]] = {}
    for candidate in candidates:
        by_staff.setdefault(candidate.staff_index, []).append(candidate)

    spans: list[MeasureSpanCandidate] = []
    for staff_index, bars in sorted(by_staff.items()):
        bars.sort(key=lambda item: item.x)
        measure_index = 1
        for left, right in zip(bars, bars[1:]):
            width = right.x - left.x
            if width < min_width_px:
                continue
            spans.append(
                MeasureSpanCandidate(
                    staff_index=staff_index,
                    measure_index=measure_index,
                    x_start=left.x,
                    x_end=right.x,
                    width_px=round(width, 2),
                    left_boundary_observed=True,
                    right_boundary_observed=True,
                    confidence=round(min(left.confidence, right.confidence), 3),
                    warning=(
                        "Intervalo geométrico entre barras candidatas; no es un "
                        "compás musical validado hasta reconocer figuras y métrica."
                    ),
                )
            )
            measure_index += 1
    return spans
