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
    """Extrae segmentos lineales candidatos y une fragmentos colineales.

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
        threshold=max(5, int(round(min_length * 0.45))),
        minLineLength=min_length,
        maxLineGap=max(2, int(round(spacing * 0.60))),
    )
    if lines is None:
        return []

    # Hough puede devolver varios fragmentos de una misma barra. Normalizamos
    # la orientación (x creciente) antes de comparar pendiente e intercepto.
    raw: list[tuple[float, float, int, int]] = []
    for line in lines[:, 0, :]:
        x1, y1, x2, y2 = (int(value) for value in line)
        if x2 < x1:
            x1, x2, y1, y2 = x2, x1, y2, y1
        dx = x2 - x1
        if dx <= 0:
            continue
        slope = (y2 - y1) / dx
        angle = abs(math.degrees(math.atan(slope)))
        if angle > max_angle_degrees:
            continue
        if dx < min_length:
            continue
        intercept = y1 - slope * x1
        raw.append((slope, intercept, x1, x2))

    # Fusiona detecciones de la misma recta cuando sus proyecciones se solapan
    # o están separadas por un hueco pequeño. Así no se cuentan fragmentos
    # Hough de una sola barra como barras rítmicas diferentes.
    raw.sort(key=lambda item: (item[0], item[1], item[2]))
    merged: list[list[float]] = []
    angle_tolerance = math.tan(math.radians(max(2, angle_step_degrees)))
    intercept_tolerance = max(3.0, spacing * 0.75)
    max_gap = max(3.0, spacing * 0.75)

    for slope, intercept, x0, x1 in raw:
        match = None
        for candidate in reversed(merged):
            if abs(slope - candidate[0]) > angle_tolerance:
                if slope - candidate[0] > angle_tolerance:
                    break
                continue
            if abs(intercept - candidate[1]) > intercept_tolerance:
                continue
            if x0 > candidate[3] + max_gap or x1 < candidate[2] - max_gap:
                continue
            match = candidate
            break
        if match is None:
            merged.append([slope, intercept, float(x0), float(x1)])
        else:
            # Promedia ligeramente para amortiguar la cuantización de Hough.
            match[0] = (match[0] + slope) / 2.0
            match[1] = (match[1] + intercept) / 2.0
            match[2] = min(match[2], float(x0))
            match[3] = max(match[3], float(x1))

    segments: set[tuple[int, int, int, int]] = set()
    for slope, intercept, x0, x1 in merged:
        left, right = int(round(x0)), int(round(x1))
        y_left = slope * left + intercept
        y_right = slope * right + intercept
        upper = int(math.floor(min(y_left, y_right))) - 2
        lower = int(math.ceil(max(y_left, y_right))) + 2
        width = right - left + 1
        height = max(1, lower - upper + 1)
        if width >= min_length and width / max(height, 1) >= 1.5:
            segments.add((left, upper, width, height))

    # Respaldo por componentes conectados: Hough puede partir una línea
    # gruesa en fragmentos distintos según la pendiente y el grosor del trazo.
    # Ajustar una recta a los píxeles de cada componente recupera su extensión
    # completa sin recurrir a primitivas vectoriales del PDF.
    count, labels, stats, _centroids = cv2.connectedComponentsWithStats(
        (ink > 0).astype(np.uint8), connectivity=8
    )
    for label in range(1, count):
        x, y, width, height, area = (int(v) for v in stats[label])
        if width < min_length or width / max(height, 1) < 1.5:
            continue
        ys, xs = np.where(labels[y:y + height, x:x + width] == label)
        if xs.size < min_length:
            continue
        points = np.column_stack((xs + x, ys + y)).astype(np.float32)
        vx, vy, x0, y0 = (float(v) for v in cv2.fitLine(
            points, cv2.DIST_L2, 0, 0.01, 0.01
        ).reshape(-1))
        if abs(vx) < 1e-6:
            continue
        angle = abs(math.degrees(math.atan2(vy, vx)))
        if angle > max_angle_degrees:
            continue
        projections = (points[:, 0] - x0) * vx + (points[:, 1] - y0) * vy
        p0, p1 = float(projections.min()), float(projections.max())
        xa = int(round(x0 + p0 * vx))
        ya = int(round(y0 + p0 * vy))
        xb = int(round(x0 + p1 * vx))
        yb = int(round(y0 + p1 * vy))
        left, right = sorted((xa, xb))
        upper, lower = sorted((ya, yb))
        candidate = (left, upper - 2, right - left + 1,
                     max(5, lower - upper + 5))
        if candidate[2] >= min_length:
            segments.add(candidate)

    return sorted(segments, key=lambda item: (item[0], item[1]))
