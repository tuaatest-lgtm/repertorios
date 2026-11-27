import json
import pytest
from palermo_omr.glyph_labeling import initialize_glyph_manifest, label_glyph, validate_glyph_manifest

def analysis_file(tmp_path):
    path = tmp_path / "analysis.json"
    path.write_text(json.dumps({"source_pdf":"sample.pdf","status":"geometric_candidates_prototype","pages":[{"page_number":1,"notation_preamble_crop_exports":[{"staff_index":0,"candidate_bbox":[10,20,8,30],"crop_file":"notation-preamble-crops/page-001-staff-000-glyph-000.png","label":None,"label_status":"needs_human_label"}]}]}), encoding="utf-8")
    return path

def test_init_creates_pending_records_with_page_staff_and_crop_reference(tmp_path):
    manifest_path=tmp_path/"glyphs.json"
    manifest=initialize_glyph_manifest(analysis_file(tmp_path),manifest_path,score_id="score-a")
    glyph=manifest["glyphs"][0]
    assert glyph["candidate_id"]=="page-001-staff-000-glyph-000"
    assert (glyph["page_number"],glyph["staff_index"])==(1,0)
    assert glyph["label"] is None and glyph["label_status"]=="pending_human_review"
    assert manifest["pending_count"]==1
    assert validate_glyph_manifest(manifest_path)==manifest

def test_label_requires_explicit_confirmation_and_valid_label(tmp_path):
    path=tmp_path/"glyphs.json"
    initialize_glyph_manifest(analysis_file(tmp_path),path,score_id="score-a")
    with pytest.raises(ValueError,match="confirm-human-label"):
        label_glyph(path,"page-001-staff-000-glyph-000","treble_clef",annotator="reviewer",human_label_confirmed=False)
    with pytest.raises(ValueError,match="Etiqueta no permitida"):
        label_glyph(path,"page-001-staff-000-glyph-000","maybe_clef",annotator="reviewer",human_label_confirmed=True)

def test_human_label_updates_audit_fields_and_counters(tmp_path):
    path=tmp_path/"glyphs.json"
    initialize_glyph_manifest(analysis_file(tmp_path),path,score_id="score-a")
    result=label_glyph(path,"page-001-staff-000-glyph-000","treble_clef",annotator="music-reviewer",human_label_confirmed=True)
    glyph=result["glyphs"][0]
    assert glyph["label"]=="treble_clef" and glyph["label_status"]=="labeled_by_human"
    assert glyph["annotator"]=="music-reviewer" and glyph["labeled_at"]
    assert result["labeled_count"]==1 and result["pending_count"]==0
    assert validate_glyph_manifest(path)==result

def test_prevents_duplicate_labeling_and_manifest_overwrite(tmp_path):
    path=tmp_path/"glyphs.json"; source=analysis_file(tmp_path)
    initialize_glyph_manifest(source,path,score_id="score-a")
    with pytest.raises(ValueError,match="ya existe"):
        initialize_glyph_manifest(source,path,score_id="score-a")
    label_glyph(path,"page-001-staff-000-glyph-000","sharp",annotator="reviewer",human_label_confirmed=True)
    with pytest.raises(ValueError,match="ya tiene etiqueta"):
        label_glyph(path,"page-001-staff-000-glyph-000","flat",annotator="reviewer",human_label_confirmed=True)

@pytest.mark.parametrize("crop",["/tmp/glyph.png","../glyph.png","a/../../glyph.png"])
def test_rejects_unsafe_crop_paths(tmp_path,crop):
    source=analysis_file(tmp_path); data=json.loads(source.read_text())
    data["pages"][0]["notation_preamble_crop_exports"][0]["crop_file"]=crop
    source.write_text(json.dumps(data),encoding="utf-8")
    with pytest.raises(ValueError,match="ruta relativa"):
        initialize_glyph_manifest(source,tmp_path/"out.json",score_id="score-a")

def test_cli_init_label_validate(tmp_path,monkeypatch):
    from palermo_omr.glyph_annotation_cli import main
    source=analysis_file(tmp_path); manifest=tmp_path/"glyphs.json"
    monkeypatch.setattr("sys.argv",["palermo-omr-glyphs","init",str(source),"--score-id","score-a","--output",str(manifest)])
    assert main()==0
    monkeypatch.setattr("sys.argv",["palermo-omr-glyphs","label",str(manifest),"--candidate-id","page-001-staff-000-glyph-000","--label","sharp","--annotator","reviewer","--confirm-human-label"])
    assert main()==0
    monkeypatch.setattr("sys.argv",["palermo-omr-glyphs","validate",str(manifest)])
    assert main()==0



def test_model_suggestions_never_become_human_labels(tmp_path):
    from palermo_omr.glyph_labeling import GLYPH_LABELS, attach_model_suggestions, validate_glyph_manifest_data

    manifest = {
        "schema_version": "1.0",
        "score_id": "score-a",
        "label_vocabulary": sorted(GLYPH_LABELS),
        "glyph_count": 1,
        "labeled_count": 0,
        "pending_count": 1,
        "glyphs": [{
            "candidate_id": "glyph-1",
            "page_number": 1,
            "staff_index": 0,
            "candidate_bbox": [1, 2, 3, 4],
            "crop_file": "page-001-glyph-1.png",
            "label": None,
            "label_status": "pending_human_review",
            "annotator": None,
            "labeled_at": None,
        }],
    }
    manifest_path = tmp_path / "manifest.json"
    predictions_path = tmp_path / "predictions.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    predictions_path.write_text(json.dumps({
        "predictions": [{
            "score_id": "score-a",
            "candidate_id": "glyph-1",
            "label": "treble_clef",
            "candidate_label": "treble_clef",
            "decision_status": "unverified_candidate_requires_review",
            "nearest_centroid_distance": 0.25,
        }]
    }), encoding="utf-8")

    result = attach_model_suggestions(manifest_path, predictions_path)
    glyph = result["glyphs"][0]
    assert glyph["model_suggestion"]["candidate_label"] == "treble_clef"
    assert glyph["label"] is None
    assert glyph["label_status"] == "pending_human_review"
    assert glyph["annotator"] is None
    assert result["labeled_count"] == 0
    validate_glyph_manifest_data(result)
