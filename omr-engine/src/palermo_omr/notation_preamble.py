"""Extracción de glifos del preámbulo y exportación para etiquetado humano."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path

import cv2
import numpy as np

from .imaging import StaffCandidate


@dataclass(frozen=True)
class NotationPreambleCandidate:
    staff_index: int
    bbox: tuple[int, int, int, int]
    center_x: float
    center_y: float
    width_to_spacing: float
    height_to_spacing: float
    aspect_ratio: float
    ink_density: float
    hole_count: int
    vertical_projection_peaks: int
    contour_count: int
    solidity: float
    extent: float
    hu_moments: tuple[float, ...]
    role: str
    status: str
    confidence: float

    def to_dict(self) -> dict:
        return asdict(self)


def _count_projection_peaks(values: np.ndarray) -> int:
    if values.size == 0 or int(values.max(initial=0)) == 0:
        return 0
    threshold = max(1, int(round(float(values.max()) * 0.28)))
    active = values >= threshold
    groups = 0
    in_group = False
    for value in active:
        if bool(value) and not in_group:
            groups += 1
        in_group = bool(value)
    return groups


def _shape_features(component: np.ndarray) -> tuple[int, float, float, tuple[float, ...]]:
    contours, hierarchy = cv2.findContours(component, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)
    holes = 0 if hierarchy is None else sum(1 for entry in hierarchy[0] if int(entry[3]) >= 0)
    external = [contour for index, contour in enumerate(contours)
                if hierarchy is None or int(hierarchy[0][index][3]) < 0]
    contour_area = float(sum(cv2.contourArea(item) for item in external))
    points = np.vstack(external) if external else np.empty((0, 1, 2), dtype=np.int32)
    hull_area = float(cv2.contourArea(cv2.convexHull(points))) if len(points) else 0.0
    solidity = contour_area / hull_area if hull_area > 0 else 0.0
    extent = float(np.count_nonzero(component)) / max(component.size, 1)
    moments = cv2.moments(component, binaryImage=True)
    raw_hu = cv2.HuMoments(moments).flatten()
    hu = tuple(round(float(-np.sign(value) * np.log10(max(abs(float(value)), 1e-30))), 6)
               for value in raw_hu)
    return holes, round(solidity, 4), round(extent, 4), hu


def detect_notation_preamble_candidates(
    binary: np.ndarray,
    staves: list[StaffCandidate],
    noteheads: list[object] | None = None,
) -> list[NotationPreambleCandidate]:
    """Extrae glifos previos a la primera nota de cada pentagrama."""
    if binary is None or binary.ndim != 2 or binary.size == 0:
        raise ValueError("Se requiere una imagen binaria monocroma no vacía")
    if not staves:
        return []
    ink = (binary < 128).astype(np.uint8) * 255
    page_width = binary.shape[1]
    noteheads = noteheads or []
    results: list[NotationPreambleCandidate] = []
    line_masks: dict[int, np.ndarray] = {}
    for staff_index, staff in enumerate(staves):
        spacing = float(staff.spacing_px)
        if len(staff.lines_y) != 5 or spacing <= 1:
            continue
        staff_heads = [item for item in noteheads if int(getattr(item, "staff_index", -1)) == staff_index]
        first_note_x = min((float(item.center_x) for item in staff_heads),
                           default=float(page_width) * 0.35)
        right = min(page_width, max(1, int(round(first_note_x - spacing * 0.75))),
                    max(1, int(round(page_width * 0.40))))
        if right <= 1:
            continue
        top = max(0, int(round(float(staff.lines_y[0]) - spacing * 1.8)))
        bottom = min(binary.shape[0], int(round(float(staff.lines_y[-1]) + spacing * 1.8)))
        kernel_width = max(15, int(round(spacing * 3.0)))
        if kernel_width not in line_masks:
            line_masks[kernel_width] = cv2.morphologyEx(
                ink, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (kernel_width, 1)))
        cleaned = cv2.subtract(ink, line_masks[kernel_width])
        roi = cleaned[top:bottom, :right]
        count, labels, stats, centroids = cv2.connectedComponentsWithStats(roi, connectivity=8)
        for label in range(1, count):
            x, y, width, height, area = (int(value) for value in stats[label])
            if area < max(4, int(round(spacing * spacing * 0.025))):
                continue
            if width > spacing * 5.5 or height > spacing * 5.5:
                continue
            if width < spacing * 0.12 and height < spacing * 0.35:
                continue
            component = (labels[y:y + height, x:x + width] == label).astype(np.uint8)
            holes, solidity, extent, hu = _shape_features(component)
            peaks = _count_projection_peaks(np.count_nonzero(component, axis=0))
            center_x, center_y = centroids[label]
            results.append(NotationPreambleCandidate(
                staff_index, (x, top + y, width, height), round(float(center_x), 2),
                round(float(center_y + top), 2), round(width / spacing, 3),
                round(height / spacing, 3), round(width / max(height, 1), 3),
                round(area / max(width * height, 1), 3), holes, peaks,
                len(cv2.findContours(component, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)[0]),
                solidity, extent, hu, "clef_key_signature_or_other",
                "unclassified_visual_glyph", 0.0))
    results.sort(key=lambda item: (item.staff_index, item.center_x, item.center_y))
    return results


def export_notation_preamble_crops(
    binary: np.ndarray,
    candidates: list[NotationPreambleCandidate],
    staves: list[StaffCandidate],
    output_dir: str | Path,
    *,
    page_number: int,
) -> list[dict[str, object]]:
    """Guarda recortes PNG identificables para etiquetado humano; nunca autoetiqueta."""
    if binary is None or binary.ndim != 2 or binary.size == 0:
        raise ValueError("Se requiere una imagen binaria monocroma no vacía")
    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    exported = []
    counters: dict[int, int] = {}
    for candidate in candidates:
        if candidate.staff_index < 0 or candidate.staff_index >= len(staves):
            raise ValueError("Índice de pentagrama fuera de rango en candidato")
        x, y, width, height = candidate.bbox
        spacing = max(2, int(round(float(staves[candidate.staff_index].spacing_px) * 0.45)))
        left, top = max(0, x - spacing), max(0, y - spacing)
        right, bottom = min(binary.shape[1], x + width + spacing), min(binary.shape[0], y + height + spacing)
        crop = binary[top:bottom, left:right]
        index = counters.get(candidate.staff_index, 0)
        counters[candidate.staff_index] = index + 1
        filename = f"page-{page_number:03d}-staff-{candidate.staff_index:03d}-glyph-{index:03d}.png"
        path = destination / filename
        if not cv2.imwrite(str(path), crop):
            raise OSError(f"No se pudo escribir el recorte {path}")
        exported.append({
            "staff_index": candidate.staff_index,
            "candidate_bbox": list(candidate.bbox),
            "crop_file": str(Path("notation-preamble-crops") / filename),
            "label": None,
            "label_status": "needs_human_label",
        })
    return exported
