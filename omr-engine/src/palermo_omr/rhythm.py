"""Análisis rítmico geométrico inicial de candidatos de nota.

Las salidas son hipótesis con confianza, no transcripciones musicales validadas.
La detección de ligaduras, silencios, puntillos y voces queda fuera de esta fase.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import cv2
import numpy as np

from .imaging import StaffCandidate
from .symbols import NoteheadCandidate


@dataclass(frozen=True)
class RhythmCandidate:
    notehead_bbox: tuple[int, int, int, int]
    staff_index: int
    notehead_fill: str
    notehead_fill_score: float
    stem_direction: str
    stem_length_px: int
    beam_count: int
    base_duration: str
    confidence: float
    warnings: tuple[str, ...]

    def to_dict(self) -> dict:
        return asdict(self)


def _ink(binary: np.ndarray) -> np.ndarray:
    return (binary < 128).astype(np.uint8)


def _classify_fill(binary: np.ndarray, head: NoteheadCandidate, spacing: float) -> tuple[str, float]:
    """Mide el núcleo de la cabeza, evitando la fila central de una línea del pentagrama."""
    ink = _ink(binary)
    cx, cy = int(round(head.center_x)), int(round(head.center_y))
    rx = max(2, int(round(spacing * 0.22)))
    ry = max(2, int(round(spacing * 0.16)))
    x0, x1 = max(0, cx-rx), min(binary.shape[1], cx+rx+1)
    y0, y1 = max(0, cy-ry), min(binary.shape[0], cy+ry+1)
    roi = ink[y0:y1, x0:x1].copy()
    if roi.size == 0:
        return "unknown", 0.0

    yy, xx = np.ogrid[y0:y1, x0:x1]
    ellipse = ((xx-cx) / max(rx, 1))**2 + ((yy-cy) / max(ry, 1))**2 <= 1.0
    # La línea horizontal del pentagrama puede atravesar una cabeza en línea.
    ellipse &= np.abs(yy-cy) > max(1, int(round(spacing * 0.045)))
    sample = ink[y0:y1, x0:x1][ellipse]
    if sample.size < 5:
        return "unknown", 0.0
    ratio = float(np.mean(sample))
    if ratio >= 0.58:
        return "filled", min(1.0, (ratio - 0.45) / 0.45)
    if ratio <= 0.28:
        return "hollow", min(1.0, (0.42 - ratio) / 0.42)
    return "unknown", 0.35


def _stem(binary: np.ndarray, head: NoteheadCandidate, spacing: float) -> tuple[str, int]:
    """Busca una plica vertical próxima a uno de los extremos de la cabeza."""
    ink = _ink(binary)
    h, w = ink.shape
    cx, cy = int(round(head.center_x)), int(round(head.center_y))
    radius = max(1, int(round(spacing * 0.42)))
    klen = max(3, int(round(spacing * 1.8)))
    vertical = cv2.morphologyEx(
        ink, cv2.MORPH_OPEN,
        cv2.getStructuringElement(cv2.MORPH_RECT, (1, klen))
    )
    best = ("none", 0)
    for offset in (-radius, radius):
        x = cx + offset
        if x < 0 or x >= w:
            continue
        col = vertical[:, max(0, x-1):min(w, x+2)].max(axis=1)
        for direction, indices in (
            ("up", range(max(0, cy-int(spacing*0.25)), -1, -1)),
            ("down", range(min(h-1, cy+int(spacing*0.25)), h)),
        ):
            run = 0
            max_run = 0
            for y in indices:
                if col[y]:
                    run += 1
                    max_run = max(max_run, run)
                elif run:
                    break
            if max_run > best[1]:
                best = (direction, max_run)
    if best[1] < int(spacing * 1.35):
        return "none", best[1]
    return best


def _beam_count(binary: np.ndarray, head: NoteheadCandidate, spacing: float) -> int:
    """Cuenta trazos horizontales cortos próximos a la región de plica."""
    ink = _ink(binary)
    h, w = ink.shape
    cx, cy = int(round(head.center_x)), int(round(head.center_y))
    pad_x = int(round(spacing * 2.5))
    pad_y = int(round(spacing * 3.2))
    x0, x1 = max(0, cx-pad_x), min(w, cx+pad_x+1)
    y0, y1 = max(0, cy-pad_y), min(h, cy+pad_y+1)
    roi = ink[y0:y1, x0:x1]
    if roi.size == 0:
        return 0
    kw = max(3, int(round(spacing * 1.1)))
    horizontal = cv2.morphologyEx(
        roi, cv2.MORPH_OPEN,
        cv2.getStructuringElement(cv2.MORPH_RECT, (kw, 1))
    )
    rows = np.flatnonzero(horizontal.sum(axis=1) >= kw)
    if rows.size == 0:
        return 0
    groups = 1 + int(np.count_nonzero(np.diff(rows) > max(1, int(spacing * 0.35))))
    return min(groups, 4)


def analyze_rhythm_candidates(
    binary: np.ndarray,
    staves: list[StaffCandidate],
    noteheads: list[NoteheadCandidate],
) -> list[RhythmCandidate]:
    """Añade una hipótesis de valor base a cada cabeza candidata."""
    if binary is None or binary.ndim != 2 or binary.size == 0:
        raise ValueError("Se requiere una imagen binaria monocroma no vacía")
    results: list[RhythmCandidate] = []
    for head in noteheads:
        if head.staff_index >= len(staves):
            continue
        spacing = float(staves[head.staff_index].spacing_px)
        if spacing <= 1:
            continue
        fill, fill_score = _classify_fill(binary, head, spacing)
        direction, stem_length = _stem(binary, head, spacing)
        beams = _beam_count(binary, head, spacing)

        duration = "unknown"
        warnings: list[str] = []
        if fill == "hollow" and direction == "none":
            duration = "whole"
            warnings.append("No distingue redonda de figuras mayores.")
        elif fill == "hollow" and direction != "none":
            duration = "half"
        elif fill == "filled" and direction != "none":
            duration = {0: "quarter", 1: "eighth", 2: "sixteenth", 3: "thirty_second", 4: "sixty_fourth"}[beams]
        elif fill == "filled":
            warnings.append("Cabeza rellena sin plica confirmada; duración indeterminada.")
        else:
            warnings.append("Relleno de cabeza ambiguo.")

        if beams:
            warnings.append("La agrupación de barras es una hipótesis geométrica.")
        confidence = min(0.95, 0.45 * fill_score + (0.4 if direction != "none" else 0.0) + (0.15 if duration != "unknown" else 0.0))
        results.append(RhythmCandidate(
            notehead_bbox=head.bbox,
            staff_index=head.staff_index,
            notehead_fill=fill,
            notehead_fill_score=round(fill_score, 3),
            stem_direction=direction,
            stem_length_px=int(stem_length),
            beam_count=beams,
            base_duration=duration,
            confidence=round(confidence, 3),
            warnings=tuple(warnings),
        ))
    return results
