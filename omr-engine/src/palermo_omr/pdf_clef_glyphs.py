"""Candidatos de clave extraídos de glifos tipográficos embebidos en PDF vectorial.

La extracción solo se activa para una fuente y mapa de glifos explícitos.
Los resultados permanecen pendientes de revisión humana y nunca asignan
automáticamente una clave a las alturas.
"""
from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import math
from pathlib import Path
from typing import Any

import fitz


_DEFAULT_GLYPH_MAP = {"°": "treble", "¢": "bass"}


@dataclass(frozen=True)
class EmbeddedPdfClefCandidate:
    candidate_id: str
    page_number: int
    staff_index: int | None
    clef_candidate: str
    glyph: str
    font_name: str
    bbox_pdf: tuple[float, float, float, float]
    center_y_pdf: float
    staff_center_distance_points: float | None
    confidence: float
    status: str = "pending_human_review"
    source: str = "embedded_pdf_font_glyph"

    def to_dict(self) -> dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "page_number": self.page_number,
            "staff_index": self.staff_index,
            "clef_candidate": self.clef_candidate,
            "glyph": self.glyph,
            "font_name": self.font_name,
            "bbox_pdf": list(self.bbox_pdf),
            "center_y_pdf": round(self.center_y_pdf, 3),
            "staff_center_distance_points": (
                round(self.staff_center_distance_points, 3)
                if self.staff_center_distance_points is not None else None
            ),
            "confidence": self.confidence,
            "status": self.status,
            "source": self.source,
        }


def detect_embedded_pdf_clef_candidates(
    pdf_path: str | Path,
    page_number: int,
    staves: Sequence[Any],
    *,
    dpi: int = 300,
    font_name: str = "RepriseSpecialStd",
    glyph_map: Mapping[str, str] | None = None,
    max_staff_center_distance_points: float = 30.0,
) -> tuple[EmbeddedPdfClefCandidate, ...]:
    """Extrae claves candidatas y las ancla al pentagrama más cercano.

    Mapa inicial para PDFs Sibelius/Reprise: ° -> treble, ¢ -> bass.
    No se usa si el documento no contiene exactamente esa fuente y esos glifos.
    """
    if not isinstance(page_number, int) or isinstance(page_number, bool) or page_number < 1:
        raise ValueError("page_number debe ser entero positivo")
    if not isinstance(dpi, int) or isinstance(dpi, bool) or not 72 <= dpi <= 600:
        raise ValueError("dpi debe estar entre 72 y 600")
    if not isinstance(font_name, str) or not font_name.strip():
        raise ValueError("font_name debe ser texto no vacío")
    if (
        isinstance(max_staff_center_distance_points, bool)
        or not isinstance(max_staff_center_distance_points, (int, float))
        or not math.isfinite(max_staff_center_distance_points)
        or not 1 <= max_staff_center_distance_points <= 100
    ):
        raise ValueError("max_staff_center_distance_points debe estar entre 1 y 100")
    mapping = dict(_DEFAULT_GLYPH_MAP if glyph_map is None else glyph_map)
    if not mapping or any(
        not isinstance(glyph, str) or len(glyph) != 1
        or clef not in {"treble", "bass", "alto", "tenor", "percussion"}
        for glyph, clef in mapping.items()
    ):
        raise ValueError("glyph_map debe mapear caracteres individuales a claves reconocidas")
    if not isinstance(staves, (list, tuple)):
        raise ValueError("staves debe ser una secuencia")
    staff_centers = []
    for staff in staves:
        lines = getattr(staff, "lines_y", None)
        if not isinstance(lines, (list, tuple)) or len(lines) != 5:
            raise ValueError("Cada pentagrama debe tener cinco líneas")
        if any(isinstance(value, bool) or not isinstance(value, (int, float)) for value in lines):
            raise ValueError("Las líneas del pentagrama deben ser numéricas")
        staff_centers.append(sum(float(value) for value in lines) / 5.0 / (dpi / 72.0))

    path = Path(pdf_path)
    if not path.is_file():
        raise FileNotFoundError(f"No existe el archivo PDF: {path}")

    with fitz.open(path) as document:
        if document.is_encrypted:
            raise ValueError("El PDF está protegido con contraseña")
        if page_number > len(document):
            raise ValueError("page_number excede el número de páginas del PDF")
        page = document[page_number - 1]
        raw = page.get_text("rawdict")

    raw_candidates = []
    for block in raw.get("blocks", []):
        for line in block.get("lines", []):
            for span in line.get("spans", []):
                if span.get("font") != font_name:
                    continue
                for char in span.get("chars", []):
                    glyph = char.get("c")
                    if glyph not in mapping:
                        continue
                    bbox = char.get("bbox")
                    if not isinstance(bbox, (list, tuple)) or len(bbox) != 4:
                        continue
                    try:
                        x0, y0, x1, y1 = (float(value) for value in bbox)
                    except (TypeError, ValueError):
                        continue
                    if x1 <= x0 or y1 <= y0:
                        continue
                    center_y = (y0 + y1) / 2.0
                    if staff_centers:
                        nearest = min(
                            range(len(staff_centers)),
                            key=lambda index: abs(staff_centers[index] - center_y),
                        )
                        distance = abs(staff_centers[nearest] - center_y)
                        staff_index = nearest if distance <= max_staff_center_distance_points else None
                        distance_value = distance
                    else:
                        staff_index, distance_value = None, None
                    raw_candidates.append({
                        "staff_index": staff_index,
                        "clef_candidate": mapping[glyph],
                        "glyph": glyph,
                        "bbox_pdf": (x0, y0, x1, y1),
                        "center_y_pdf": center_y,
                        "distance": distance_value,
                    })

    clefs_by_staff: dict[int, set[str]] = defaultdict(set)
    for item in raw_candidates:
        if item["staff_index"] is not None:
            clefs_by_staff[item["staff_index"]].add(item["clef_candidate"])

    results = []
    for index, item in enumerate(raw_candidates, start=1):
        staff_index = item["staff_index"]
        status = "pending_human_review"
        if staff_index is None:
            status = "unassigned_staff"
        elif len(clefs_by_staff[staff_index]) > 1:
            status = "conflicting_clef_glyphs"
        results.append(EmbeddedPdfClefCandidate(
            candidate_id=f"p{page_number}-embedded-clef-{index}",
            page_number=page_number,
            staff_index=staff_index,
            clef_candidate=item["clef_candidate"],
            glyph=item["glyph"],
            font_name=font_name,
            bbox_pdf=item["bbox_pdf"],
            center_y_pdf=item["center_y_pdf"],
            staff_center_distance_points=item["distance"],
            confidence=0.95 if staff_index is not None else 0.40,
            status=status,
        ))
    return tuple(results)
