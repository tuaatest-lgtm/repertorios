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
    make_pdf(pdf_path, [(20, 130, "BASSES")])
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
