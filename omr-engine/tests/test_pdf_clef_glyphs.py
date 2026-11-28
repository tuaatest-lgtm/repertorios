from pathlib import Path

import pytest

from palermo_omr.imaging import StaffCandidate
from palermo_omr.pdf_clef_glyphs import detect_embedded_pdf_clef_candidates


class _FakePage:
    def __init__(self, raw):
        self.raw = raw

    def get_text(self, kind):
        assert kind == "rawdict"
        return self.raw


class _FakeDocument:
    def __init__(self, pages):
        self.pages = pages
        self.is_encrypted = False

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def __len__(self):
        return len(self.pages)

    def __getitem__(self, index):
        return self.pages[index]


def _char(glyph, y0, y1, font="RepriseSpecialStd"):
    return {
        "blocks": [{
            "lines": [{
                "spans": [{
                    "font": font,
                    "chars": [{"c": glyph, "bbox": [10, y0, 12, y1]}],
                }]
            }]
        }]
    }


def _staffs():
    return [
        StaffCandidate([100, 110, 120, 130, 140], 10, .9),
        StaffCandidate([200, 210, 220, 230, 240], 10, .9),
    ]


def test_extracts_reprise_clef_glyphs_and_keeps_them_pending(monkeypatch, tmp_path):
    pdf_path = tmp_path / "vector.pdf"
    pdf_path.write_bytes(b"fake")
    raw = {
        "blocks": [
            {"lines": [{"spans": [{"font": "RepriseSpecialStd", "chars": [
                {"c": "°", "bbox": [10, 90, 12, 112]},
                {"c": "¢", "bbox": [10, 210, 12, 230]},
                {"c": "™", "bbox": [10, 200, 12, 220]},
            ]}]}]},
            {"lines": [{"spans": [{"font": "OtherFont", "chars": [
                {"c": "°", "bbox": [10, 90, 12, 112]},
            ]}]}]},
        ]
    }
    monkeypatch.setattr(
        "palermo_omr.pdf_clef_glyphs.fitz.open",
        lambda _path: _FakeDocument([_FakePage(raw)]),
    )

    candidates = detect_embedded_pdf_clef_candidates(pdf_path, 1, _staffs(), dpi=72)

    assert len(candidates) == 2
    assert [item.clef_candidate for item in candidates] == ["treble", "bass"]
    assert [item.staff_index for item in candidates] == [0, 1]
    assert all(item.status == "pending_human_review" for item in candidates)
    assert all(item.source == "embedded_pdf_font_glyph" for item in candidates)
    assert candidates[0].confidence == .95
    assert candidates[0].to_dict()["glyph"] == "°"


def test_marks_conflicting_and_unassigned_clef_glyphs(monkeypatch, tmp_path):
    pdf_path = tmp_path / "conflict.pdf"
    pdf_path.write_bytes(b"fake")
    raw = {
        "blocks": [{
            "lines": [{
                "spans": [{
                    "font": "RepriseSpecialStd",
                    "chars": [
                        {"c": "°", "bbox": [10, 90, 12, 112]},
                        {"c": "¢", "bbox": [10, 90, 12, 112]},
                        {"c": "°", "bbox": [10, 500, 12, 522]},
                    ],
                }]
            }]
        }]
    }
    monkeypatch.setattr(
        "palermo_omr.pdf_clef_glyphs.fitz.open",
        lambda _path: _FakeDocument([_FakePage(raw)]),
    )

    candidates = detect_embedded_pdf_clef_candidates(pdf_path, 1, _staffs(), dpi=72)

    assert [item.status for item in candidates] == [
        "conflicting_clef_glyphs", "conflicting_clef_glyphs", "unassigned_staff",
    ]
    assert candidates[-1].staff_index is None
    assert candidates[-1].confidence == .4


def test_rejects_invalid_page_dpi_mapping_and_staff_geometry(monkeypatch, tmp_path):
    pdf_path = tmp_path / "invalid.pdf"
    pdf_path.write_bytes(b"fake")
    monkeypatch.setattr(
        "palermo_omr.pdf_clef_glyphs.fitz.open",
        lambda _path: _FakeDocument([_FakePage({"blocks": []})]),
    )
    with pytest.raises(ValueError, match="page_number"):
        detect_embedded_pdf_clef_candidates(pdf_path, 0, _staffs())
    with pytest.raises(ValueError, match="dpi"):
        detect_embedded_pdf_clef_candidates(pdf_path, 1, _staffs(), dpi=30)
    with pytest.raises(ValueError, match="glyph_map"):
        detect_embedded_pdf_clef_candidates(pdf_path, 1, _staffs(), glyph_map={"ab": "treble"})
    with pytest.raises(ValueError, match="cinco líneas"):
        detect_embedded_pdf_clef_candidates(
            pdf_path, 1, [StaffCandidate([1, 2, 3], 1, .9)], dpi=72,
        )
