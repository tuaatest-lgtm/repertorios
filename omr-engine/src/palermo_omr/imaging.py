"""Carga de PDF y análisis geométrico inicial de pentagramas."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path

import cv2
import fitz
import numpy as np


@dataclass(frozen=True)
class StaffCandidate:
    """Cinco líneas aproximadamente equidistantes de un pentagrama."""

    lines_y: list[int]
    spacing_px: float
    confidence: float


@dataclass(frozen=True)
class PageAnalysis:
    page_number: int
    width_px: int
    height_px: int
    horizontal_lines_y: list[int]
    staves: list[StaffCandidate]

    def to_dict(self) -> dict:
        return asdict(self)


def render_pdf(pdf_path: str | Path, dpi: int = 300) -> list[np.ndarray]:
    """Renderiza todas las páginas de un PDF como imágenes BGR."""
    if dpi < 72 or dpi > 600:
        raise ValueError("dpi debe estar entre 72 y 600")

    path = Path(pdf_path)
    if not path.is_file():
        raise FileNotFoundError(f"No existe el archivo: {path}")

    pages: list[np.ndarray] = []
    with fitz.open(path) as document:
        if document.is_encrypted:
            raise ValueError("El PDF está protegido con contraseña")
        for page in document:
            pix = page.get_pixmap(dpi=dpi, colorspace=fitz.csRGB, alpha=False)
            image = np.frombuffer(pix.samples, dtype=np.uint8)
            image = image.reshape(pix.height, pix.width, 3)
            pages.append(cv2.cvtColor(image, cv2.COLOR_RGB2BGR))
    return pages


def binarize_page(image: np.ndarray) -> np.ndarray:
    """Convierte una página a blanco/negro; la tinta queda en negro."""
    if image is None or image.size == 0:
        raise ValueError("La imagen de página está vacía")
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if image.ndim == 3 else image
    gray = cv2.GaussianBlur(gray, (3, 3), 0)
    return cv2.adaptiveThreshold(
        gray,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        35,
        11,
    )


def _row_centres(mask: np.ndarray) -> list[int]:
    """Obtiene el centro vertical de cada trazo horizontal detectado."""
    row_strength = np.count_nonzero(mask, axis=1)
    active = np.flatnonzero(row_strength >= max(10, int(mask.shape[1] * 0.35)))
    if active.size == 0:
        return []

    groups: list[list[int]] = [[int(active[0])]]
    for y in active[1:]:
        y = int(y)
        if y <= groups[-1][-1] + 1:
            groups[-1].append(y)
        else:
            groups.append([y])
    return [int(round(sum(group) / len(group))) for group in groups]


def detect_staff_lines(binary: np.ndarray) -> tuple[list[int], list[StaffCandidate]]:
    """Detecta líneas horizontales y propone grupos de cinco líneas.

    binary debe ser una imagen monocroma con tinta negra y fondo blanco.
    Esta detección geométrica es una etapa inicial: barras, subrayados y
    otros trazos pueden producir candidatos falsos.
    """
    if binary is None or binary.ndim != 2 or binary.size == 0:
        raise ValueError("Se requiere una imagen binaria monocroma no vacía")

    ink = cv2.bitwise_not(binary)
    width = binary.shape[1]
    kernel_width = max(25, width // 6)
    horizontal_kernel = cv2.getStructuringElement(
        cv2.MORPH_RECT, (kernel_width, 1)
    )
    horizontal = cv2.morphologyEx(ink, cv2.MORPH_OPEN, horizontal_kernel)
    lines = _row_centres(horizontal)

    staves: list[StaffCandidate] = []
    index = 0
    while index + 4 < len(lines):
        group = lines[index : index + 5]
        gaps = np.diff(group).astype(float)
        mean_gap = float(np.mean(gaps))
        if mean_gap > 0 and float(np.std(gaps)) / mean_gap <= 0.35:
            regularity = max(0.0, 1.0 - float(np.std(gaps)) / mean_gap)
            staves.append(
                StaffCandidate(
                    lines_y=group,
                    spacing_px=round(mean_gap, 2),
                    confidence=round(min(1.0, regularity), 3),
                )
            )
            index += 5
        else:
            index += 1

    return lines, staves


def analyze_page(image: np.ndarray, page_number: int) -> tuple[np.ndarray, PageAnalysis]:
    binary = binarize_page(image)
    lines, staves = detect_staff_lines(binary)
    result = PageAnalysis(
        page_number=page_number,
        width_px=int(binary.shape[1]),
        height_px=int(binary.shape[0]),
        horizontal_lines_y=lines,
        staves=staves,
    )
    return binary, result
