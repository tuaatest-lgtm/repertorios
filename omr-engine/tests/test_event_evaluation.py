from fractions import Fraction

import pytest

from palermo_omr.event_evaluation import ScoreEvent, evaluate_score_events


def event(
    event_id,
    onset,
    *,
    page=1,
    staff=0,
    measure=0,
    kind="note",
    pitches=(60,),
    duration=1,
    voice="soprano",
):
    return ScoreEvent(
        event_id=event_id,
        page_number=page,
        staff_index=staff,
        measure_index=measure,
        onset_quarters=onset,
        event_type=kind,
        pitches_midi=pitches,
        duration_quarters=duration,
        voice_id=voice,
    )


def test_exact_match_scores_detection_and_every_attribute_as_perfect():
    result = evaluate_score_events(
        [event("ref", Fraction(0))],
        [event("pred", Fraction(0))],
    )
    assert result.true_positive == 1
    assert result.false_positive == result.false_negative == 0
    assert result.f1 == 1.0
    assert result.event_type_accuracy == 1.0
    assert result.pitch_accuracy == 1.0
    assert result.duration_accuracy == 1.0
    assert result.voice_accuracy == 1.0
    assert result.mean_onset_error_quarters == 0.0


def test_onset_tolerance_is_exact_and_configurable():
    result = evaluate_score_events(
        [event("ref", Fraction(1))],
        [event("pred", Fraction(9, 8))],
    )
    assert result.true_positive == 1
    assert result.mean_onset_error_quarters == 0.125

    outside = evaluate_score_events(
        [event("ref", Fraction(1))],
        [event("pred", Fraction(5, 4))],
    )
    assert outside.true_positive == 0
    assert outside.false_positive == outside.false_negative == 1


def test_matches_without_using_pitch_duration_voice_or_event_type():
    result = evaluate_score_events(
        [event("ref", 0, kind="note", pitches=(60, 64), duration=2, voice="alto")],
        [event("pred", 0, kind="rest", pitches=(), duration=1, voice="soprano")],
    )
    assert result.true_positive == 1
    assert result.event_type_accuracy == 0.0
    assert result.pitch_accuracy == 0.0
    assert result.duration_accuracy == 0.0
    assert result.voice_accuracy == 0.0


def test_chord_pitch_sets_are_compared_as_complete_tuples():
    exact = evaluate_score_events(
        [event("ref", 0, pitches=(60, 64, 67))],
        [event("pred", 0, pitches=(60, 64, 67))],
    )
    partial = evaluate_score_events(
        [event("ref", 0, pitches=(60, 64, 67))],
        [event("pred", 0, pitches=(60, 64))],
    )
    assert exact.pitch_accuracy == 1.0
    assert partial.pitch_accuracy == 0.0



def test_rest_events_do_not_inflate_note_pitch_accuracy():
    result = evaluate_score_events(
        [
            event("ref-note", 0, kind="note", pitches=(60,)),
            event("ref-rest", 1, kind="rest", pitches=()),
        ],
        [
            event("pred-note", 0, kind="note", pitches=(62,)),
            event("pred-rest", 1, kind="rest", pitches=()),
        ],
    )
    assert result.true_positive == 2
    # La altura incorrecta de la nota vale 0/1; el silencio no suma un acierto.
    assert result.pitch_correct == 0
    assert result.pitch_accuracy == 0.0


def test_different_page_staff_or_measure_does_not_match():
    reference = [event("ref", 0)]
    for prediction in (
        event("p1", 0, page=2),
        event("p2", 0, staff=1),
        event("p3", 0, measure=1),
    ):
        result = evaluate_score_events(reference, [prediction])
        assert result.true_positive == 0


def test_unknown_prediction_onset_remains_unmatched_not_guessed():
    prediction = event("pred", None)
    result = evaluate_score_events([event("ref", 0)], [prediction])
    assert result.true_positive == 0
    assert result.unmatched_predicted_indices == (0,)
    assert result.unmatched_reference_indices == (0,)


def test_matching_minimizes_total_onset_error_after_maximizing_cardinality():
    references = [event("r0", 0), event("r1", Fraction(3, 100))]
    predictions = [event("p0", 0), event("p1", Fraction(1, 100))]
    result = evaluate_score_events(
        references,
        predictions,
        onset_tolerance_quarters=Fraction(3, 100),
    )
    assert result.true_positive == 2
    # La asignación óptima es p0->r0 y p1->r1 (error total 0.02),
    # no p0->r1 y p1->r0 (error total 0.04).
    assert [(m.predicted_index, m.reference_index) for m in result.matches] == [
        (0, 0), (1, 1)
    ]
    assert result.mean_onset_error_quarters == pytest.approx(0.01)


def test_maximum_cardinality_matching_avoids_greedy_pair_loss():
    references = [event("r0", 0), event("r1", Fraction(1, 4))]
    predictions = [
        event("p0", Fraction(1, 8)),
        event("p1", 0),
    ]
    result = evaluate_score_events(
        references,
        predictions,
        onset_tolerance_quarters=Fraction(1, 8),
    )
    assert result.true_positive == 2


def test_empty_inputs_return_undefined_metrics():
    result = evaluate_score_events([], [])
    assert result.precision is None
    assert result.recall is None
    assert result.f1 is None
    assert result.pitch_accuracy is None


def test_to_dict_serializes_fraction_fields():
    result = evaluate_score_events(
        [event("ref", Fraction(1, 3))],
        [event("pred", Fraction(1, 3))],
    )
    data = result.to_dict()
    assert data["onset_tolerance_quarters"] == "1/8"
    assert data["matches"][0]["onset_error_quarters"] == "0"


def test_validation_rejects_incomplete_reference_and_duplicate_ids():
    with pytest.raises(ValueError, match="onset conocido"):
        evaluate_score_events([event("ref", None)], [])
    with pytest.raises(ValueError, match="event_id debe ser único"):
        evaluate_score_events(
            [event("r1", 0), event("r1", 1)],
            [],
        )


def test_validation_rejects_invalid_pitch_and_nonpositive_duration():
    with pytest.raises(ValueError, match="MIDI"):
        evaluate_score_events(
            [event("ref", 0)],
            [event("pred", 0, pitches=(-1,))],
        )
    with pytest.raises(ValueError, match="mayor que cero"):
        evaluate_score_events(
            [event("ref", 0)],
            [event("pred", 0, duration=0)],
        )


def test_rests_require_empty_pitch_tuple_in_human_reference():
    with pytest.raises(ValueError, match="pitches_midi vacío"):
        evaluate_score_events(
            [event("ref", 0, kind="rest", pitches=None)],
            [],
        )
