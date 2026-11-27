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
    global_section_ranges = analysis.get("global_section_range_candidates", [])
    global_measure_sequence = analysis.get("global_measure_sequence", {
        "global_measure_candidates": [],
        "global_measure_candidate_count": 0,
        "staff_measure_map": [],
        "warning": "No se proporcionó una secuencia global de intervalos candidatos.",
    })
    if not isinstance(global_section_ranges, list):
        raise ValueError("global_section_range_candidates debe ser una lista")
    if not isinstance(global_measure_sequence, dict):
        raise ValueError("global_measure_sequence debe ser un objeto")
    global_measure_candidates = global_measure_sequence.get("global_measure_candidates", [])
    cross_staff_aligned_count = global_measure_sequence.get(
        "cross_staff_aligned_candidate_count", 0
    )
    single_staff_only_count = global_measure_sequence.get(
        "single_staff_only_candidate_count", len(global_measure_candidates)
    )
    measure_sequence_scope = global_measure_sequence.get("sequence_scope", "unknown")
    staff_measure_map = global_measure_sequence.get("staff_measure_map", [])
    if not isinstance(global_measure_candidates, list):
        raise ValueError("global_measure_candidates debe ser una lista")
    if (not isinstance(cross_staff_aligned_count, int)
            or isinstance(cross_staff_aligned_count, bool)
            or cross_staff_aligned_count < 0
            or not isinstance(single_staff_only_count, int)
            or isinstance(single_staff_only_count, bool)
            or single_staff_only_count < 0):
        raise ValueError("Los conteos de alineación de compases deben ser enteros no negativos")
    if cross_staff_aligned_count + single_staff_only_count > len(global_measure_candidates):
        raise ValueError("Los conteos de alineación superan los compases candidatos")
    if not isinstance(staff_measure_map, list):
        raise ValueError("staff_measure_map debe ser una lista")
    if any(not isinstance(item, dict) for item in global_measure_candidates):
        raise ValueError("Cada compás global candidato debe ser un objeto")
    if any(not isinstance(item, dict) for item in staff_measure_map):
        raise ValueError("Cada referencia local/global debe ser un objeto")
    if any(not isinstance(item, dict) for item in global_section_ranges):
        raise ValueError("Cada rango global de sección debe ser un objeto")
    for section_range in global_section_ranges:
        if not isinstance(section_range.get("start"), dict):
            raise ValueError("Cada rango global requiere un extremo inicial")
        if section_range.get("end") is not None and not isinstance(section_range.get("end"), dict):
            raise ValueError("El extremo final del rango debe ser un objeto o null")
    section_range_statuses = [
        item.get("review_status", "pending")
        for item in global_section_ranges if isinstance(item, dict)
    ]
    if any(status not in {"pending", "accepted", "rejected", "needs_revision"}
           for status in section_range_statuses):
        raise ValueError("review_status de rango de sección no válido")
    pending_section_ranges = section_range_statuses.count("pending")
    accepted_section_ranges = section_range_statuses.count("accepted")
    rejected_section_ranges = section_range_statuses.count("rejected")
    needs_revision_section_ranges = section_range_statuses.count("needs_revision")
    section_boundary_candidates = [
        boundary.get("musical_boundary_candidate")
        for item in global_section_ranges if isinstance(item, dict)
        for boundary in (item.get("start"), item.get("end"))
        if isinstance(boundary, dict)
        and isinstance(boundary.get("musical_boundary_candidate"), dict)
    ]
    cross_staff_section_boundaries = sum(
        item.get("global_alignment_status") == "cross_staff_alignment_candidate"
        for item in section_boundary_candidates
    )
    single_staff_section_boundaries = sum(
        item.get("global_alignment_status") == "single_staff_only_unmatched"
        for item in section_boundary_candidates
    )
    unmatched_section_boundaries = sum(
        item.get("global_alignment_status") in (None, "unmatched_local_interval", "unknown")
        for item in section_boundary_candidates
    )
    partial_section_boundaries = sum(
        item.get("partial_measure_boundary") is True
        for item in section_boundary_candidates
    )
    inside_measure_section_boundaries = sum(
        item.get("position_kind") == "inside_measure_candidate"
        for item in section_boundary_candidates
    )
    before_measure_section_boundaries = sum(
        item.get("position_kind") == "before_measure_candidate"
        for item in section_boundary_candidates
    )
    after_measure_section_boundaries = sum(
        item.get("position_kind") == "after_measure_candidate"
        for item in section_boundary_candidates
    )
    pending_measure_candidates = sum(
        1 for item in global_measure_candidates
        if isinstance(item, dict) and item.get("review_status", "pending") == "pending"
    )
    section_marker_reviews = [
        item for page in pages for item in page["other_candidates"]
        if item["family"] == "section_marker"
    ]
    section_marker_statuses = [
        item["candidate_data"].get("global_boundary_status")
        for item in section_marker_reviews
    ]
    if not isinstance(measure_sequence_scope, str) or not measure_sequence_scope:
        raise ValueError("sequence_scope debe ser texto no vacío")
    source_pages = analysis.get("pages", [])
    if not isinstance(source_pages, list):
        raise ValueError("pages debe ser una lista")
    system_candidates = []
    system_barline_count = 0
    grouping_mark_count = 0
    identity_evidence_count = 0
    for page in source_pages:
        if not isinstance(page, dict):
            raise ValueError("Cada página debe ser un objeto")
        page_staves = page.get("staves", [])
        systems = page.get("staff_system_candidates", [])
        system_barlines = page.get("system_barline_candidates", [])
        if not isinstance(page_staves, list):
            raise ValueError("staves debe ser una lista")
        grouping_marks = page.get("staff_grouping_mark_candidates", [])
        identity_evidence = page.get("staff_identity_evidence", [])
        if not isinstance(systems, list):
            raise ValueError("staff_system_candidates debe ser una lista")
        if not isinstance(system_barlines, list):
            raise ValueError("system_barline_candidates debe ser una lista")
        if not isinstance(grouping_marks, list):
            raise ValueError("staff_grouping_mark_candidates debe ser una lista")
        if not isinstance(identity_evidence, list):
            raise ValueError("staff_identity_evidence debe ser una lista")
        if any(not isinstance(item, dict) for item in systems):
            raise ValueError("Cada sistema candidato debe ser un objeto")
        if any(not isinstance(item, dict) for item in system_barlines):
            raise ValueError("Cada compás compartido candidato debe ser un objeto")
        if any(not isinstance(item, dict) for item in grouping_marks):
            raise ValueError("Cada marca de agrupación debe ser un objeto")
        if any(not isinstance(item, dict) for item in identity_evidence):
            raise ValueError("Cada evidencia de identidad debe ser un objeto")
        for system in systems:
            indices = system.get("staff_indices", [])
            if not isinstance(indices, list) or not indices or any(
                not isinstance(index, int) or isinstance(index, bool) or index < 0
                for index in indices
            ):
                raise ValueError("staff_indices debe contener índices enteros no negativos")
            if any(index >= len(page_staves) for index in indices):
                raise ValueError("staff_indices referencia un pentagrama inexistente")
            system_candidates.append(system)
        system_barline_count += len(system_barlines)
        grouping_mark_count += len(grouping_marks)
        identity_evidence_count += len(identity_evidence)
    multi_staff_system_count = sum(
        len(system.get("staff_indices", [])) >= 2
        for system in system_candidates
    )
    single_staff_system_count = len(system_candidates) - multi_staff_system_count
    eligible_section_markers = sum(
        status == "eligible_candidate" for status in section_marker_statuses
    )
    excluded_section_markers = sum(
        isinstance(status, str) and status.startswith("excluded_")
        for status in section_marker_statuses
    )
    return {
        "review_package_version": "1.0",
        "score_id": score_id,
        "source_pdf": analysis.get("source_pdf"),
        "analysis_version": analysis.get("version"),
        "global_section_range_candidates": global_section_ranges,
        "global_measure_sequence": global_measure_sequence,
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
            "global_measure_candidate_count": len(global_measure_candidates),
            "pending_global_measure_candidate_count": pending_measure_candidates,
            "cross_staff_aligned_measure_candidate_count": cross_staff_aligned_count,
            "single_staff_only_measure_candidate_count": single_staff_only_count,
            "global_measure_sequence_scope": measure_sequence_scope,
            "system_barline_candidate_count": system_barline_count,
            "global_section_range_candidate_count": len(global_section_ranges),
            "pending_global_section_range_candidate_count": pending_section_ranges,
            "accepted_global_section_range_candidate_count": accepted_section_ranges,
            "rejected_global_section_range_candidate_count": rejected_section_ranges,
            "needs_revision_global_section_range_candidate_count": needs_revision_section_ranges,
            "section_boundary_candidate_count": len(section_boundary_candidates),
            "cross_staff_aligned_section_boundary_candidate_count": cross_staff_section_boundaries,
            "single_staff_only_section_boundary_candidate_count": single_staff_section_boundaries,
            "unmatched_section_boundary_candidate_count": unmatched_section_boundaries,
            "partial_section_boundary_candidate_count": partial_section_boundaries,
            "inside_measure_section_boundary_candidate_count": inside_measure_section_boundaries,
            "before_measure_section_boundary_candidate_count": before_measure_section_boundaries,
            "after_measure_section_boundary_candidate_count": after_measure_section_boundaries,
            "section_marker_candidate_count": len(section_marker_reviews),
            "eligible_global_section_marker_candidate_count": eligible_section_markers,
            "excluded_global_section_marker_candidate_count": excluded_section_markers,
            "unclassified_global_section_marker_candidate_count": (
                len(section_marker_reviews) - eligible_section_markers - excluded_section_markers
            ),
            "staff_system_candidate_count": len(system_candidates),
            "multi_staff_system_candidate_count": multi_staff_system_count,
            "single_staff_system_candidate_count": single_staff_system_count,
            "staff_grouping_mark_candidate_count": grouping_mark_count,
            "staff_identity_evidence_count": identity_evidence_count,
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
