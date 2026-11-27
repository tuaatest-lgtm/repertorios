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
