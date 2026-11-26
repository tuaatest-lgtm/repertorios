import numpy as np
import pytest

from palermo_omr.symbols import NoteheadCandidate
from palermo_omr.visualization import draw_geometry_overlay, draw_notehead_overlay


def _candidate(confidence=0.8, bbox=(10, 20, 12, 8)):
    return NoteheadCandidate(
        bbox=bbox,
        center_x=16.0,
        center_y=24.0,
        staff_index=1,
        diatonic_step_from_bottom=3,
        fill_ratio=0.6,
        notehead_shape_score=0.9,
        confidence=confidence,
    )


def test_draws_overlay_without_mutating_source_image():
    image = np.full((80, 120, 3), 255, dtype=np.uint8)
    original = image.copy()

    overlay = draw_notehead_overlay(image, [_candidate()])

    assert overlay.shape == image.shape
    assert not np.array_equal(overlay, original)
    assert np.array_equal(image, original)


def test_empty_candidates_return_visual_copy():
    image = np.full((40, 60, 3), 255, dtype=np.uint8)
    overlay = draw_notehead_overlay(image, [])

    assert np.array_equal(overlay, image)
    assert overlay is not image


def test_rejects_non_color_page():
    with pytest.raises(ValueError, match="BGR"):
        draw_notehead_overlay(np.zeros((20, 20), dtype=np.uint8), [])


def test_rejects_empty_page():
    with pytest.raises(ValueError, match="vacía"):
        draw_notehead_overlay(np.zeros((0, 0, 3), dtype=np.uint8), [])



def test_draw_geometry_overlay_marks_candidate_families_without_mutating_source():
    image = np.full((120, 180, 3), 255, dtype=np.uint8)
    original = image.copy()
    page_data = {
        "staves": [{"lines_y": [30, 35, 40, 45, 50]}],
        "rest_shape_candidates": [{"bbox": [20, 35, 8, 10]}],
        "tie_slur_shape_candidates": [{"bbox": [40, 25, 30, 5]}],
        "beam_group_candidates": [{"bbox": [70, 20, 25, 3]}],
        "augmentation_dot_candidates": [{"x": 105.0, "y": 40.0}],
        "barline_candidates": [{"x": 120.0, "y_top": 30, "y_bottom": 50}],
        "barline_group_candidates": [{
            "staff_index": 0, "x_positions": [130.0, 133.0],
        }],
        "system_barline_candidates": [{
            "x": 145.0, "staff_indices": [0],
        }],
        "staff_system_candidates": [{"staff_indices": [0]}],
        "measure_span_candidates": [{
            "staff_index": 0, "x_start": 150.0, "x_end": 170.0,
        }],
    }

    overlay = draw_geometry_overlay(image, page_data)

    assert overlay.shape == image.shape
    assert not np.array_equal(overlay, original)
    assert np.array_equal(image, original)


def test_draw_geometry_overlay_rejects_invalid_inputs():
    with pytest.raises(ValueError, match="BGR"):
        draw_geometry_overlay(np.zeros((20, 20), dtype=np.uint8), {})
    with pytest.raises(ValueError, match="objeto"):
        draw_geometry_overlay(np.zeros((20, 20, 3), dtype=np.uint8), [])
