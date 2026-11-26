import json

import fitz
import pytest

from palermo_omr.annotation_dataset import AnnotatedScore, AnnotationDataset
from palermo_omr.annotation_cli import (
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
