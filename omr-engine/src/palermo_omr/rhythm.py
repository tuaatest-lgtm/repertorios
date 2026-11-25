"""Análisis rítmico geométrico preliminar.

Los resultados son hipótesis visuales, nunca eventos musicales confirmados.
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
    ink = _ink(binary)
    cx, cy = int(round(head.center_x)), int(round(head.center_y))
    rx, ry = max(3, int(round(spacing * .38))), max(2, int(round(spacing * .28)))
    x0, x1 = max(0, cx-rx), min(binary.shape[1], cx+rx+1)
    y0, y1 = max(0, cy-ry), min(binary.shape[0], cy+ry+1)
    yy, xx = np.ogrid[y0:y1, x0:x1]
    ellipse = ((xx-cx)/rx)**2 + ((yy-cy)/ry)**2 <= 1.0
    ellipse &= np.abs(yy-cy) > max(1, int(round(spacing*.045)))
    sample = ink[y0:y1, x0:x1][ellipse]
    if sample.size < 5:
        return "unknown", 0.0
    ratio = float(np.mean(sample))
    if ratio >= .58:
        return "filled", min(1.0, (ratio-.45)/.45)
    if ratio <= .28:
        return "hollow", min(1.0, (.42-ratio)/.42)
    return "unknown", .35


def _stem(binary: np.ndarray, head: NoteheadCandidate, spacing: float) -> tuple[str, int]:
    ink = _ink(binary)
    h, w = ink.shape
    cx, cy = int(round(head.center_x)), int(round(head.center_y))
    radius = max(1, int(round(spacing*.72)))
    vertical = cv2.morphologyEx(ink, cv2.MORPH_OPEN,
        cv2.getStructuringElement(cv2.MORPH_RECT, (1, max(3, int(round(spacing*1.8))))))
    best = ("none", 0)
    for x in (cx-radius, cx+radius):
        if not 0 <= x < w:
            continue
        col = vertical[:, max(0,x-1):min(w,x+2)].max(axis=1)
        for direction, indices in (
            ("up", range(max(0,cy-int(spacing*.25)), -1, -1)),
            ("down", range(min(h-1,cy+int(spacing*.25)), h)),
        ):
            run = maximum = 0
            for y in indices:
                if col[y]:
                    run += 1
                    maximum = max(maximum, run)
                elif run:
                    break
            if maximum > best[1]:
                best = (direction, maximum)
    return best if best[1] >= int(spacing*1.35) else ("none", best[1])


def _beam_count(binary: np.ndarray, head: NoteheadCandidate, spacing: float) -> int:
    ink = _ink(binary)
    h, w = ink.shape
    cx, cy = int(round(head.center_x)), int(round(head.center_y))
    x0, x1 = max(0,cx-int(spacing*3)), min(w,cx+int(spacing*3)+1)
    y0, y1 = max(0,cy-int(spacing*3.2)), min(h,cy+int(spacing*3.2)+1)
    roi = ink[y0:y1,x0:x1]
    kw = max(3,int(round(spacing*1.05)))
    horizontal = cv2.morphologyEx(roi,cv2.MORPH_OPEN,
        cv2.getStructuringElement(cv2.MORPH_RECT,(kw,1)))
    count, _, stats, centroids = cv2.connectedComponentsWithStats(horizontal,8)
    rows = []
    for label in range(1,count):
        _,_,cw,ch,_ = (int(v) for v in stats[label])
        row = y0 + float(centroids[label][1])
        if abs(row-cy) < spacing*.75:
            continue
        if spacing*.9 <= cw <= spacing*5 and ch <= max(2,int(spacing*.4)):
            rows.append(row)
    if not rows:
        return 0
    rows.sort()
    groups = 1 + sum(1 for a,b in zip(rows,rows[1:]) if b-a > max(1.5,spacing*.35))
    return min(groups,4)


def analyze_rhythm_candidates(binary: np.ndarray, staves: list[StaffCandidate],
                              noteheads: list[NoteheadCandidate]) -> list[RhythmCandidate]:
    """Propone relleno, plica y valor base para cada cabeza candidata."""
    if binary is None or binary.ndim != 2 or binary.size == 0:
        raise ValueError("Se requiere una imagen binaria monocroma no vacía")
    results = []
    for head in noteheads:
        if not 0 <= head.staff_index < len(staves):
            continue
        spacing = float(staves[head.staff_index].spacing_px)
        if spacing <= 1:
            continue
        fill, fill_score = _classify_fill(binary,head,spacing)
        direction, stem_length = _stem(binary,head,spacing)
        beams = _beam_count(binary,head,spacing)
        duration = "unknown"
        warnings = []
        if fill == "hollow" and direction == "none":
            duration = "whole"
            warnings.append("No distingue redonda de figuras mayores.")
        elif fill == "hollow" and direction != "none":
            duration = "half"
        elif fill == "filled" and direction != "none":
            duration = {0:"quarter",1:"eighth",2:"sixteenth",3:"thirty_second",4:"sixty_fourth"}[beams]
        elif fill == "filled":
            warnings.append("Cabeza rellena sin plica confirmada.")
        else:
            warnings.append("Relleno de cabeza ambiguo.")
        if beams:
            warnings.append("La agrupación de barras es una hipótesis geométrica.")
        confidence = min(.95,.45*fill_score+(.4 if direction!="none" else 0)+(.15 if duration!="unknown" else 0))
        results.append(RhythmCandidate(head.bbox,head.staff_index,fill,round(fill_score,3),
            direction,int(stem_length),beams,duration,round(confidence,3),tuple(warnings)))
    return results
