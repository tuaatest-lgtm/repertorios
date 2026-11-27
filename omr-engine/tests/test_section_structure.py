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

def test_links_sections_across_pages_without_closing_at_page_break():
    from palermo_omr.section_structure import link_section_ranges_across_pages

    pages = [
        {
            "page_number": 1,
            "section_marker_candidates": [
                {"normalized_text": "CORO", "text": "Coro", "bbox_pdf": [10, 20, 40, 30],
                 "center_x_px": 25, "center_y_px": 25}
            ],
            "section_identifier_candidates": [
                {"related_marker_index": 0, "identifier": "A"}
            ],
        },
        {"page_number": 2, "section_marker_candidates": [],
         "section_identifier_candidates": []},
        {
            "page_number": 3,
            "section_marker_candidates": [
                {"normalized_text": "PUENTE", "text": "Puente", "bbox_pdf": [10, 20, 50, 30],
                 "center_x_px": 30, "center_y_px": 25}
            ],
            "section_identifier_candidates": [],
        },
    ]

    ranges = link_section_ranges_across_pages(pages)
    assert len(ranges) == 2
    assert ranges[0]["section_name"] == "CORO"
    assert ranges[0]["identifier"] == "A"
    assert ranges[0]["start"]["page_number"] == 1
    assert ranges[0]["end"]["page_number"] == 3
    assert ranges[0]["extent"] == "cross_page_candidate"
    assert ranges[0]["page_span"] == 3
    assert ranges[1]["extent"] == "open_ended_score_candidate"
    assert ranges[1]["end"] is None


def test_global_section_ranges_ignore_input_page_order():
    from palermo_omr.section_structure import link_section_ranges_across_pages

    pages = [
        {"page_number": 2, "section_marker_candidates": [
            {"normalized_text": "FINAL", "text": "Final", "bbox_pdf": [0, 0, 10, 10]}
        ], "section_identifier_candidates": []},
        {"page_number": 1, "section_marker_candidates": [
            {"normalized_text": "ESTROFA", "text": "Estrofa", "bbox_pdf": [0, 0, 10, 10]}
        ], "section_identifier_candidates": []},
    ]
    ranges = link_section_ranges_across_pages(pages)
    assert ranges[0]["section_name"] == "ESTROFA"
    assert ranges[0]["end"]["page_number"] == 2
    assert ranges[1]["section_name"] == "FINAL"

def test_anchors_section_marker_to_local_measure_interval():
    from palermo_omr.section_structure import anchor_section_markers_to_measure_spans

    anchors = anchor_section_markers_to_measure_spans(
        [{"center_x_px": 100, "center_y_px": 120}],
        [StaffCandidate([100, 110, 120, 130, 140], 10, 1)],
        [_span()],
    )
    assert len(anchors) == 1
    assert anchors[0]["marker_index"] == 0
    assert anchors[0]["staff_index"] == 0
    assert anchors[0]["measure_index_on_staff"] == 1
    assert anchors[0]["position_ratio_in_interval"] == 0.5
    assert anchors[0]["relation"] == "inside_interval"
    assert anchors[0]["review_status"] == "pending"


def test_anchor_rejects_marker_far_from_measure_intervals():
    from palermo_omr.section_structure import anchor_section_markers_to_measure_spans

    anchors = anchor_section_markers_to_measure_spans(
        [{"center_x_px": 500, "center_y_px": 120}],
        [StaffCandidate([100, 110, 120, 130, 140], 10, 1)],
        [_span()],
    )
    assert anchors == []




def test_global_measure_sequence_never_merges_two_intervals_from_same_staff():
    from palermo_omr.section_structure import build_global_measure_sequence

    pages = [{
        "page_number": 1,
        "staff_system_candidates": [
            {"system_index": 0, "staff_indices": [0, 1]}
        ],
        "measure_span_candidates": [
            {"staff_index": 0, "measure_index": 1, "x_start": 40, "x_end": 60,
             "width_px": 20, "confidence": 0.8},
            {"staff_index": 1, "measure_index": 1, "x_start": 40, "x_end": 60,
             "width_px": 20, "confidence": 0.8},
            {"staff_index": 0, "measure_index": 2, "x_start": 43, "x_end": 63,
             "width_px": 20, "confidence": 0.8},
            {"staff_index": 1, "measure_index": 2, "x_start": 43, "x_end": 63,
             "width_px": 20, "confidence": 0.8},
        ],
    }]

    result = build_global_measure_sequence(pages)
    candidates = result["global_measure_candidates"]
    assert len(candidates) == 2
    assert [item["staff_support"] for item in candidates] == [2, 2]
    assert [item["global_measure_candidate"] for item in candidates] == [1, 2]
    assert len(result["staff_measure_map"]) == 4
