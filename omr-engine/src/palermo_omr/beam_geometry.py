"""Geometría de barras: extracción multiángulo para trazos inclinados."""
from __future__ import annotations

import math

import cv2
import numpy as np


def extract_beam_segments(
    binary: np.ndarray,
    *,
    spacing: float,
    min_length_spacing: float = 1.0,
    max_angle_degrees: int = 18,
    angle_step_degrees: int = 3,
) -> list[tuple[int, int, int, int]]:
    """Extrae candidatos de barras con apertura morfológica multiángulo.

    Entrada: imagen binaria con fondo blanco y tinta negra. Devuelve bbox
    (x, y, width, height) de componentes persistentes en una familia de
    orientaciones. No confirma grupos ni valores rítmicos.
    """
    if binary is None or binary.ndim != 2 or binary.size == 0:
        raise ValueError("Se requiere una imagen binaria monocroma no vacía")
    if spacing <= 1 or min_length_spacing <= 0:
        raise ValueError("El espaciamiento y la longitud mínima deben ser positivos")
    if max_angle_degrees < 0 or angle_step_degrees <= 0:
        raise ValueError("Los parámetros angulares no son válidos")

    ink = (binary < 128).astype(np.uint8) * 255
    length = max(7, int(round(spacing * min_length_spacing)))
    thickness = max(2, int(round(spacing * 0.17)))
    radius = int(math.ceil(length / 2 + thickness + 2))
    size = radius * 2 + 1
    combined = np.zeros_like(ink)

    for angle in range(
        -max_angle_degrees,
        max_angle_degrees + 1,
        angle_step_degrees,
    ):
        kernel = np.zeros((size, size), dtype=np.uint8)
        center = radius
        radians = math.radians(angle)
        dx = (length / 2) * math.cos(radians)
        dy = (length / 2) * math.sin(radians)
        start = (round(center - dx), round(center - dy))
        end = (round(center + dx), round(center + dy))
        cv2.line(kernel, start, end, 1, thickness)
        opened = cv2.morphologyEx(ink, cv2.MORPH_OPEN, kernel)
        combined = cv2.bitwise_or(combined, opened)

    count, _labels, stats, _centroids = cv2.connectedComponentsWithStats(
        combined, connectivity=8
    )
    min_width = max(3, int(round(spacing * min_length_spacing * 0.75)))
    max_height = max(4, int(round(spacing * 0.75 + thickness * 2)))
    segments: list[tuple[int, int, int, int]] = []
    for index in range(1, count):
        x, y, width, height, _area = (int(value) for value in stats[index])
        if width < min_width or height > max_height:
            continue
        if width / max(height, 1) < 1.5:
            continue
        segments.append((x, y, width, height))

    return sorted(segments, key=lambda item: (item[0], item[1]))
