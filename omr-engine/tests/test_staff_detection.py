import numpy as np
import pytest

from palermo_omr.imaging import detect_staff_lines


def test_detects_five_staff_lines():
    image = np.full((180, 900), 255, dtype=np.uint8)
    for y in (40, 50, 60, 70, 80):
        image[y : y + 1, :] = 0

    lines, staves = detect_staff_lines(image)

    assert len(lines) == 5
    assert [line for line in staves[0].lines_y] == [40, 50, 60, 70, 80]
    assert staves[0].spacing_px == pytest.approx(10.0)


def test_rejects_invalid_image():
    with pytest.raises(ValueError):
        detect_staff_lines(np.array([]))
