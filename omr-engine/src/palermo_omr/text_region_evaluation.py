"""Evaluación geométrica de regiones de texto contra anotaciones humanas.

No interpreta contenido ni decide si una caja corresponde a una etiqueta musical.
Las cajas usan coordenadas de imagen (x_min, y_min, x_max, y_max).
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from math import isfinite
from typing import Sequence

Box = tuple[float, float, float, float]


@dataclass(frozen=True)
class RegionMatch:
    predicted_index: int
    annotated_index: int
    intersection_over_union: float


@dataclass(frozen=True)
class TextRegionEvaluation:
    iou_threshold: float
    predicted_count: int
    annotated_count: int
    matches: tuple[RegionMatch, ...]
    unmatched_predicted_indices: tuple[int, ...]
    unmatched_annotated_indices: tuple[int, ...]
    true_positive: int
    false_positive: int
    false_negative: int
    precision: float | None
    recall: float | None
    f1: float | None
    mean_matched_iou: float | None

    def to_dict(self) -> dict:
        return asdict(self)


def _validate_box(box: Sequence[float], index: int, kind: str) -> Box:
    if len(box) != 4:
        raise ValueError(f"{kind}[{index}] debe contener x_min, y_min, x_max, y_max")
    values = tuple(float(value) for value in box)
    if not all(isfinite(value) for value in values):
        raise ValueError(f"{kind}[{index}] contiene coordenadas no finitas")
    x_min, y_min, x_max, y_max = values
    if x_max <= x_min or y_max <= y_min:
        raise ValueError(f"{kind}[{index}] debe tener ancho y alto positivos")
    return values  # type: ignore[return-value]


def intersection_over_union(first: Sequence[float], second: Sequence[float]) -> float:
    """Calcula IoU entre dos cajas xyxy; devuelve un valor entre 0 y 1."""
    a = _validate_box(first, 0, "first")
    b = _validate_box(second, 0, "second")
    left = max(a[0], b[0])
    top = max(a[1], b[1])
    right = min(a[2], b[2])
    bottom = min(a[3], b[3])
    intersection = max(0.0, right - left) * max(0.0, bottom - top)
    area_a = (a[2] - a[0]) * (a[3] - a[1])
    area_b = (b[2] - b[0]) * (b[3] - b[1])
    union = area_a + area_b - intersection
    return intersection / union if union > 0 else 0.0


def evaluate_text_regions(
    predicted_boxes: Sequence[Sequence[float]],
    annotated_boxes: Sequence[Sequence[float]],
    *,
    iou_threshold: float = 0.5,
) -> TextRegionEvaluation:
    """Compara detecciones con cajas humanas mediante emparejamiento 1 a 1.

    Se maximiza primero el número de pares que superan el umbral de IoU.
    En cada paso se exploran primero las parejas con mayor IoU. Una detección
    y una anotación solo pueden participar en un emparejamiento.
    Las métricas cuyo denominador es cero se devuelven como None.
    """
    if not isfinite(iou_threshold) or not 0 < iou_threshold <= 1:
        raise ValueError("iou_threshold debe ser mayor que 0 y menor o igual que 1")

    predicted = tuple(
        _validate_box(box, index, "predicted_boxes")
        for index, box in enumerate(predicted_boxes)
    )
    annotated = tuple(
        _validate_box(box, index, "annotated_boxes")
        for index, box in enumerate(annotated_boxes)
    )

    # Lista de anotaciones elegibles por predicción, ordenadas por IoU.
    eligible: list[list[tuple[float, int]]] = []
    for pred_box in predicted:
        options = []
        for annotation_index, annotation_box in enumerate(annotated):
            score = intersection_over_union(pred_box, annotation_box)
            if score >= iou_threshold:
                options.append((score, annotation_index))
        options.sort(key=lambda item: (-item[0], item[1]))
        eligible.append(options)

    # Kuhn: obtiene un emparejamiento de cardinalidad máxima en el grafo
    # de parejas que superan el umbral. El orden favorece IoU alto.
    annotation_to_prediction: dict[int, tuple[int, float]] = {}

    def assign(prediction_index: int, visited: set[int]) -> bool:
        for score, annotation_index in eligible[prediction_index]:
            if annotation_index in visited:
                continue
            visited.add(annotation_index)
            previous = annotation_to_prediction.get(annotation_index)
            if previous is None or assign(previous[0], visited):
                annotation_to_prediction[annotation_index] = (prediction_index, score)
                return True
        return False

    # Las detecciones más restringidas se procesan primero; los desempates
    # son estables y reproducibles.
    prediction_order = sorted(
        range(len(predicted)),
        key=lambda index: (len(eligible[index]), index),
    )
    for prediction_index in prediction_order:
        assign(prediction_index, set())

    matches = tuple(sorted(
        (
            RegionMatch(predicted_index, annotation_index, score)
            for annotation_index, (predicted_index, score)
            in annotation_to_prediction.items()
        ),
        key=lambda item: (item.predicted_index, item.annotated_index),
    ))
    matched_predictions = {match.predicted_index for match in matches}
    matched_annotations = {match.annotated_index for match in matches}
    unmatched_predictions = tuple(
        index for index in range(len(predicted))
        if index not in matched_predictions
    )
    unmatched_annotations = tuple(
        index for index in range(len(annotated))
        if index not in matched_annotations
    )

    tp = len(matches)
    fp = len(unmatched_predictions)
    fn = len(unmatched_annotations)
    precision = tp / (tp + fp) if tp + fp else None
    recall = tp / (tp + fn) if tp + fn else None
    f1 = (
        2 * precision * recall / (precision + recall)
        if precision is not None and recall is not None and precision + recall > 0
        else (0.0 if precision == 0 or recall == 0 else None)
    )
    mean_iou = (
        sum(match.intersection_over_union for match in matches) / tp
        if tp else None
    )

    return TextRegionEvaluation(
        iou_threshold=iou_threshold,
        predicted_count=len(predicted),
        annotated_count=len(annotated),
        matches=matches,
        unmatched_predicted_indices=unmatched_predictions,
        unmatched_annotated_indices=unmatched_annotations,
        true_positive=tp,
        false_positive=fp,
        false_negative=fn,
        precision=precision,
        recall=recall,
        f1=f1,
        mean_matched_iou=mean_iou,
    )
