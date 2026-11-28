import json

import fitz
import pytest

from palermo_omr.annotation_dataset import AnnotatedScore, AnnotationDataset
from palermo_omr.annotation_cli import (
    review_section_package,
    main,
    confirm_score_review,
    initialize_score_manifest,
    validate_manifest,
)


def make_pdf(path):
    doc = fitz.open()
    doc.new_page(width=300, height=400)
    doc.new_page(width=300, height=400)
    doc.save(path)
    doc.close()


def test_init_registers_pdf_hash_and_page_count_as_unreviewed_draft(tmp_path):
    pdf = tmp_path / "score.pdf"
    manifest = tmp_path / "dataset.json"
    make_pdf(pdf)
    dataset = initialize_score_manifest(
        pdf, manifest, score_id="score-01", split="test"
    )
    score = dataset.scores[0]
    assert score.page_count == 2
    assert len(score.source_sha256) == 64
    assert score.review_status == "draft"
    assert score.events == ()
    assert validate_manifest(manifest, allow_drafts=True) == dataset
    with pytest.raises(ValueError, match="aún no está revisada"):
        validate_manifest(manifest)


def test_init_rejects_duplicate_pdf_and_duplicate_score_id(tmp_path):
    pdf = tmp_path / "score.pdf"
    manifest = tmp_path / "dataset.json"
    make_pdf(pdf)
    initialize_score_manifest(pdf, manifest, score_id="score-01", split="train")
    with pytest.raises(ValueError, match="mismo PDF"):
        initialize_score_manifest(pdf, manifest, score_id="score-02", split="test")
    other_pdf = tmp_path / "other.pdf"
    make_pdf(other_pdf)
    with pytest.raises(ValueError, match="score_id debe ser único"):
        initialize_score_manifest(
            other_pdf, manifest, score_id="score-01", split="test"
        )


def test_review_requires_explicit_human_confirmation_and_nonempty_events(tmp_path):
    manifest = tmp_path / "dataset.json"
    dataset = AnnotationDataset("0.1", (
        AnnotatedScore(
            score_id="score-01", source_sha256="a" * 64, page_count=1,
            split="test", annotation_version="1.0", review_status="draft",
            events=(),
        ),
    ))
    manifest.write_text(json.dumps(dataset.to_dict()), encoding="utf-8")
    with pytest.raises(ValueError, match="confirmación humana"):
        confirm_score_review(manifest, "score-01", human_review_confirmed=False)
    with pytest.raises(ValueError, match="sin eventos"):
        confirm_score_review(manifest, "score-01", human_review_confirmed=True)


def test_review_marks_only_selected_score_after_explicit_confirmation(tmp_path):
    from fractions import Fraction
    from palermo_omr.event_evaluation import ScoreEvent

    manifest = tmp_path / "dataset.json"
    score = AnnotatedScore(
        score_id="score-01", source_sha256="a" * 64, page_count=1,
        split="test", annotation_version="1.0", review_status="draft",
        events=(ScoreEvent(
            event_id="e1", page_number=1, staff_index=0, measure_index=0,
            onset_quarters=Fraction(0), event_type="note", pitches_midi=(60,),
            duration_quarters=Fraction(1), voice_id="soprano",
        ),),
    )
    dataset = AnnotationDataset("0.1", (score,))
    manifest.write_text(json.dumps(dataset.to_dict()), encoding="utf-8")
    reviewed = confirm_score_review(
        manifest, "score-01", human_review_confirmed=True
    )
    assert reviewed.scores[0].review_status == "reviewed"
    assert validate_manifest(manifest).scores[0].review_status == "reviewed"


def test_init_rejects_missing_or_invalid_pdf(tmp_path):
    with pytest.raises(ValueError, match="No existe"):
        initialize_score_manifest(
            tmp_path / "missing.pdf", tmp_path / "dataset.json",
            score_id="x", split="train",
        )
    invalid_pdf = tmp_path / "invalid.pdf"
    invalid_pdf.write_text("not a pdf")
    with pytest.raises(ValueError, match="No se pudo abrir"):
        initialize_score_manifest(
            invalid_pdf, tmp_path / "dataset.json",
            score_id="x", split="train",
        )


def test_import_events_populates_draft_without_approving_it(tmp_path):
    from palermo_omr.annotation_cli import import_score_events

    manifest = tmp_path / "dataset.json"
    events_file = tmp_path / "events.json"
    dataset = AnnotationDataset("0.1", (
        AnnotatedScore(
            score_id="score-01", source_sha256="a" * 64, page_count=1,
            split="test", annotation_version="1.0", review_status="draft",
            events=(),
        ),
    ))
    manifest.write_text(json.dumps(dataset.to_dict()), encoding="utf-8")
    events_file.write_text(json.dumps([{
        "event_id": "e1", "page_number": 1, "staff_index": 0,
        "measure_index": 0, "onset_quarters": "1/2",
        "event_type": "note", "pitches_midi": [60, 64],
        "duration_quarters": "3/2", "voice_id": "piano-right",
    }]), encoding="utf-8")
    imported = import_score_events(manifest, "score-01", events_file)
    event = imported.scores[0].events[0]
    assert event.pitches_midi == (60, 64)
    assert event.onset_quarters.numerator == 1
    assert event.duration_quarters.numerator == 3
    assert imported.scores[0].review_status == "draft"


def test_import_events_rejects_duplicate_or_reviewed_score(tmp_path):
    from dataclasses import replace
    from palermo_omr.annotation_cli import import_score_events

    manifest = tmp_path / "dataset.json"
    events_file = tmp_path / "events.json"
    dataset = AnnotationDataset("0.1", (
        AnnotatedScore(
            score_id="score-01", source_sha256="a" * 64, page_count=1,
            split="test", annotation_version="1.0", review_status="draft",
            events=(),
        ),
    ))
    manifest.write_text(json.dumps(dataset.to_dict()), encoding="utf-8")
    events_file.write_text("[]", encoding="utf-8")
    with pytest.raises(ValueError, match="lista JSON no vacía"):
        import_score_events(manifest, "score-01", events_file)

    reviewed = replace(dataset.scores[0], review_status="reviewed")
    manifest.write_text(
        json.dumps(AnnotationDataset("0.1", (reviewed,)).to_dict()),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="ya revisada"):
        import_score_events(manifest, "score-01", events_file)


def test_evaluate_cli_adapter_writes_micro_metrics_and_per_score(tmp_path):
    from fractions import Fraction
    from palermo_omr.annotation_cli import evaluate_manifest
    from palermo_omr.event_evaluation import ScoreEvent

    manifest = tmp_path / "dataset.json"
    predictions = tmp_path / "predictions.json"
    reference = ScoreEvent(
        event_id="ref", page_number=1, staff_index=0, measure_index=0,
        onset_quarters=Fraction(0), event_type="note", pitches_midi=(60,),
        duration_quarters=Fraction(1), voice_id="soprano",
    )
    score = AnnotatedScore(
        score_id="score-01", source_sha256="a" * 64, page_count=1,
        split="test", annotation_version="1.0", review_status="reviewed",
        events=(reference,),
    )
    manifest.write_text(
        json.dumps(AnnotationDataset("0.1", (score,)).to_dict()),
        encoding="utf-8",
    )
    predictions.write_text(json.dumps({"score-01": [{
        "event_id": "pred", "page_number": 1, "staff_index": 0,
        "measure_index": 0, "onset_quarters": "0",
        "event_type": "note", "pitches_midi": [60],
        "duration_quarters": "1", "voice_id": "soprano",
    }]}), encoding="utf-8")
    report = evaluate_manifest(manifest, predictions, split="test")
    assert report["f1"] == 1.0
    assert report["pitch_accuracy"] == 1.0
    assert report["per_score"][0]["score_id"] == "score-01"


def test_evaluate_cli_adapter_rejects_malformed_predictions(tmp_path):
    from palermo_omr.annotation_cli import evaluate_manifest

    manifest = tmp_path / "dataset.json"
    predictions = tmp_path / "predictions.json"
    score = AnnotatedScore(
        score_id="score-01", source_sha256="a" * 64, page_count=1,
        split="test", annotation_version="1.0", review_status="reviewed",
        events=(),
    )
    manifest.write_text(
        json.dumps(AnnotationDataset("0.1", (score,)).to_dict()),
        encoding="utf-8",
    )
    predictions.write_text('{"score-01":[{"event_id":"missing-fields"}]}')
    with pytest.raises(ValueError, match="campos ausentes"):
        evaluate_manifest(manifest, predictions)



def test_review_section_package_requires_confirmation_and_writes_decisions(tmp_path):
    # Import local explícito: mantiene el adaptador bajo prueba ligado a esta prueba.
    from palermo_omr.annotation_cli import review_section_package
    package_path = tmp_path / "review-package.json"
    decisions_path = tmp_path / "decisions.json"
    output_path = tmp_path / "reviewed-package.json"
    package = {
        "global_section_range_candidates": [{
            "section_range_id": "section-1",
            "start": {"musical_boundary_candidate": {"page_number": 1}},
            "end": {"musical_boundary_candidate": {"page_number": 1}},
            "review_status": "pending",
        }],
        "summary": {
            "global_section_range_candidate_count": 1,
            "pending_global_section_range_candidate_count": 1,
        },
    }
    package_path.write_text(json.dumps(package), encoding="utf-8")
    decisions_path.write_text(json.dumps([{
        "section_range_id": "section-1", "decision": "accepted", "notes": "Revisado visualmente"
    }]), encoding="utf-8")

    with pytest.raises(ValueError, match="confirmación humana"):
        review_section_package(
            package_path, decisions_path, output_path,
            human_review_confirmed=False,
        )
    updated = review_section_package(
        package_path, decisions_path, output_path,
        human_review_confirmed=True,
    )
    assert updated["global_section_range_candidates"][0]["review_status"] == "accepted"
    assert json.loads(output_path.read_text(encoding="utf-8")) == updated



def test_review_sections_cli_command_applies_human_decision(tmp_path, monkeypatch):
    package_path = tmp_path / "package.json"
    decisions_path = tmp_path / "decisions.json"
    output_path = tmp_path / "reviewed.json"
    package_path.write_text(json.dumps({
        "global_section_range_candidates": [{
            "section_range_id": "section-cli",
            "start": {"musical_boundary_candidate": {"page_number": 1}},
            "end": {"musical_boundary_candidate": {"page_number": 1}},
            "review_status": "pending",
        }],
        "summary": {
            "global_section_range_candidate_count": 1,
            "pending_global_section_range_candidate_count": 1,
        },
    }), encoding="utf-8")
    decisions_path.write_text(json.dumps([{
        "section_range_id": "section-cli", "decision": "accepted"
    }]), encoding="utf-8")
    monkeypatch.setattr(
        "sys.argv",
        ["palermo-omr-dataset", "review-sections", str(package_path),
         "--decisions", str(decisions_path), "--output", str(output_path),
         "--confirm-human-review"],
    )
    assert main() == 0
    result = json.loads(output_path.read_text(encoding="utf-8"))
    assert result["global_section_range_candidates"][0]["review_status"] == "accepted"


def test_import_events_preserves_visual_candidate_evidence(tmp_path):
    from palermo_omr.annotation_cli import import_score_events

    manifest = tmp_path / "manifest.json"
    events_file = tmp_path / "events.json"
    dataset = AnnotationDataset("0.1", (
        AnnotatedScore(
            score_id="score-evidence", source_sha256="b" * 64, page_count=1,
            split="validation", annotation_version="1.0", review_status="draft",
            events=(),
        ),
    ))
    manifest.write_text(json.dumps(dataset.to_dict()), encoding="utf-8")
    events_file.write_text(json.dumps([{
        "event_id": "e1", "page_number": 1, "staff_index": 0,
        "measure_index": 0, "onset_quarters": "1/3",
        "event_type": "note", "pitches_midi": [60],
        "duration_quarters": "3/2", "voice_id": "soprano",
        "source_candidate_ids": ["p1-filled_notehead-3", "p1-staff-1"],
    }]), encoding="utf-8")

    review_package = tmp_path / "review-package.json"
    review_package.write_text('{"package_version":"1"}', encoding="utf-8")
    imported = import_score_events(
        manifest, "score-evidence", events_file,
        review_package_path=review_package,
    )
    event = imported.scores[0].events[0]
    assert event.source_candidate_ids == ("p1-filled_notehead-3", "p1-staff-1")
    assert imported.scores[0].review_status == "draft"


def test_import_events_requires_review_package_for_visual_evidence(tmp_path):
    from palermo_omr.annotation_cli import import_score_events

    manifest = tmp_path / "manifest.json"
    events_file = tmp_path / "events.json"
    dataset = AnnotationDataset("0.1", (AnnotatedScore(
        score_id="score-evidence", source_sha256="e" * 64, page_count=1,
        split="validation", annotation_version="1.0", review_status="draft",
        events=(),
    ),))
    manifest.write_text(json.dumps(dataset.to_dict()), encoding="utf-8")
    events_file.write_text(json.dumps([{
        "event_id": "e1", "page_number": 1, "staff_index": 0,
        "measure_index": 0, "onset_quarters": "0",
        "event_type": "note", "pitches_midi": [60],
        "duration_quarters": "1", "voice_id": "soprano",
        "source_candidate_ids": ["p1-notehead-1"],
    }]), encoding="utf-8")
    with pytest.raises(ValueError, match="Debe proporcionar --review-package"):
        import_score_events(manifest, "score-evidence", events_file)
