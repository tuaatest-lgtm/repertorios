import json
import sys

import fitz

from palermo_omr.cli import main
from palermo_omr.review_package import build_review_package


def test_cli_exports_printed_labels_and_identity_evidence_for_review(tmp_path, monkeypatch):
    pdf_path = tmp_path / "synthetic-choir-score.pdf"
    document = fitz.open()
    page = document.new_page(width=612, height=792)
    page.insert_text((30, 260), "Soprano", fontsize=12)
    for y in (250, 255, 260, 265, 270):
        page.draw_line((100, y), (550, y), color=(0, 0, 0), width=0.7)
    document.save(pdf_path)
    document.close()

    output_dir = tmp_path / "output"
    monkeypatch.setattr(
        sys,
        "argv",
        ["palermo-omr", str(pdf_path), "--output", str(output_dir), "--dpi", "72"],
    )

    assert main() == 0

    analysis = json.loads((output_dir / "analysis.json").read_text(encoding="utf-8"))
    page_data = analysis["pages"][0]
    assert page_data["printed_label_candidate_count"] == 1
    label = page_data["printed_label_candidates"][0]
    assert label["normalized_text"] == "SOPRANO"
    assert label["association_status"] == "associated_candidate"
    assert page_data["staff_identity_evidence_count"] == 1
    evidence = page_data["staff_identity_evidence"][0]
    assert evidence["kind"] == "printed_voice_label"
    assert evidence["source"] == "visual_candidate"
    assert (output_dir / page_data["geometry_overlay"]).is_file()

    package = build_review_package(analysis, score_id="synthetic-choir-score")
    other = package["pages"][0]["other_candidates"]
    assert any(item["family"] == "printed_label" for item in other)
    assert any(item["family"] == "staff_identity_evidence" for item in other)
