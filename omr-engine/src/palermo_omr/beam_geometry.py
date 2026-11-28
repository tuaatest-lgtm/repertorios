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
    """Extrae segmentos lineales candidatos con Hough multiángulo.

    Entrada: imagen binaria con fondo blanco y tinta negra. Devuelve bbox
    (x, y, width, height). Son segmentos geométricos, no grupos rítmicos.
    """
    if binary is None or binary.ndim != 2 or binary.size == 0:
        raise ValueError("Se requiere una imagen binaria monocroma no vacía")
    if spacing <= 1 or min_length_spacing <= 0:
        raise ValueError("El espaciamiento y la longitud mínima deben ser positivos")
    if max_angle_degrees < 0 or angle_step_degrees <= 0:
        raise ValueError("Los parámetros angulares no son válidos")

    ink = (binary < 128).astype(np.uint8) * 255
    min_length = max(7, int(round(spacing * min_length_spacing * 0.75)))
    lines = cv2.HoughLinesP(
        ink,
        rho=1,
        theta=np.pi / 180.0,
        threshold=max(5, int(round(min_length * 0.55))),
        minLineLength=min_length,
        maxLineGap=max(1, int(round(spacing * 0.30))),
    )
    if lines is None:
        return []

    segments: set[tuple[int, int, int, int]] = set()
    for line in lines[:, 0, :]:
        x1, y1, x2, y2 = (int(value) for value in line)
        dx, dy = x2 - x1, y2 - y1
        if dx == 0:
            continue
        angle = abs(math.degrees(math.atan2(dy, dx)))
        if angle > max_angle_degrees:
            continue
        left, right = sorted((x1, x2))
        upper, lower = sorted((y1, y2))
        width = right - left + 1
        height = lower - upper + 1
        if width < min_length or width / max(height, 1) < 1.5:
            continue
        segments.add((left, upper, width, height))

    return sorted(segments, key=lambda item: (item[0], item[1]))
