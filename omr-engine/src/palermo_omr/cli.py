"""Interfaz de línea de comandos del prototipo Palermo OMR."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import cv2

from . import __version__
from .imaging import analyze_page, render_pdf
from .symbols import (
    detect_hollow_notehead_candidates,
    detect_notehead_candidates,
)
from .visualization import draw_geometry_overlay, draw_notehead_overlay
from .rhythm import analyze_rhythm_candidates
from .beam_groups import detect_beam_group_candidates
from .rhythm_interpretation import interpret_rhythm_from_beam_groups
from .rhythm_symbols import (detect_augmentation_dot_candidates, detect_rest_shape_candidates, detect_tie_slur_shape_candidates)
from .staff_grouping import detect_staff_grouping_mark_candidates
from .printed_labels import extract_printed_label_candidates
from .section_structure import (
    anchor_section_markers_to_measure_spans,
    detect_section_candidates,
    link_section_ranges_across_pages,
    build_global_measure_sequence,
    resolve_section_range_boundaries,
)
from .identity_evidence import build_page_identity_evidence
from .score_structure import ScoreStaff, ScoreStructure
from .measure_layout import (
    classify_barline_groups,
    detect_barline_candidates,
    detect_staff_systems,
    detect_staff_systems_from_connectors,
    group_system_barlines,
    infer_measure_spans,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="palermo-omr",
        description="Analiza geometría y candidatos musicales preliminares en un PDF.",
    )
    parser.add_argument("pdf", help="Ruta al archivo PDF")
    parser.add_argument("--output", default="omr-output", help="Carpeta de salida")
    parser.add_argument("--dpi", type=int, default=300, help="Resolución de renderizado (72-600)")
    args = parser.parse_args()

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    pages = render_pdf(args.pdf, dpi=args.dpi)
    analyses = []

    for page_number, page in enumerate(pages, start=1):
        binary, analysis = analyze_page(page, page_number)
        image_path = output_dir / f"page-{page_number:03d}-binary.png"
        if not cv2.imwrite(str(image_path), binary):
            raise OSError(f"No se pudo escribir {image_path}")

        page_data = analysis.to_dict()
        page_data["render_dpi"] = args.dpi
        noteheads = detect_notehead_candidates(binary, analysis.staves)
        hollow_noteheads = detect_hollow_notehead_candidates(binary, analysis.staves)
        overlay = draw_notehead_overlay(page, noteheads)
        hollow_overlay = draw_notehead_overlay(page, hollow_noteheads)
        hollow_overlay_path = output_dir / f"page-{page_number:03d}-hollow-noteheads-overlay.png"
        if not cv2.imwrite(str(hollow_overlay_path), hollow_overlay):
            raise OSError(f"No se pudo escribir {hollow_overlay_path}")
        overlay_path = output_dir / f"page-{page_number:03d}-noteheads-overlay.png"
        if not cv2.imwrite(str(overlay_path), overlay):
            raise OSError(f"No se pudo escribir {overlay_path}")
        page_data["notehead_candidates"] = [item.to_dict() for item in noteheads]
        page_data["notehead_candidate_count"] = len(noteheads)
        page_data["hollow_notehead_candidates"] = [item.to_dict() for item in hollow_noteheads]
        page_data["hollow_notehead_candidate_count"] = len(hollow_noteheads)
        page_data["hollow_notehead_overlay"] = hollow_overlay_path.name
        page_data["notehead_overlay"] = overlay_path.name
        rhythms = analyze_rhythm_candidates(binary, analysis.staves, noteheads)
        # Las cabezas huecas se analizan aparte: la presencia de plica propone
        # blanca; su ausencia propone redonda. No se mezclan con cabezas rellenas.
        hollow_rhythms = analyze_rhythm_candidates(
            binary, analysis.staves, hollow_noteheads
        )
        beam_groups = detect_beam_group_candidates(binary, analysis.staves, noteheads, rhythms)
        rhythmic_interpretations = interpret_rhythm_from_beam_groups(rhythms, beam_groups)
        page_data["rhythm_candidates"] = [item.to_dict() for item in rhythms]
        page_data["rhythm_candidate_count"] = len(rhythms)
        page_data["hollow_rhythm_candidates"] = [item.to_dict() for item in hollow_rhythms]
        page_data["hollow_rhythm_candidate_count"] = len(hollow_rhythms)
        page_data["beam_group_candidates"] = [item.to_dict() for item in beam_groups]
        page_data["beam_group_candidate_count"] = len(beam_groups)
        page_data["rhythmic_interpretation_candidates"] = [item.to_dict() for item in rhythmic_interpretations]
        page_data["rhythmic_interpretation_candidate_count"] = len(rhythmic_interpretations)
        dots = detect_augmentation_dot_candidates(binary, analysis.staves, noteheads)
        rests = detect_rest_shape_candidates(
            binary, analysis.staves, noteheads + hollow_noteheads
        )
        tie_slurs = detect_tie_slur_shape_candidates(binary, analysis.staves)
        barlines = detect_barline_candidates(binary, analysis.staves)
        barline_groups = classify_barline_groups(barlines, analysis.staves)
        staff_systems = detect_staff_systems_from_connectors(analysis.staves, binary)
        system_barlines = group_system_barlines(
            barlines, analysis.staves, system_candidates=staff_systems
        )
        measure_spans = infer_measure_spans(barlines)
        grouping_marks = detect_staff_grouping_mark_candidates(binary, analysis.staves)
        section_data = detect_section_candidates(
            args.pdf, page_number, analysis.staves, measure_spans, dpi=args.dpi
        )
        section_data["section_measure_anchor_candidates"] = anchor_section_markers_to_measure_spans(
            [item.to_dict() for item in section_data["section_marker_candidates"]],
            analysis.staves,
            measure_spans,
        )
        section_identifiers = section_data["section_identifier_candidates"]
        section_identifier_boxes = {
            tuple(item.bbox_pdf) for item in section_identifiers
        }
        printed_labels = extract_printed_label_candidates(
            args.pdf, page_number, analysis.staves, dpi=args.dpi
        )
        # Una letra ya vinculada a una marca de sección no debe duplicarse
        # como abreviatura SATB en la misma página.
        printed_labels = [
            item for item in printed_labels
            if tuple(item.bbox_pdf) not in section_identifier_boxes
        ]
        score_structure = ScoreStructure(
            page_number=page_number,
            staves=tuple(
                ScoreStaff(
                    staff_id=f"p{page_number}-staff-{index + 1}",
                    page_number=page_number,
                    detected_staff_index=index,
                )
                for index, _ in enumerate(analysis.staves)
            ),
        )
        identity_evidence = build_page_identity_evidence(
            score_structure,
            printed_labels=printed_labels,
            grouping_marks=grouping_marks,
        )
        page_data["augmentation_dot_candidates"] = [item.to_dict() for item in dots]
        page_data["rest_shape_candidates"] = [item.to_dict() for item in rests]
        page_data["tie_slur_shape_candidates"] = [item.to_dict() for item in tie_slurs]
        page_data["staff_system_candidates"] = [item.to_dict() for item in staff_systems]
        page_data["staff_system_candidate_count"] = len(staff_systems)
        page_data["barline_candidates"] = [item.to_dict() for item in barlines]
        page_data["barline_group_candidates"] = [item.to_dict() for item in barline_groups]
        page_data["barline_group_candidate_count"] = len(barline_groups)
        page_data["barline_candidate_count"] = len(barlines)
        page_data["system_barline_candidates"] = [item.to_dict() for item in system_barlines]
        page_data["measure_span_candidates"] = [item.to_dict() for item in measure_spans]
        page_data["measure_span_candidate_count"] = len(measure_spans)
        page_data["staff_grouping_mark_candidates"] = [item.to_dict() for item in grouping_marks]
        page_data["staff_grouping_mark_candidate_count"] = len(grouping_marks)
        page_data["printed_label_candidates"] = [item.to_dict() for item in printed_labels]
        page_data["printed_label_candidate_count"] = len(printed_labels)
        for key, values in section_data.items():
            page_data[key] = [item.to_dict() if hasattr(item, "to_dict") else item for item in values]
            page_data[key.replace("_candidates", "_candidate_count")] = len(values)
        page_data["staff_identity_evidence"] = [item.__dict__ for item in identity_evidence]
        page_data["staff_identity_evidence_count"] = len(identity_evidence)
        geometry_overlay = draw_geometry_overlay(page, page_data)
        geometry_overlay_path = output_dir / f"page-{page_number:03d}-geometry-overlay.png"
        if not cv2.imwrite(str(geometry_overlay_path), geometry_overlay):
            raise OSError(f"No se pudo escribir {geometry_overlay_path}")
        page_data["geometry_overlay"] = geometry_overlay_path.name
        analyses.append(page_data)

    global_measure_sequence = build_global_measure_sequence(analyses)
    global_measure_map = {
        (item["page_number"], item["staff_index"], item["measure_index_on_staff"]):
        item["global_measure_candidate"]
        for item in global_measure_sequence["staff_measure_map"]
    }
    for page_data in analyses:
        for anchor in page_data.get("section_measure_anchor_candidates", []):
            anchor["global_measure_candidate"] = global_measure_map.get((
                page_data["page_number"], anchor["staff_index"],
                anchor["measure_index_on_staff"],
            ))
            anchor["warning"] += (
                " El ordinal global asociado también es provisional y depende "
                "de la conciliación geométrica de pentagramas."
            )
    global_section_ranges = link_section_ranges_across_pages(analyses)
    for section_range in global_section_ranges:
        for boundary_name in ("start", "end"):
            boundary = section_range.get(boundary_name)
            if not boundary:
                continue
            for anchor in boundary.get("measure_anchors", []):
                anchor["global_measure_candidate"] = global_measure_map.get((
                    boundary["page_number"], anchor["staff_index"],
                    anchor["measure_index_on_staff"],
                ))
    global_section_ranges = resolve_section_range_boundaries(
        global_section_ranges, global_measure_sequence
    )
    report = {
        "global_measure_sequence": global_measure_sequence,
        "engine": "Palermo OMR",
        "global_section_range_candidates": global_section_ranges,
        "global_section_range_candidate_count": len(global_section_ranges),
        "version": __version__,
        "status": "geometric_candidates_prototype",
        "warning": (
            "Los resultados son hipótesis visuales, no una transcripción musical validada. "
            "Todavía no se reconocen de forma fiable claves, armaduras, alturas absolutas, "
            "duraciones, tipos de silencio, puntillos, ligaduras, voces ni estructura métrica. "
            "Los detectores de puntillos, silencios, barras y regiones de compás solo generan candidatos."
        ),
        "source_pdf": Path(args.pdf).name,
        "pages": analyses,
    }
    report_path = output_dir / "analysis.json"
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    total_staves = sum(len(page["staves"]) for page in analyses)
    total_heads = sum(page["notehead_candidate_count"] for page in analyses)
    total_hollow_heads = sum(page["hollow_notehead_candidate_count"] for page in analyses)
    total_rhythms = sum(page["rhythm_candidate_count"] for page in analyses)
    total_hollow_rhythms = sum(page["hollow_rhythm_candidate_count"] for page in analyses)
    total_beam_groups = sum(page["beam_group_candidate_count"] for page in analyses)
    total_rhythm_interpretations = sum(page["rhythmic_interpretation_candidate_count"] for page in analyses)
    total_dots = sum(len(page["augmentation_dot_candidates"]) for page in analyses)
    total_rests = sum(len(page["rest_shape_candidates"]) for page in analyses)
    total_typed_rest_shapes = sum(
        sum(item["rest_type_candidate"] != "unclassified" for item in page["rest_shape_candidates"])
        for page in analyses
    )
    total_tie_slurs = sum(len(page["tie_slur_shape_candidates"]) for page in analyses)
    total_barlines = sum(page["barline_candidate_count"] for page in analyses)
    total_spans = sum(page["measure_span_candidate_count"] for page in analyses)
    total_grouping_marks = sum(page["staff_grouping_mark_candidate_count"] for page in analyses)
    total_printed_labels = sum(page["printed_label_candidate_count"] for page in analyses)
    total_section_markers = sum(page["section_marker_candidate_count"] for page in analyses)
    total_section_identifiers = sum(page["section_identifier_candidate_count"] for page in analyses)
    total_section_ranges = sum(page["section_range_candidate_count"] for page in analyses)
    total_global_section_ranges = len(global_section_ranges)
    total_identity_evidence = sum(page["staff_identity_evidence_count"] for page in analyses)
    print(f"Análisis terminado: {report_path}")
    print(f"Pentagramas candidatos: {total_staves}")
    print(f"Cabezas de nota rellenas candidatas: {total_heads}")
    print(f"Cabezas de nota huecas candidatas (separadas): {total_hollow_heads}")
    print(f"Análisis rítmicos de cabezas rellenas: {total_rhythms}")
    print(f"Análisis rítmicos de cabezas huecas (blancas/redondas candidatas): {total_hollow_rhythms}")
    print(f"Grupos de barras compartidas candidatos: {total_beam_groups}")
    print(f"Interpretaciones rítmicas candidatas: {total_rhythm_interpretations}")
    print(f"Puntillos candidatos: {total_dots}")
    print(f"Formas candidatas a silencio: {total_rests}")
    print(f"Formas con familia de silencio sugerida: {total_typed_rest_shapes}")
    print(f"Arcos candidatos a ligadura: {total_tie_slurs}")
    print(f"Barras de compás candidatas: {total_barlines}")
    print(f"Intervalos entre barras candidatas: {total_spans}")
    print(f"Marcas de agrupación de pentagramas candidatas: {total_grouping_marks}")
    print(f"Etiquetas musicales impresas candidatas: {total_printed_labels}")
    print(f"Marcas de sección candidatas: {total_section_markers}")
    print(f"Identificadores de sección candidatos: {total_section_identifiers}")
    print(f"Rangos de sección candidatos por página: {total_section_ranges}")
    print(f"Rangos globales de sección candidatos: {total_global_section_ranges}")
    print(f"Intervalos globales de compás candidatos: {global_measure_sequence['global_measure_candidate_count']}")
    print(f"Evidencias de identidad pendientes de revisión: {total_identity_evidence}")
    print("Aviso: ningún candidato equivale todavía a un evento musical confirmado.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
