import cv2
import numpy as np
import pytest

from palermo_omr.beam_geometry import extract_beam_segments


@pytest.mark.parametrize("slope", [-0.18, -0.10, 0.0, 0.10, 0.18])
def test_extracts_horizontal_and_sloped_beam_segments(slope):
    image = np.full((120, 180), 255, dtype=np.uint8)
    x0, x1, y0 = 35, 125, 45
    y1 = round(y0 + (x1 - x0) * slope)
    cv2.line(image, (x0, y0), (x1, y1), 0, 5)

    segments = extract_beam_segments(image, spacing=10)

    assert segments
    assert any(
        x <= x0 + 8 and x + width >= x1 - 8
        for x, _y, width, _height in segments
    )


def test_ignores_short_non_beam_mark():
    image = np.full((100, 140), 255, dtype=np.uint8)
    cv2.line(image, (50, 40), (57, 42), 0, 2)

    assert extract_beam_segments(image, spacing=10) == []


def test_rejects_invalid_binary_input():
    with pytest.raises(ValueError):
        extract_beam_segments(np.zeros((10, 10, 3), dtype=np.uint8), spacing=10)


def test_connected_horizontal_beam_and_stems_are_not_sloped_beam():
    image = np.full((120, 180), 255, dtype=np.uint8)
    # Una barra horizontal unida a dos plicas forma un único componente.
    cv2.line(image, (55, 40), (125, 40), 0, 4)
    cv2.line(image, (60, 40), (60, 95), 0, 2)
    cv2.line(image, (120, 40), (120, 95), 0, 2)

    assert extract_beam_segments(image, spacing=10) == []
