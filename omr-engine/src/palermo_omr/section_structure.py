"""Detección conservadora de marcas e identificadores de secciones musicales.

Las salidas son evidencias geométricas pendientes de revisión. Un rango puede
atravesar sistemas y terminar/comenzar dentro de un sistema; nunca se equipara
una sección con un compás o con un sistema.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import asdict, dataclass
from pathlib import Path

import fitz

from .imaging import StaffCandidate
from .measure_layout import MeasureSpanCandidate


_SECTION_NAMES = {
    "CORO", "ESTROFA", "VERSO", "PUENTE", "FINAL", "INTRO",
    "INTRODUCCION", "PRECORO", "CODA", "INTERLUDIO", "REFRAIN",
    "CHORUS", "VERSE", "BRIDGE", "ENDING", "OUTRO",
}


def _normalize(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value)
    plain = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    return re.sub(r"[^A-Z0-9]+", " ", plain.upper()).strip()


@dataclass(frozen=True)
class SectionMarkerCandidate:
    page_number: int
    text: str
    normalized_text: str
    bbox_pdf: tuple[float, float, float, float]
    center_x_px: float
    center_y_px: float
    confidence: float
    warning: str

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class SectionIdentifierCandidate:
    page_number: int
    text: str
    identifier: str
    bbox_pdf: tuple[float, float, float, float]
    related_marker_index: int
    horizontal_distance_measures: float
    confidence: float
    warning: str

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class SectionRangeCandidate:
    page_number: int
    section_name: str
    identifier: str | None
    start_marker_index: int
    end_marker_index: int | None
    start_bbox_pdf: tuple[float, float, float, float]
    end_bbox_pdf: tuple[float, float, float, float] | None
    extent: str
    confidence: float
    warning: str

    def to_dict(self) -> dict:
        return asdict(self)


def detect_section_candidates(
    pdf_path: str | Path,
    page_number: int,
    staves: list[StaffCandidate],
    measure_spans: list[MeasureSpanCandidate],
    *,
    dpi: int = 300,
    max_identifier_distance_measures: float = 1.0,
) -> dict[str, list]:
    """Extrae rótulos de sección y letras cercanas en la misma página.

    La proximidad se mide horizontalmente en anchos medios de intervalos entre
    barras del pentagrama geométricamente más cercano. La relación se mantiene
    como candidata: el PDF puede carecer de barras o de texto seleccionable.
    """
    if dpi < 72 or dpi > 600:
        raise ValueError("dpi debe estar entre 72 y 600")
    if page_number < 1:
        raise ValueError("page_number debe ser mayor o igual a 1")
    if max_identifier_distance_measures <= 0:
        raise ValueError("max_identifier_distance_measures debe ser positivo")
    path = Path(pdf_path)
    if not path.is_file():
        raise FileNotFoundError(f"No existe el archivo: {path}")

    with fitz.open(path) as document:
        if document.is_encrypted:
            raise ValueError("El PDF está protegido con contraseña")
        if page_number > len(document):
            raise ValueError("page_number supera el número de páginas del PDF")
        page = document[page_number - 1]
        scale = dpi / 72.0
        lines = []
        for block in page.get_text("dict").get("blocks", []):
            for line in block.get("lines", []):
                spans = line.get("spans", [])
                raw = " ".join(s.get("text", "").strip() for s in spans).strip()
                boxes = [s["bbox"] for s in spans if s.get("text", "").strip()]
                if not raw or not boxes:
                    continue
                bbox = (
                    min(b[0] for b in boxes), min(b[1] for b in boxes),
                    max(b[2] for b in boxes), max(b[3] for b in boxes),
                )
                normalized = _normalize(raw)
                lines.append((raw, normalized, bbox))

        markers = []
        for raw, normalized, bbox in lines:
            if normalized not in _SECTION_NAMES:
                continue
            markers.append(SectionMarkerCandidate(
                page_number=page_number,
                text=raw,
                normalized_text=normalized,
                bbox_pdf=tuple(round(float(v), 3) for v in bbox),
                center_x_px=round((bbox[0] + bbox[2]) * 0.5 * scale, 2),
                center_y_px=round((bbox[1] + bbox[3]) * 0.5 * scale, 2),
                confidence=0.65,
                warning=(
                    "Rótulo textual candidato de sección; no confirma por sí solo "
                    "el límite musical ni el alcance de la sección."
                ),
            ))
        markers.sort(key=lambda item: (item.center_y_px, item.center_x_px))

        valid_staves = [
            (i, s) for i, s in enumerate(staves)
            if len(s.lines_y) == 5 and s.spacing_px > 0
        ]
        widths_by_staff: dict[int, list[float]] = {}
        for span in measure_spans:
            if span.width_px > 0:
                widths_by_staff.setdefault(span.staff_index, []).append(span.width_px)

        identifiers = []
        for raw, normalized, bbox in lines:
            # Letra aislada A-Z; las asociaciones SATB se resuelven por contexto.
            if not re.fullmatch(r"[A-Z]", normalized):
                continue
            cx = (bbox[0] + bbox[2]) * 0.5 * scale
            cy = (bbox[1] + bbox[3]) * 0.5 * scale
            nearby = []
            for marker_index, marker in enumerate(markers):
                nearest_staff = min(
                    valid_staves,
                    key=lambda pair: abs(cy - sum(pair[1].lines_y) / 5),
                    default=None,
                )
                if nearest_staff is None:
                    continue
                staff_index, staff = nearest_staff
                typical_widths = widths_by_staff.get(staff_index, [])
                if not typical_widths:
                    all_widths = [s.width_px for s in measure_spans if s.width_px > 0]
                    typical_width = float(__import__("statistics").median(all_widths)) if all_widths else staff.spacing_px * 8
                else:
                    typical_width = float(__import__("statistics").median(typical_widths))
                measure_distance = abs(cx - marker.center_x_px) / max(typical_width, 1.0)
                vertical_distance = abs(cy - marker.center_y_px)
                if (measure_distance <= max_identifier_distance_measures
                        and vertical_distance <= staff.spacing_px * 12):
                    nearby.append((measure_distance, vertical_distance, marker_index))
            if not nearby:
                continue
            distance, _, marker_index = min(nearby)
            identifiers.append(SectionIdentifierCandidate(
                page_number=page_number,
                text=raw,
                identifier=normalized,
                bbox_pdf=tuple(round(float(v), 3) for v in bbox),
                related_marker_index=marker_index,
                horizontal_distance_measures=round(distance, 3),
                confidence=0.55,
                warning=(
                    "Letra aislada cercana a un rótulo de sección; posible identificador "
                    "editorial, no debe clasificarse automáticamente como voz SATB."
                ),
            ))

        ranges = []
        for index, marker in enumerate(markers):
            next_marker = markers[index + 1] if index + 1 < len(markers) else None
            linked = [item for item in identifiers if item.related_marker_index == index]
            identifier = linked[0].identifier if len(linked) == 1 else None
            ranges.append(SectionRangeCandidate(
                page_number=page_number,
                section_name=marker.normalized_text,
                identifier=identifier,
                start_marker_index=index,
                end_marker_index=index + 1 if next_marker else None,
                start_bbox_pdf=marker.bbox_pdf,
                end_bbox_pdf=next_marker.bbox_pdf if next_marker else None,
                extent="between_section_markers" if next_marker else "open_ended_page_candidate",
                confidence=0.45 if next_marker else 0.3,
                warning=(
                    "Rango de sección provisional dentro de esta página, ordenado por "
                    "lectura (sistema superior a inferior, izquierda a derecha). Puede "
                    "comenzar o terminar dentro de un sistema. No enlaza páginas ni "
                    "confirma compases musicales hasta validar sus límites."
                ),
            ))
        return {
            "section_marker_candidates": markers,
            "section_identifier_candidates": identifiers,
            "section_range_candidates": ranges,
        }

def link_section_ranges_across_pages(pages: list[dict]) -> list[dict]:
    """Enlaza marcas de sección en orden de página para proponer rangos globales.

    Las páginas sin marcas no interrumpen una sección. El siguiente rótulo
    encontrado cierra el rango anterior, aunque esté en otra página. El último
    rango permanece abierto hasta el final de la partitura y requiere revisión.
    """
    ordered_pages = sorted(pages, key=lambda item: item.get("page_number", 0))
    markers = []
    for page in ordered_pages:
        page_number = page.get("page_number")
        if not isinstance(page_number, int) or page_number < 1:
            raise ValueError("Cada página requiere page_number positivo")
        page_markers = page.get("section_marker_candidates", [])
        identifiers = page.get("section_identifier_candidates", [])
        if not isinstance(page_markers, list) or not isinstance(identifiers, list):
            raise ValueError("Las marcas e identificadores de sección deben ser listas")
        for index, marker in enumerate(page_markers):
            if not isinstance(marker, dict):
                raise ValueError("Cada marca de sección debe ser un objeto")
            linked = [
                item for item in identifiers
                if isinstance(item, dict) and item.get("related_marker_index") == index
            ]
            identifier = linked[0].get("identifier") if len(linked) == 1 else None
            markers.append({
                "page_number": page_number,
                "marker_index": index,
                "section_name": marker.get("normalized_text"),
                "text": marker.get("text"),
                "bbox_pdf": marker.get("bbox_pdf"),
                "identifier": identifier,
                "center_x_px": marker.get("center_x_px"),
                "center_y_px": marker.get("center_y_px"),
            })

    ranges = []
    for index, marker in enumerate(markers):
        following = markers[index + 1] if index + 1 < len(markers) else None
        ranges.append({
            "section_range_id": f"section-{index + 1}",
            "section_name": marker["section_name"],
            "identifier": marker["identifier"],
            "start": {
                "page_number": marker["page_number"],
                "marker_index": marker["marker_index"],
                "bbox_pdf": marker["bbox_pdf"],
            },
            "end": ({
                "page_number": following["page_number"],
                "marker_index": following["marker_index"],
                "bbox_pdf": following["bbox_pdf"],
                "boundary_type": "next_section_marker",
            } if following else None),
            "extent": (
                "cross_page_candidate"
                if following and following["page_number"] != marker["page_number"]
                else "between_markers_candidate" if following
                else "open_ended_score_candidate"
            ),
            "page_span": (
                following["page_number"] - marker["page_number"] + 1
                if following else None
            ),
            "confidence": 0.4 if following else 0.25,
            "review_status": "pending",
            "warning": (
                "Rango global provisional delimitado por marcas textuales sucesivas. "
                "La posición exacta del primer y último compás, los compases parciales "
                "y la continuidad musical entre páginas requieren validación humana. "
                "El fin de página nunca se interpreta como fin de sección."
            ),
        })
    return ranges
