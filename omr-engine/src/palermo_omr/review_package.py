"""Paquetes de revisión humana para candidatos visuales de análisis OMR.

No convierte candidatos en notas, voces ni eventos musicales confirmados.
"""
from __future__ import annotations

from pathlib import Path
import json
from typing import Any


def _validated_indices(value: Any, upper_bound: int, label: str) -> list[int]:
    if not isinstance(value, list) or not value:
        raise ValueError(f"{label} debe contener índices")
    if any(
        not isinstance(item, int) or isinstance(item, bool)
        or item < 0 or item >= upper_bound
        for item in value
    ):
        raise ValueError(f"{label} referencia elementos inexistentes")
    if len(set(value)) != len(value):
        raise ValueError(f"{label} contiene índices duplicados")
    return value


def build_review_package(analysis: dict[str, Any], *, score_id: str) -> dict[str, Any]:
    if not isinstance(analysis, dict) or not isinstance(analysis.get("pages"), list):
        raise ValueError("analysis.json debe contener una lista pages")
    if not isinstance(score_id, str) or not score_id.strip():
        raise ValueError("score_id debe ser texto no vacío")

    pages = []
    seen_pages: set[int] = set()
    total_noteheads = 0
    total_other = 0
    for page in analysis["pages"]:
        if not isinstance(page, dict):
            raise ValueError("Cada página debe ser un objeto")
        page_number = page.get("page_number")
        if not isinstance(page_number, int) or isinstance(page_number, bool) or page_number < 1:
            raise ValueError("Cada página requiere page_number entero positivo")
        if page_number in seen_pages:
            raise ValueError("page_number duplicado en analysis.json")
        seen_pages.add(page_number)

        staves = page.get("staves", [])
        if not isinstance(staves, list):
            raise ValueError("staves debe ser una lista")
        staff_count = len(staves)
        staff_id_by_index = {
            f"p{page_number}-staff-{index + 1}": index
            for index in range(staff_count)
        }
        candidates = []
        filled_candidate_ids = []
        filled_candidate_staff_indices = []
        staff_candidates = [
            {
                "candidate_id": f"p{page_number}-staff-{index + 1}",
                "family": "staff_geometry",
                "staff_index": index,
                "candidate_data": staff,
                "review_status": "pending",
                "decision": None,
                "reviewer_note": "",
            }
            for index, staff in enumerate(staves)
        ]
        total_other += len(staff_candidates)
        for family, key, rhythm_key, interpretation_key in (
            ("filled_notehead", "notehead_candidates", "rhythm_candidates", "rhythmic_interpretation_candidates"),
            ("hollow_notehead", "hollow_notehead_candidates", "hollow_rhythm_candidates", None),
        ):
            heads = page.get(key, [])
            rhythms = page.get(rhythm_key, [])
            interpretations = page.get(interpretation_key, []) if interpretation_key else []
            if not isinstance(heads, list) or not isinstance(rhythms, list) or not isinstance(interpretations, list):
                raise ValueError(f"Candidatos de {family} deben ser listas")
            if len(rhythms) not in (0, len(heads)):
                raise ValueError(f"Ritmos de {family} no corresponden uno a uno con sus cabezas")
            if interpretations and len(interpretations) != len(heads):
                raise ValueError("Interpretaciones rítmicas no corresponden con cabezas rellenas")
            for index, head in enumerate(heads):
                if not isinstance(head, dict):
                    raise ValueError("Cada cabeza candidata debe ser un objeto")
                staff_index = head.get("staff_index")
                if (not isinstance(staff_index, int) or isinstance(staff_index, bool) or not 0 <= staff_index < staff_count):
                    raise ValueError("Una cabeza candidata referencia un pentagrama inexistente")
                candidates.append({
                    "candidate_id": f"p{page_number}-{family}-{index + 1}",
                    "family": family,
                    "candidate_index": index,
                    "staff_index": staff_index,
                    "related_candidate_ids": [f"p{page_number}-staff-{staff_index + 1}"],
                    "bbox": head.get("bbox"),
                    "center_x": head.get("center_x"),
                    "center_y": head.get("center_y"),
                    "diatonic_step_from_bottom": head.get("diatonic_step_from_bottom"),
                    "confidence_heuristic": head.get("confidence"),
                    "rhythm_hypothesis": rhythms[index] if rhythms else None,
                    "rhythm_interpretation_hypothesis": interpretations[index] if interpretations else None,
                    "review_status": "pending",
                    "decision": None,
                    "reviewer_note": "",
                })
                if family == "filled_notehead":
                    filled_candidate_ids.append(candidates[-1]["candidate_id"])
                    filled_candidate_staff_indices.append(staff_index)
                total_noteheads += 1

        # Se conserva también la geometría que relaciona símbolos y compases.
        # Estas relaciones siguen siendo candidatos y requieren revisión humana.
        other_families = (
            ("rest_shape", "rest_shape_candidates"),
            ("tie_slur_shape", "tie_slur_shape_candidates"),
            ("augmentation_dot", "augmentation_dot_candidates"),
            ("barline", "barline_candidates"),
            ("beam_group", "beam_group_candidates"),
            ("barline_group", "barline_group_candidates"),
            ("system_barline", "system_barline_candidates"),
            ("staff_system", "staff_system_candidates"),
            ("measure_span", "measure_span_candidates"),
            ("staff_grouping_mark", "staff_grouping_mark_candidates"),
            ("printed_label", "printed_label_candidates"),
            ("staff_identity_evidence", "staff_identity_evidence"),
            ("section_marker", "section_marker_candidates"),
            ("section_identifier", "section_identifier_candidates"),
            ("section_range", "section_range_candidates"),
        )
        other_candidates = []
        for family, key in other_families:
            values = page.get(key, [])
            if not isinstance(values, list):
                raise ValueError(f"{key} debe ser una lista")
            for index, value in enumerate(values):
                if not isinstance(value, dict):
                    raise ValueError(f"Cada elemento de {key} debe ser un objeto")
                related_ids = []
                if family == "augmentation_dot":
                    notehead_index = value.get("associated_notehead_index")
                    if (not isinstance(notehead_index, int) or isinstance(notehead_index, bool)
                            or not 0 <= notehead_index < len(filled_candidate_ids)):
                        raise ValueError("Un puntillo referencia una cabeza rellena inexistente")
                    staff_index = filled_candidate_staff_indices[notehead_index]
                    related_ids = [
                        filled_candidate_ids[notehead_index],
                        f"p{page_number}-staff-{staff_index + 1}",
                    ]
                elif family == "beam_group":
                    indices = _validated_indices(
                        value.get("notehead_indices", []),
                        len(filled_candidate_ids),
                        "Un grupo de vigas",
                    )
                    related_ids = [
                        filled_candidate_ids[item] for item in indices
                    ]
                elif family in {"rest_shape", "tie_slur_shape", "barline", "barline_group", "measure_span"}:
                    staff_index = value.get("staff_index")
                    if (not isinstance(staff_index, int) or isinstance(staff_index, bool)
                            or not 0 <= staff_index < staff_count):
                        raise ValueError(f"{key} referencia un pentagrama inexistente")
                    related_ids = [f"p{page_number}-staff-{staff_index + 1}"]
                elif family == "printed_label":
                    status = value.get("association_status")
                    if status not in {"associated_candidate", "ambiguous", "unassigned"}:
                        raise ValueError("Una etiqueta impresa tiene estado de asociación no válido")
                    if status == "associated_candidate":
                        staff_index = value.get("staff_index")
                        if (not isinstance(staff_index, int) or isinstance(staff_index, bool)
                                or not 0 <= staff_index < staff_count):
                            raise ValueError("Una etiqueta impresa referencia un pentagrama inexistente")
                        related_ids = [f"p{page_number}-staff-{staff_index + 1}"]
                elif family == "staff_identity_evidence":
                    staff_id = value.get("staff_id")
                    staff_index = staff_id_by_index.get(staff_id)
                    if staff_index is None:
                        raise ValueError("Una evidencia de identidad referencia un pentagrama inexistente")
                    related_ids = [f"p{page_number}-staff-{staff_index + 1}"]
                elif family in {"system_barline", "staff_system", "staff_grouping_mark"}:
                    indices = _validated_indices(
                        value.get("staff_indices", []),
                        staff_count,
                        key,
                    )
                    related_ids = [
                        f"p{page_number}-staff-{item + 1}" for item in indices
                    ]
                other_candidates.append({
                    "candidate_id": f"p{page_number}-{family}-{index + 1}",
                    "family": family,
                    "candidate_index": index,
                    "candidate_data": value,
                    "related_candidate_ids": related_ids,
                    "review_status": "pending",
                    "decision": None,
                    "reviewer_note": "",
                })
                total_other += 1

        pages.append({
            "page_number": page_number,
            "staff_count": staff_count,
            "staff_candidates": staff_candidates,
            "overlays": {
                "filled_noteheads": page.get("notehead_overlay"),
                "hollow_noteheads": page.get("hollow_notehead_overlay"),
                "geometry": page.get("geometry_overlay"),
            },
            "notehead_candidates": candidates,
            "other_candidates": other_candidates,
        })

    if not pages:
        raise ValueError("El análisis no contiene páginas")
    pages.sort(key=lambda item: item["page_number"])
    return {
        "review_package_version": "1.0",
        "score_id": score_id,
        "source_pdf": analysis.get("source_pdf"),
        "analysis_version": analysis.get("version"),
        "global_section_range_candidates": analysis.get("global_section_range_candidates", []),
        "global_measure_sequence": analysis.get("global_measure_sequence", {
            "global_measure_candidates": [],
            "global_measure_candidate_count": 0,
            "staff_measure_map": [],
            "warning": "No se proporcionó una secuencia global de intervalos candidatos.",
        }),
        "review_policy": (
            "Todos los elementos son candidatos visuales. No representan eventos, "
            "alturas, voces ni duraciones confirmadas. La revisión humana debe "
            "consultar el PDF y los overlays originales."
        ),
        "summary": {
            "page_count": len(pages),
            "notehead_candidate_count": total_noteheads,
            "other_candidate_count": total_other,
            "pending_count": total_noteheads + total_other,
        },
        "pages": pages,
    }


def prepare_review_package(
    analysis_path: str | Path,
    output_path: str | Path,
    *,
    score_id: str,
) -> dict[str, Any]:
    source = Path(analysis_path)
    try:
        analysis = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"No se pudo leer analysis.json: {exc}") from exc
    package = build_review_package(analysis, score_id=score_id)
    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".tmp")
    temporary.write_text(
        json.dumps(package, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(destination)
    return package
