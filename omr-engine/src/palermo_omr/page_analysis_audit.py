"""Auditoría reproducible de cobertura geométrica y candidatos de una página OMR.

Los conteos describen candidatos y relaciones espaciales; no son métricas de
precisión musical, ni convierten detecciones en notas confirmadas.
"""
from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
from typing import Any


def _list(page: Mapping[str, Any], key: str) -> list:
    value = page.get(key, [])
    if not isinstance(value, list):
        raise ValueError(f"{key} debe ser una lista")
    return value


def _count_values(items: Sequence[Mapping], key: str, default: str = "unknown") -> dict[str, int]:
    counts = Counter()
    for item in items:
        value = item.get(key, default)
        counts[str(value if value is not None else default)] += 1
    return dict(sorted(counts.items()))


def _page_audit(page: Mapping[str, Any], *, low_confidence_threshold: float) -> dict[str, Any]:
    page_number = page.get("page_number")
    if not isinstance(page_number, int) or isinstance(page_number, bool) or page_number < 1:
        raise ValueError("Cada página debe tener page_number entero positivo")
    staves = _list(page, "staves")
    heads = _list(page, "notehead_candidates")
    hollow_heads = _list(page, "hollow_notehead_candidates")
    rhythms = _list(page, "rhythm_candidates")
    interpretations = _list(page, "rhythmic_interpretation_candidates")
    beams = _list(page, "beam_group_candidates")
    spans = _list(page, "measure_span_candidates")
    systems = _list(page, "staff_system_candidates")
    rests = _list(page, "rest_shape_candidates")
    ties = _list(page, "tie_slur_shape_candidates")
    dots = _list(page, "augmentation_dot_candidates")

    if len(rhythms) not in {0, len(heads)}:
        raise ValueError("rhythm_candidates debe alinearse con notehead_candidates")
    if len(interpretations) not in {0, len(heads)}:
        raise ValueError("rhythmic_interpretation_candidates debe alinearse con notehead_candidates")

    staff_systems: Counter[int] = Counter()
    for system in systems:
        if not isinstance(system, Mapping):
            raise ValueError("Cada sistema candidato debe ser un objeto")
        staff_indices = system.get("staff_indices", [])
        if not isinstance(staff_indices, list):
            raise ValueError("staff_indices debe ser una lista")
        for staff_index in staff_indices:
            if not isinstance(staff_index, int) or isinstance(staff_index, bool) or not 0 <= staff_index < len(staves):
                raise ValueError("Un sistema candidato referencia un pentagrama inexistente")
            staff_systems[staff_index] += 1

    measure_matches = Counter()
    invalid_staff_heads = 0
    for head in heads:
        if not isinstance(head, Mapping):
            raise ValueError("Cada cabeza candidata debe ser un objeto")
        staff_index = head.get("staff_index")
        center_x = head.get("center_x")
        if not isinstance(staff_index, int) or isinstance(staff_index, bool) or not 0 <= staff_index < len(staves):
            invalid_staff_heads += 1
            continue
        if not isinstance(center_x, (int, float)) or isinstance(center_x, bool):
            raise ValueError("Cada cabeza debe tener center_x numérico")
        matches = 0
        for span in spans:
            if not isinstance(span, Mapping):
                raise ValueError("Cada intervalo de compás debe ser un objeto")
            if span.get("staff_index") != staff_index:
                continue
            x_start, x_end = span.get("x_start"), span.get("x_end")
            if not isinstance(x_start, (int, float)) or not isinstance(x_end, (int, float)):
                raise ValueError("Cada intervalo de compás debe tener límites numéricos")
            if x_start <= center_x <= x_end:
                matches += 1
        measure_matches[matches] += 1

    low_confidence = 0
    for rhythm in rhythms:
        if not isinstance(rhythm, Mapping):
            raise ValueError("Cada candidato rítmico debe ser un objeto")
        confidence = rhythm.get("confidence")
        if not isinstance(confidence, (int, float)) or isinstance(confidence, bool):
            raise ValueError("Cada candidato rítmico debe tener confidence numérica")
        if confidence < low_confidence_threshold:
            low_confidence += 1

    stem_counts = _count_values(rhythms, "stem_direction")
    duration_counts = _count_values(rhythms, "base_duration")
    interpretation_counts = _count_values(interpretations, "status")
    beam_counts = _count_values(rhythms, "beam_count", "0")

    return {
        "page_number": page_number,
        "counts": {
            "staves": len(staves),
            "staff_system_candidates": len(systems),
            "measure_span_candidates": len(spans),
            "filled_notehead_candidates": len(heads),
            "hollow_notehead_candidates": len(hollow_heads),
            "rhythm_candidates": len(rhythms),
            "beam_group_candidates": len(beams),
            "rest_shape_candidates": len(rests),
            "tie_slur_shape_candidates": len(ties),
            "augmentation_dot_candidates": len(dots),
        },
        "geometry_coverage": {
            "noteheads_with_valid_staff_index": len(heads) - invalid_staff_heads,
            "noteheads_with_invalid_staff_index": invalid_staff_heads,
            "noteheads_with_one_measure_span": measure_matches[1],
            "noteheads_with_multiple_measure_spans": sum(
                count for matches, count in measure_matches.items() if matches > 1
            ),
            "noteheads_without_measure_span": measure_matches[0],
            "staves_in_exactly_one_system_candidate": sum(
                1 for index in range(len(staves)) if staff_systems[index] == 1
            ),
            "staves_in_multiple_system_candidates": sum(
                1 for count in staff_systems.values() if count > 1
            ),
            "staves_without_system_candidate": sum(
                1 for index in range(len(staves)) if staff_systems[index] == 0
            ),
        },
        "rhythm_candidate_distribution": {
            "stem_direction": stem_counts,
            "base_duration": duration_counts,
            "beam_count": beam_counts,
            "interpretation_status": interpretation_counts,
            "below_confidence_threshold": low_confidence,
            "low_confidence_threshold": low_confidence_threshold,
        },
        "interpretation": (
            "Cobertura geométrica y distribución de candidatos; no equivale "
            "a precisión, recall ni exactitud musical."
        ),
    }




def build_rhythm_review_queue(analysis: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Crea una cola priorizada de candidatos que necesitan revisión rítmica."""
    if not isinstance(analysis, Mapping) or not isinstance(analysis.get("pages"), list):
        raise ValueError("analysis debe contener una lista pages")
    queue = []
    for page in analysis["pages"]:
        if not isinstance(page, Mapping):
            raise ValueError("Cada página debe ser un objeto")
        page_number = page.get("page_number")
        heads = _list(page, "notehead_candidates")
        rhythms = _list(page, "rhythm_candidates")
        interpretations = _list(page, "rhythmic_interpretation_candidates")
        if len(rhythms) != len(heads) or len(interpretations) != len(heads):
            raise ValueError("Cabezas, ritmos e interpretaciones deben estar alineados para la cola de revisión")
        for index, (head, rhythm, interpretation) in enumerate(zip(heads, rhythms, interpretations)):
            if not all(isinstance(item, Mapping) for item in (head, rhythm, interpretation)):
                raise ValueError("Cada candidato de revisión debe ser un objeto")
            reasons = []
            if rhythm.get("stem_direction") == "none":
                reasons.append("missing_stem_direction")
            if rhythm.get("base_duration") == "unknown":
                reasons.append("unknown_duration")
            if interpretation.get("status") in {"ambiguous", "unclassified"}:
                reasons.append("ambiguous_or_unclassified_rhythm")
            if interpretation.get("status") == "candidate_from_partial_beam":
                reasons.append("partial_beam_requires_review")
            if not reasons:
                continue
            confidence = rhythm.get("confidence", 0.0)
            if isinstance(confidence, bool) or not isinstance(confidence, (int, float)) or not 0 <= confidence <= 1:
                raise ValueError("confidence del candidato rítmico debe estar entre 0 y 1")
            priority = 1 if "missing_stem_direction" in reasons else 2
            candidate_id = f"p{page_number}-filled_notehead-{index + 1}"
            queue.append({
                "candidate_id": candidate_id,
                "page_number": page_number,
                "candidate_index": index,
                "staff_index": head.get("staff_index"),
                "bbox": head.get("bbox"),
                "center_x": head.get("center_x"),
                "center_y": head.get("center_y"),
                "confidence": float(confidence),
                "stem_direction": rhythm.get("stem_direction"),
                "base_duration": rhythm.get("base_duration"),
                "beam_count": rhythm.get("beam_count"),
                "interpretation_status": interpretation.get("status"),
                "review_reasons": reasons,
                "priority": priority,
            })
    queue.sort(key=lambda item: (
        item["priority"], item["confidence"],
        item["page_number"], item["candidate_index"],
    ))
    return queue


def audit_page_analysis(
    analysis: Mapping[str, Any],
    *,
    low_confidence_threshold: float = 0.60,
) -> dict[str, Any]:
    """Resume todas las páginas y calcula cobertura geométrica sin ground truth."""
    if not isinstance(analysis, Mapping):
        raise ValueError("analysis debe ser un objeto")
    if (
        isinstance(low_confidence_threshold, bool)
        or not isinstance(low_confidence_threshold, (int, float))
        or not 0 <= low_confidence_threshold <= 1
    ):
        raise ValueError("low_confidence_threshold debe estar entre 0 y 1")
    pages = analysis.get("pages")
    if not isinstance(pages, list) or not pages:
        raise ValueError("analysis debe contener una lista pages no vacía")
    page_numbers = []
    results = []
    for page in pages:
        if not isinstance(page, Mapping):
            raise ValueError("Cada página debe ser un objeto")
        result = _page_audit(page, low_confidence_threshold=float(low_confidence_threshold))
        page_numbers.append(result["page_number"])
        results.append(result)
    if len(page_numbers) != len(set(page_numbers)):
        raise ValueError("page_number debe ser único")

    total_heads = sum(item["counts"]["filled_notehead_candidates"] for item in results)
    unique_measure = sum(item["geometry_coverage"]["noteheads_with_one_measure_span"] for item in results)
    ambiguous_measure = sum(item["geometry_coverage"]["noteheads_with_multiple_measure_spans"] for item in results)
    unassigned_measure = sum(item["geometry_coverage"]["noteheads_without_measure_span"] for item in results)
    total_rhythm = sum(item["counts"]["rhythm_candidates"] for item in results)
    unknown_durations = sum(
        item["rhythm_candidate_distribution"]["base_duration"].get("unknown", 0)
        for item in results
    )
    missing_stems = sum(
        item["rhythm_candidate_distribution"]["stem_direction"].get("none", 0)
        for item in results
    )
    review_queue = build_rhythm_review_queue(analysis)
    return {
        "status": "candidate_geometry_audit",
        "source_pdf": analysis.get("source_pdf"),
        "page_count": len(results),
        "totals": {
            "filled_notehead_candidates": total_heads,
            "rhythm_candidates": total_rhythm,
            "unknown_duration_candidates": unknown_durations,
            "missing_stem_direction_candidates": missing_stems,
            "one_measure_span": unique_measure,
            "multiple_measure_spans": ambiguous_measure,
            "no_measure_span": unassigned_measure,
            "measure_span_unique_coverage": unique_measure / total_heads if total_heads else None,
        },
        "pages": results,
        "rhythm_review_queue_count": len(review_queue),
        "rhythm_review_queue": review_queue,
        "limitations": [
            "No se compara con anotaciones de referencia ni ground truth.",
            "Los intervalos de compás y pentagramas son candidatos geométricos.",
            "La cobertura de ubicación no valida alturas, figuras, alteraciones, silencios o voces.",
            "Las distribuciones rítmicas describen hipótesis del detector, no notas reconocidas.",
        ],
    }
