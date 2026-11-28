import fitz
import pytest
from palermo_omr.pdf_glyph_validation import _maximum_cardinality_matches, evaluate_pdf_glyph_noteheads

def test_one_to_one_matching_does_not_reuse_reference_glyphs():
    matches = _maximum_cardinality_matches([(0.,0.),(.2,0.),(5.,0.)],[(.1,0.),(5.1,0.)],1.)
    assert len(matches) == 2
    assert len({item[1] for item in matches}) == 2

def test_pdf_glyph_evaluation_reports_explicit_limited_scope(tmp_path, monkeypatch):
    pdf_path=tmp_path/"score.pdf"
    document=fitz.open(); document.new_page(width=612,height=792); document.save(pdf_path); document.close()
    monkeypatch.setattr("palermo_omr.pdf_glyph_validation._glyph_centers",lambda page,font_name,glyph_char:[(10.,20.),(30.,40.)])
    analysis={"pages":[{"page_number":1,"render_dpi":300,
      "notehead_candidates":[{"center_x":10*300/72,"center_y":20*300/72,"confidence":.9},{"center_x":50*300/72,"center_y":60*300/72,"confidence":.4}],
      "hollow_notehead_candidates":[]}]}
    result=evaluate_pdf_glyph_noteheads(pdf_path,analysis,tolerance_points=1.)
    assert result["true_positive"]==1 and result["false_positive"]==1 and result["false_negative"]==1
    assert result["f1"]==pytest.approx(.5)
    assert any("No es una métrica" in item for item in result["limitations"])
    filtered=result["confidence_threshold_sweep"][1]
    assert filtered["confidence_threshold"]==.70
    assert filtered["predicted_count"]==1
    assert filtered["true_positive"]==1
    assert filtered["false_positive"]==0
    assert filtered["f1"]==pytest.approx(2/3)

def test_rejects_mismatched_pdf_and_analysis_page_counts(tmp_path):
    pdf_path=tmp_path/"score.pdf"
    document=fitz.open(); document.new_page(width=612,height=792); document.save(pdf_path); document.close()
    with pytest.raises(ValueError,match="analysis debe contener"):
        evaluate_pdf_glyph_noteheads(pdf_path,{"pages":[]})



def test_confidence_sweep_rejects_invalid_or_duplicate_thresholds(tmp_path):
    pdf_path=tmp_path/"score.pdf"
    document=fitz.open(); document.new_page(width=612,height=792); document.save(pdf_path); document.close()
    analysis={"pages":[{"page_number":1,"render_dpi":300,"notehead_candidates":[]}]}
    with pytest.raises(ValueError,match="entre 0 y 1"):
        evaluate_pdf_glyph_noteheads(pdf_path,analysis,confidence_thresholds=(1.2,))
    with pytest.raises(ValueError,match="repetir"):
        evaluate_pdf_glyph_noteheads(pdf_path,analysis,confidence_thresholds=(.7,.7))
