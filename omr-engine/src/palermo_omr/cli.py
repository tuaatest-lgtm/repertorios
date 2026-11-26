"""Interfaz de línea de comandos del prototipo Palermo OMR."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import cv2

from . import __version__
from .imaging import analyze_page, render_pdf
from .symbols import detect_notehead_candidates
from .visualization import draw_notehead_overlay
from .rhythm import analyze_rhythm_candidates
from .beam_groups import detect_beam_group_candidates
from .rhythm_interpretation import interpret_rhythm_from_beam_groups
from .rhythm_symbols import (detect_augmentation_dot_candidates, detect_rest_shape_candidates, detect_tie_slur_shape_candidates)
from .measure_layout import (
    classify_barline_groups,
    detect_barline_candidates,
    detect_staff_systems,
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
        noteheads = detect_notehead_candidates(binary, analysis.staves)
        overlay = draw_notehead_overlay(page, noteheads)
        overlay_path = output_dir / f"page-{page_number:03d}-noteheads-overlay.png"
        if not cv2.imwrite(str(overlay_path), overlay):
            raise OSError(f"No se pudo escribir {overlay_path}")
        page_data["notehead_candidates"] = [item.to_dict() for item in noteheads]
        page_data["notehead_candidate_count"] = len(noteheads)
        page_data["notehead_overlay"] = overlay_path.name
        rhythms = analyze_rhythm_candidates(binary, analysis.staves, noteheads)
        beam_groups = detect_beam_group_candidates(binary, analysis.staves, noteheads, rhythms)
        rhythmic_interpretations = interpret_rhythm_from_beam_groups(rhythms, beam_groups)
        page_data["rhythm_candidates"] = [item.to_dict() for item in rhythms]
        page_data["rhythm_candidate_count"] = len(rhythms)
        page_data["beam_group_candidates"] = [item.to_dict() for item in beam_groups]
        page_data["beam_group_candidate_count"] = len(beam_groups)
        page_data["rhythmic_interpretation_candidates"] = [item.to_dict() for item in rhythmic_interpretations]
        page_data["rhythmic_interpretation_candidate_count"] = len(rhythmic_interpretations)
        dots = detect_augmentation_dot_candidates(binary, analysis.staves, noteheads)
        rests = detect_rest_shape_candidates(binary, analysis.staves)
        tie_slurs = detect_tie_slur_shape_candidates(binary, analysis.staves)
        barlines = detect_barline_candidates(binary, analysis.staves)
        barline_groups = classify_barline_groups(barlines, analysis.staves)
        staff_systems = detect_staff_systems(analysis.staves)
        system_barlines = group_system_barlines(barlines, analysis.staves)
        measure_spans = infer_measure_spans(barlines)
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
        analyses.append(page_data)

    report = {
        "engine": "Palermo OMR",
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
    total_rhythms = sum(page["rhythm_candidate_count"] for page in analyses)
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
    print(f"Análisis terminado: {report_path}")
    print(f"Pentagramas candidatos: {total_staves}")
    print(f"Cabezas de nota candidatas: {total_heads}")
    print(f"Análisis rítmicos candidatos: {total_rhythms}")
    print(f"Grupos de barras compartidas candidatos: {total_beam_groups}")
    print(f"Interpretaciones rítmicas candidatas: {total_rhythm_interpretations}")
    print(f"Puntillos candidatos: {total_dots}")
    print(f"Formas candidatas a silencio: {total_rests}")
    print(f"Formas con familia de silencio sugerida: {total_typed_rest_shapes}")
    print(f"Arcos candidatos a ligadura: {total_tie_slurs}")
    print(f"Barras de compás candidatas: {total_barlines}")
    print(f"Intervalos entre barras candidatas: {total_spans}")
    print("Aviso: ningún candidato equivale todavía a un evento musical confirmado.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
