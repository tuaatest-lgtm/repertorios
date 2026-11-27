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



def test_cli_exports_dictionary_section_anchors(tmp_path, monkeypatch):
    pdf_path = tmp_path / "synthetic-section-score.pdf"
    document = fitz.open()
    page = document.new_page(width=612, height=792)
    page.insert_text((100, 250), "Coro", fontsize=12)
    for y in (250, 255, 260, 265, 270):
        page.draw_line((100, y), (550, y), color=(0, 0, 0), width=0.7)
    document.save(pdf_path)
    document.close()

    monkeypatch.setattr(
        "palermo_omr.cli.anchor_section_markers_to_measure_spans",
        lambda *args, **kwargs: [{
            "marker_index": 0,
            "staff_index": 0,
            "measure_index_on_staff": 1,
            "position_ratio_in_interval": 0.5,
            "review_status": "pending",
            "warning": "synthetic anchor",
        }],
    )
    output_dir = tmp_path / "section-output"
    monkeypatch.setattr(
        sys,
        "argv",
        ["palermo-omr", str(pdf_path), "--output", str(output_dir), "--dpi", "72"],
    )

    assert main() == 0
    analysis = json.loads((output_dir / "analysis.json").read_text(encoding="utf-8"))
    page_data = analysis["pages"][0]
    assert page_data["section_measure_anchor_candidate_count"] == 1
    assert page_data["section_measure_anchor_candidates"][0]["position_ratio_in_interval"] == 0.5



def test_cli_aligns_measure_intervals_across_connector_grouped_staves(tmp_path, monkeypatch):
    pdf_path = tmp_path / "synthetic-grand-staff.pdf"
    document = fitz.open()
    page = document.new_page(width=612, height=792)
    for top in (100, 250):
        for offset in (0, 10, 20, 30, 40):
            page.draw_line((40, top + offset), (580, top + offset), width=1)
        for x in (150, 300, 450):
            page.draw_line((x, top), (x, top + 40), width=2)
    page.draw_line((20, 100), (20, 290), width=2)
    document.save(pdf_path)
    document.close()

    output_dir = tmp_path / "connector-output"
    monkeypatch.setattr(
        sys,
        "argv",
        ["palermo-omr", str(pdf_path), "--output", str(output_dir), "--dpi", "72"],
    )
    assert main() == 0

    analysis = json.loads((output_dir / "analysis.json").read_text(encoding="utf-8"))
    page_data = analysis["pages"][0]
    assert [item["staff_indices"] for item in page_data["staff_system_candidates"]] == [[0, 1]]
    sequence = analysis["global_measure_sequence"]
    assert sequence["cross_staff_aligned_candidate_count"] >= 1
    assert sequence["sequence_scope"] in (
        "cross_staff_aligned_candidates", "partially_cross_staff_aligned"
    )
    assert all(
        item["staff_support"] >= 2
        for item in sequence["global_measure_candidates"]
        if item["alignment_status"] == "cross_staff_alignment_candidate"
    )
