from palermo_omr.section_structure import build_global_measure_sequence


def test_global_measure_sequence_merges_aligned_staves_and_continues_across_pages():
    pages = [
        {
            "page_number": 2,
            "staff_system_candidates": [{"system_index": 0, "staff_indices": [0]}],
            "measure_span_candidates": [
                {"staff_index": 0, "measure_index": 1, "x_start": 10, "x_end": 110,
                 "width_px": 100, "confidence": 0.8},
            ],
        },
        {
            "page_number": 1,
            "staff_system_candidates": [
                {"system_index": 0, "staff_indices": [0, 1]},
                {"system_index": 1, "staff_indices": [2]},
            ],
            "measure_span_candidates": [
                {"staff_index": 0, "measure_index": 1, "x_start": 10, "x_end": 110,
                 "width_px": 100, "confidence": 0.8},
                {"staff_index": 1, "measure_index": 1, "x_start": 11, "x_end": 111,
                 "width_px": 100, "confidence": 0.7},
                {"staff_index": 0, "measure_index": 2, "x_start": 110, "x_end": 210,
                 "width_px": 100, "confidence": 0.8},
                {"staff_index": 1, "measure_index": 2, "x_start": 111, "x_end": 211,
                 "width_px": 100, "confidence": 0.7},
                {"staff_index": 2, "measure_index": 1, "x_start": 10, "x_end": 110,
                 "width_px": 100, "confidence": 0.6},
            ],
        },
    ]

    result = build_global_measure_sequence(pages)
    candidates = result["global_measure_candidates"]

    assert [item["global_measure_candidate"] for item in candidates] == [1, 2, 3, 4]
    assert [item["page_number"] for item in candidates] == [1, 1, 1, 2]
    assert candidates[0]["staff_support"] == 2
    assert candidates[1]["staff_support"] == 2
    assert candidates[2]["system_index"] == 1
    assert result["global_measure_candidate_count"] == 4

    refs = result["staff_measure_map"]
    assert next(item for item in refs if item["staff_index"] == 1)["global_measure_candidate"] == 1


def test_global_measure_sequence_skips_spans_without_system_membership():
    result = build_global_measure_sequence([{
        "page_number": 1,
        "staff_system_candidates": [{"system_index": 0, "staff_indices": [0]}],
        "measure_span_candidates": [
            {"staff_index": 3, "measure_index": 1, "x_start": 0, "x_end": 100,
             "width_px": 100, "confidence": 0.5},
        ],
    }])
    assert result["global_measure_candidates"] == []
    assert result["staff_measure_map"] == []


def test_section_range_boundaries_retain_partial_measure_positions():
    from palermo_omr.section_structure import resolve_section_range_boundaries

    ranges = [{
        "section_range_id": "section-1",
        "start": {
            "page_number": 1,
            "measure_anchors": [{
                "staff_index": 0, "measure_index_on_staff": 2,
                "position_ratio_in_interval": 0.35,
                "confidence": 0.5, "vertical_distance_px": 3,
            }],
        },
        "end": {
            "page_number": 2,
            "measure_anchors": [{
                "staff_index": 1, "measure_index_on_staff": 1,
                "position_ratio_in_interval": 1.0,
                "confidence": 0.6, "vertical_distance_px": 2,
            }],
        },
    }]
    sequence = {"staff_measure_map": [
        {"page_number": 1, "staff_index": 0, "measure_index_on_staff": 2,
         "global_measure_candidate": 7},
        {"page_number": 2, "staff_index": 1, "measure_index_on_staff": 1,
         "global_measure_candidate": 12},
    ]}

    result = resolve_section_range_boundaries(ranges, sequence)
    start = result[0]["start"]["musical_boundary_candidate"]
    end = result[0]["end"]["musical_boundary_candidate"]
    assert start["global_measure_candidate"] == 7
    assert start["position_kind"] == "inside_measure_candidate"
    assert start["partial_measure_boundary"] is True
    assert start["position_ratio_in_interval"] == 0.35
    assert end["global_measure_candidate"] == 12
    assert end["position_kind"] == "at_measure_end_candidate"
    assert end["partial_measure_boundary"] is False
    assert start["review_status"] == "pending"


def test_section_boundary_without_measure_anchor_remains_unresolved():
    from palermo_omr.section_structure import resolve_section_range_boundaries

    result = resolve_section_range_boundaries(
        [{"start": {"page_number": 1, "measure_anchors": []}, "end": None}],
        {"staff_measure_map": []},
    )
    assert result[0]["start"]["musical_boundary_candidate"] is None


def test_missing_barline_span_is_ambiguous_not_a_third_global_measure():
    pages = [{
        "page_number": 1,
        "staff_system_candidates": [{"system_index": 0, "staff_indices": [0, 1]}],
        "measure_span_candidates": [
            {"staff_index": 0, "measure_index": 1, "x_start": 0, "x_end": 100,
             "width_px": 100, "confidence": 0.8},
            {"staff_index": 0, "measure_index": 2, "x_start": 100, "x_end": 200,
             "width_px": 100, "confidence": 0.8},
            {"staff_index": 1, "measure_index": 1, "x_start": 0, "x_end": 200,
             "width_px": 200, "confidence": 0.7},
        ],
    }]

    result = build_global_measure_sequence(pages)

    assert result["global_measure_candidate_count"] == 2
    assert [item["global_measure_candidate"] for item in result["global_measure_candidates"]] == [1, 2]
    ambiguous = next(
        item for item in result["staff_measure_map"]
        if item["staff_index"] == 1
    )
    assert ambiguous["global_measure_candidate"] is None
    assert ambiguous["alignment_status"] == "ambiguous_spans_multiple_measure_candidates"
    assert ambiguous["possible_global_measure_candidates"] == [1, 2]


def test_ambiguous_missing_bar_span_does_not_reset_global_order_on_next_page():
    pages = [
        {
            "page_number": 1,
            "staff_system_candidates": [{"system_index": 0, "staff_indices": [0, 1]}],
            "measure_span_candidates": [
                {"staff_index": 0, "measure_index": 1, "x_start": 0, "x_end": 100,
                 "width_px": 100, "confidence": 0.8},
                {"staff_index": 0, "measure_index": 2, "x_start": 100, "x_end": 200,
                 "width_px": 100, "confidence": 0.8},
                {"staff_index": 1, "measure_index": 1, "x_start": 0, "x_end": 200,
                 "width_px": 200, "confidence": 0.7},
            ],
        },
        {
            "page_number": 2,
            "staff_system_candidates": [{"system_index": 0, "staff_indices": [0]}],
            "measure_span_candidates": [
                {"staff_index": 0, "measure_index": 1, "x_start": 10, "x_end": 110,
                 "width_px": 100, "confidence": 0.8},
            ],
        },
    ]

    result = build_global_measure_sequence(pages)

    assert [item["global_measure_candidate"] for item in result["global_measure_candidates"]] == [1, 2, 3]
    ambiguous = next(
        item for item in result["staff_measure_map"]
        if item["page_number"] == 1 and item["staff_index"] == 1
    )
    assert ambiguous["global_measure_candidate"] is None
