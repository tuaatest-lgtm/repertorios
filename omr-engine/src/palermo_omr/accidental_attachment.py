"""Adjunta glifos de alteración revisados a cabezas sin adivinar notas.

La geometría propone una relación; la aplicación musical requiere aceptación
humana explícita para que una proximidad espacial no cambie una altura por error.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

_ALLOWED = {"sharp", "flat", "natural", "double_sharp", "double_flat"}


def _box(value: Any, label: str) -> tuple[float, float, float, float]:
    if isinstance(value, Mapping):
        value = value.get("bbox")
    if not isinstance(value, (list, tuple)) or len(value) != 4:
        raise ValueError(f"{label}: bbox debe tener x, y, width, height")
    x, y, width, height = value
    if any(not isinstance(v, (int, float)) or isinstance(v, bool) for v in value):
        raise ValueError(f"{label}: bbox debe contener números")
    x, y, width, height = map(float, value)
    if width <= 0 or height <= 0:
        raise ValueError(f"{label}: dimensiones de bbox deben ser positivas")
    return x, y, width, height


def attach_reviewed_accidentals(
    accidental_glyphs: Sequence[Mapping[str, Any]],
    noteheads: Sequence[Mapping[str, Any]],
    staff_spacing_by_index: Mapping[int, float],
    *,
    max_vertical_spacing_ratio: float = 0.65,
    max_horizontal_spacing_ratio: float = 2.5,
    ambiguity_score_margin: float = 0.15,
) -> dict[str, Any]:
    """Propone la cabeza destino de cada alteración confirmada visualmente.

    Solo compara cabezas del mismo pentagrama y compás, a la derecha del glifo.
    Si no hay una única cabeza claramente más próxima, no adjunta la alteración.
    El resultado nunca modifica alturas; requiere aceptación humana posterior.
    """
    for name, value in (
        ("max_vertical_spacing_ratio", max_vertical_spacing_ratio),
        ("max_horizontal_spacing_ratio", max_horizontal_spacing_ratio),
        ("ambiguity_score_margin", ambiguity_score_margin),
    ):
        if not isinstance(value, (int, float)) or isinstance(value, bool) or value < 0:
            raise ValueError(f"{name} debe ser un número no negativo")
    if max_vertical_spacing_ratio == 0 or max_horizontal_spacing_ratio == 0:
        raise ValueError("Los límites de distancia deben ser positivos")
    if not isinstance(staff_spacing_by_index, Mapping):
        raise ValueError("staff_spacing_by_index debe ser un mapa")

    spacings: dict[int, float] = {}
    for staff, spacing in staff_spacing_by_index.items():
        if not isinstance(staff, int) or isinstance(staff, bool) or staff < 0:
            raise ValueError("Los índices de pentagrama deben ser enteros no negativos")
        if not isinstance(spacing, (int, float)) or isinstance(spacing, bool) or spacing <= 0:
            raise ValueError("El espaciado de pentagrama debe ser positivo")
        spacings[staff] = float(spacing)

    heads_by_id: dict[str, dict[str, Any]] = {}
    for index, head in enumerate(noteheads):
        if not isinstance(head, Mapping):
            raise ValueError(f"noteheads[{index}] debe ser un objeto")
        head_id = head.get("candidate_id")
        staff = head.get("staff_index")
        measure = head.get("measure_id")
        if not isinstance(head_id, str) or not head_id.strip() or head_id in heads_by_id:
            raise ValueError("Los candidate_id de cabezas deben ser únicos y no vacíos")
        if not isinstance(staff, int) or isinstance(staff, bool) or staff not in spacings:
            raise ValueError(f"{head_id}: falta espaciado/índice de pentagrama")
        if measure is None or not isinstance(measure, (str, int)) or isinstance(measure, bool):
            raise ValueError(f"{head_id}: requiere measure_id explícito")
        heads_by_id[head_id] = {
            "staff_index": staff, "measure_id": measure,
            "bbox": _box(head.get("bbox"), head_id),
        }

    attached_to: dict[str, list[str]] = {}
    attachments: list[dict[str, Any]] = []
    unresolved: list[dict[str, str]] = []
    seen_glyphs: set[str] = set()

    for index, glyph in enumerate(accidental_glyphs):
        if not isinstance(glyph, Mapping):
            raise ValueError(f"accidental_glyphs[{index}] debe ser un objeto")
        glyph_id = glyph.get("candidate_id")
        if not isinstance(glyph_id, str) or not glyph_id.strip() or glyph_id in seen_glyphs:
            raise ValueError("Los candidate_id de alteraciones deben ser únicos y no vacíos")
        seen_glyphs.add(glyph_id)
        if glyph.get("status") != "human_confirmed":
            unresolved.append({"candidate_id": glyph_id, "reason": "glyph_not_human_confirmed"})
            continue
        kind = glyph.get("kind")
        if kind not in _ALLOWED:
            unresolved.append({"candidate_id": glyph_id, "reason": "unsupported_accidental_kind"})
            continue
        staff = glyph.get("staff_index")
        measure = glyph.get("measure_id")
        if not isinstance(staff, int) or isinstance(staff, bool) or staff not in spacings:
            unresolved.append({"candidate_id": glyph_id, "reason": "missing_staff_spacing"})
            continue
        if measure is None or not isinstance(measure, (str, int)) or isinstance(measure, bool):
            unresolved.append({"candidate_id": glyph_id, "reason": "missing_measure_context"})
            continue
        gx, gy, gw, gh = _box(glyph.get("bbox"), glyph_id)
        spacing = spacings[staff]
        glyph_cy = gy + gh / 2
        candidates = []
        for head_id, head in heads_by_id.items():
            if head["staff_index"] != staff or head["measure_id"] != measure:
                continue
            hx, hy, hw, hh = head["bbox"]
            gap_x = hx + hw / 2 - (gx + gw)
            delta_y = abs(hy + hh / 2 - glyph_cy)
            if gap_x < 0 or gap_x > max_horizontal_spacing_ratio * spacing:
                continue
            if delta_y > max_vertical_spacing_ratio * spacing:
                continue
            score = (delta_y / spacing) + (gap_x / (max_horizontal_spacing_ratio * spacing))
            candidates.append((score, head_id, delta_y, gap_x))
        candidates.sort(key=lambda item: (item[0], item[1]))
        if not candidates:
            unresolved.append({"candidate_id": glyph_id, "reason": "no_compatible_notehead"})
            continue
        if len(candidates) > 1 and candidates[1][0] - candidates[0][0] <= ambiguity_score_margin:
            unresolved.append({"candidate_id": glyph_id, "reason": "ambiguous_notehead_attachment"})
            continue
        _, head_id, delta_y, gap_x = candidates[0]
        attached_to.setdefault(head_id, []).append(glyph_id)
        attachments.append({
            "accidental_id": glyph_id,
            "notehead_id": head_id,
            "kind": kind,
            "staff_index": staff,
            "measure_id": measure,
            "vertical_distance_px": round(delta_y, 4),
            "horizontal_gap_px": round(gap_x, 4),
            "status": "pending_human_attachment_review",
        })

    conflicted = {head_id for head_id, glyph_ids in attached_to.items() if len(glyph_ids) > 1}
    if conflicted:
        conflicted_ids = {glyph_id for head_id in conflicted for glyph_id in attached_to[head_id]}
        attachments = [item for item in attachments if item["accidental_id"] not in conflicted_ids]
        unresolved.extend(
            {"candidate_id": glyph_id, "reason": "multiple_accidentals_target_same_notehead"}
            for glyph_id in sorted(conflicted_ids)
        )

    return {
        "status": "unconfirmed_accidental_attachment_map",
        "attachments": sorted(attachments, key=lambda item: item["accidental_id"]),
        "unresolved": sorted(unresolved, key=lambda item: item["candidate_id"]),
        "warning": "Las asociaciones espaciales no alteran alturas hasta aceptación humana explícita.",
    }


def build_accepted_explicit_accidentals(
    notehead_ids: Sequence[str],
    attachment_map: Mapping[str, Any],
    accepted_accidental_ids: Sequence[str],
) -> list[str | None]:
    """Devuelve explicit_accidentals alineado con notehead_ids aceptados.

    Los IDs no aceptados o no resueltos producen None; no se propagan por
    proximidad ni por pertenecer al mismo acorde.
    """
    if not isinstance(attachment_map, Mapping) or attachment_map.get("status") != "unconfirmed_accidental_attachment_map":
        raise ValueError("Se requiere un mapa de adjunción Palermo provisional")
    if len(notehead_ids) != len(set(notehead_ids)):
        raise ValueError("notehead_ids debe ser único")
    if len(accepted_accidental_ids) != len(set(accepted_accidental_ids)):
        raise ValueError("accepted_accidental_ids debe ser único")
    by_head: dict[str, list[Mapping[str, Any]]] = {}
    known: set[str] = set()
    for item in attachment_map.get("attachments", []):
        glyph_id = item["accidental_id"]
        known.add(glyph_id)
        by_head.setdefault(item["notehead_id"], []).append(item)
    accepted = set(accepted_accidental_ids)
    unknown = accepted - known
    if unknown:
        raise ValueError(f"Alteraciones aceptadas sin adjunción resuelta: {sorted(unknown)}")
    result: list[str | None] = []
    for head_id in notehead_ids:
        matches = [item for item in by_head.get(head_id, []) if item["accidental_id"] in accepted]
        if len(matches) > 1:
            raise ValueError(f"{head_id}: más de una alteración aceptada")
        result.append(matches[0]["kind"] if matches else None)
    return result
