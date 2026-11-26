"""Extracción de etiquetas musicales impresas desde la capa de texto PDF.

No realiza OCR de imágenes escaneadas. Las coincidencias se conservan como
candidatos y su asociación geométrica a un pentagrama puede quedar ambigua.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import asdict, dataclass
from pathlib import Path

import fitz

from .imaging import StaffCandidate


@dataclass(frozen=True)
class PrintedLabelCandidate:
    page_number: int
    text: str
    normalized_text: str
    label_kind: str
    bbox_pdf: tuple[float, float, float, float]
    staff_index: int | None
    association_status: str
    vertical_distance_px: float | None
    confidence: float
    warning: str

    def to_dict(self) -> dict:
        return asdict(self)


def _normalize_label(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value)
    without_marks = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    return re.sub(r"[^A-Z0-9]+", " ", without_marks.upper()).strip()


_LABELS = {
    "MALE SOLO": ("vocal", "male_solo"),
    "FEMALE SOLO": ("vocal", "female_solo"),
    "LADIES": ("vocal", "female_group"),
    "WOMEN": ("vocal", "female_group"),
    "MEN": ("vocal", "male_group"),
    "SOPRANO": ("vocal", "soprano"),
    "SOPRANOS": ("vocal", "soprano"),
    "ALTO": ("vocal", "alto"),
    "ALTOS": ("vocal", "alto"),
    "CONTRALTO": ("vocal", "alto"),
    "TENOR": ("vocal", "tenor"),
    "TENORS": ("vocal", "tenor"),
    "BASS": ("vocal", "bass"),
    "BASSES": ("vocal", "bass"),
    "BARITONE": ("vocal", "baritone"),
    "PIANO": ("instrument", "piano"),
    "KEYBOARD": ("instrument", "keyboard"),
    "ORGAN": ("instrument", "organ"),
}


def _line_text_candidates(page: fitz.Page):
    data = page.get_text("dict")
    for block in data.get("blocks", []):
        for line in block.get("lines", []):
            spans = line.get("spans", [])
            text = " ".join(span.get("text", "").strip() for span in spans).strip()
            if not text:
                continue
            normalized = _normalize_label(text)
            if normalized not in _LABELS:
                continue
            boxes = [span["bbox"] for span in spans if span.get("text", "").strip()]
            if not boxes:
                continue
            yield text, normalized, (
                min(box[0] for box in boxes),
                min(box[1] for box in boxes),
                max(box[2] for box in boxes),
                max(box[3] for box in boxes),
            )


def extract_printed_label_candidates(
    pdf_path: str | Path,
    page_number: int,
    staves: list[StaffCandidate],
    *,
    dpi: int = 300,
    max_vertical_distance_spacing: float = 3.5,
    ambiguity_margin_spacing: float = 0.75,
) -> list[PrintedLabelCandidate]:
    """Extrae etiquetas conocidas de la capa PDF y propone pentagrama cercano.

    page_number usa numeración humana desde 1. La asociación se calcula con
    la coordenada vertical del centro de la etiqueta y la escala dpi/72.
    No se usa la posición horizontal porque las editoriales colocan etiquetas
    tanto al inicio como encima o dentro del sistema.
    """
    if dpi < 72 or dpi > 600:
        raise ValueError("dpi debe estar entre 72 y 600")
    if page_number < 1:
        raise ValueError("page_number debe ser mayor o igual a 1")
    if max_vertical_distance_spacing <= 0 or ambiguity_margin_spacing < 0:
        raise ValueError("Los umbrales geométricos no son válidos")

    path = Path(pdf_path)
    if not path.is_file():
        raise FileNotFoundError(f"No existe el archivo: {path}")

    with fitz.open(path) as document:
        if document.is_encrypted:
            raise ValueError("El PDF está protegido con contraseña")
        if page_number > len(document):
            raise ValueError("page_number supera el número de páginas del PDF")
        page = document[page_number - 1]
        scale = dpi / 72.0
        valid_staves = [
            (index, staff) for index, staff in enumerate(staves)
            if len(staff.lines_y) == 5 and staff.spacing_px > 0
        ]
        results: list[PrintedLabelCandidate] = []

        for text, normalized, bbox in _line_text_candidates(page):
            label_kind, _ = _LABELS[normalized]
            center_y_px = ((bbox[1] + bbox[3]) / 2) * scale
            distances = sorted(
                (
                    abs(center_y_px - (
                        (staff.lines_y[0] + staff.lines_y[-1]) / 2
                    )),
                    index,
                    staff.spacing_px,
                )
                for index, staff in valid_staves
            )
            staff_index = None
            vertical_distance = None
            status = "unassigned"
            confidence = 0.45
            warning = (
                "Etiqueta reconocida en la capa de texto PDF; no se encontró "
                "un pentagrama suficientemente cercano."
            )
            if distances:
                nearest_distance, nearest_index, nearest_spacing = distances[0]
                vertical_distance = round(nearest_distance, 2)
                if nearest_distance <= nearest_spacing * max_vertical_distance_spacing:
                    if len(distances) > 1:
                        second_distance = distances[1][0]
                    else:
                        second_distance = float("inf")
                    if second_distance - nearest_distance <= nearest_spacing * ambiguity_margin_spacing:
                        status = "ambiguous"
                        confidence = 0.5
                        warning = (
                            "La etiqueta está a distancias similares de varios "
                            "pentagramas; requiere revisión humana."
                        )
                    else:
                        staff_index = nearest_index
                        status = "associated_candidate"
                        confidence = 0.72
                        warning = (
                            "Asociación geométrica candidata por proximidad vertical; "
                            "no confirma que la etiqueta describa exclusivamente "
                            "este pentagrama."
                        )

            results.append(PrintedLabelCandidate(
                page_number=page_number,
                text=text,
                normalized_text=normalized,
                label_kind=label_kind,
                bbox_pdf=tuple(round(float(value), 3) for value in bbox),
                staff_index=staff_index,
                association_status=status,
                vertical_distance_px=vertical_distance,
                confidence=confidence,
                warning=warning,
            ))
        return results
