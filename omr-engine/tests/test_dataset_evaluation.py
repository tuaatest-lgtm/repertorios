from fractions import Fraction

import pytest

from palermo_omr.annotation_dataset import AnnotatedScore, AnnotationDataset
from palermo_omr.dataset_evaluation import evaluate_annotation_dataset
from palermo_omr.event_evaluation import ScoreEvent


def event(event_id, onset=0, *, pitch=60, voice="soprano"):
    return ScoreEvent(
        event_id=event_id,
        page_number=1,
        staff_index=0,
        measure_index=0,
        onset_quarters=Fraction(onset),
        event_type="note",
        pitches_midi=(pitch,),
        duration_quarters=1,
        voice_id=voice,
    )


def score(score_id, digest, split, reference_events):
    return AnnotatedScore(
        score_id=score_id,
        source_sha256=digest * 64,
        page_count=1,
        split=split,
        annotation_version="1.0",
        review_status="reviewed",
        events=tuple(reference_events),
    )


def dataset():
    return AnnotationDataset("0.1", (
        score("score-a", "a", "test", [event("ref-a"), event("ref-b", 1)]),
        score("score-b", "b", "test", [event("ref-c", 0, pitch=64)]),
        score("score-c", "c", "train", [event("ref-d")]),
    ))


def test_aggregates_counts_and_attributes_micro_across_selected_scores():
    result = evaluate_annotation_dataset(
        dataset(),
        {
            "score-a": [event("pred-a"), event("pred-b", 1)],
            "score-b": [event("pred-c", 0, pitch=60)],
        },
        split="test",
    )
    assert result.score_count == 2
    assert result.true_positive == 3
    assert result.false_positive == 0
    assert result.false_negative == 0
    assert result.precision == result.recall == result.f1 == 1.0
    assert result.pitch_correct == 2
    assert result.pitch_accuracy == pytest.approx(2 / 3)
    assert len(result.per_score) == 2


def test_missing_prediction_entry_counts_all_reference_events_as_missed():
    result = evaluate_annotation_dataset(
        dataset(),
        {"score-a": [event("pred-a")]},
        split="test",
    )
    assert result.true_positive == 1
    assert result.false_negative == 2
    assert result.recall == pytest.approx(1 / 3)


def test_rejects_predictions_for_unknown_or_other_split_scores():
    with pytest.raises(ValueError, match="desconocidas"):
        evaluate_annotation_dataset(dataset(), {"not-a-score": []})
    with pytest.raises(ValueError, match="fuera de test"):
        evaluate_annotation_dataset(dataset(), {"score-c": []})


def test_rejects_missing_split_and_unreviewed_dataset():
    with pytest.raises(ValueError, match="No hay partituras"):
        evaluate_annotation_dataset(dataset(), {}, split="validation")

    draft = dataset()
    from dataclasses import replace

    draft_score = replace(draft.scores[0], review_status="draft")
    invalid = replace(draft, scores=(draft_score, *draft.scores[1:]))
    with pytest.raises(ValueError, match="aún no está revisada"):
        evaluate_annotation_dataset(invalid, {})


def test_aggregate_onset_error_uses_all_matched_events_not_mean_of_score_means():
    result = evaluate_annotation_dataset(
        dataset(),
        {
            "score-a": [event("pred-a", Fraction(1, 8)), event("pred-b", 1)],
            "score-b": [event("pred-c", Fraction(1, 8), pitch=64)],
        },
    )
    assert result.mean_onset_error_quarters == pytest.approx(1 / 12)
