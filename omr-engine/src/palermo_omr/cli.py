"""Interfaz de línea de comandos del prototipo Palermo OMR."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import cv2

from .imaging import analyze_page, render_pdf


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="palermo-omr",
        description="Analiza geometría de pentagramas en un PDF musical.",
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
        analyses.append(analysis.to_dict())

    report = {
        "engine": "Palermo OMR",
        "version": "0.1.0",
        "status": "geometry_prototype",
        "warning": (
            "No hay reconocimiento de símbolos musicales todavía. "
            "Las líneas detectadas son candidatos geométricos."
        ),
        "source_pdf": Path(args.pdf).name,
        "pages": analyses,
    }
    report_path = output_dir / "analysis.json"
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"Análisis terminado: {report_path}")
    print("Aviso: esta versión detecta geometría, no interpreta notas musicales.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
