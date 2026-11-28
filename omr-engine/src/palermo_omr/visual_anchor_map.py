"""Proyección de geometría de cabezas/eventos hacia anclajes del cursor visual.

No inventa ubicaciones: exige página, sistema y compás explícitos. Para notas,
el rectángulo se obtiene de las cajas reales de las cabezas detectadas; para
silencios u otros eventos se puede suministrar una caja de glifo revisada.
"""
from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from typing import Any


def _payload(value: Any) -> Mapping[str, Any]:
    if hasattr(value, "to_dict"):
        value = value.to_dict()
    if not isinstance(value, Mapping):
        raise ValueError("La geometría debe ser un mapa o implementar to_dict()")
    return value


def _bbox(value: Any, *, label: str) -> tuple[float, float, float, float]:
    payload = _payload(value)
    raw = payload.get("bbox")
    if not isinstance(raw, (tuple, list)) or len(raw) != 4:
        raise ValueError(f"{label}: bbox debe contener x, y, width, height")
    x, y, width, height = raw
    values = (x, y, width, height)
    if any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v)
           for v in values):
        raise ValueError(f"{label}: bbox contiene coordenadas no válidas")
    if width <= 0 or height <= 0:
        raise ValueError(f"{label}: bbox debe tener dimensiones positivas")
    return float(x), float(y), float(width), float(height)


def build_visual_anchor_map(
    events: Sequence[Any],
    notehead_geometry_by_id: Mapping[str, Any],
    *,
    page_index: int,
    system_by_staff: Mapping[int, int],
    measure_by_event: Mapping[str, int],
    event_geometry_by_id: Mapping[str, Any] | None = None,
    padding_px: float = 2.0,
) -> dict[str, Any]:
    """Construye anclajes compatibles con ScoreVisualCursor.

    Los IDs de cabezas de ScoreEventCandidate deben referir a la geometría
    producida en el mismo orden/documento. Los acordes reciben la unión de
    sus cajas. Los silencios sin cabezas requieren event_geometry_by_id.
    Eventos con contexto espacial incompleto se conservan en unresolved.
    """
    if not isinstance(page_index, int) or isinstance(page_index, bool) or page_index < 0:
        raise ValueError("page_index debe ser un entero no negativo")
    if not isinstance(system_by_staff, Mapping) or not isinstance(measure_by_event, Mapping):
        raise ValueError("Se requieren mapas explícitos de sistema y compás")
    if not isinstance(notehead_geometry_by_id, Mapping):
        raise ValueError("notehead_geometry_by_id debe ser un mapa")
    if isinstance(padding_px, bool) or not isinstance(padding_px, (int, float)) or not math.isfinite(padding_px) or padding_px < 0:
        raise ValueError("padding_px debe ser un número no negativo")
    event_geometry = event_geometry_by_id or {}
    anchors: list[dict[str, Any]] = []
    unresolved: list[dict[str, str]] = []
    seen: set[str] = set()

    for event in events:
        payload = _payload(event)
        event_id = payload.get("event_id")
        staff_index = payload.get("staff_index")
        if not isinstance(event_id, str) or not event_id.strip() or event_id in seen:
            raise ValueError("Los eventos deben tener event_id único y no vacío")
        seen.add(event_id)
        if not isinstance(staff_index, int) or isinstance(staff_index, bool) or staff_index < 0:
            unresolved.append({"event_id": event_id, "reason": "missing_staff"})
            continue
        system_index = system_by_staff.get(staff_index)
        measure_index = measure_by_event.get(event_id)
        if not isinstance(system_index, int) or isinstance(system_index, bool) or system_index < 0:
            unresolved.append({"event_id": event_id, "reason": "missing_system_mapping"})
            continue
        if not isinstance(measure_index, int) or isinstance(measure_index, bool) or measure_index < 0:
            unresolved.append({"event_id": event_id, "reason": "missing_measure_mapping"})
            continue

        head_ids = payload.get("notehead_candidate_ids", ())
        boxes = []
        if head_ids:
            if not isinstance(head_ids, (tuple, list)) or any(not isinstance(h, str) or not h for h in head_ids):
                raise ValueError(f"{event_id}: notehead_candidate_ids inválidos")
            missing = [head_id for head_id in head_ids if head_id not in notehead_geometry_by_id]
            if missing:
                unresolved.append({"event_id": event_id, "reason": "missing_notehead_geometry"})
                continue
            boxes = [_bbox(notehead_geometry_by_id[head_id], label=f"{event_id}/{head_id}")
                     for head_id in head_ids]
        elif event_id in event_geometry:
            boxes = [_bbox(event_geometry[event_id], label=event_id)]
        else:
            unresolved.append({"event_id": event_id, "reason": "missing_event_geometry"})
            continue

        left = min(box[0] for box in boxes)
        top = min(box[1] for box in boxes)
        right = max(box[0] + box[2] for box in boxes)
        bottom = max(box[1] + box[3] for box in boxes)
        padding = float(padding_px)
        anchors.append({
            "event_id": event_id,
            "page_index": page_index,
            "system_index": system_index,
            "measure_index": measure_index,
            "x": round(max(0.0, left - padding), 3),
            "y": round(max(0.0, top - padding), 3),
            "width": round(right - left + 2 * padding, 3),
            "height": round(bottom - top + 2 * padding, 3),
        })

    anchors.sort(key=lambda item: item["event_id"])
    unresolved.sort(key=lambda item: item["event_id"])
    return {
        "status": "unconfirmed_visual_anchor_map",
        "page_index": page_index,
        "anchors": anchors,
        "unresolved": unresolved,
        "warning": (
            "Anclajes visuales provisionales derivados de geometría explícita. "
            "No confirman la identidad musical ni la posición temporal."
        ),
    }
