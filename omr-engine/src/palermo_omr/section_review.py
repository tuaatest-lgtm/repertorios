"""Apply explicit human decisions to global section-range candidates."""
from __future__ import annotations

from copy import deepcopy


_ALLOWED_DECISIONS = {"accepted", "rejected", "needs_revision"}


def apply_section_range_decisions(
    package: dict,
    decisions: list[dict],
    *,
    human_review_confirmed: bool,
    allow_open_ended: bool = False,
) -> dict:
    """Return a reviewed copy of a section review package.

    A range is never accepted implicitly: callers must provide explicit human
    confirmation. Open-ended ranges require a second explicit opt-in.
    """
    if not human_review_confirmed:
        raise ValueError(
            "Se requiere confirmación humana explícita antes de aplicar decisiones"
        )
    if not isinstance(package, dict):
        raise ValueError("El paquete de revisión debe ser un objeto")
    if not isinstance(decisions, list) or not decisions:
        raise ValueError("Las decisiones deben ser una lista JSON no vacía")
    if not isinstance(allow_open_ended, bool):
        raise ValueError("allow_open_ended debe ser booleano")

    reviewed = deepcopy(package)
    ranges = reviewed.get("global_section_range_candidates")
    if not isinstance(ranges, list):
        raise ValueError("El paquete no contiene una lista de rangos globales")

    by_id = {}
    for item in ranges:
        if not isinstance(item, dict):
            raise ValueError("Cada rango global debe ser un objeto")
        range_id = item.get("section_range_id")
        if not isinstance(range_id, str) or not range_id.strip():
            raise ValueError("Cada rango requiere section_range_id no vacío")
        if range_id in by_id:
            raise ValueError("section_range_id duplicado en el paquete")
        by_id[range_id] = item

    seen = set()
    for decision in decisions:
        if not isinstance(decision, dict):
            raise ValueError("Cada decisión debe ser un objeto")
        if set(decision) - {"section_range_id", "decision", "notes"}:
            raise ValueError("La decisión contiene campos desconocidos")
        range_id = decision.get("section_range_id")
        status = decision.get("decision")
        notes = decision.get("notes", "")
        if not isinstance(range_id, str) or not range_id.strip():
            raise ValueError("Cada decisión requiere section_range_id no vacío")
        if range_id in seen:
            raise ValueError("No se permiten decisiones duplicadas para el mismo rango")
        seen.add(range_id)
        if range_id not in by_id:
            raise ValueError(f"No existe el rango section_range_id={range_id}")
        if status not in _ALLOWED_DECISIONS:
            raise ValueError("decision debe ser accepted, rejected o needs_revision")
        if not isinstance(notes, str):
            raise ValueError("notes debe ser texto")
        target = by_id[range_id]
        if target.get("review_status", "pending") != "pending":
            raise ValueError(f"El rango {range_id} ya tiene una decisión previa")

        if status == "accepted":
            start = target.get("start")
            if not isinstance(start, dict) or not isinstance(
                start.get("musical_boundary_candidate"), dict
            ):
                raise ValueError(
                    f"El rango {range_id} no tiene un límite inicial revisable"
                )
            end = target.get("end")
            if end is None:
                if not allow_open_ended:
                    raise ValueError(
                        f"El rango {range_id} es abierto; requiere allow_open_ended"
                    )
            elif not isinstance(end, dict) or not isinstance(
                end.get("musical_boundary_candidate"), dict
            ):
                raise ValueError(
                    f"El rango {range_id} no tiene un límite final revisable"
                )

        target["review_status"] = status
        target["review_decision"] = {
            "decision": status,
            "notes": notes,
            "human_review_confirmed": True,
        }

    summary = reviewed.get("summary")
    if isinstance(summary, dict):
        statuses = [item.get("review_status", "pending") for item in ranges]
        summary["global_section_range_candidate_count"] = len(ranges)
        summary["pending_global_section_range_candidate_count"] = statuses.count("pending")
        summary["accepted_global_section_range_candidate_count"] = statuses.count("accepted")
        summary["rejected_global_section_range_candidate_count"] = statuses.count("rejected")
        summary["needs_revision_global_section_range_candidate_count"] = statuses.count(
            "needs_revision"
        )
    return reviewed
