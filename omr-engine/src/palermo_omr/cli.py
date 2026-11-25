"""Interfaz de línea de comandos del prototipo Palermo OMR."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import cv2

from . import __version__
from .imaging import analyze_page, render_pdf
from .symbols import detect_notehead_candidates
from .rhythm import analyze_rhythm_candidates
from .rhythm_symbols import detect_augmentation_dot_candidates, detect_rest_shape_candidates


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
        page_data["notehead_candidates"] = [item.to_dict() for item in noteheads]
        page_data["notehead_candidate_count"] = len(noteheads)
        rhythms = analyze_rhythm_candidates(binary, analysis.staves, noteheads)
        page_data["rhythm_candidates"] = [item.to_dict() for item in rhythms]
        page_data["rhythm_candidate_count"] = len(rhythms)
        dots = detect_augmentation_dot_candidates(binary, analysis.staves, noteheads)
        rests = detect_rest_shape_candidates(binary, analysis.staves)
        page_data["augmentation_dot_candidates"] = [item.to_dict() for item in dots]
        page_data["rest_shape_candidates"] = [item.to_dict() for item in rests]
        analyses.append(page_data)

    report = {
        "engine": "Palermo OMR",
        "version": __version__,
        "status": "geometric_candidates_prototype",
        "warning": (
            "Los resultados son hipótesis visuales, no una transcripción musical validada. "
            "Todavía no se reconocen de forma fiable claves, armaduras, alturas absolutas, "
            "duraciones, tipos de silencio, puntillos, ligaduras, voces, barras ni estructura "
            "de compases. Los detectores de puntillos y silencios solo generan candidatos."
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
    total_dots = sum(len(page["augmentation_dot_candidates"]) for page in analyses)
    total_rests = sum(len(page["rest_shape_candidates"]) for page in analyses)
    print(f"Análisis terminado: {report_path}")
    print(f"Pentagramas candidatos: {total_staves}")
    print(f"Cabezas de nota candidatas: {total_heads}")
    print(f"Análisis rítmicos candidatos: {total_rhythms}")
    print(f"Puntillos candidatos: {total_dots}")
    print(f"Formas candidatas a silencio: {total_rests}")
    print("Aviso: ningún candidato equivale todavía a un evento musical confirmado.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
