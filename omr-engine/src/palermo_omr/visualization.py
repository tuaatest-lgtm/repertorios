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



def draw_geometry_overlay(page_image: np.ndarray, page_data: dict) -> np.ndarray:
    """Dibuja evidencia geométrica de símbolos, vigas y compases candidatos.

    Los colores solo separan familias visuales; no expresan certeza ni
    confirman la función musical de los trazos.
    """
    if page_image is None or page_image.size == 0:
        raise ValueError("La imagen de página está vacía")
    if page_image.ndim != 3 or page_image.shape[2] != 3:
        raise ValueError("Se requiere una imagen BGR de tres canales")
    if not isinstance(page_data, dict):
        raise ValueError("page_data debe ser un objeto")

    overlay = page_image.copy()
    height, width = overlay.shape[:2]
    staves = page_data.get("staves", [])

    def point(x: float, y: float) -> tuple[int, int]:
        return (int(round(x)), int(round(y)))

    def label(text: str, x: int, y: int, color: tuple[int, int, int]) -> None:
        cv2.putText(
            overlay, text, (max(2, min(width - 2, x)), max(12, min(height - 2, y))),
            cv2.FONT_HERSHEY_SIMPLEX, 0.38, color, 1, cv2.LINE_AA,
        )

    def bbox_rect(value: dict, color: tuple[int, int, int], tag: str) -> None:
        box = value.get("bbox")
        if not isinstance(box, (list, tuple)) or len(box) != 4:
            return
        x, y, w, h = (int(round(float(v))) for v in box)
        if w <= 0 or h <= 0:
            return
        x1, y1 = max(0, x), max(0, y)
        x2, y2 = min(width - 1, x + w), min(height - 1, y + h)
        if x1 <= x2 and y1 <= y2:
            cv2.rectangle(overlay, (x1, y1), (x2, y2), color, 2)
            label(tag, x1, y1 - 3, color)

    # Silencios y arcos son formas sin clasificación musical confirmada.
    for key, color, tag in (
        ("rest_shape_candidates", (190, 70, 190), "REST?"),
        ("tie_slur_shape_candidates", (220, 120, 30), "ARC?"),
        ("beam_group_candidates", (30, 170, 220), "BEAM?"),
    ):
        for item in page_data.get(key, []):
            if isinstance(item, dict):
                bbox_rect(item, color, tag)

    # Etiquetas PDF: bbox_pdf está expresado en puntos PDF; se convierte a
    # píxeles usando el DPI del render. LABEL? indica que el texto reconocido
    # y su proximidad no confirman a qué pentagrama pertenece.
    render_dpi = page_data.get("render_dpi", 300)
    if isinstance(render_dpi, (int, float)) and not isinstance(render_dpi, bool) and render_dpi > 0:
        label_scale = float(render_dpi) / 72.0
        for item in page_data.get("printed_label_candidates", []):
            if not isinstance(item, dict):
                continue
            box = item.get("bbox_pdf")
            if not isinstance(box, (list, tuple)) or len(box) != 4:
                continue
            try:
                x0, y0, x1, y1 = (int(round(float(value) * label_scale)) for value in box)
            except (TypeError, ValueError):
                continue
            if x1 <= x0 or y1 <= y0:
                continue
            left, top = max(0, x0), max(0, y0)
            right, bottom = min(width - 1, x1), min(height - 1, y1)
            if left > right or top > bottom:
                continue
            color = (180, 80, 30)
            cv2.rectangle(overlay, (left, top), (right, bottom), color, 2)
            text = str(item.get("text", "label")).replace("\\n", " ").strip()
            label(f"LABEL? {text[:24]}", left, top - 3, color)

    # Rótulos de sección y anclas: se visualizan como hipótesis de ubicación.
    # La línea atraviesa el sistema candidato, no confirma un límite de compás.
    section_markers = page_data.get("section_marker_candidates", [])
    for item in section_markers:
        if not isinstance(item, dict):
            continue
        box = item.get("bbox_pdf")
        if not isinstance(box, (list, tuple)) or len(box) != 4:
            continue
        try:
            x0, y0, x1, y1 = (int(round(float(value) * float(render_dpi) / 72.0)) for value in box)
        except (TypeError, ValueError):
            continue
        left, top = max(0, x0), max(0, y0)
        right, bottom = min(width - 1, x1), min(height - 1, y1)
        if left <= right and top <= bottom:
            excluded_status = str(item.get("global_boundary_status", "")).startswith("excluded_")
            color = (120, 120, 150) if excluded_status else (180, 60, 220)
            tag = "HEADER?" if excluded_status else "SECTION?"
            cv2.rectangle(overlay, (left, top), (right, bottom), color, 2)
            label(f"{tag} {str(item.get('text', ''))[:18]}", left, top - 4, color)

    systems_by_index = {
        item.get("system_index"): item
        for item in page_data.get("staff_system_candidates", [])
        if isinstance(item, dict) and isinstance(item.get("system_index"), int)
    }
    drawn_anchors = set()
    for anchor in page_data.get("section_measure_anchor_candidates", []):
        if not isinstance(anchor, dict):
            continue
        system_index = anchor.get("system_index")
        staff_index = anchor.get("staff_index")
        x_start, x_end = anchor.get("interval_x_start"), anchor.get("interval_x_end")
        ratio = anchor.get("position_ratio_in_interval")
        if not all(isinstance(value, (int, float)) for value in (x_start, x_end, ratio)):
            continue
        x = int(round(x_start + (x_end - x_start) * ratio))
        system = systems_by_index.get(system_index)
        if system is not None:
            indices = system.get("staff_indices", [])
            selected = [
                staves[index] for index in indices
                if isinstance(indices, list) and isinstance(index, int)
                and not isinstance(index, bool) and 0 <= index < len(staves)
                and len(staves[index].get("lines_y", [])) == 5
            ]
            if not selected:
                continue
            y_top = min(staff["lines_y"][0] for staff in selected)
            y_bottom = max(staff["lines_y"][-1] for staff in selected)
        elif isinstance(staff_index, int) and not isinstance(staff_index, bool) and 0 <= staff_index < len(staves):
            lines = staves[staff_index].get("lines_y", [])
            if len(lines) != 5:
                continue
            y_top, y_bottom = lines[0], lines[-1]
        else:
            continue
        key = (anchor.get("marker_index"), system_index, x, y_top, y_bottom)
        if key in drawn_anchors:
            continue
        drawn_anchors.add(key)
        x = max(0, min(width - 1, x))
        color = (255, 100, 20)
        cv2.line(overlay, point(x, y_top), point(x, y_bottom), color, 2, cv2.LINE_AA)
        cv2.circle(overlay, point(x, y_top), 5, color, -1)
        label("SECTION-ANCHOR?", x + 5, int(y_top) - 4, color)

    # Puntillos: se muestra el punto y su relación geométrica candidata.
    for item in page_data.get("augmentation_dot_candidates", []):
        if not isinstance(item, dict):
            continue
        x, y = item.get("x"), item.get("y")
        if isinstance(x, (int, float)) and isinstance(y, (int, float)):
            center = point(x, y)
            cv2.circle(overlay, center, 5, (0, 180, 255), 2)
            label("DOT?", center[0] + 5, center[1] - 5, (0, 180, 255))

    # Barras por pentagrama y sus agrupaciones.
    for item in page_data.get("barline_candidates", []):
        if not isinstance(item, dict):
            continue
        x, y1, y2 = item.get("x"), item.get("y_top"), item.get("y_bottom")
        if all(isinstance(v, (int, float)) for v in (x, y1, y2)):
            cv2.line(overlay, point(x, y1), point(x, y2), (200, 100, 20), 2)
    for item in page_data.get("barline_group_candidates", []):
        if not isinstance(item, dict):
            continue
        staff_index = item.get("staff_index")
        if not isinstance(staff_index, int) or isinstance(staff_index, bool) or not 0 <= staff_index < len(staves):
            continue
        lines = staves[staff_index].get("lines_y", [])
        if len(lines) != 5:
            continue
        for x in item.get("x_positions", []):
            if isinstance(x, (int, float)):
                cv2.line(overlay, point(x, lines[0]), point(x, lines[-1]), (80, 160, 220), 1)
                label("BAR?", int(x), int(lines[0]) - 4, (80, 160, 220))

    # Relaciones entre pentagramas: se delimitan en la extensión real de los
    # pentagramas referenciados, sin inferir llaves, partes ni compases válidos.
    for key in ("system_barline_candidates", "staff_system_candidates"):
        for item in page_data.get(key, []):
            if not isinstance(item, dict):
                continue
            indices = item.get("staff_indices", [])
            selected = [
                staves[i] for i in indices
                if isinstance(i, int) and not isinstance(i, bool)
                and 0 <= i < len(staves) and len(staves[i].get("lines_y", [])) == 5
            ] if isinstance(indices, list) else []
            if not selected:
                continue
            y1 = min(staff["lines_y"][0] for staff in selected)
            y2 = max(staff["lines_y"][-1] for staff in selected)
            if key == "system_barline_candidates" and isinstance(item.get("x"), (int, float)):
                x = item["x"]
                cv2.line(overlay, point(x, y1), point(x, y2), (40, 190, 190), 2)
                label("SYS-BAR?", int(x), int(y1) - 4, (40, 190, 190))
            elif key == "staff_system_candidates":
                cv2.line(overlay, point(5, y1), point(5, y2), (180, 120, 40), 2)
                label("SYSTEM?", 8, int(y1) - 4, (180, 120, 40))

    # Marcas de agrupación: se dibujan como hipótesis gráficas, nunca como
    # asignaciones confirmadas de piano, instrumento o voz.
    for item in page_data.get("staff_grouping_mark_candidates", []):
        if not isinstance(item, dict):
            continue
        x = item.get("x")
        y1, y2 = item.get("y_top"), item.get("y_bottom")
        width_px = item.get("width_px", 2)
        if not all(isinstance(v, (int, float)) for v in (x, y1, y2, width_px)):
            continue
        if y2 < y1 or width_px <= 0:
            continue
        kind = item.get("kind", "")
        color = (180, 60, 180) if kind == "curly_brace_candidate" else (80, 100, 210)
        half_width = max(1, int(round(width_px / 2)))
        center_x = int(round(x))
        top_y, bottom_y = int(round(y1)), int(round(y2))
        cv2.rectangle(
            overlay,
            (max(0, center_x - half_width), max(0, top_y)),
            (min(width - 1, center_x + half_width), min(height - 1, bottom_y)),
            color, 2,
        )
        tag = {
            "curly_brace_candidate": "BRACE?",
            "square_bracket_candidate": "BRACKET?",
        }.get(kind, "GROUP?")
        label(tag, center_x + half_width + 3, top_y - 3, color)

    # Intervalos entre barras: se dibujan como límites verticales en el staff.
    for item in page_data.get("measure_span_candidates", []):
        if not isinstance(item, dict):
            continue
        staff_index = item.get("staff_index")
        if not isinstance(staff_index, int) or isinstance(staff_index, bool) or not 0 <= staff_index < len(staves):
            continue
        lines = staves[staff_index].get("lines_y", [])
        if len(lines) != 5:
            continue
        x1, x2 = item.get("x_start"), item.get("x_end")
        if isinstance(x1, (int, float)) and isinstance(x2, (int, float)):
            cv2.line(overlay, point(x1, lines[0]), point(x1, lines[-1]), (120, 180, 40), 1)
            cv2.line(overlay, point(x2, lines[0]), point(x2, lines[-1]), (120, 180, 40), 1)
            label("MEASURE?", int(x1), int(lines[0]) - 4, (120, 180, 40))

    return overlay
