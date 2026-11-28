"""Puente de análisis de página a candidatos de altura con contexto revisado."""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import replace
from types import SimpleNamespace
from typing import Any

from .pitch_candidates import PitchCandidate, build_pitch_candidates

_CLEFS = {"treble", "bass", "alto", "tenor"}
_CONTEXT_STATES = {
    "human_confirmed", "pending_human_review",
    "conflicting_human_labels", "no_clef_evidence",
    "no_key_signature_evidence",
}


def _normalize_context_map(values: Mapping[Any, Any]) -> dict[int, Any]:
    if not isinstance(values, Mapping):
        raise ValueError("staff_contexts debe ser un mapa")
    result: dict[int, Any] = {}
    for raw_index, context in values.items():
        if isinstance(raw_index, bool):
            raise ValueError("Índice de pentagrama no válido")
        try:
            index = int(raw_index)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Índice de pentagrama no válido: {raw_index!r}") from exc
        if index < 0 or str(index) != str(raw_index) or index in result:
            raise ValueError(f"Índice de pentagrama no válido o duplicado: {raw_index!r}")
        if not isinstance(context, Mapping):
            raise ValueError(f"Contexto del pentagrama {index} debe ser un objeto")
        result[index] = context
    return result


def build_pitch_candidates_from_page_analysis(
    page_analysis: Mapping[str, Any],
    staff_contexts: Mapping[int | str, Mapping[str, Any]],
    *,
    measure_ids: Sequence[str | int | None] | None = None,
    simultaneous_group_ids: Sequence[str | int | None] | None = None,
    explicit_accidentals: Sequence[str | None] | None = None,
) -> dict[str, Any]:
    """Interpreta posiciones verticales solo con clave y armadura confirmadas.

    `human_confirmed` es obligatorio tanto para la clave como para la
    armadura. Una armadura vacía también debe confirmarse explícitamente:
    significa que el pentagrama no tiene alteraciones de armadura.
    """
    if not isinstance(page_analysis, Mapping):
        raise ValueError("page_analysis debe ser un objeto")
    page_number = page_analysis.get("page_number")
    if not isinstance(page_number, int) or isinstance(page_number, bool) or page_number < 1:
        raise ValueError("page_number debe ser un entero positivo")
    raw_heads = page_analysis.get("notehead_candidates")
    if not isinstance(raw_heads, list):
        raise ValueError("El análisis debe incluir notehead_candidates")
    contexts = _normalize_context_map(staff_contexts)

    noteheads = []
    head_staffs: list[int] = []
    for index, raw in enumerate(raw_heads):
        if not isinstance(raw, Mapping):
            raise ValueError(f"notehead_candidates[{index}] debe ser un objeto")
        staff = raw.get("staff_index")
        step = raw.get("diatonic_step_from_bottom")
        center_x = raw.get("center_x")
        if not isinstance(staff, int) or isinstance(staff, bool) or staff < 0:
            raise ValueError(f"notehead_candidates[{index}] tiene staff_index no válido")
        if not isinstance(step, int) or isinstance(step, bool):
            raise ValueError(f"notehead_candidates[{index}] no tiene posición diatónica válida")
        if not isinstance(center_x, (int, float)) or isinstance(center_x, bool):
            raise ValueError(f"notehead_candidates[{index}] no tiene center_x válido")
        noteheads.append(SimpleNamespace(
            staff_index=staff, diatonic_step_from_bottom=step, center_x=float(center_x)
        ))
        head_staffs.append(staff)

    clefs: dict[int, str] = {}
    signatures: dict[int, Mapping[str, int]] = {}
    context_by_staff: dict[int, tuple[str, str]] = {}
    unresolved_staffs: dict[int, dict[str, str]] = {}
    for staff in sorted(set(head_staffs)):
        context = contexts.get(staff, {})
        clef_status = context.get("clef_status", "no_clef_evidence")
        key_status = context.get("key_signature_status", "no_key_signature_evidence")
        if clef_status not in _CONTEXT_STATES:
            raise ValueError(f"Estado de clave no válido en pentagrama {staff}")
        if key_status not in _CONTEXT_STATES:
            raise ValueError(f"Estado de armadura no válido en pentagrama {staff}")
        clef = context.get("clef")
        signature = context.get("key_signature")
        if clef_status == "human_confirmed":
            if clef not in _CLEFS:
                raise ValueError(f"Clave confirmada no soportada en pentagrama {staff}")
            clefs[staff] = clef
        if key_status == "human_confirmed":
            if not isinstance(signature, Mapping):
                raise ValueError(f"La armadura confirmada del pentagrama {staff} debe ser un mapa")
            signatures[staff] = dict(signature)
        if clef_status != "human_confirmed":
            unresolved_staffs[staff] = {
                "staff_index": str(staff), "reason": "unresolved_clef",
            }
        elif key_status != "human_confirmed":
            unresolved_staffs[staff] = {
                "staff_index": str(staff), "reason": "unresolved_key_signature",
            }
        context_by_staff[staff] = (clef_status, key_status)

    # No permitir que un pentagrama con contexto incompleto reciba MIDI por
    # la armadura vacía implícita del motor de alturas.
    safe_clefs = {
        staff: clefs[staff]
        for staff, (clef_status, key_status) in context_by_staff.items()
        if clef_status == "human_confirmed" and key_status == "human_confirmed"
    }
    safe_signatures = {
        staff: signatures[staff] for staff in safe_clefs
    }
    base = build_pitch_candidates(
        noteheads,
        staff_clefs=safe_clefs,
        key_signatures=safe_signatures,
        measure_ids=measure_ids,
        simultaneous_group_ids=simultaneous_group_ids,
        explicit_accidentals=explicit_accidentals,
        source_indices=list(range(len(noteheads))),
    )

    candidates: list[PitchCandidate] = []
    for index, candidate in enumerate(base):
        staff = head_staffs[index]
        if staff in unresolved_staffs:
            clef_status, key_status = context_by_staff[staff]
            reason = "unresolved_clef" if clef_status != "human_confirmed" else "unresolved_key_signature"
            candidate = replace(
                candidate,
                clef=clefs.get(staff),
                key_signature=dict(signatures.get(staff, {})),
                status=reason,
                pitch=None,
            )
        candidates.append(candidate)

    return {
        "status": "unconfirmed_page_pitch_candidates",
        "page_number": page_number,
        "pitch_candidates": [item.to_dict() for item in candidates],
        "unresolved_staff_contexts": [
            unresolved_staffs[index] for index in sorted(unresolved_staffs)
        ],
        "warning": (
            "Las alturas son derivadas de posiciones geométricas y contexto "
            "notacional confirmado; no validan la detección de cabezas, claves, "
            "armaduras, alteraciones ni voces."
        ),
    }
