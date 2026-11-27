import cv2
import numpy as np

from palermo_omr.imaging import StaffCandidate
from palermo_omr.rhythm_symbols import (detect_augmentation_dot_candidates, detect_rest_shape_candidates, detect_tie_slur_shape_candidates)
from palermo_omr.symbols import NoteheadCandidate


def test_detects_dot_candidate_next_to_notehead():
    image=np.full((160,260),255,dtype=np.uint8)
    cv2.ellipse(image,(100,80),(8,5),0,0,360,0,-1)
    cv2.circle(image,(116,80),2,0,-1)
    staff=StaffCandidate([60,70,80,90,100],10.0,1.0)
    head=NoteheadCandidate((92,75,16,10),100.0,80.0,0,2,.8,.9,.9)
    dots=detect_augmentation_dot_candidates(image,[staff],[head])
    assert len(dots)==1
    assert dots[0].associated_notehead_index==0


def test_rest_candidates_are_explicitly_unconfirmed():
    image=np.full((160,260),255,dtype=np.uint8)
    for y in [60,70,80,90,100]:
        cv2.line(image,(5,y),(250,y),0,1)
    cv2.rectangle(image,(120,74),(126,88),0,-1)
    staff=StaffCandidate([60,70,80,90,100],10.0,1.0)
    candidates=detect_rest_shape_candidates(image,[staff])
    assert candidates
    assert "no confirmado" in candidates[0].warning.lower()



def test_rest_candidate_proposes_half_rest_shape_near_middle_line():
    image=np.full((160,260),255,dtype=np.uint8)
    for y in [60,70,80,90,100]:
        cv2.line(image,(5,y),(250,y),0,1)
    cv2.rectangle(image,(120,78),(128,82),0,-1)
    staff=StaffCandidate([60,70,80,90,100],10.0,1.0)
    candidates=detect_rest_shape_candidates(image,[staff])
    assert candidates
    assert candidates[0].rest_type_candidate == "half_rest_shape_candidate"
    assert candidates[0].type_confidence < .5


def test_rest_candidate_proposes_whole_rest_shape_but_keeps_low_confidence():
    image=np.full((160,260),255,dtype=np.uint8)
    for y in [60,70,80,90,100]:
        cv2.line(image,(5,y),(250,y),0,1)
    cv2.rectangle(image,(120,83),(128,87),0,-1)
    staff=StaffCandidate([60,70,80,90,100],10.0,1.0)
    candidates=detect_rest_shape_candidates(image,[staff])
    assert candidates
    assert candidates[0].rest_type_candidate == "whole_rest_shape_candidate"
    assert candidates[0].type_confidence < .5



def test_detects_arc_shape_candidate_near_staff():
    image=np.full((160,260),255,dtype=np.uint8)
    for y in [60,70,80,90,100]:
        cv2.line(image,(5,y),(250,y),0,1)
    cv2.ellipse(image,(130,58),(25,6),0,0,180,0,1)
    staff=StaffCandidate([60,70,80,90,100],10.0,1.0)
    candidates=detect_tie_slur_shape_candidates(image,[staff])
    assert candidates
    assert candidates[0].staff_index == 0
    assert "no confirmado" in candidates[0].warning.lower()


def test_tie_slur_detector_rejects_empty_image():
    image=np.full((160,260),255,dtype=np.uint8)
    staff=StaffCandidate([60,70,80,90,100],10.0,1.0)
    assert detect_tie_slur_shape_candidates(image,[staff]) == []


def test_rest_detector_excludes_components_outside_staff_interior():
    image = np.full((160, 260), 255, dtype=np.uint8)
    for y in [60, 70, 80, 90, 100]:
        cv2.line(image, (5, y), (250, y), 0, 1)
    cv2.rectangle(image, (120, 105), (128, 119), 0, -1)
    staff = StaffCandidate([60, 70, 80, 90, 100], 10.0, 1.0)

    assert detect_rest_shape_candidates(image, [staff]) == []


def test_rest_detector_excludes_components_overlapping_detected_noteheads():
    image = np.full((160, 260), 255, dtype=np.uint8)
    for y in [60, 70, 80, 90, 100]:
        cv2.line(image, (5, y), (250, y), 0, 1)
    cv2.ellipse(image, (120, 80), (8, 5), 0, 0, 360, 0, -1)
    staff = StaffCandidate([60, 70, 80, 90, 100], 10.0, 1.0)
    head = NoteheadCandidate((112, 75, 16, 10), 120.0, 80.0, 0, 2, .8, .9, .9)

    assert detect_rest_shape_candidates(image, [staff], [head]) == []


def test_rest_detector_rejects_thin_stem_like_components():
    image = np.full((160, 260), 255, dtype=np.uint8)
    for y in [60, 70, 80, 90, 100]:
        cv2.line(image, (5, y), (250, y), 0, 1)
    cv2.rectangle(image, (120, 72), (121, 91), 0, -1)
    staff = StaffCandidate([60, 70, 80, 90, 100], 10.0, 1.0)

    assert detect_rest_shape_candidates(image, [staff]) == []
