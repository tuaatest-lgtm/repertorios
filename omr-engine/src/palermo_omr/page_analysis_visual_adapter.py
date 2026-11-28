"""Adaptador del JSON de análisis de página a anclajes del cursor visual."""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from .imaging import StaffCandidate
from .measure_layout import MeasureSpanCandidate, StaffSystemCandidate
from .score_geometry import build_geometric_score_structure
from .visual_anchor_map import build_visual_anchor_map_from_score_structure


def build_visual_anchor_map_from_page_analysis(
    page_analysis: Mapping[str, Any],
    event_notehead_indices: Mapping[str, Sequence[int]],
    *,
    event_staff_indices: Mapping[str, int] | None = None,
    event_geometry_by_id: Mapping[str, Any] | None = None,
    padding_px: float = 2.0,
) -> dict[str, Any]:
    """Construye anclajes desde la salida JSON real del análisis de página.

    Los índices de cabeza deben referir al array notehead_candidates de esa
    página. Cada evento conserva su ID externo; los IDs de cabeza se hacen
    deterministas como p{page}-head-{index}. No asigna voz ni altura musical.
    """
    if not isinstance(page_analysis, Mapping):
        raise ValueError("page_analysis debe ser un objeto")
    page_number = page_analysis.get("page_number")
    staves_raw = page_analysis.get("staves")
    systems_raw = page_analysis.get("staff_system_candidates")
    spans_raw = page_analysis.get("measure_span_candidates")
    heads_raw = page_analysis.get("notehead_candidates")
    if not isinstance(staves_raw, list) or not isinstance(systems_raw, list) or not isinstance(spans_raw, list) or not isinstance(heads_raw, list):
        raise ValueError("El análisis debe incluir staves, systems, measure spans y noteheads")

    staves = [StaffCandidate(
        lines_y=list(item["lines_y"]),
        spacing_px=float(item["spacing_px"]),
        confidence=float(item.get("confidence", 0.0)),
    ) for item in staves_raw]
    systems = [StaffSystemCandidate(
        system_index=int(item["system_index"]),
        staff_indices=list(item["staff_indices"]),
        y_top=float(item["y_top"]),
        y_bottom=float(item["y_bottom"]),
        confidence=float(item["confidence"]),
        warning=str(item.get("warning", "Sistema geométrico candidato.")),
    ) for item in systems_raw]
    spans = [MeasureSpanCandidate(
        staff_index=int(item["staff_index"]),
        measure_index=int(item["measure_index"]),
        x_start=float(item["x_start"]),
        x_end=float(item["x_end"]),
        width_px=float(item.get("width_px", item["x_end"] - item["x_start"])),
        left_boundary_observed=bool(item.get("left_boundary_observed", False)),
        right_boundary_observed=bool(item.get("right_boundary_observed", False)),
        confidence=float(item.get("confidence", 0.0)),
        warning=str(item.get("warning", "Intervalo geométrico candidato.")),
    ) for item in spans_raw]
    structure = build_geometric_score_structure(page_number, staves, systems, spans)

    if not isinstance(event_notehead_indices, Mapping):
        raise ValueError("event_notehead_indices debe ser un mapa")
    staff_overrides = dict(event_staff_indices or {})
    geometry_by_event = dict(event_geometry_by_id or {})
    notehead_geometry = {
        f"p{page_number}-head-{index}": item
        for index, item in enumerate(heads_raw)
    }
    events = []
    unresolved: list[dict[str, str]] = []
    assigned_heads: set[int] = set()

    for event_id, raw_indices in sorted(event_notehead_indices.items()):
        if not isinstance(event_id, str) or not event_id.strip():
            raise ValueError("Los event_id deben ser textos no vacíos")
        if not isinstance(raw_indices, (tuple, list)):
            raise ValueError(f"{event_id}: los índices de cabezas deben ser una lista")
        indices = list(raw_indices)
        if any(not isinstance(index, int) or isinstance(index, bool) or index < 0 or index >= len(heads_raw)
               for index in indices):
            raise ValueError(f"{event_id}: índice de cabeza fuera del rango de la página")
        if len(indices) != len(set(indices)):
            raise ValueError(f"{event_id}: no se puede repetir una cabeza")
        if assigned_heads.intersection(indices):
            raise ValueError("Una cabeza no puede asignarse a más de un evento")
        assigned_heads.update(indices)
        head_staffs = {heads_raw[index].get("staff_index") for index in indices}
        if len(head_staffs) > 1:
            unresolved.append({"event_id": event_id, "reason": "cross_staff_event"})
            continue
        staff_index = staff_overrides.get(event_id)
        if staff_index is None and head_staffs:
            staff_index = next(iter(head_staffs))
        if staff_index is None:
            unresolved.append({"event_id": event_id, "reason": "missing_staff"})
            continue
        if head_staffs and staff_index not in head_staffs:
            unresolved.append({"event_id": event_id, "reason": "staff_mismatch"})
            continue
        events.append({
            "event_id": event_id,
            "staff_index": staff_index,
            "notehead_candidate_ids": [
                f"p{page_number}-head-{index}" for index in indices
            ],
        })

    # Los silencios/eventos sin cabeza requieren índice de pentagrama explícito.
    for event_id in sorted(set(staff_overrides) - set(event_notehead_indices)):
        staff_index = staff_overrides[event_id]
        events.append({
            "event_id": event_id, "staff_index": staff_index,
            "notehead_candidate_ids": [],
        })

    result = build_visual_anchor_map_from_score_structure(
        events, notehead_geometry, structure,
        event_geometry_by_id=geometry_by_event,
        padding_px=padding_px,
    )
    merged = {item["event_id"]: item for item in result["unresolved"]}
    for item in unresolved:
        merged[item["event_id"]] = item
    result["unresolved"] = sorted(merged.values(), key=lambda item: item["event_id"])
    result["notehead_id_by_index"] = {
        str(index): f"p{page_number}-head-{index}" for index in range(len(heads_raw))
    }
    return result
