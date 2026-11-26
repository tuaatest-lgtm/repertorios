import cv2
import numpy as np
import pytest

from palermo_omr.imaging import StaffCandidate
from palermo_omr.text_regions import detect_text_region_candidates


def staff():
    return [StaffCandidate([100, 110, 120, 130, 140], 10.0, 1.0)]


def draw_glyph_word(image, x, y, scale=1.0):
    # Three compact, disconnected glyph-like marks in a single word.
    cv2.rectangle(image, (x, y), (x + int(3 * scale), y + int(7 * scale)), 0, -1)
    cv2.rectangle(image, (x + int(6 * scale), y + int(2 * scale)),
                  (x + int(9 * scale), y + int(7 * scale)), 0, -1)
    cv2.rectangle(image, (x + int(12 * scale), y),
                  (x + int(15 * scale), y + int(7 * scale)), 0, -1)


def test_detects_text_like_region_above_staff_without_reading_it():
    image = np.full((240, 500), 255, dtype=np.uint8)
    draw_glyph_word(image, 35, 65)

    results = detect_text_region_candidates(image, staff())

    assert len(results) == 1
    assert results[0].location_hint == "above_staff"
    assert results[0].nearby_staff_indices == (0,)
    assert results[0].association_status == "nearby_staff_candidate"
    assert "no se ha leído" in results[0].warning


def test_ignores_staff_lines_and_music_region_outside_left_margin():
    image = np.full((240, 500), 255, dtype=np.uint8)
    for y in [100, 110, 120, 130, 140]:
        cv2.line(image, (20, y), (480, y), 0, 1)
    draw_glyph_word(image, 350, 65)

    assert detect_text_region_candidates(image, staff()) == []


def test_reports_ambiguous_vertical_proximity_between_staves():
    image = np.full((260, 500), 255, dtype=np.uint8)
    two = [
        StaffCandidate([70, 80, 90, 100, 110], 10.0, 1.0),
        StaffCandidate([140, 150, 160, 170, 180], 10.0, 1.0),
    ]
    draw_glyph_word(image, 35, 120)

    results = detect_text_region_candidates(image, two)

    assert len(results) == 1
    assert results[0].association_status == "ambiguous"
    assert results[0].nearby_staff_indices == (0, 1)


def test_rejects_invalid_image_and_thresholds():
    with pytest.raises(ValueError):
        detect_text_region_candidates(None, staff())
    image = np.full((240, 500), 255, dtype=np.uint8)
    with pytest.raises(ValueError):
        detect_text_region_candidates(image, staff(), left_margin_ratio=0)
    with pytest.raises(ValueError):
        detect_text_region_candidates(image, staff(), max_region_width_spacing=0)


def test_returns_empty_when_no_valid_staff_is_supplied():
    image = np.full((240, 500), 255, dtype=np.uint8)
    assert detect_text_region_candidates(image, []) == []
