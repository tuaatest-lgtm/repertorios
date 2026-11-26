from fractions import Fraction

import pytest

from palermo_omr.annotation_dataset import (
    AnnotatedScore,
    AnnotationDataset,
)


def score(
    score_id="coral-001",
    digest="a" * 64,
    *,
    split="train",
    status="reviewed",
    page_count=2,
):
    from palermo_omr.event_evaluation import ScoreEvent

    return AnnotatedScore(
        score_id=score_id,
        source_sha256=digest,
        page_count=page_count,
        split=split,
        annotation_version="1.0",
        review_status=status,
        events=(
            ScoreEvent(
                event_id="p1-s0-m0-e0",
                page_number=1,
                staff_index=0,
                measure_index=0,
                onset_quarters=Fraction(1, 3),
                event_type="note",
                pitches_midi=(60, 64, 67),
                duration_quarters=Fraction(3, 2),
                voice_id="soprano",
            ),
            ScoreEvent(
                event_id="p1-s0-m0-r0",
                page_number=1,
                staff_index=0,
                measure_index=0,
                onset_quarters=Fraction(11, 6),
                event_type="rest",
                pitches_midi=(),
                duration_quarters=Fraction(1, 2),
                voice_id="soprano",
            ),
        ),
    )


def test_valid_dataset_round_trips_exact_fractions_and_chords():
    dataset = AnnotationDataset("0.1", (score(),))
    dataset.validate()
    restored = AnnotationDataset.from_dict(dataset.to_dict())
    restored.validate()
    event = restored.scores[0].events[0]
    assert event.onset_quarters == Fraction(1, 3)
    assert event.duration_quarters == Fraction(3, 2)
    assert event.pitches_midi == (60, 64, 67)


def test_rejects_unreviewed_score_for_evaluation_dataset():
    dataset = AnnotationDataset("0.1", (score(status="draft"),))
    with pytest.raises(ValueError, match="aún no está revisada"):
        dataset.validate()


def test_draft_manifest_can_be_loaded_but_not_accepted_as_ground_truth():
    dataset = AnnotationDataset("0.1", (score(status="draft"),))
    restored = AnnotationDataset.from_dict(dataset.to_dict())
    with pytest.raises(ValueError, match="aún no está revisada"):
        restored.validate()


def test_rejects_duplicate_score_id_and_duplicate_pdf_hash():
    with pytest.raises(ValueError, match="score_id debe ser único"):
        AnnotationDataset("0.1", (score(), score(digest="b" * 64))).validate()
    with pytest.raises(ValueError, match="mismo PDF"):
        AnnotationDataset("0.1", (score(), score(score_id="coral-002"))).validate()


def test_rejects_event_outside_pdf_page_range():
    item = score(page_count=1)
    event = item.events[0]
    from dataclasses import replace

    invalid = replace(event, page_number=2)
    item = replace(item, events=(invalid,))
    with pytest.raises(ValueError, match="fuera del PDF"):
        item.validate()


def test_rejects_invalid_hash_and_unknown_split():
    with pytest.raises(ValueError, match="64 caracteres"):
        score(digest="not-a-hash").validate()
    with pytest.raises(ValueError, match="split"):
        score(split="test-ish").validate()


def test_rejects_incomplete_human_event():
    from dataclasses import replace

    item = score()
    invalid = replace(item.events[0], onset_quarters=None)
    with pytest.raises(ValueError, match="onset conocido"):
        replace(item, events=(invalid,)).validate()


def test_rejects_unknown_or_extra_manifest_fields():
    dataset = AnnotationDataset("0.1", (score(),))
    data = dataset.to_dict()
    data["untracked"] = True
    with pytest.raises(ValueError, match="requiere dataset_version"):
        AnnotationDataset.from_dict(data)
