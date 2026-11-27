import fitz
import pytest

from palermo_omr.imaging import StaffCandidate
from palermo_omr.printed_labels import extract_printed_label_candidates


def make_pdf(path, labels):
    document = fitz.open()
    page = document.new_page(width=600, height=800)
    for x, y, text in labels:
        page.insert_text((x, y), text, fontsize=12)
    document.save(path)
    document.close()


def test_extracts_known_vocal_and_instrument_labels(tmp_path):
    pdf_path = tmp_path / "labels.pdf"
    make_pdf(pdf_path, [(20, 120, "TENORS"), (20, 300, "PIANO")])
    staves = [
        StaffCandidate([100, 110, 120, 130, 140], 10.0, 1.0),
        StaffCandidate([280, 290, 300, 310, 320], 10.0, 1.0),
    ]

    results = extract_printed_label_candidates(pdf_path, 1, staves, dpi=72)

    assert [item.normalized_text for item in results] == ["TENORS", "PIANO"]
    assert [item.label_kind for item in results] == ["vocal", "instrument"]
    assert [item.staff_index for item in results] == [0, 1]
    assert all(item.association_status == "associated_candidate" for item in results)


def test_keeps_equal_distance_staff_association_ambiguous(tmp_path):
    pdf_path = tmp_path / "ambiguous.pdf"
    make_pdf(pdf_path, [(20, 137, "BASSES")])
    staves = [
        StaffCandidate([100, 110, 120, 130, 140], 10.0, 1.0),
        StaffCandidate([120, 130, 140, 150, 160], 10.0, 1.0),
    ]

    results = extract_printed_label_candidates(pdf_path, 1, staves, dpi=72)

    assert len(results) == 1
    assert results[0].association_status == "ambiguous"
    assert results[0].staff_index is None


def test_ignores_unrecognized_text(tmp_path):
    pdf_path = tmp_path / "other-text.pdf"
    make_pdf(pdf_path, [(20, 120, "Allegro"), (20, 300, "Repeat")])
    staff = [StaffCandidate([100, 110, 120, 130, 140], 10.0, 1.0)]

    assert extract_printed_label_candidates(pdf_path, 1, staff, dpi=72) == []


def test_validates_page_and_dpi(tmp_path):
    pdf_path = tmp_path / "one-page.pdf"
    make_pdf(pdf_path, [])
    with pytest.raises(ValueError, match="dpi"):
        extract_printed_label_candidates(pdf_path, 1, [], dpi=50)
    with pytest.raises(ValueError, match="page_number"):
        extract_printed_label_candidates(pdf_path, 0, [], dpi=72)
    with pytest.raises(ValueError, match="supera"):
        extract_printed_label_candidates(pdf_path, 2, [], dpi=72)


def test_recognizes_labels_with_common_score_qualifiers(tmp_path):
    pdf_path = tmp_path / "qualified.pdf"
    make_pdf(pdf_path, [
        (20, 120, "TENORS only"),
        (20, 300, "Add BASSES"),
        (20, 480, "LADIES unis."),
    ])
    staves = [
        StaffCandidate([100, 110, 120, 130, 140], 10.0, 1.0),
        StaffCandidate([280, 290, 300, 310, 320], 10.0, 1.0),
        StaffCandidate([460, 470, 480, 490, 500], 10.0, 1.0),
    ]

    results = extract_printed_label_candidates(pdf_path, 1, staves, dpi=72)

    assert [item.normalized_text for item in results] == [
        "TENORS", "BASSES", "LADIES"
    ]
    assert [item.staff_index for item in results] == [0, 1, 2]


def test_recognizes_standalone_satb_abbreviations(tmp_path):
    pdf_path = tmp_path / "satb-abbreviations.pdf"
    make_pdf(pdf_path, [
        (20, 120, "S"),
        (20, 300, "A"),
        (20, 480, "T"),
        (20, 660, "B"),
    ])
    staves = [
        StaffCandidate([100, 110, 120, 130, 140], 10.0, 1.0),
        StaffCandidate([280, 290, 300, 310, 320], 10.0, 1.0),
        StaffCandidate([460, 470, 480, 490, 500], 10.0, 1.0),
        StaffCandidate([640, 650, 660, 670, 680], 10.0, 1.0),
    ]

    results = extract_printed_label_candidates(pdf_path, 1, staves, dpi=72)

    assert [item.normalized_text for item in results] == ["S", "A", "T", "B"]
    assert [item.label_kind for item in results] == ["vocal"] * 4
    assert [item.staff_index for item in results] == [0, 1, 2, 3]
    assert all(item.association_status == "associated_candidate" for item in results)


def test_does_not_match_satb_letters_inside_other_words(tmp_path):
    pdf_path = tmp_path / "not-labels.pdf"
    make_pdf(pdf_path, [
        (20, 120, "Score"),
        (20, 300, "Allegro"),
        (20, 480, "Bassoon"),
    ])
    staff = [StaffCandidate([100, 110, 120, 130, 140], 10.0, 1.0)]

    assert extract_printed_label_candidates(pdf_path, 1, staff, dpi=72) == []


def test_ignores_bracketed_section_marker_and_harmonic_b_chord(tmp_path):
    pdf_path = tmp_path / "ambiguous-b.pdf"
    make_pdf(pdf_path, [(20, 120, "[B]"), (100, 300, "B")])
    staves = [
        StaffCandidate([100, 110, 120, 130, 140], 10.0, 1.0),
        StaffCandidate([280, 290, 300, 310, 320], 10.0, 1.0),
    ]

    assert extract_printed_label_candidates(pdf_path, 1, staves, dpi=72) == []


def test_accepts_literal_satb_abbreviation_in_left_margin(tmp_path):
    pdf_path = tmp_path / "left-margin-b.pdf"
    make_pdf(pdf_path, [(20, 120, "B")])
    staff = [StaffCandidate([100, 110, 120, 130, 140], 10.0, 1.0)]

    results = extract_printed_label_candidates(pdf_path, 1, staff, dpi=72)

    assert len(results) == 1
    assert results[0].normalized_text == "B"
    assert results[0].label_kind == "vocal"
