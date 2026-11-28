"""Selección reproducible de un fragmento para revisión humana.

No crea eventos musicales ni aprueba candidatos. Conserva los IDs del paquete
original y limita el trabajo a una página y un conjunto explícito de pentagramas.
"""
from __future__ import annotations

from typing import Any


def build_focused_review_package(
    review_package: dict[str, Any],
    *,
    page_number: int,
    staff_indices: list[int],
    scope_label: str = "Fragmento seleccionado",
) -> dict[str, Any]:
    """Devuelve un paquete de revisión acotado sin alterar candidatos ni IDs."""
    if not isinstance(review_package, dict):
        raise ValueError("El paquete de revisión debe ser un objeto")
    if review_package.get("review_package_version") != "1.0":
        raise ValueError("Versión de paquete de revisión no compatible")
    if not isinstance(page_number, int) or isinstance(page_number, bool) or page_number < 1:
        raise ValueError("page_number debe ser un entero positivo")
    if not isinstance(staff_indices, list) or not staff_indices:
        raise ValueError("staff_indices debe contener al menos un pentagrama")
    if any(
        not isinstance(index, int) or isinstance(index, bool) or index < 0
        for index in staff_indices
    ):
        raise ValueError("staff_indices debe contener enteros no negativos")
    if len(set(staff_indices)) != len(staff_indices):
        raise ValueError("staff_indices no puede contener duplicados")
    if not isinstance(scope_label, str) or not scope_label.strip():
        raise ValueError("scope_label debe ser texto no vacío")

    pages = review_package.get("pages")
    if not isinstance(pages, list):
        raise ValueError("El paquete debe contener pages")
    matches = [page for page in pages if page.get("page_number") == page_number]
    if len(matches) != 1:
        raise ValueError("page_number no identifica una única página del paquete")
    source_page = matches[0]
    staff_count = source_page.get("staff_count")
    if not isinstance(staff_count, int) or isinstance(staff_count, bool) or staff_count < 1:
        raise ValueError("La página no contiene un recuento válido de pentagramas")
    if any(index >= staff_count for index in staff_indices):
        raise ValueError("staff_indices referencia un pentagrama inexistente")

    selected_staff_ids = {
        f"p{page_number}-staff-{index + 1}" for index in staff_indices
    }
    staff_candidates = source_page.get("staff_candidates", [])
    noteheads = source_page.get("notehead_candidates", [])
    other = source_page.get("other_candidates", [])
    if not all(isinstance(items, list) for items in (staff_candidates, noteheads, other)):
        raise ValueError("La página contiene listas de candidatos inválidas")

    selected_staves = [
        item for item in staff_candidates
        if isinstance(item, dict) and item.get("staff_index") in staff_indices
    ]
    if {item.get("candidate_id") for item in selected_staves} != selected_staff_ids:
        raise ValueError("Faltan candidatos geométricos para uno o más pentagramas")

    selected_noteheads = [
        item for item in noteheads
        if isinstance(item, dict) and item.get("staff_index") in staff_indices
    ]
    notehead_ids = {
        item.get("candidate_id") for item in selected_noteheads
        if isinstance(item.get("candidate_id"), str)
    }
    selected_other = []
    for item in other:
        if not isinstance(item, dict):
            raise ValueError("Un candidato relacionado no es un objeto")
        related = item.get("related_candidate_ids", [])
        if not isinstance(related, list):
            raise ValueError("related_candidate_ids debe ser una lista")
        selected_scope_ids = selected_staff_ids | notehead_ids
        if related and set(related).issubset(selected_scope_ids):
            selected_other.append(item)

    all_selected_ids = (
        selected_staff_ids
        | notehead_ids
        | {
            item["candidate_id"] for item in selected_other
            if isinstance(item.get("candidate_id"), str)
        }
    )
    if len(all_selected_ids) != (
        len(selected_staff_ids) + len(notehead_ids) + len(selected_other)
    ):
        raise ValueError("Los IDs de candidatos seleccionados deben ser únicos")

    staff_lines = []
    for item in selected_staves:
        lines = item.get("candidate_data", {}).get("lines_y")
        if not isinstance(lines, list) or len(lines) != 5:
            raise ValueError("Cada pentagrama seleccionado requiere cinco líneas")
        if any(not isinstance(y, (int, float)) or isinstance(y, bool) for y in lines):
            raise ValueError("Las coordenadas de pentagrama deben ser numéricas")
        staff_lines.extend(lines)

    focused_page = {
        "page_number": page_number,
        "staff_count": len(selected_staves),
        "staff_candidates": selected_staves,
        "overlays": source_page.get("overlays", {}),
        "notehead_candidates": selected_noteheads,
        "other_candidates": selected_other,
    }
    return {
        "focused_review_package_version": "1.0",
        "score_id": review_package.get("score_id"),
        "source_pdf": review_package.get("source_pdf"),
        "source_analysis_version": review_package.get("analysis_version"),
        "source_review_package_version": review_package.get("review_package_version"),
        "scope": {
            "label": scope_label.strip(),
            "page_number": page_number,
            "staff_indices": sorted(staff_indices),
            "staff_candidate_ids": sorted(selected_staff_ids),
            "vertical_bounds_px": [min(staff_lines), max(staff_lines)],
            "selection_basis": "human_selected_region",
            "review_status": "pending",
            "warning": (
                "La selección delimita el área de trabajo; no confirma que los "
                "pentagramas formen una misma parte, sistema, instrumento o voz."
            ),
        },
        "candidate_ids": sorted(all_selected_ids),
        "summary": {
            "staff_candidate_count": len(selected_staves),
            "notehead_candidate_count": len(selected_noteheads),
            "other_candidate_count": len(selected_other),
            "pending_candidate_count": len(all_selected_ids),
            "event_count": 0,
            "annotation_status": "draft",
            "ground_truth_eligible": False,
        },
        "review_policy": (
            "Los candidatos conservan su estado y sus IDs de origen. No se crean "
            "ScoreEvent, alturas, compases, voces, onsets ni duraciones confirmadas. "
            "La aprobación requiere anotación y revisión humana independiente."
        ),
        "pages": [focused_page],
        "events": [],
        "annotation_status": "draft",
        "ground_truth_eligible": False,
    }
