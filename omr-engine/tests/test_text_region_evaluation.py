import pytest

from palermo_omr.text_region_evaluation import (
    evaluate_text_regions,
    intersection_over_union,
)


def test_iou_for_identical_and_disjoint_boxes():
    assert intersection_over_union((0, 0, 10, 10), (0, 0, 10, 10)) == 1.0
    assert intersection_over_union((0, 0, 10, 10), (20, 20, 30, 30)) == 0.0


def test_evaluation_counts_true_false_positives_and_false_negatives():
    result = evaluate_text_regions(
        [(0, 0, 10, 10), (40, 40, 50, 50)],
        [(1, 1, 9, 9), (20, 20, 30, 30)],
        iou_threshold=0.5,
    )

    assert result.true_positive == 1
    assert result.false_positive == 1
    assert result.false_negative == 1
    assert result.precision == 0.5
    assert result.recall == 0.5
    assert result.f1 == 0.5
    assert result.unmatched_predicted_indices == (1,)
    assert result.unmatched_annotated_indices == (1,)


def test_each_prediction_and_annotation_can_only_be_matched_once():
    result = evaluate_text_regions(
        [(0, 0, 10, 10), (1, 1, 11, 11)],
        [(0, 0, 10, 10)],
        iou_threshold=0.5,
    )

    assert result.true_positive == 1
    assert result.false_positive == 1
    assert len(result.matches) == 1


def test_matching_maximizes_number_of_valid_pairs_not_greedy_first_pair():
    # The first prediction overlaps both references, the second only the first.
    # A maximum-cardinality assignment must retain two valid matches.
    result = evaluate_text_regions(
        [(0, 0, 10, 10), (0, 0, 6, 10)],
        [(0, 0, 6, 10), (4, 0, 10, 10)],
        iou_threshold=0.3,
    )

    assert result.true_positive == 2
    assert len({match.predicted_index for match in result.matches}) == 2
    assert len({match.annotated_index for match in result.matches}) == 2


def test_empty_inputs_report_undefined_metrics_as_none():
    empty = evaluate_text_regions([], [])
    no_predictions = evaluate_text_regions([], [(0, 0, 10, 10)])
    no_annotations = evaluate_text_regions([(0, 0, 10, 10)], [])

    assert empty.precision is None
    assert empty.recall is None
    assert empty.f1 is None
    assert no_predictions.precision is None
    assert no_predictions.recall == 0.0
    assert no_annotations.precision == 0.0
    assert no_annotations.recall is None


def test_rejects_invalid_boxes_and_thresholds():
    with pytest.raises(ValueError):
        evaluate_text_regions([(0, 0, 0, 10)], [])
    with pytest.raises(ValueError):
        evaluate_text_regions([(0, 0, 10, 10)], [], iou_threshold=0)
    with pytest.raises(ValueError):
        evaluate_text_regions([(0, 0, 10, 10)], [(0, 0, float("inf"), 10)])
    with pytest.raises(ValueError):
        intersection_over_union((0, 0, 10), (0, 0, 10, 10))
