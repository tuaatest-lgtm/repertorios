import numpy as np
import pytest

from palermo_omr.imaging import StaffCandidate
from palermo_omr.notation_preamble import (
    detect_notation_preamble_candidates,
    export_notation_preamble_crops,
)


def staff():
    return StaffCandidate(lines_y=[40, 50, 60, 70, 80], spacing_px=10.0, confidence=0.95)


def test_extracts_preamble_glyph_and_shape_descriptor_without_classifying():
    image = np.full((120, 240), 255, dtype=np.uint8)
    for y in [40, 50, 60, 70, 80]:
        image[y, :] = 0
    image[45:76, 12:20] = 0
    image[50:56, 20:25] = 0
    candidates = detect_notation_preamble_candidates(image, [staff()])
    assert candidates
    candidate = candidates[0]
    assert candidate.role == "clef_key_signature_or_other"
    assert candidate.status == "unclassified_visual_glyph"
    assert candidate.confidence == 0.0
    assert candidate.bbox[0] < 40
    assert candidate.contour_count >= 1
    assert len(candidate.hu_moments) == 7
    assert all(np.isfinite(candidate.hu_moments))


def test_shape_descriptor_distinguishes_different_silhouettes():
    from palermo_omr.notation_preamble import _shape_features
    vertical = np.zeros((30, 12), dtype=np.uint8)
    vertical[2:28, 4:8] = 1
    diagonal = np.zeros((30, 12), dtype=np.uint8)
    for y in range(3, 27):
        diagonal[y, max(0, min(11, y // 2 - 2))] = 1
    assert _shape_features(vertical)[3] != _shape_features(diagonal)[3]


def test_empty_staff_region_returns_no_candidates():
    image = np.full((120, 240), 255, dtype=np.uint8)
    for y in [40, 50, 60, 70, 80]:
        image[y, :] = 0
    assert detect_notation_preamble_candidates(image, [staff()]) == []


def test_rejects_invalid_binary_image():
    with pytest.raises(ValueError):
        detect_notation_preamble_candidates(np.array([]), [staff()])


def test_exports_reviewable_crops_without_inventing_labels(tmp_path):
    image = np.full((120, 240), 255, dtype=np.uint8)
    for y in [40, 50, 60, 70, 80]:
        image[y, :] = 0
    image[45:76, 12:20] = 0
    candidates = detect_notation_preamble_candidates(image, [staff()])
    exported = export_notation_preamble_crops(
        image, candidates, [staff()], tmp_path / "notation-preamble-crops", page_number=2
    )
    assert len(exported) == len(candidates)
    assert exported[0]["label"] is None
    assert exported[0]["label_status"] == "needs_human_label"
    assert (tmp_path / exported[0]["crop_file"]).is_file()
