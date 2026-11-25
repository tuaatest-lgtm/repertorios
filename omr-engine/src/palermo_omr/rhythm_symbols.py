"""Candidatos geométricos de puntillos y símbolos de silencio.

No asigna silencios musicales definitivos: la forma y el contexto se deben
validar con el sistema completo y con revisión humana.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import cv2
import numpy as np

from .imaging import StaffCandidate
from .symbols import NoteheadCandidate


@dataclass(frozen=True)
class DotCandidate:
    x: float
    y: float
    associated_notehead_index: int
    confidence: float

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class RestSymbolCandidate:
    bbox: tuple[int, int, int, int]
    staff_index: int
    shape_score: float
    confidence: float
    warning: str

    def to_dict(self) -> dict:
        return asdict(self)


def detect_augmentation_dot_candidates(
    binary: np.ndarray,
    staves: list[StaffCandidate],
    noteheads: list[NoteheadCandidate],
) -> list[DotCandidate]:
    """Busca pequeñas manchas circulares a la derecha y cerca del centro de notas."""
    if binary is None or binary.ndim != 2 or binary.size == 0:
        raise ValueError("Se requiere una imagen binaria monocroma no vacía")
    ink = (binary < 128).astype(np.uint8)
    count, _, stats, centroids = cv2.connectedComponentsWithStats(ink, 8)
    components = []
    for label in range(1, count):
        x,y,w,h,area = (int(v) for v in stats[label])
        if area <= 0:
            continue
        aspect = w / max(h,1)
        if .55 <= aspect <= 1.8 and area >= 2:
            components.append((x,y,w,h,area,centroids[label]))
    found = []
    used = set()
    for note_index, head in enumerate(noteheads):
        if not 0 <= head.staff_index < len(staves):
            continue
        spacing = float(staves[head.staff_index].spacing_px)
        best = None
        for x,y,w,h,area,center in components:
            cx,cy = float(center[0]),float(center[1])
            dx,dy = cx-head.center_x,abs(cy-head.center_y)
            if (note_index, x, y) in used:
                continue
            if not .18*spacing <= dx <= 1.25*spacing:
                continue
            if dy > .32*spacing or not .12*spacing <= w <= .6*spacing:
                continue
            if not .12*spacing <= h <= .6*spacing:
                continue
            score = max(0.0,1.0-dy/(.32*spacing)) * max(0.0,1.0-abs(dx-.48*spacing)/(.8*spacing))
            if best is None or score > best[0]:
                best = (score,cx,cy,x,y)
        if best and best[0] >= .2:
            score,cx,cy,x,y = best
            used.add((note_index,x,y))
            found.append(DotCandidate(round(cx,2),round(cy,2),note_index,round(min(.85,score),3)))
    return found


def detect_rest_shape_candidates(
    binary: np.ndarray,
    staves: list[StaffCandidate],
) -> list[RestSymbolCandidate]:
    """Marca componentes compactos dentro de pentagramas como posibles símbolos.

    Es deliberadamente inclusivo: letras, articulaciones y fragmentos pueden
    parecer silencios. No identifica todavía el tipo ni la duración del silencio.
    """
    if binary is None or binary.ndim != 2 or binary.size == 0:
        raise ValueError("Se requiere una imagen binaria monocroma no vacía")
    ink = (binary < 128).astype(np.uint8)
    # Quitar líneas largas del pentagrama para aislar parte de los glifos.
    kw = max(15,binary.shape[1]//5)
    horizontal = cv2.morphologyEx(ink,cv2.MORPH_OPEN,
        cv2.getStructuringElement(cv2.MORPH_RECT,(kw,1)))
    cleaned = cv2.subtract(ink,horizontal)
    count, _, stats, centroids = cv2.connectedComponentsWithStats(cleaned,8)
    results = []
    for label in range(1,count):
        x,y,w,h,area = (int(v) for v in stats[label])
        if area < 3:
            continue
        cx,cy = centroids[label]
        for staff_index,staff in enumerate(staves):
            spacing=float(staff.spacing_px)
            if spacing <= 1 or not (staff.lines_y[0]-spacing*.7 <= cy <= staff.lines_y[-1]+spacing*.7):
                continue
            if not (.18*spacing <= w <= 2.2*spacing and .25*spacing <= h <= 2.8*spacing):
                continue
            aspect=w/max(h,1)
            compactness=min(w,h)/max(w,h)
            shape_score=max(0.0,1.0-abs(aspect-.75)/2.0)
            if compactness < .12:
                continue
            results.append(RestSymbolCandidate((x,y,w,h),staff_index,round(shape_score,3),
                round(min(.55,shape_score*.55),3),
                "Candidato no confirmado: puede ser texto, articulación o fragmento de otro símbolo."))
            break
    return results
