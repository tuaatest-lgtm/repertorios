import numpy as np
import pytest

from palermo_omr.imaging import StaffCandidate
from palermo_omr.notation_preamble import detect_notation_preamble_candidates


def staff():
    return StaffCandidate(
        lines_y=[40, 50, 60, 70, 80],
        spacing_px=10.0,
        confidence=0.95,
    )


def test_extracts_preamble_glyph_without_claiming_it_is_a_clef():
    image = np.full((120, 240), 255, dtype=np.uint8)
    for y in [40, 50, 60, 70, 80]:
        image[y, :] = 0
    # A compact, synthetic glyph before the first note.
    image[45:76, 12:20] = 0
    image[50:56, 20:25] = 0

    candidates = detect_notation_preamble_candidates(image, [staff()])
    assert candidates
    candidate = candidates[0]
    assert candidate.role == "clef_key_signature_or_other"
    assert candidate.status == "unclassified_visual_glyph"
    assert candidate.confidence == 0.0
    assert candidate.bbox[0] < 40


def test_empty_staff_region_returns_no_candidates():
    image = np.full((120, 240), 255, dtype=np.uint8)
    for y in [40, 50, 60, 70, 80]:
        image[y, :] = 0
    assert detect_notation_preamble_candidates(image, [staff()]) == []


def test_rejects_invalid_binary_image():
    with pytest.raises(ValueError):
        detect_notation_preamble_candidates(np.array([]), [staff()])
