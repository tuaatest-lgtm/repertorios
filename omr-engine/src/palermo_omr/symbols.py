"""Propuestas geométricas de cabezas de nota y posición diatónica.

La detección usa una apertura elíptica sobre la tinta original para extraer
el núcleo de cabezas rellenas aunque estén unidas a plicas, barras o líneas
del pentagrama. Los resultados siguen siendo candidatos visuales.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass

import cv2
import numpy as np

from .imaging import StaffCandidate


@dataclass(frozen=True)
class NoteheadCandidate:
    bbox: tuple[int, int, int, int]
    center_x: float
    center_y: float
    staff_index: int
    diatonic_step_from_bottom: int
    fill_ratio: float
    notehead_shape_score: float
    confidence: float

    def to_dict(self) -> dict:
        return asdict(self)


def detect_notehead_candidates(
    binary: np.ndarray,
    staves: list[StaffCandidate],
) -> list[NoteheadCandidate]:
    """Propone cabezas de nota rellenas y su posición diatónica aproximada.

    Se extrae el núcleo ovalado mediante apertura morfológica elíptica.
    Esto evita que una plica o una barra compartida convierta toda la nota
    en un único componente demasiado grande. Convención: 0 es la línea
    inferior; los espacios y líneas hacia arriba son 1, 2, 3...
    No asigna nombres de nota porque depende de la clave.
    """
    if binary is None or binary.ndim != 2 or binary.size == 0:
        raise ValueError("Se requiere una imagen binaria monocroma no vacía")
    if not staves:
        return []

    ink = (binary < 128).astype(np.uint8) * 255
    candidates: list[NoteheadCandidate] = []

    for staff_index, staff in enumerate(staves):
        if len(staff.lines_y) != 5:
            continue
        spacing = float(staff.spacing_px)
        if spacing <= 1:
            continue

        # El núcleo de una cabeza rellena suele ser ovalado. La apertura
        # elimina trazos finos (líneas, plicas y barras) y conserva su masa.
        kernel_width = max(5, int(round(spacing * 0.90)) | 1)
        kernel_height = max(3, int(round(spacing * 0.48)) | 1)
        kernel = cv2.getStructuringElement(
            cv2.MORPH_ELLIPSE, (kernel_width, kernel_height)
        )
        opened = cv2.morphologyEx(ink, cv2.MORPH_OPEN, kernel)

        top = max(0, int(round(staff.lines_y[0] - spacing * 1.7)))
        bottom = min(binary.shape[0], int(round(staff.lines_y[-1] + spacing * 1.7)))
        roi = opened[top:bottom, :]
        count, _, stats, centroids = cv2.connectedComponentsWithStats(
            roi, connectivity=8
        )

        min_w, max_w = spacing * 0.55, spacing * 2.0
        min_h, max_h = spacing * 0.30, spacing * 1.35

        for label in range(1, count):
            x, y, w, h, area = (int(v) for v in stats[label])
            cx, cy_local = (float(v) for v in centroids[label])
            cy = cy_local + top

            # Recuperación complementaria: dos cabezas desplazadas pueden
            # tocarse y aparecer como un único componente. Buscamos dos picos
            # robustos en su transformada de distancia, pero solo si ambos
            # coinciden con posiciones diatónicas plausibles del pentagrama.
            component = (roi[y:y + h, x:x + w] > 0).astype(np.uint8)
            if w > spacing * 1.35 and h > spacing * 0.65 and component.size:
                # Una barra inclinada puede producir dos máximos locales en la
                # transformada de distancia. Antes de separarla, exigimos una
                # masa compacta, compatible con dos cabezas tocándose, y no un
                # trazo largo y delgado como una viga o línea de expresión.
                component_aspect = max(w, h) / max(min(w, h), 1)
                if component_aspect > 2.2:
                    continue
                ys, xs = np.nonzero(component)
                if len(xs) < 3:
                    continue
                points = np.column_stack((xs, ys)).astype(np.float32)
                eigenvalues = np.linalg.eigvalsh(np.cov(points, rowvar=False))
                elongation = float(
                    np.sqrt(max(eigenvalues[-1], 1e-6) / max(eigenvalues[0], 1e-6))
                )
                if elongation > 4.5:
                    continue

                distance = cv2.distanceTransform(component, cv2.DIST_L2, 5)
                peak_threshold = max(1.0, float(distance.max()) * 0.62)
                local_max = cv2.dilate(
                    distance,
                    np.ones((3, 3), dtype=np.uint8),
                )
                peak_mask = (
                    (distance >= peak_threshold)
                    & (distance >= local_max - 1e-6)
                ).astype(np.uint8)
                peak_count, peak_labels, peak_stats, peak_centroids = (
                    cv2.connectedComponentsWithStats(peak_mask, connectivity=8)
                )
                peaks: list[tuple[float, float, float]] = []
                for peak_label in range(1, peak_count):
                    px, py, pw, ph, peak_area = (
                        int(v) for v in peak_stats[peak_label]
                    )
                    if peak_area == 0:
                        continue
                    pcx, pcy = peak_centroids[peak_label]
                    peak_value = float(distance[
                        min(component.shape[0] - 1, max(0, int(round(pcy)))),
                        min(component.shape[1] - 1, max(0, int(round(pcx)))),
                    ])
                    absolute_y = top + y + float(pcy)
                    step_candidate = int(round(
                        (float(staff.lines_y[-1]) - absolute_y) / (spacing / 2.0)
                    ))
                    snapped = float(staff.lines_y[-1]) - step_candidate * spacing / 2.0
                    alignment_error = abs(absolute_y - snapped) / max(spacing / 2.0, 1.0)
                    if alignment_error <= 0.60:
                        peaks.append((
                            float(x) + float(pcx),
                            absolute_y,
                            peak_value,
                        ))

                split_pair: tuple[tuple[float, float, float], ...] | None = None
                best_pair_score = -1.0
                for first_index in range(len(peaks)):
                    for second_index in range(first_index + 1, len(peaks)):
                        first, second = peaks[first_index], peaks[second_index]
                        dx = abs(first[0] - second[0])
                        dy = abs(first[1] - second[1])
                        if not (spacing * 0.55 <= dx <= spacing * 2.2):
                            continue
                        if not (spacing * 0.30 <= dy <= spacing * 1.25):
                            continue
                        score = first[2] + second[2]
                        if score > best_pair_score:
                            best_pair_score = score
                            split_pair = (first, second)

                if split_pair is not None:
                    for peak_x, peak_y, peak_strength in split_pair:
                        step = int(round(
                            (float(staff.lines_y[-1]) - peak_y) / (spacing / 2.0)
                        ))
                        snapped_y = float(staff.lines_y[-1]) - step * spacing / 2.0
                        vertical_error = abs(peak_y - snapped_y) / max(spacing / 2.0, 1.0)
                        alignment_score = max(0.0, 1.0 - vertical_error)
                        # La confianza se limita deliberadamente: una separación
                        # geométrica no equivale todavía a una nota confirmada.
                        split_confidence = min(
                            0.72,
                            0.48 + 0.16 * alignment_score
                            + 0.08 * min(1.0, peak_strength / max(spacing * 0.35, 1.0)),
                        )
                        box_width = max(3, int(round(spacing * 1.55)))
                        box_height = max(3, int(round(spacing * 0.95)))
                        box_x = int(round(peak_x - box_width / 2.0))
                        box_y = int(round(peak_y - box_height / 2.0))
                        candidates.append(
                            NoteheadCandidate(
                                bbox=(box_x, box_y, box_width, box_height),
                                center_x=round(peak_x, 2),
                                center_y=round(peak_y, 2),
                                staff_index=staff_index,
                                diatonic_step_from_bottom=step,
                                fill_ratio=0.5,
                                notehead_shape_score=0.70,
                                confidence=round(split_confidence, 3),
                            )
                        )
                    # No añadimos además el componente combinado como una tercera nota.
                    continue

            if not (min_w <= w <= max_w and min_h <= h <= max_h):
                continue

            aspect = w / max(h, 1)
            if not 0.85 <= aspect <= 2.6:
                continue

            bottom_line = float(staff.lines_y[-1])
            step = int(round((bottom_line - cy) / (spacing / 2.0)))
            snapped_y = bottom_line - step * spacing / 2.0
            vertical_error = abs(cy - snapped_y) / max(spacing / 2.0, 1.0)
            if vertical_error > 0.52:
                continue

            component = roi[y:y + h, x:x + w]
            fill_ratio = float(np.count_nonzero(component)) / max(w * h, 1)
            if not 0.20 <= fill_ratio <= 0.98:
                continue

            shape_score = max(0.0, 1.0 - abs(aspect - 1.35) / 1.75)
            alignment_score = max(0.0, 1.0 - vertical_error)
            size_score = min(1.0, w / max(spacing * 1.0, 1.0))
            fill_score = min(1.0, fill_ratio / 0.65)
            confidence = (
                0.35 * shape_score
                + 0.30 * alignment_score
                + 0.20 * size_score
                + 0.15 * fill_score
            )

            candidates.append(
                NoteheadCandidate(
                    bbox=(x, top + y, w, h),
                    center_x=round(cx, 2),
                    center_y=round(cy, 2),
                    staff_index=staff_index,
                    diatonic_step_from_bottom=step,
                    fill_ratio=round(fill_ratio, 3),
                    notehead_shape_score=round(shape_score, 3),
                    confidence=round(confidence, 3),
                )
            )

    candidates.sort(key=lambda item: (item.staff_index, item.center_x, item.center_y))
    return candidates


def detect_hollow_notehead_candidates(
    binary: np.ndarray,
    staves: list[StaffCandidate],
) -> list[NoteheadCandidate]:
    """Propone cabezas huecas mediante contornos con hueco interior.

    Se eliminan primero las líneas largas del pentagrama y se cierran pequeñas
    interrupciones del contorno. La función es independiente del detector de
    cabezas rellenas: sus resultados no deben tratarse como notas confirmadas.
    """
    if binary is None or binary.ndim != 2 or binary.size == 0:
        raise ValueError("Se requiere una imagen binaria monocroma no vacía")
    if not staves:
        return []

    ink = (binary < 128).astype(np.uint8) * 255
    line_width = max(25, binary.shape[1] // 6)
    line_kernel = cv2.getStructuringElement(
        cv2.MORPH_RECT, (line_width, 1)
    )
    staff_lines = cv2.morphologyEx(ink, cv2.MORPH_OPEN, line_kernel)
    cleaned = cv2.subtract(ink, staff_lines)
    close_kernel = cv2.getStructuringElement(
        cv2.MORPH_ELLIPSE, (3, 3)
    )
    cleaned = cv2.morphologyEx(cleaned, cv2.MORPH_CLOSE, close_kernel)

    results: list[NoteheadCandidate] = []
    for staff_index, staff in enumerate(staves):
        spacing = float(staff.spacing_px)
        if len(staff.lines_y) != 5 or spacing <= 1:
            continue

        top = max(0, int(round(staff.lines_y[0] - spacing * 1.5)))
        bottom = min(
            binary.shape[0],
            int(round(staff.lines_y[-1] + spacing * 1.5)),
        )
        roi = cleaned[top:bottom, :]
        contours, hierarchy = cv2.findContours(
            roi, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE
        )
        if hierarchy is None:
            continue

        staff_results: list[NoteheadCandidate] = []
        for contour_index, contour in enumerate(contours):
            parent_index = int(hierarchy[0][contour_index][3])
            if parent_index < 0:
                continue

            x, y, w, h = cv2.boundingRect(contour)
            if not (
                spacing * 0.60 <= w <= spacing * 1.90
                and spacing * 0.30 <= h <= spacing * 1.20
            ):
                continue

            aspect = w / max(h, 1)
            if not 0.90 <= aspect <= 2.40:
                continue

            parent_area = float(cv2.contourArea(contours[parent_index]))
            if not (
                spacing * spacing * 0.35
                <= parent_area
                <= spacing * spacing * 3.0
            ):
                continue

            hole_area = float(cv2.contourArea(contour))
            if hole_area < spacing * spacing * 0.08:
                continue

            center_x = x + w / 2.0
            center_y = top + y + h / 2.0
            step = int(round(
                (float(staff.lines_y[-1]) - center_y) / (spacing / 2.0)
            ))
            snapped_y = float(staff.lines_y[-1]) - step * spacing / 2.0
            vertical_error = abs(center_y - snapped_y) / max(spacing / 2.0, 1.0)
            if vertical_error > 0.55:
                continue

            alignment_score = max(0.0, 1.0 - vertical_error)
            hole_score = min(1.0, hole_area / max(spacing * spacing * 0.45, 1.0))
            confidence = min(
                0.68,
                0.42 + 0.16 * alignment_score + 0.08 * hole_score,
            )
            box_width = max(3, int(round(spacing * 1.70)))
            box_height = max(3, int(round(spacing * 1.10)))
            staff_results.append(
                NoteheadCandidate(
                    bbox=(
                        int(round(center_x - box_width / 2.0)),
                        int(round(center_y - box_height / 2.0)),
                        box_width,
                        box_height,
                    ),
                    center_x=round(center_x, 2),
                    center_y=round(center_y, 2),
                    staff_index=staff_index,
                    diatonic_step_from_bottom=step,
                    fill_ratio=0.25,
                    notehead_shape_score=round(
                        max(0.0, 1.0 - abs(aspect - 1.35) / 1.75), 3
                    ),
                    confidence=round(confidence, 3),
                )
            )

        # Una línea del pentagrama puede partir el hueco en dos fragmentos.
        # Fusionamos solo fragmentos casi coincidentes; dos cabezas de segunda
        # suelen estar desplazadas horizontalmente y se mantienen separadas.
        staff_results.sort(key=lambda item: (item.center_x, item.center_y))
        deduplicated: list[NoteheadCandidate] = []
        for candidate in staff_results:
            duplicate = any(
                abs(candidate.center_x - previous.center_x) < spacing * 0.30
                and abs(candidate.center_y - previous.center_y) < spacing * 0.65
                for previous in deduplicated
            )
            if not duplicate:
                deduplicated.append(candidate)
        results.extend(deduplicated)

    results.sort(
        key=lambda item: (item.staff_index, item.center_x, item.center_y)
    )
    return results
