"""Herramientas de visualización para inspeccionar candidatos OMR."""

from __future__ import annotations

import cv2
import numpy as np

from .symbols import NoteheadCandidate


def draw_notehead_overlay(
    page_image: np.ndarray,
    candidates: list[NoteheadCandidate],
) -> np.ndarray:
    """Dibuja candidatos; etiqueta solo los de confianza inferior a 0.75.

    Verde: confianza >= 0.75; ámbar: >= 0.50; rojo: < 0.50.
    Se omiten etiquetas verdes para evitar saturar partituras densas. La posición
    y puntuación de todos los candidatos permanecen en analysis.json. Los colores
    expresan una puntuación heurística, no validación musical.
    """
    if page_image is None or page_image.size == 0:
        raise ValueError("La imagen de página está vacía")
    if page_image.ndim != 3 or page_image.shape[2] != 3:
        raise ValueError("Se requiere una imagen BGR de tres canales")

    overlay = page_image.copy()
    height, width = overlay.shape[:2]

    for candidate in candidates:
        x, y, box_width, box_height = candidate.bbox
        if box_width <= 0 or box_height <= 0:
            continue
        x1, y1 = max(0, x), max(0, y)
        x2, y2 = min(width - 1, x + box_width), min(height - 1, y + box_height)
        if x1 >= width or y1 >= height or x2 < 0 or y2 < 0:
            continue

        if candidate.confidence >= 0.75:
            color = (40, 180, 40)
        elif candidate.confidence >= 0.50:
            color = (0, 165, 255)
        else:
            color = (40, 40, 220)

        center = (
            int(round(candidate.center_x)),
            int(round(candidate.center_y)),
        )
        cv2.rectangle(overlay, (x1, y1), (x2, y2), color, 2)
        cv2.circle(overlay, center, 3, color, -1)
        label = (
            f"S{candidate.staff_index + 1} "
            f"p{candidate.diatonic_step_from_bottom:+d} "
            f"{candidate.confidence:.2f}"
        )
        text_y = max(14, y1 - 5)
        cv2.putText(
            overlay, label, (x1, text_y),
            cv2.FONT_HERSHEY_SIMPLEX, 0.38, color, 1, cv2.LINE_AA,
        )

    return overlay
