"""CPU gates for the isolated source-anchored Makeup inpaint pilot."""

from pathlib import Path
import sys

import numpy as np
import pytest


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "notebooks"))
from data_m001_inpaint_prepare import REGION_WEIGHTS, soft_mask, soft_mask_v2  # noqa: E402
from data_m001_inpaint_kaggle import run  # noqa: E402


def face_labels():
    labels = np.zeros((512, 512), dtype=np.uint8)
    labels[90:440, 110:400] = 1
    labels[190:210, 165:220] = 4
    labels[190:210, 290:345] = 5
    labels[270:315, 240:270] = 2
    labels[350:363, 205:305] = 11
    labels[364:375, 205:305] = 12
    labels[230:250, 200:270] = 13
    labels[180:185, 160:220] = 6
    labels[180:185, 290:350] = 7
    labels[363:364, 205:305] = 10
    return labels


@pytest.mark.parametrize("style_id", REGION_WEIGHTS)
def test_soft_mask_retains_feather_and_protects_anatomy(style_id):
    labels = face_labels()
    eye = np.ones((512, 512), np.float32)
    cheek = lip = brow = np.zeros_like(eye)
    lip[labels == 11] = 1
    brow[labels == 6] = 1
    mask = soft_mask(labels, eye, cheek, lip, brow, REGION_WEIGHTS[style_id], style_id)
    assert np.any((mask > 0) & (mask < 255))
    assert np.all(mask[np.isin(labels, (0, 2, 4, 5, 10, 13))] == 0)
    assert mask[355, 250] > 0


def test_generation_requires_successful_load_gate(tmp_path, monkeypatch):
    import data_m001_inpaint_kaggle as kaggle
    inputs = tmp_path / "inputs"
    inputs.mkdir()
    (inputs / "plan.json").write_text("{}", encoding="utf-8")
    monkeypatch.setattr(kaggle, "validate", lambda _: ({"jobs": []}, "frozen-plan-hash"))
    with pytest.raises(ValueError, match="successful load-only verification"):
        run(inputs, tmp_path / "results", "generate")


@pytest.mark.parametrize("style_id,prior", [("natural_makeup", .50), ("soft_glam", .78),
                                              ("smoky_glam", .93)])
def test_v2_undoes_previous_eye_strength_before_inpaint_opacity(style_id, prior):
    labels = face_labels()
    eye = np.zeros((512, 512), np.float32)
    eye[165:220, 145:360] = prior
    blank = np.zeros_like(eye)
    fields = (eye, blank, blank, blank)
    strengths = dict(eye=prior, cheek=.67, lip=.68, brow=.25)
    old = soft_mask(labels, *fields, REGION_WEIGHTS[style_id], style_id)
    new = soft_mask_v2(labels, fields, strengths, style_id)
    assert new.max() > old.max()
    assert np.all(new[np.isin(labels, (0, 2, 4, 5, 10, 13))] == 0)


def test_v2_red_lip_has_inward_feather_at_open_mouth_boundary():
    labels = face_labels()
    lip = np.zeros((512, 512), np.float32)
    lip[np.isin(labels, (11, 12))] = .92
    blank = np.zeros_like(lip)
    mask = soft_mask_v2(labels, (blank, blank, lip, blank),
                        dict(eye=.22, cheek=.28, lip=.92, brow=.10), "classic_red_lip")
    assert mask[350, 250] < mask[357, 250]
    assert mask[363, 250] == 0  # mouth opening
    assert mask[360, 250] < mask[357, 250]
