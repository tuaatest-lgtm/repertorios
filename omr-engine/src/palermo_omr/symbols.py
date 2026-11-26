"""Propuestas geométricas de cabezas de nota y posición diatónica.

La detección usa una apertura elíptica sobre la tinta original para extraer
el núcleo de cabezas rellenas aunque estén unidas a plicas, barras o líneas
del pentagrama. Los resultados siguen siendo candidatos visuales.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass

import cv2
import numpy as np

from .imaging import StaffCandidate


@dataclass(frozen=True)
class NoteheadCandidate:
    bbox: tuple[int, int, int, int]
    center_x: float
    center_y: float
    staff_index: int
    diatonic_step_from_bottom: int
    fill_ratio: float
    notehead_shape_score: float
    confidence: float

    def to_dict(self) -> dict:
        return asdict(self)


def detect_notehead_candidates(
    binary: np.ndarray,
    staves: list[StaffCandidate],
) -> list[NoteheadCandidate]:
    """Propone cabezas de nota rellenas y su posición diatónica aproximada.

    Se extrae el núcleo ovalado mediante apertura morfológica elíptica.
    Esto evita que una plica o una barra compartida convierta toda la nota
    en un único componente demasiado grande. Convención: 0 es la línea
    inferior; los espacios y líneas hacia arriba son 1, 2, 3...
    No asigna nombres de nota porque depende de la clave.
    """
    if binary is None or binary.ndim != 2 or binary.size == 0:
        raise ValueError("Se requiere una imagen binaria monocroma no vacía")
    if not staves:
        return []

    ink = (binary < 128).astype(np.uint8) * 255
    candidates: list[NoteheadCandidate] = []

    for staff_index, staff in enumerate(staves):
        if len(staff.lines_y) != 5:
            continue
        spacing = float(staff.spacing_px)
        if spacing <= 1:
            continue

        # El núcleo de una cabeza rellena suele ser ovalado. La apertura
        # elimina trazos finos (líneas, plicas y barras) y conserva su masa.
        kernel_width = max(5, int(round(spacing * 0.90)) | 1)
        kernel_height = max(3, int(round(spacing * 0.48)) | 1)
        kernel = cv2.getStructuringElement(
            cv2.MORPH_ELLIPSE, (kernel_width, kernel_height)
        )
        opened = cv2.morphologyEx(ink, cv2.MORPH_OPEN, kernel)

        top = max(0, int(round(staff.lines_y[0] - spacing * 1.7)))
        bottom = min(binary.shape[0], int(round(staff.lines_y[-1] + spacing * 1.7)))
        roi = opened[top:bottom, :]
        count, _, stats, centroids = cv2.connectedComponentsWithStats(
            roi, connectivity=8
        )

        min_w, max_w = spacing * 0.55, spacing * 2.0
        min_h, max_h = spacing * 0.30, spacing * 1.35

        for label in range(1, count):
            x, y, w, h, area = (int(v) for v in stats[label])
            cx, cy_local = (float(v) for v in centroids[label])
            cy = cy_local + top
            if not (min_w <= w <= max_w and min_h <= h <= max_h):
                continue

            aspect = w / max(h, 1)
            if not 0.85 <= aspect <= 2.6:
                continue

            bottom_line = float(staff.lines_y[-1])
            step = int(round((bottom_line - cy) / (spacing / 2.0)))
            snapped_y = bottom_line - step * spacing / 2.0
            vertical_error = abs(cy - snapped_y) / max(spacing / 2.0, 1.0)
            if vertical_error > 0.52:
                continue

            component = roi[y:y + h, x:x + w]
            fill_ratio = float(np.count_nonzero(component)) / max(w * h, 1)
            if not 0.20 <= fill_ratio <= 0.98:
                continue

            shape_score = max(0.0, 1.0 - abs(aspect - 1.35) / 1.75)
            alignment_score = max(0.0, 1.0 - vertical_error)
            size_score = min(1.0, w / max(spacing * 1.0, 1.0))
            fill_score = min(1.0, fill_ratio / 0.65)
            confidence = (
                0.35 * shape_score
                + 0.30 * alignment_score
                + 0.20 * size_score
                + 0.15 * fill_score
            )

            candidates.append(
                NoteheadCandidate(
                    bbox=(x, top + y, w, h),
                    center_x=round(cx, 2),
                    center_y=round(cy, 2),
                    staff_index=staff_index,
                    diatonic_step_from_bottom=step,
                    fill_ratio=round(fill_ratio, 3),
                    notehead_shape_score=round(shape_score, 3),
                    confidence=round(confidence, 3),
                )
            )

    candidates.sort(key=lambda item: (item.staff_index, item.center_x, item.center_y))
    return candidates
