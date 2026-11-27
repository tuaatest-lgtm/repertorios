import cv2
import numpy as np
import pytest

from palermo_omr.glyph_features import FEATURE_SCHEMA, extract_glyph_features, resolve_crop_path


def test_extracts_stable_shape_descriptor_from_black_on_white_crop(tmp_path):
    image = np.full((40, 30), 255, dtype=np.uint8)
    cv2.line(image, (15, 5), (15, 34), 0, 4)
    cv2.line(image, (5, 20), (25, 20), 0, 4)
    path = tmp_path / "cross.png"
    assert cv2.imwrite(str(path), image)
    result = extract_glyph_features(path)
    assert result["feature_schema"] == FEATURE_SCHEMA
    assert result["feature_count"] == len(result["feature_vector"])
    assert len(result["feature_vector"]) == 5 + 1 + 7 + 64
    assert result["ink_bbox"] == [3, 3, 25, 34]


def test_descriptor_is_polarity_independent(tmp_path):
    image = np.full((32, 32), 255, dtype=np.uint8)
    cv2.circle(image, (16, 16), 9, 0, -1)
    a, b = tmp_path / "a.png", tmp_path / "b.png"
    cv2.imwrite(str(a), image)
    cv2.imwrite(str(b), cv2.bitwise_not(image))
    assert extract_glyph_features(a)["feature_vector"] == extract_glyph_features(b)["feature_vector"]


def test_rejects_blank_crop_and_unsafe_relative_path(tmp_path):
    blank = tmp_path / "blank.png"
    cv2.imwrite(str(blank), np.full((20, 20), 255, dtype=np.uint8))
    with pytest.raises(ValueError, match="no contiene tinta"):
        extract_glyph_features(blank)
    with pytest.raises(ValueError, match="no segura"):
        resolve_crop_path(tmp_path, "../secret.png")
