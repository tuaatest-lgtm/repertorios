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
    assert (output_dir / page_data["rhythm_overlay"]).is_file()
    assert page_data["rhythmic_event_group_candidate_count"] == len(
        page_data["rhythmic_event_group_candidates"]
    )
    assert page_data["rhythmic_event_group_candidate_count"] == page_data["rhythm_candidate_count"]
    assert all(
        item["voice_id_candidate"] is None
        for item in page_data["rhythmic_event_group_candidates"]
    )
    assert page_data["staff_voice_layer_candidate_count"] == len(
        page_data["staff_voice_layer_candidates"]
    )
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



def test_cli_redraws_overlays_after_global_header_classification(tmp_path, monkeypatch):
    pdf_path = tmp_path / "repeated-header-score.pdf"
    document = fitz.open()
    for _ in range(2):
        page = document.new_page(width=612, height=792)
        page.insert_text((100, 50), "Coro", fontsize=12)
    document.save(pdf_path)
    document.close()

    import palermo_omr.cli as cli_module
    original_draw = cli_module.draw_geometry_overlay
    observed_statuses = []

    def capture_overlay(page_image, page_data):
        observed_statuses.extend(
            item.get("global_boundary_status")
            for item in page_data.get("section_marker_candidates", [])
        )
        return original_draw(page_image, page_data)

    monkeypatch.setattr(cli_module, "draw_geometry_overlay", capture_overlay)
    output_dir = tmp_path / "header-overlay-output"
    monkeypatch.setattr(
        sys,
        "argv",
        ["palermo-omr", str(pdf_path), "--output", str(output_dir), "--dpi", "72"],
    )

    assert main() == 0
    assert observed_statuses.count("excluded_repeated_page_header_candidate") == 2
    for page_number in (1, 2):
        assert (output_dir / f"page-{page_number:03d}-geometry-overlay.png").exists()



def test_cli_applies_human_reviewed_accidental_manifest_to_pitch_candidates(tmp_path, monkeypatch):
    from palermo_omr.symbols import NoteheadCandidate

    pdf_path = tmp_path / "reviewed-pitch-score.pdf"
    document = fitz.open()
    page = document.new_page(width=612, height=792)
    for y in (250, 255, 260, 265, 270):
        page.draw_line((100, y), (550, y), color=(0, 0, 0), width=0.7)
    document.save(pdf_path)
    document.close()

    candidate = NoteheadCandidate(
        bbox=(195, 255, 205, 265), center_x=200.0, center_y=260.0,
        staff_index=0, diatonic_step_from_bottom=1,
        fill_ratio=0.8, notehead_shape_score=0.9, confidence=0.9,
    )
    monkeypatch.setattr("palermo_omr.cli.detect_notehead_candidates", lambda *args: [candidate])
    monkeypatch.setattr("palermo_omr.cli.detect_hollow_notehead_candidates", lambda *args: [])

    manifest_path = tmp_path / "pitch-review.json"
    manifest_path.write_text(json.dumps({
        "schema_version": "1",
        "pages": [{
            "page_number": 1,
            "reviewer_confirmed": True,
            "heads": [{
                "source_kind": "filled",
                "source_index": 0,
                "measure_id": "p1-s0-m1",
                "event_order": 0,
                "explicit_accidental": "natural",
            }],
        }],
    }), encoding="utf-8")
    output_dir = tmp_path / "reviewed-pitch-output"
    monkeypatch.setattr(
        sys, "argv",
        [
            "palermo-omr", str(pdf_path), "--output", str(output_dir), "--dpi", "72",
            "--staff-clefs", '{"0":"treble"}',
            "--key-signatures", '{"0":{"F":1}}',
            "--pitch-review-manifest", str(manifest_path),
        ],
    )

    assert main() == 0
    analysis = json.loads((output_dir / "analysis.json").read_text(encoding="utf-8"))
    pitch = analysis["pages"][0]["pitch_candidates"]
    assert len(pitch) == 1
    assert pitch[0]["source_index"] == 0
    assert pitch[0]["explicit_accidental"] == "natural"
    assert pitch[0]["pitch"]["midi"] == 65


def test_cli_rejects_unconfirmed_pitch_review_manifest(tmp_path, monkeypatch):
    pdf_path = tmp_path / "unconfirmed-pitch-score.pdf"
    document = fitz.open()
    document.new_page(width=612, height=792)
    document.save(pdf_path)
    document.close()

    manifest_path = tmp_path / "unconfirmed-pitch-review.json"
    manifest_path.write_text(json.dumps({
        "schema_version": "1",
        "pages": [{"page_number": 1, "reviewer_confirmed": False, "heads": []}],
    }), encoding="utf-8")
    monkeypatch.setattr(
        sys, "argv",
        ["palermo-omr", str(pdf_path), "--pitch-review-manifest", str(manifest_path)],
    )
    import pytest
    with pytest.raises(ValueError, match="confirmada"):
        main()



def test_cli_supports_opt_in_filled_notehead_confidence_filter(tmp_path, monkeypatch):
    from palermo_omr.symbols import NoteheadCandidate

    pdf_path = tmp_path / "confidence-filter-score.pdf"
    document = fitz.open()
    page = document.new_page(width=612, height=792)
    for y in (250, 255, 260, 265, 270):
        page.draw_line((100, y), (550, y), color=(0, 0, 0), width=0.7)
    document.save(pdf_path)
    document.close()

    candidates = [
        NoteheadCandidate((195, 255, 10, 5), 200, 260, 0, 1, .8, .9, .9),
        NoteheadCandidate((295, 255, 10, 5), 300, 260, 0, 1, .7, .8, .6),
    ]
    monkeypatch.setattr("palermo_omr.cli.detect_notehead_candidates", lambda *args: candidates)
    monkeypatch.setattr("palermo_omr.cli.detect_hollow_notehead_candidates", lambda *args: [])
    output_dir = tmp_path / "confidence-output"
    monkeypatch.setattr(
        sys, "argv",
        ["palermo-omr", str(pdf_path), "--output", str(output_dir), "--dpi", "72",
         "--min-notehead-confidence", "0.7"],
    )
    assert main() == 0
    analysis = json.loads((output_dir / "analysis.json").read_text(encoding="utf-8"))
    page_data = analysis["pages"][0]
    assert page_data["notehead_confidence_filter"] == .7
    assert page_data["notehead_candidate_count"] == 1
    assert page_data["notehead_candidates"][0]["confidence"] == .9


def test_notehead_confidence_filter_is_opt_in_and_validated():
    import pytest
    from palermo_omr.symbols import (
        NoteheadCandidate,
        filter_notehead_candidates_by_confidence,
    )

    candidates = [
        NoteheadCandidate((0, 0, 10, 5), 5, 2, 0, 0, .8, .9, .9),
        NoteheadCandidate((20, 0, 10, 5), 25, 2, 0, 0, .7, .8, .6),
    ]
    assert filter_notehead_candidates_by_confidence(candidates) == candidates
    assert filter_notehead_candidates_by_confidence(candidates, .7) == [candidates[0]]
    with pytest.raises(ValueError, match="entre 0 y 1"):
        filter_notehead_candidates_by_confidence(candidates, 1.2)
