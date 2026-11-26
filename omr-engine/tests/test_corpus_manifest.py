import json
from pathlib import Path

from palermo_omr.annotation_dataset import AnnotationDataset


def test_first_real_score_is_registered_as_unannotated_draft():
    manifest_path = Path(__file__).parents[1] / "corpus" / "manifest.json"
    dataset = AnnotationDataset.from_dict(
        json.loads(manifest_path.read_text(encoding="utf-8"))
    )
    dataset.validate(require_reviewed=False)
    score = dataset.scores[0]
    assert score.score_id == "clamare-a-dios-coro"
    assert score.page_count == 3
    assert score.review_status == "draft"
    assert score.events == ()
