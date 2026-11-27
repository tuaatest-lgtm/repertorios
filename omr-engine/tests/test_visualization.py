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
        "staff_grouping_mark_candidates": [{
            "x": 12.0, "y_top": 28, "y_bottom": 52, "width_px": 5,
            "kind": "curly_brace_candidate", "staff_indices": [0],
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


def test_geometry_overlay_draws_printed_pdf_label_bbox_in_render_pixels():
    image = np.full((100, 120, 3), 255, dtype=np.uint8)
    page_data = {
        "render_dpi": 72,
        "printed_label_candidates": [
            {
                "text": "Soprano",
                "bbox_pdf": [10.0, 20.0, 45.0, 32.0],
                "association_status": "associated_candidate",
            }
        ],
    }

    overlay = draw_geometry_overlay(image, page_data)

    assert not np.array_equal(overlay, image)
    assert np.any(overlay[20:33, 10:46] != 255)


def test_geometry_overlay_scales_printed_label_bbox_with_render_dpi():
    image = np.full((100, 120, 3), 255, dtype=np.uint8)
    page_data = {
        "render_dpi": 144,
        "printed_label_candidates": [
            {"text": "Alto", "bbox_pdf": [10.0, 10.0, 20.0, 15.0]},
        ],
    }

    overlay = draw_geometry_overlay(image, page_data)

    assert np.any(overlay[20:31, 20:41] != 255)



def test_geometry_overlay_draws_section_markers_and_system_anchors():
    image = np.full((320, 420, 3), 255, dtype=np.uint8)
    page_data = {
        "render_dpi": 72,
        "staves": [
            {"lines_y": [100, 110, 120, 130, 140]},
            {"lines_y": [250, 260, 270, 280, 290]},
        ],
        "staff_system_candidates": [
            {"system_index": 0, "staff_indices": [0, 1], "y_top": 100, "y_bottom": 290}
        ],
        "section_marker_candidates": [{
            "text": "Intro", "bbox_pdf": [90, 70, 120, 85],
        }],
        "section_measure_anchor_candidates": [
            {"marker_index": 0, "system_index": 0, "staff_index": 0,
             "interval_x_start": 80, "interval_x_end": 180,
             "position_ratio_in_interval": 0.5},
            {"marker_index": 0, "system_index": 0, "staff_index": 1,
             "interval_x_start": 80, "interval_x_end": 180,
             "position_ratio_in_interval": 0.5},
        ],
    }
    overlay = draw_geometry_overlay(image, page_data)
    assert np.any(overlay != image)
    # La misma marca anclada a dos pentagramas del mismo sistema dibuja
    # una única línea vertical de referencia, no dos límites independientes.
    assert np.any(np.any(overlay[100:291, 130] != image[100:291, 130], axis=1))



def test_geometry_overlay_distinguishes_excluded_headers_from_section_labels():
    image = np.full((100, 160, 3), 255, dtype=np.uint8)
    overlay = draw_geometry_overlay(image, {
        "render_dpi": 72,
        "staves": [],
        "section_marker_candidates": [
            {"text": "Coro", "bbox_pdf": [10, 10, 30, 30],
             "global_boundary_status": "excluded_repeated_page_header_candidate"},
            {"text": "Intro", "bbox_pdf": [50, 10, 70, 30],
             "global_boundary_status": "eligible_candidate"},
        ],
    })
    assert tuple(overlay[10, 10]) == (120, 120, 150)
    assert tuple(overlay[10, 50]) == (180, 60, 220)



def test_geometry_overlay_prefers_cross_staff_anchor_for_system_label():
    image = np.full((320, 420, 3), 255, dtype=np.uint8)
    page_data = {
        "render_dpi": 72,
        "staves": [
            {"lines_y": [100, 110, 120, 130, 140]},
            {"lines_y": [250, 260, 270, 280, 290]},
        ],
        "staff_system_candidates": [
            {"system_index": 0, "staff_indices": [0, 1], "y_top": 100, "y_bottom": 290}
        ],
        "section_measure_anchor_candidates": [
            {"marker_index": 0, "system_index": 0, "staff_index": 0,
             "interval_x_start": 80, "interval_x_end": 180,
             "position_ratio_in_interval": 0.5,
             "global_alignment_status": "single_staff_only_unmatched", "staff_support": 1},
            {"marker_index": 0, "system_index": 0, "staff_index": 1,
             "interval_x_start": 80, "interval_x_end": 180,
             "position_ratio_in_interval": 0.5,
             "global_alignment_status": "cross_staff_alignment_candidate", "staff_support": 2},
        ],
    }
    overlay = draw_geometry_overlay(image, page_data)
    assert tuple(overlay[100, 130]) == (20, 150, 30)



def test_geometry_overlay_marks_ambiguous_measure_spans_in_red():
    image = np.full((200, 240, 3), 255, dtype=np.uint8)
    overlay = draw_geometry_overlay(image, {
        "render_dpi": 72,
        "staves": [{"lines_y": [50, 60, 70, 80, 90]}],
        "measure_span_candidates": [{
            "staff_index": 0,
            "measure_index": 1,
            "x_start": 40,
            "x_end": 140,
            "width_px": 100,
            "alignment_status": "ambiguous_spans_multiple_measure_candidates",
            "possible_global_measure_candidates": [1, 2],
        }],
    })
    assert tuple(overlay[70, 40]) == (0, 0, 255)
