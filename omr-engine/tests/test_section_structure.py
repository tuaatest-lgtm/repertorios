import fitz

from palermo_omr.imaging import StaffCandidate
from palermo_omr.measure_layout import MeasureSpanCandidate
from palermo_omr.section_structure import detect_section_candidates


def _span():
    return MeasureSpanCandidate(
        staff_index=0, measure_index=1, x_start=50, x_end=150,
        width_px=100, left_boundary_observed=True,
        right_boundary_observed=True, confidence=0.8, warning="test",
    )


def test_detects_section_markers_identifiers_and_open_ranges(tmp_path):
    path = tmp_path / "sections.pdf"
    document = fitz.open()
    page = document.new_page(width=600, height=400)
    page.insert_text((100, 90), "Coro", fontsize=12)
    page.insert_text((150, 90), "A", fontsize=12)
    page.insert_text((400, 90), "Puente", fontsize=12)
    document.save(path)
    document.close()

    result = detect_section_candidates(
        path, 1, [StaffCandidate([100, 110, 120, 130, 140], 10, 1)],
        [_span()], dpi=72,
    )

    assert [item.normalized_text for item in result["section_marker_candidates"]] == [
        "CORO", "PUENTE"
    ]
    assert len(result["section_identifier_candidates"]) == 1
    assert result["section_identifier_candidates"][0].identifier == "A"
    assert result["section_identifier_candidates"][0].related_marker_index == 0
    ranges = result["section_range_candidates"]
    assert len(ranges) == 2
    assert ranges[0].extent == "between_section_markers"
    assert ranges[0].end_marker_index == 1
    assert ranges[1].extent == "open_ended_page_candidate"
    assert ranges[1].end_marker_index is None


def test_does_not_attach_distant_letter_to_section(tmp_path):
    path = tmp_path / "distant.pdf"
    document = fitz.open()
    page = document.new_page(width=600, height=400)
    page.insert_text((100, 90), "Estrofa", fontsize=12)
    page.insert_text((350, 90), "B", fontsize=12)
    document.save(path)
    document.close()

    result = detect_section_candidates(
        path, 1, [StaffCandidate([100, 110, 120, 130, 140], 10, 1)],
        [_span()], dpi=72,
    )

    assert result["section_identifier_candidates"] == []


def test_rejects_invalid_page_and_distance(tmp_path):
    path = tmp_path / "empty.pdf"
    document = fitz.open()
    document.new_page()
    document.save(path)
    document.close()
    staff = [StaffCandidate([100, 110, 120, 130, 140], 10, 1)]
    for kwargs in ({"page_number": 0}, {"max_identifier_distance_measures": 0}):
        try:
            detect_section_candidates(
                path, kwargs.get("page_number", 1), staff, [_span()],
                **{k: v for k, v in kwargs.items() if k != "page_number"},
            )
        except ValueError:
            continue
        raise AssertionError("Expected ValueError")
