import fitz
import pytest

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
    assert ranges[0]["identifier_status"] == "unconfirmed_candidate"
    assert "cifrado armónico" in ranges[0]["identifier_warning"]
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



def test_global_measure_sequence_rejects_duplicate_page_numbers():
    from palermo_omr.section_structure import build_global_measure_sequence

    page = {
        "page_number": 1,
        "staff_system_candidates": [],
        "measure_span_candidates": [],
    }
    try:
        build_global_measure_sequence([page, dict(page)])
    except ValueError as error:
        assert "duplicado" in str(error)
    else:
        raise AssertionError("Expected duplicate page number to be rejected")


def test_global_measure_sequence_rejects_staff_in_multiple_systems():
    from palermo_omr.section_structure import build_global_measure_sequence

    pages = [{
        "page_number": 1,
        "staff_system_candidates": [
            {"system_index": 0, "staff_indices": [0, 1]},
            {"system_index": 1, "staff_indices": [1, 2]},
        ],
        "measure_span_candidates": [],
    }]
    try:
        build_global_measure_sequence(pages)
    except ValueError as error:
        assert "dos sistemas" in str(error)
    else:
        raise AssertionError("Expected overlapping system membership to be rejected")



def test_anchor_rejects_section_marker_far_above_all_staves():
    from palermo_omr.section_structure import anchor_section_markers_to_measure_spans

    anchors = anchor_section_markers_to_measure_spans(
        [{"center_x_px": 100, "center_y_px": -30}],
        [StaffCandidate([100, 110, 120, 130, 140], 10, 1)],
        [_span()],
    )
    assert anchors == []


def test_resolve_section_boundaries_does_not_mutate_source_ranges():
    from copy import deepcopy
    from palermo_omr.section_structure import resolve_section_range_boundaries

    source = [{
        "section_range_id": "section-1",
        "start": {
            "page_number": 1,
            "measure_anchors": [{
                "staff_index": 0,
                "measure_index_on_staff": 1,
                "position_ratio_in_interval": 0.5,
                "confidence": 0.6,
                "vertical_distance_px": 0,
            }],
        },
        "end": None,
    }]
    original = deepcopy(source)
    resolved = resolve_section_range_boundaries(
        source,
        {"staff_measure_map": [{
            "page_number": 1, "staff_index": 0,
            "measure_index_on_staff": 1, "global_measure_candidate": 1,
        }]},
    )
    assert source == original
    assert resolved[0]["start"]["musical_boundary_candidate"]["global_measure_candidate"] == 1


def test_resolve_section_boundaries_ignores_non_finite_anchor_ratios():
    from palermo_omr.section_structure import resolve_section_range_boundaries

    resolved = resolve_section_range_boundaries(
        [{
            "section_range_id": "section-1",
            "start": {"page_number": 1, "measure_anchors": [{
                "staff_index": 0, "measure_index_on_staff": 1,
                "position_ratio_in_interval": float("nan"),
                "confidence": 0.9,
            }]},
            "end": None,
        }],
        {"staff_measure_map": []},
    )
    assert resolved[0]["start"]["musical_boundary_candidate"] is None



def test_global_measure_sequence_rejects_duplicate_local_measure_span():
    from palermo_omr.section_structure import build_global_measure_sequence

    span = {
        "staff_index": 0, "measure_index": 1, "x_start": 40, "x_end": 60,
        "width_px": 20, "confidence": 0.8,
    }
    with pytest.raises(ValueError, match="duplicado"):
        build_global_measure_sequence([{
            "page_number": 1,
            "staff_system_candidates": [{"system_index": 0, "staff_indices": [0]}],
            "measure_span_candidates": [span, dict(span)],
        }])


@pytest.mark.parametrize(
    ("field", "value"),
    [("x_start", float("nan")), ("x_end", 39), ("width_px", 0)],
)
def test_global_measure_sequence_rejects_invalid_interval_geometry(field, value):
    from palermo_omr.section_structure import build_global_measure_sequence

    span = {
        "staff_index": 0, "measure_index": 1, "x_start": 40, "x_end": 60,
        "width_px": 20, "confidence": 0.8,
    }
    span[field] = value
    with pytest.raises(ValueError):
        build_global_measure_sequence([{
            "page_number": 1,
            "staff_system_candidates": [{"system_index": 0, "staff_indices": [0]}],
            "measure_span_candidates": [span],
        }])



def test_repeated_top_page_headers_do_not_split_global_sections():
    from palermo_omr.section_structure import link_section_ranges_across_pages

    header = {
        "normalized_text": "CORO", "text": "Coro",
        "bbox_pdf": [250, 10, 270, 20],
        "center_x_px": 1275, "center_y_px": 70,
        "page_width_px": 2550, "page_height_px": 3300,
    }
    pages = [
        {
            "page_number": 1,
            "section_marker_candidates": [
                dict(header),
                {"normalized_text": "ESTROFA", "text": "Estrofa",
                 "bbox_pdf": [20, 100, 70, 120], "center_x_px": 180,
                 "center_y_px": 500, "page_width_px": 2550, "page_height_px": 3300},
            ],
            "section_identifier_candidates": [],
        },
        {
            "page_number": 2,
            "section_marker_candidates": [
                dict(header),
                {"normalized_text": "PUENTE", "text": "Puente",
                 "bbox_pdf": [20, 200, 70, 220], "center_x_px": 180,
                 "center_y_px": 1000, "page_width_px": 2550, "page_height_px": 3300},
            ],
            "section_identifier_candidates": [],
        },
        {
            "page_number": 3,
            "section_marker_candidates": [dict(header)],
            "section_identifier_candidates": [],
        },
    ]

    ranges = link_section_ranges_across_pages(pages)
    assert [item["section_name"] for item in ranges] == ["ESTROFA", "PUENTE"]
    assert ranges[0]["end"]["page_number"] == 2
    assert ranges[1]["extent"] == "open_ended_score_candidate"



def test_unanchored_top_margin_label_is_not_global_section_boundary():
    from palermo_omr.section_structure import link_section_ranges_across_pages

    ranges = link_section_ranges_across_pages([{
        "page_number": 1,
        "section_marker_candidates": [
            {"normalized_text": "CORO", "text": "Coro",
             "center_x_px": 160, "center_y_px": 150,
             "page_width_px": 2550, "page_height_px": 3300},
            {"normalized_text": "INTRO", "text": "Intro",
             "center_x_px": 500, "center_y_px": 500,
             "page_width_px": 2550, "page_height_px": 3300},
        ],
        "section_identifier_candidates": [],
        "section_measure_anchor_candidates": [
            {"marker_index": 1, "staff_index": 0,
             "measure_index_on_staff": 1,
             "position_ratio_in_interval": 0.5},
        ],
    }])
    assert [item["section_name"] for item in ranges] == ["INTRO"]



def test_global_section_marker_dispositions_are_written_to_page_candidates():
    from palermo_omr.section_structure import link_section_ranges_across_pages

    header = {
        "normalized_text": "CORO", "text": "Coro",
        "center_x_px": 1275, "center_y_px": 70,
        "page_width_px": 2550, "page_height_px": 3300,
    }
    unanchored = {
        "normalized_text": "CORO", "text": "Coro",
        "center_x_px": 160, "center_y_px": 150,
        "page_width_px": 2550, "page_height_px": 3300,
    }
    anchored = {
        "normalized_text": "INTRO", "text": "Intro",
        "center_x_px": 500, "center_y_px": 500,
        "page_width_px": 2550, "page_height_px": 3300,
    }
    pages = [
        {"page_number": 1,
         "section_marker_candidates": [dict(header), dict(unanchored), anchored],
         "section_identifier_candidates": [],
         "section_measure_anchor_candidates": [
             {"marker_index": 2, "staff_index": 0, "measure_index_on_staff": 1}
         ]},
        {"page_number": 2,
         "section_marker_candidates": [dict(header)],
         "section_identifier_candidates": [],
         "section_measure_anchor_candidates": []},
    ]

    link_section_ranges_across_pages(pages)
    assert pages[0]["section_marker_candidates"][0]["global_boundary_status"] == (
        "excluded_repeated_page_header_candidate"
    )
    assert pages[1]["section_marker_candidates"][0]["global_boundary_status"] == (
        "excluded_repeated_page_header_candidate"
    )
    assert pages[0]["section_marker_candidates"][1]["global_boundary_status"] == (
        "excluded_unanchored_top_margin_candidate"
    )
    assert pages[0]["section_marker_candidates"][2]["global_boundary_status"] == (
        "eligible_candidate"
    )



def test_link_section_ranges_rejects_duplicate_page_numbers():
    from palermo_omr.section_structure import link_section_ranges_across_pages

    page = {
        "page_number": 1,
        "section_marker_candidates": [],
        "section_identifier_candidates": [],
    }
    try:
        link_section_ranges_across_pages([page, dict(page)])
    except ValueError as error:
        assert "duplicado" in str(error)
    else:
        raise AssertionError("Expected duplicate page numbers to be rejected")


def test_link_section_ranges_rejects_boolean_page_number():
    from palermo_omr.section_structure import link_section_ranges_across_pages

    try:
        link_section_ranges_across_pages([{
            "page_number": True,
            "section_marker_candidates": [],
            "section_identifier_candidates": [],
        }])
    except ValueError as error:
        assert "entero positivo" in str(error)
    else:
        raise AssertionError("Expected boolean page number to be rejected")



def test_nearby_section_letter_remains_low_confidence_and_ambiguous(tmp_path):
    path = tmp_path / "ambiguous-letter.pdf"
    document = fitz.open()
    page = document.new_page(width=600, height=400)
    page.insert_text((100, 90), "Intro", fontsize=12)
    page.insert_text((150, 90), "B", fontsize=12)
    document.save(path)
    document.close()

    result = detect_section_candidates(
        path, 1, [StaffCandidate([100, 110, 120, 130, 140], 10, 1)],
        [_span()], dpi=72,
    )
    assert len(result["section_identifier_candidates"]) == 1
    candidate = result["section_identifier_candidates"][0]
    assert candidate.confidence <= 0.4
    assert "cifrado armónico" in candidate.warning
    assert "revisión humana" in candidate.warning



def test_global_measure_sequence_marks_single_staff_intervals_unmatched():
    from palermo_omr.section_structure import build_global_measure_sequence

    result = build_global_measure_sequence([{
        "page_number": 1,
        "staff_system_candidates": [{"system_index": 0, "staff_indices": [0]}],
        "measure_span_candidates": [{
            "staff_index": 0, "measure_index": 1, "x_start": 40, "x_end": 60,
            "width_px": 20, "confidence": 0.8,
        }],
    }])
    assert result["sequence_scope"] == "document_ordered_single_staff_intervals"
    assert result["cross_staff_aligned_candidate_count"] == 0
    assert result["single_staff_only_candidate_count"] == 1
    assert result["global_measure_candidates"][0]["alignment_status"] == (
        "single_staff_only_unmatched"
    )
    assert result["staff_measure_map"][0]["alignment_status"] == (
        "single_staff_only_unmatched"
    )


def test_global_measure_sequence_marks_multi_staff_alignment_candidate():
    from palermo_omr.section_structure import build_global_measure_sequence

    result = build_global_measure_sequence([{
        "page_number": 1,
        "staff_system_candidates": [{"system_index": 0, "staff_indices": [0, 1]}],
        "measure_span_candidates": [
            {"staff_index": 0, "measure_index": 1, "x_start": 40, "x_end": 60,
             "width_px": 20, "confidence": 0.8},
            {"staff_index": 1, "measure_index": 1, "x_start": 40, "x_end": 60,
             "width_px": 20, "confidence": 0.8},
        ],
    }])
    assert result["sequence_scope"] == "cross_staff_aligned_candidates"
    assert result["cross_staff_aligned_candidate_count"] == 1
    assert result["single_staff_only_candidate_count"] == 0
    assert result["global_measure_candidates"][0]["alignment_status"] == (
        "cross_staff_alignment_candidate"
    )
    assert all(item["staff_support"] == 2 for item in result["staff_measure_map"])



def test_section_marker_anchors_to_each_staff_in_nearest_system():
    from palermo_omr.measure_layout import StaffSystemCandidate
    from palermo_omr.section_structure import anchor_section_markers_to_measure_spans

    staves = [
        StaffCandidate([100, 110, 120, 130, 140], 10, 1),
        StaffCandidate([250, 260, 270, 280, 290], 10, 1),
        StaffCandidate([500, 510, 520, 530, 540], 10, 1),
    ]
    spans = [
        MeasureSpanCandidate(0, 1, 50, 150, 100, True, True, 0.8, "test"),
        MeasureSpanCandidate(1, 1, 50, 150, 100, True, True, 0.8, "test"),
        MeasureSpanCandidate(2, 1, 50, 150, 100, True, True, 0.8, "test"),
    ]
    systems = [
        StaffSystemCandidate(0, [0, 1], 100, 290, 0.82, "connector"),
        StaffSystemCandidate(1, [2], 500, 540, 0.45, "single"),
    ]
    anchors = anchor_section_markers_to_measure_spans(
        [{"center_x_px": 100, "center_y_px": 80}],
        staves,
        spans,
        staff_system_candidates=systems,
    )
    assert [item["staff_index"] for item in anchors] == [0, 1]
    assert all(item["system_index"] == 0 for item in anchors)
    assert all(item["anchor_scope"] == "system_candidate" for item in anchors)



def test_section_boundary_prefers_cross_staff_aligned_anchor():
    from palermo_omr.section_structure import resolve_section_range_boundaries

    resolved = resolve_section_range_boundaries(
        [{
            "section_range_id": "section-cross-staff",
            "start": {
                "page_number": 1,
                "measure_anchors": [
                    {"staff_index": 0, "measure_index_on_staff": 1,
                     "position_ratio_in_interval": 0.4, "confidence": 0.6,
                     "vertical_distance_px": 0},
                    {"staff_index": 1, "measure_index_on_staff": 1,
                     "position_ratio_in_interval": 0.5, "confidence": 0.5,
                     "vertical_distance_px": 180},
                ],
            },
            "end": None,
        }],
        {"staff_measure_map": [
            {"page_number": 1, "staff_index": 0, "measure_index_on_staff": 1,
             "global_measure_candidate": 1, "alignment_status": "single_staff_only_unmatched",
             "staff_support": 1},
            {"page_number": 1, "staff_index": 1, "measure_index_on_staff": 1,
             "global_measure_candidate": 2, "alignment_status": "cross_staff_alignment_candidate",
             "staff_support": 2},
        ]},
    )
    boundary = resolved[0]["start"]["musical_boundary_candidate"]
    assert boundary["staff_index"] == 1
    assert boundary["global_alignment_status"] == "cross_staff_alignment_candidate"
    assert boundary["staff_support"] == 2



def test_global_measure_alignment_rejects_nested_interval_with_same_center():
    from palermo_omr.section_structure import build_global_measure_sequence

    result = build_global_measure_sequence([{
        "page_number": 1,
        "staff_system_candidates": [{"system_index": 0, "staff_indices": [0, 1]}],
        "measure_span_candidates": [
            {"staff_index": 0, "measure_index": 1, "x_start": 0, "x_end": 100,
             "width_px": 100, "confidence": 0.8},
            {"staff_index": 1, "measure_index": 1, "x_start": 40, "x_end": 60,
             "width_px": 20, "confidence": 0.8},
        ],
    }])
    assert result["cross_staff_aligned_candidate_count"] == 0
    assert result["single_staff_only_candidate_count"] == 2
    assert all(item["staff_support"] == 1 for item in result["global_measure_candidates"])


def test_global_measure_alignment_accepts_close_centers_and_boundaries():
    from palermo_omr.section_structure import build_global_measure_sequence

    result = build_global_measure_sequence([{
        "page_number": 1,
        "staff_system_candidates": [{"system_index": 0, "staff_indices": [0, 1]}],
        "measure_span_candidates": [
            {"staff_index": 0, "measure_index": 1, "x_start": 0, "x_end": 100,
             "width_px": 100, "confidence": 0.8},
            {"staff_index": 1, "measure_index": 1, "x_start": 10, "x_end": 110,
             "width_px": 100, "confidence": 0.8},
        ],
    }])
    assert result["cross_staff_aligned_candidate_count"] == 1
    assert result["global_measure_candidates"][0]["staff_support"] == 2



@pytest.mark.parametrize(
    ("ratio", "position_kind", "partial"),
    [
        (-0.5, "before_measure_candidate", False),
        (0.35, "inside_measure_candidate", True),
        (1.5, "after_measure_candidate", False),
    ],
)
def test_section_boundary_preserves_partial_and_adjacent_measure_positions(
    ratio, position_kind, partial
):
    from palermo_omr.section_structure import resolve_section_range_boundaries

    resolved = resolve_section_range_boundaries(
        [{
            "section_range_id": "section-partial-boundary",
            "start": {
                "page_number": 1,
                "measure_anchors": [{
                    "staff_index": 0,
                    "measure_index_on_staff": 2,
                    "position_ratio_in_interval": ratio,
                    "confidence": 0.5,
                    "vertical_distance_px": 0,
                }],
            },
            "end": None,
        }],
        {"staff_measure_map": [{
            "page_number": 1,
            "staff_index": 0,
            "measure_index_on_staff": 2,
            "global_measure_candidate": 7,
            "alignment_status": "single_staff_only_unmatched",
            "staff_support": 1,
        }]},
    )
    boundary = resolved[0]["start"]["musical_boundary_candidate"]
    assert boundary["position_kind"] == position_kind
    assert boundary["partial_measure_boundary"] is partial
    assert boundary["global_measure_candidate"] == 7
    assert boundary["review_status"] == "pending"
