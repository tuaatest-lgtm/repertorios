"""Detección de regiones candidatas de texto en partituras rasterizadas.

No realiza OCR ni interpreta palabras. Su salida son cajas geométricas para
revisión posterior; nunca asigna por sí sola una parte o una voz musical.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass

import cv2
import numpy as np

from .imaging import StaffCandidate


@dataclass(frozen=True)
class TextRegionCandidate:
    region_id: str
    bbox: tuple[int, int, int, int]
    component_count: int
    nearby_staff_indices: tuple[int, ...]
    association_status: str
    location_hint: str
    confidence: float
    warning: str

    def to_dict(self) -> dict:
        return asdict(self)


def _remove_staff_lines(ink: np.ndarray) -> np.ndarray:
    """Elimina trazos horizontales largos conservando el resto de la tinta."""
    width = ink.shape[1]
    kernel_width = max(20, width // 7)
    horizontal = cv2.morphologyEx(
        ink,
        cv2.MORPH_OPEN,
        cv2.getStructuringElement(cv2.MORPH_RECT, (kernel_width, 1)),
    )
    return cv2.subtract(ink, horizontal)


def _component_regions(
    ink_without_staff: np.ndarray,
    *,
    left_width: int,
    min_area: int,
    max_area: int,
    max_component_height: int,
) -> list[tuple[int, int, int, int, int]]:
    """Agrupa componentes próximos horizontalmente como bloques tipo texto."""
    roi = ink_without_staff[:, :left_width]
    if roi.size == 0:
        return []

    count, labels, stats, _ = cv2.connectedComponentsWithStats(roi, 8)
    filtered = np.zeros(roi.shape, dtype=np.uint8)
    original_components = 0
    for label in range(1, count):
        x, y, width, height, area = (int(v) for v in stats[label])
        if area < min_area or area > max_area or height > max_component_height:
            continue
        filtered[labels == label] = 255
        original_components += 1

    if original_components == 0:
        return []

    # Unir letras de una misma palabra, sin cerrar espacios verticales grandes.
    horizontal_gap = max(3, int(round(max_component_height * 0.42)))
    vertical_gap = max(1, int(round(max_component_height * 0.12)))
    kernel = cv2.getStructuringElement(
        cv2.MORPH_RECT, (horizontal_gap, vertical_gap)
    )
    grouped = cv2.morphologyEx(filtered, cv2.MORPH_CLOSE, kernel)
    count, labels, stats, _ = cv2.connectedComponentsWithStats(grouped, 8)

    regions = []
    for label in range(1, count):
        x, y, width, height, area = (int(v) for v in stats[label])
        if area < min_area or width < 2 or height < 2:
            continue
        component_count = int(np.count_nonzero(
            np.unique(labels[filtered[y:y + height, x:x + width] > 0])
        ))
        # A grouped blob with only one source glyph is less likely to be a word.
        if component_count < 2:
            continue
        regions.append((x, y, width, height, component_count))
    return regions


def detect_text_region_candidates(
    binary: np.ndarray,
    staves: list[StaffCandidate],
    *,
    left_margin_ratio: float = 0.22,
    min_component_area: int = 3,
    max_component_area_spacing: float = 1.2,
    max_component_height_spacing: float = 1.8,
    max_region_width_spacing: float = 12.0,
    max_region_height_spacing: float = 2.8,
    max_staff_distance_spacing: float = 3.5,
) -> list[TextRegionCandidate]:
    """Propone bloques tipo texto en el margen izquierdo de pentagramas.

    La imagen debe ser binaria, tinta negra y fondo blanco. Se retiran primero
    las líneas horizontales largas; después se agrupan componentes pequeños
    en la franja izquierda. La relación con pentagramas es solo proximidad
    vertical y se informa como candidata o ambigua.
    """
    if binary is None or binary.ndim != 2 or binary.size == 0:
        raise ValueError("Se requiere una imagen binaria monocroma no vacía")
    if not 0 < left_margin_ratio <= 1:
        raise ValueError("left_margin_ratio debe estar entre 0 y 1")
    if min_component_area < 1:
        raise ValueError("min_component_area debe ser positivo")
    for value, name in (
        (max_component_area_spacing, "max_component_area_spacing"),
        (max_component_height_spacing, "max_component_height_spacing"),
        (max_region_width_spacing, "max_region_width_spacing"),
        (max_region_height_spacing, "max_region_height_spacing"),
        (max_staff_distance_spacing, "max_staff_distance_spacing"),
    ):
        if value <= 0:
            raise ValueError(f"{name} debe ser positivo")

    valid_staves = [
        (index, staff) for index, staff in enumerate(staves)
        if len(staff.lines_y) == 5 and staff.spacing_px > 1
    ]
    if not valid_staves:
        return []

    height, width = binary.shape
    left_width = max(1, int(round(width * left_margin_ratio)))
    typical_spacing = float(np.median([
        staff.spacing_px for _, staff in valid_staves
    ]))
    ink = cv2.bitwise_not(binary)
    ink_without_staff = _remove_staff_lines(ink)
    regions = _component_regions(
        ink_without_staff,
        left_width=left_width,
        min_area=min_component_area,
        max_area=max(min_component_area, int(round(typical_spacing ** 2 * max_component_area_spacing))),
        max_component_height=max(3, int(round(typical_spacing * max_component_height_spacing))),
    )

    results: list[TextRegionCandidate] = []
    for x, y, region_width, region_height, component_count in regions:
        if region_width > typical_spacing * max_region_width_spacing:
            continue
        if region_height > typical_spacing * max_region_height_spacing:
            continue
        center_y = y + region_height / 2
        distances = sorted(
            (
                abs(center_y - (staff.lines_y[0] + staff.lines_y[-1]) / 2),
                index,
                staff.spacing_px,
            )
            for index, staff in valid_staves
        )
        if not distances:
            continue
        nearest_distance, nearest_index, nearest_spacing = distances[0]
        if nearest_distance > nearest_spacing * max_staff_distance_spacing:
            continue

        tied = [
            index for distance, index, spacing in distances
            if abs(distance - nearest_distance) <= max(1.0, spacing * 0.45)
        ]
        if len(tied) > 1:
            nearby = tuple(sorted(tied))
            status = "ambiguous"
            confidence = 0.38
            warning = (
                "Región tipo texto próxima a varios pentagramas; no se puede "
                "determinar a cuál pertenece sin revisión visual."
            )
        else:
            nearby = (nearest_index,)
            status = "nearby_staff_candidate"
            confidence = 0.48
            warning = (
                "Bloque geométrico tipo texto en el margen izquierdo; no se "
                "ha leído su contenido ni confirmado que sea una etiqueta musical."
            )

        staff_top = staves[nearest_index].lines_y[0]
        if y + region_height <= staff_top:
            location_hint = "above_staff"
        elif y >= staves[nearest_index].lines_y[-1]:
            location_hint = "below_staff"
        else:
            location_hint = "beside_staff"

        results.append(TextRegionCandidate(
            region_id=f"text-region-{len(results) + 1}",
            bbox=(x, y, x + region_width, y + region_height),
            component_count=component_count,
            nearby_staff_indices=nearby,
            association_status=status,
            location_hint=location_hint,
            confidence=confidence,
            warning=warning,
        ))

    results.sort(key=lambda item: (item.bbox[1], item.bbox[0]))
    return results
