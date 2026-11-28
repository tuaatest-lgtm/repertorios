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
    stem_x: int | None = None

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


def _stem(
    binary: np.ndarray,
    head: NoteheadCandidate,
    spacing: float,
) -> tuple[str, int, int | None]:
    """Localiza la plica desde los bordes reales de la cabeza.

    La versión anterior muestreaba solo centro_x ± 0.72 * spacing. En cabezas
    cuyo bbox o núcleo ovalado está desplazado unos píxeles, esa posición cae
    dentro/fuera de la plica y provoca pérdida o inversión de dirección.
    Ahora se inspeccionan bandas estrechas junto a ambos bordes del bbox y se
    conserva la coordenada x real para validar después su unión con las barras.
    """
    if spacing <= 1:
        return "none", 0, None
    ink = _ink(binary)
    height, width = ink.shape
    x0, y0, box_width, box_height = head.bbox
    x1 = x0 + box_width - 1
    y1 = y0 + box_height - 1
    edge_band = max(2, int(round(min(spacing * 0.40, box_width * 0.32))))
    vertical = cv2.morphologyEx(
        ink,
        cv2.MORPH_OPEN,
        cv2.getStructuringElement(
            cv2.MORPH_RECT, (1, max(3, int(round(spacing * 1.8))))
        ),
    )

    candidates: list[tuple[int, str, int]] = []
    edge_ranges = (
        range(max(0, x0 - 2), min(width, x0 + edge_band + 1)),
        range(max(0, x1 - edge_band + 1), min(width, x1 + 3)),
    )
    for edge_xs in edge_ranges:
        for x in edge_xs:
            col = vertical[:, max(0, x - 1):min(width, x + 2)].max(axis=1)
            ys = np.flatnonzero(col)
            if ys.size == 0:
                continue
            runs = np.split(ys, np.where(np.diff(ys) > 1)[0] + 1)
            for run in runs:
                # La plica debe atravesar la zona central de la cabeza; así
                # evitamos aceptar una barra o plica vecina que solo pasa cerca.
                if run[-1] < y0 + box_height * 0.25:
                    continue
                if run[0] > y0 + box_height * 0.75:
                    continue
                up_length = max(0, y0 - int(run[0]))
                down_length = max(0, int(run[-1]) - y1)
                if up_length >= down_length:
                    direction, length = "up", up_length
                else:
                    direction, length = "down", down_length
                if length >= int(spacing * 1.35):
                    candidates.append((int(x), direction, int(length)))

    if not candidates:
        return "none", 0, None
    # Evita que una detección marginal en el borde opuesto venza a una plica
    # claramente conectada. Si ambas direcciones tienen extensiones similares,
    # no inventa una dirección.
    candidates.sort(key=lambda item: item[2], reverse=True)
    best = candidates[0]
    competing = next(
        (item for item in candidates[1:] if item[1] != best[1]),
        None,
    )
    if competing and best[2] - competing[2] < int(spacing * 0.35):
        return "none", best[2], None
    return best[1], best[2], best[0]


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
        direction, stem_length, stem_x = _stem(binary, head, spacing)
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
            direction,int(stem_length),beams,duration,round(confidence,3),tuple(warnings),stem_x))
    return results
