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
    page_width_px: float
    page_height_px: float
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
                page_width_px=round(page.rect.width * scale, 2),
                page_height_px=round(page.rect.height * scale, 2),
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
    seen_page_numbers = set()
    for page in ordered_pages:
        page_number = page.get("page_number")
        if (not isinstance(page_number, int) or isinstance(page_number, bool)
                or page_number < 1):
            raise ValueError("Cada página requiere page_number entero positivo")
        if page_number in seen_page_numbers:
            raise ValueError("page_number duplicado al enlazar secciones")
        seen_page_numbers.add(page_number)
        page_markers = page.get("section_marker_candidates", [])
        identifiers = page.get("section_identifier_candidates", [])
        anchors = page.get("section_measure_anchor_candidates", [])
        if (not isinstance(page_markers, list) or not isinstance(identifiers, list)
                or not isinstance(anchors, list)):
            raise ValueError("Las marcas, identificadores y anclas de sección deben ser listas")
        for index, marker in enumerate(page_markers):
            if not isinstance(marker, dict):
                raise ValueError("Cada marca de sección debe ser un objeto")
            linked = [
                item for item in identifiers
                if isinstance(item, dict) and item.get("related_marker_index") == index
            ]
            identifier = linked[0].get("identifier") if len(linked) == 1 else None
            marker_anchors = [
                item for item in anchors
                if isinstance(item, dict) and item.get("marker_index") == index
            ]
            markers.append({
                "page_number": page_number,
                "measure_anchors": marker_anchors,
                "marker_index": index,
                "section_name": marker.get("normalized_text"),
                "text": marker.get("text"),
                "bbox_pdf": marker.get("bbox_pdf"),
                "identifier": identifier,
                "center_x_px": marker.get("center_x_px"),
                "center_y_px": marker.get("center_y_px"),
                "page_width_px": marker.get("page_width_px"),
                "page_height_px": marker.get("page_height_px"),
                "source_marker": marker,
            })

    # Un rótulo repetido en la misma coordenada de la franja superior
    # de varias páginas se trata como encabezado editorial, no como una
    # nueva sección en cada página. Se conserva en los candidatos locales.
    header_groups = {}
    for marker in markers:
        width = marker.get("page_width_px")
        height = marker.get("page_height_px")
        x, y = marker.get("center_x_px"), marker.get("center_y_px")
        if (not isinstance(width, (int, float)) or not isinstance(height, (int, float))
                or width <= 0 or height <= 0
                or not isinstance(x, (int, float)) or not isinstance(y, (int, float))):
            continue
        normalized_y = y / height
        if normalized_y > 0.08:
            continue
        key = (
            marker.get("section_name"),
            round(x / width, 2),
            round(normalized_y, 2),
        )
        header_groups.setdefault(key, set()).add(marker["page_number"])
    repeated_header_keys = {
        key for key, page_numbers in header_groups.items()
        if len(page_numbers) >= 2
    }
    filtered_markers = []
    for marker in markers:
        width = marker.get("page_width_px")
        height = marker.get("page_height_px")
        x, y = marker.get("center_x_px"), marker.get("center_y_px")
        key = None
        if (isinstance(width, (int, float)) and isinstance(height, (int, float))
                and width > 0 and height > 0
                and isinstance(x, (int, float)) and isinstance(y, (int, float))
                and y / height <= 0.08):
            key = (marker.get("section_name"), round(x / width, 2), round(y / height, 2))
        top_unanchored = (
            isinstance(height, (int, float)) and height > 0
            and isinstance(y, (int, float)) and y / height <= 0.08
            and not marker.get("measure_anchors")
        )
        source_marker = marker["source_marker"]
        if key in repeated_header_keys:
            source_marker["global_boundary_status"] = "excluded_repeated_page_header_candidate"
            source_marker["global_boundary_reason"] = (
                "Rótulo repetido en la misma posición superior de varias páginas; "
                "se conserva como candidato local, pero no divide rangos globales."
            )
        elif top_unanchored:
            source_marker["global_boundary_status"] = "excluded_unanchored_top_margin_candidate"
            source_marker["global_boundary_reason"] = (
                "Rótulo en el margen superior sin ancla geométrica a un intervalo; "
                "se conserva para revisión local, pero no divide rangos globales."
            )
        else:
            source_marker["global_boundary_status"] = "eligible_candidate"
            source_marker["global_boundary_reason"] = None
            filtered_markers.append(marker)

    ranges = []
    for index, marker in enumerate(filtered_markers):
        following = filtered_markers[index + 1] if index + 1 < len(filtered_markers) else None
        ranges.append({
            "section_range_id": f"section-{index + 1}",
            "section_name": marker["section_name"],
            "identifier": marker["identifier"],
            "start": {
                "page_number": marker["page_number"],
                "marker_index": marker["marker_index"],
                "bbox_pdf": marker["bbox_pdf"],
                "measure_anchors": marker["measure_anchors"],
            },
            "end": ({
                "page_number": following["page_number"],
                "marker_index": following["marker_index"],
                "bbox_pdf": following["bbox_pdf"],
                "measure_anchors": following["measure_anchors"],
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


def anchor_section_markers_to_measure_spans(
    markers: list[dict],
    staves: list,
    measure_spans: list,
    *,
    max_distance_measures: float = 1.0,
) -> list[dict]:
    """Asocia cada marca con el intervalo geométrico más cercano del pentagrama.

    La posición relativa dentro del intervalo es una referencia visual, no una
    afirmación de que el intervalo sea un compás musical confirmado.
    """
    if max_distance_measures <= 0:
        raise ValueError("max_distance_measures debe ser positivo")
    from statistics import median

    by_staff: dict[int, list] = {}
    for span in measure_spans:
        if span.width_px > 0:
            by_staff.setdefault(span.staff_index, []).append(span)

    anchors = []
    for marker_index, marker in enumerate(markers):
        x = marker.get("center_x_px")
        y = marker.get("center_y_px")
        if not isinstance(x, (int, float)) or not isinstance(y, (int, float)):
            continue
        possible = []
        for staff_index, staff in enumerate(staves):
            if len(staff.lines_y) != 5 or staff.spacing_px <= 0:
                continue
            spans = by_staff.get(staff_index, [])
            if not spans:
                continue
            staff_center = sum(staff.lines_y) / 5
            typical_width = float(median([span.width_px for span in spans]))
            for span in spans:
                gap = max(span.x_start - x, 0, x - span.x_end)
                distance_measures = gap / max(typical_width, 1.0)
                vertical_distance = abs(y - staff_center)
                possible.append((
                    distance_measures, vertical_distance, staff_index,
                    span, typical_width,
                ))
        if not possible:
            continue
        distance, vertical_distance, staff_index, span, typical_width = min(
            possible, key=lambda item: (
                item[0] + item[1] / max(staves[item[2]].spacing_px * 10, 1),
                item[1],
            )
        )
        # Evita anclar rótulos de encabezado/pie de página a un pentagrama
        # solo porque sea el más cercano disponible. La tolerancia vertical
        # se expresa en espacios del pentagrama para escalar con el tamaño.
        if vertical_distance > staves[staff_index].spacing_px * 12:
            continue
        if distance > max_distance_measures:
            continue
        ratio = (x - span.x_start) / max(span.width_px, 1.0)
        anchors.append({
            "marker_index": marker_index,
            "staff_index": staff_index,
            "measure_index_on_staff": span.measure_index,
            "interval_x_start": span.x_start,
            "interval_x_end": span.x_end,
            "position_ratio_in_interval": round(float(ratio), 3),
            "relation": (
                "before_interval" if ratio < 0
                else "after_interval" if ratio > 1
                else "inside_interval"
            ),
            "distance_in_measure_widths": round(float(distance), 3),
            "vertical_distance_px": round(float(vertical_distance), 2),
            "confidence": round(min(0.6, span.confidence * 0.7), 3),
            "review_status": "pending",
            "warning": (
                "Ancla geométrica local a un intervalo entre barras candidatas. "
                "El índice de compás es local al pentagrama/página, no global, y "
                "el intervalo no está validado como compás musical."
            ),
        })
    return anchors


def build_global_measure_sequence(pages: list[dict]) -> dict:
    """Construye ordinales globales provisionales conciliando pentagramas por sistema."""
    from statistics import median

    ordered_pages = sorted(pages, key=lambda item: item.get("page_number", 0))
    sequence, staff_measure_map = [], {}
    global_index = 0
    seen_pages = set()
    for page in ordered_pages:
        page_number = page.get("page_number")
        if not isinstance(page_number, int) or isinstance(page_number, bool) or page_number < 1:
            raise ValueError("Cada página requiere page_number positivo")
        if page_number in seen_pages:
            raise ValueError("page_number duplicado en la secuencia global")
        seen_pages.add(page_number)
        spans = page.get("measure_span_candidates", [])
        systems = page.get("staff_system_candidates", [])
        if not isinstance(spans, list) or not isinstance(systems, list):
            raise ValueError("Los intervalos y sistemas deben ser listas")
        staff_to_system = {}
        seen_systems = set()
        for system in systems:
            if not isinstance(system, dict):
                raise ValueError("Cada sistema debe ser un objeto")
            system_index = system.get("system_index")
            staff_indices = system.get("staff_indices")
            if (not isinstance(system_index, int) or isinstance(system_index, bool)
                    or system_index < 0 or system_index in seen_systems):
                raise ValueError("Cada sistema requiere un system_index único no negativo")
            if not isinstance(staff_indices, list):
                raise ValueError("staff_indices debe ser una lista")
            seen_systems.add(system_index)
            for staff_index in staff_indices:
                if (not isinstance(staff_index, int) or isinstance(staff_index, bool)
                        or staff_index < 0):
                    raise ValueError("staff_indices debe contener índices no negativos")
                if staff_index in staff_to_system:
                    raise ValueError("Un pentagrama no puede pertenecer a dos sistemas")
                staff_to_system[staff_index] = system_index
        from math import isfinite

        by_system = {}
        seen_local_spans = set()
        for span in spans:
            if not isinstance(span, dict):
                raise ValueError("Cada intervalo de compás debe ser un objeto")
            staff_index = span.get("staff_index")
            measure_index = span.get("measure_index")
            x_start, x_end, width = (
                span.get("x_start"), span.get("x_end"), span.get("width_px")
            )
            if (not isinstance(staff_index, int) or isinstance(staff_index, bool)
                    or staff_index < 0):
                raise ValueError("Cada intervalo requiere staff_index no negativo")
            if (not isinstance(measure_index, int) or isinstance(measure_index, bool)
                    or measure_index < 1):
                raise ValueError("Cada intervalo requiere measure_index positivo")
            if any(not isinstance(value, (int, float)) or isinstance(value, bool)
                   or not isfinite(float(value)) for value in (x_start, x_end, width)):
                raise ValueError("Las coordenadas y anchura del intervalo deben ser finitas")
            if x_end <= x_start or width <= 0:
                raise ValueError("El intervalo debe tener anchura positiva y límites ordenados")
            local_key = (staff_index, measure_index)
            if local_key in seen_local_spans:
                raise ValueError("Intervalo local duplicado para el mismo pentagrama y compás")
            seen_local_spans.add(local_key)
            system_index = staff_to_system.get(staff_index)
            if system_index is not None:
                by_system.setdefault(system_index, []).append(span)
        for system_index in sorted(by_system):
            candidates = sorted(by_system[system_index],
                key=lambda v: (v["x_start"] + v["x_end"]) / 2)
            clusters = []
            for span in candidates:
                center, width = (span["x_start"] + span["x_end"]) / 2, span["width_px"]
                match = None
                for cluster in reversed(clusters):
                    # Un pentagrama no puede aportar dos intervalos al mismo
                    # compás global candidato. Esta restricción evita que dos
                    # intervalos locales cercanos del mismo staff se fusionen
                    # por una tolerancia geométrica amplia.
                    if any(v.get("staff_index") == span.get("staff_index") for v in cluster):
                        continue
                    centers = [(v["x_start"] + v["x_end"]) / 2 for v in cluster]
                    widths = [v["width_px"] for v in cluster]
                    tolerance = max(3.0, min(float(median(widths)), float(width)) * 0.18)
                    if abs(center - float(median(centers))) <= tolerance:
                        match = cluster
                        break
                    if center - float(median(centers)) > max(width, float(median(widths))):
                        break
                if match is None:
                    clusters.append([span])
                else:
                    match.append(span)
            for local_index, cluster in enumerate(clusters, start=1):
                global_index += 1
                centers = [(v["x_start"] + v["x_end"]) / 2 for v in cluster]
                record = {
                    "global_measure_candidate": global_index,
                    "page_number": page_number,
                    "system_index": system_index,
                    "measure_index_in_system": local_index,
                    "x_start_median": round(float(median([v["x_start"] for v in cluster])), 2),
                    "x_end_median": round(float(median([v["x_end"] for v in cluster])), 2),
                    "center_x_median": round(float(median(centers)), 2),
                    "staff_support": len({v["staff_index"] for v in cluster}),
                    "staff_measure_refs": [
                        {"staff_index": v["staff_index"], "measure_index_on_staff": v["measure_index"]}
                        for v in cluster
                    ],
                    "confidence": round(min(0.65, float(median([v.get("confidence", 0.3) for v in cluster]))), 3),
                    "review_status": "pending",
                    "warning": (
                        "Ordinal global provisional por alineación horizontal de intervalos "
                        "entre barras candidatas; no es numeración musical confirmada."
                    ),
                }
                sequence.append(record)
                for span in cluster:
                    staff_measure_map[(page_number, span["staff_index"], span["measure_index"])] = global_index
    return {
        "global_measure_candidates": sequence,
        "global_measure_candidate_count": len(sequence),
        "staff_measure_map": [
            {"page_number": k[0], "staff_index": k[1],
             "measure_index_on_staff": k[2], "global_measure_candidate": v}
            for k, v in sorted(staff_measure_map.items())
        ],
        "warning": (
            "Secuencia provisional por página, sistema y posición horizontal. "
            "Anacrusas, compases incompletos, barras omitidas y alineación irregular "
            "requieren revisión humana."
        ),
    }


def resolve_section_range_boundaries(
    section_ranges: list[dict],
    global_measure_sequence: dict,
) -> list[dict]:
    """Enriquece los extremos de sección con coordenadas de compás candidatas.

    Usa la mejor ancla disponible de cada marca y conserva la fracción dentro
    del intervalo. La posición del rótulo es solo un proxy del límite musical:
    toda resolución queda pendiente de revisión humana.
    """
    if not isinstance(global_measure_sequence, dict):
        raise ValueError("global_measure_sequence debe ser un objeto")
    raw_map = global_measure_sequence.get("staff_measure_map", [])
    if not isinstance(raw_map, list):
        raise ValueError("staff_measure_map debe ser una lista")
    measure_map = {}
    for item in raw_map:
        if not isinstance(item, dict):
            raise ValueError("Cada referencia de compás debe ser un objeto")
        key = (item.get("page_number"), item.get("staff_index"),
               item.get("measure_index_on_staff"))
        measure_map[key] = item.get("global_measure_candidate")

    from copy import deepcopy
    from math import isfinite

    resolved = []
    for source in section_ranges:
        if not isinstance(source, dict):
            raise ValueError("Cada rango de sección debe ser un objeto")
        section = deepcopy(source)
        for boundary_name in ("start", "end"):
            boundary = section.get(boundary_name)
            if not isinstance(boundary, dict):
                continue
            anchors = boundary.get("measure_anchors", [])
            valid = [
                anchor for anchor in anchors
                if isinstance(anchor, dict)
                and isinstance(anchor.get("position_ratio_in_interval"), (int, float))
                and isfinite(float(anchor["position_ratio_in_interval"]))
            ]
            if not valid:
                boundary["musical_boundary_candidate"] = None
                continue
            anchor = max(
                valid,
                key=lambda value: (
                    value.get("confidence", 0),
                    -value.get("vertical_distance_px", float("inf")),
                ),
            )
            ratio = float(anchor["position_ratio_in_interval"])
            global_measure = measure_map.get((
                boundary.get("page_number"),
                anchor.get("staff_index"),
                anchor.get("measure_index_on_staff"),
            ))
            boundary["musical_boundary_candidate"] = {
                "global_measure_candidate": global_measure,
                "staff_index": anchor.get("staff_index"),
                "measure_index_on_staff": anchor.get("measure_index_on_staff"),
                "position_ratio_in_interval": round(ratio, 4),
                "position_kind": (
                    "at_measure_start_candidate" if ratio == 0
                    else "at_measure_end_candidate" if ratio == 1
                    else "inside_measure_candidate" if 0 < ratio < 1
                    else "before_measure_candidate" if ratio < 0
                    else "after_measure_candidate"
                ),
                "partial_measure_boundary": 0 < ratio < 1,
                "anchor_confidence": anchor.get("confidence"),
                "review_status": "pending",
                "warning": (
                    "Coordenada basada en la posición del rótulo, no en un límite "
                    "musical observado. La fracción identifica una ubicación visual "
                    "dentro del intervalo candidato; debe confirmarse manualmente."
                ),
            }
        resolved.append(section)
    return resolved
