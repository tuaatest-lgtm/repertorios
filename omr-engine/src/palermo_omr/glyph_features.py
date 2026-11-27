"""Descriptores visuales reproducibles para glifos musicales recortados."""
from __future__ import annotations

from pathlib import Path, PurePosixPath

import cv2
import numpy as np

FEATURE_SCHEMA = "palermo-glyph-shape-v1"
GRID_SIZE = 8


def extract_glyph_features(image_path: str | Path) -> dict:
    """Extrae geometría normalizada; no asigna clases ni interpreta notación."""
    path = Path(image_path)
    image = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
    if image is None or image.size == 0:
        raise ValueError(f"No se pudo leer el recorte de glifo: {path}")
    # La tinta se representa como 1 independientemente de la polaridad del PNG.
    _, threshold = cv2.threshold(image, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)
    ink = threshold if float(np.mean(threshold)) < 127.5 else cv2.bitwise_not(threshold)
    ys, xs = np.where(ink > 0)
    if len(xs) == 0:
        raise ValueError(f"El recorte no contiene tinta: {path}")
    x0, x1 = int(xs.min()), int(xs.max()) + 1
    y0, y1 = int(ys.min()), int(ys.max()) + 1
    glyph = ink[y0:y1, x0:x1]
    height, width = glyph.shape
    normalized = cv2.resize(glyph, (64, 64), interpolation=cv2.INTER_AREA)
    occupancy = []
    for row in np.array_split(normalized, GRID_SIZE, axis=0):
        for cell in np.array_split(row, GRID_SIZE, axis=1):
            occupancy.append(round(float(np.mean(cell > 0)), 6))
    contours, hierarchy = cv2.findContours(glyph, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)
    holes = 0 if hierarchy is None else sum(1 for entry in hierarchy[0] if int(entry[3]) >= 0)
    moments = cv2.moments(glyph, binaryImage=True)
    hu = cv2.HuMoments(moments).flatten()
    hu_features = [
        round(float(-np.sign(value) * np.log10(max(abs(float(value)), 1e-30))), 6)
        for value in hu
    ]
    area = int(np.count_nonzero(glyph))
    vector = [
        round(width / max(height, 1), 6),
        round(height / max(width, 1), 6),
        round(area / max(width * height, 1), 6),
        round(width / max(image.shape[1], 1), 6),
        round(height / max(image.shape[0], 1), 6),
        float(holes),
        *hu_features,
        *occupancy,
    ]
    return {
        "feature_schema": FEATURE_SCHEMA,
        "feature_vector": vector,
        "feature_count": len(vector),
        "source_width": int(image.shape[1]),
        "source_height": int(image.shape[0]),
        "ink_bbox": [x0, y0, width, height],
    }


def resolve_crop_path(crop_root: str | Path, crop_file: str) -> Path:
    relative = PurePosixPath(crop_file)
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError(f"Ruta de recorte no segura: {crop_file}")
    return Path(crop_root).joinpath(*relative.parts)
