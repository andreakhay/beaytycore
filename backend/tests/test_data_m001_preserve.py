"""Focused DATA-M001 appearance transfer invariants. No model download needed."""

import importlib.util
from pathlib import Path
import sys

import cv2
import numpy as np
import pytest


SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "data_m001_preserve.py"
SPEC = importlib.util.spec_from_file_location("data_m001_preserve", SCRIPT)
preserve = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(preserve)
sys.path.insert(0, str(SCRIPT.parent))
import data_m001_preserve_v4 as preserve_v4


def fixture_face():
    labels = np.zeros((512, 512), np.uint8)
    cv2.ellipse(labels, (256, 245), (155, 190), 0, 0, 360, 1, -1)
    cv2.ellipse(labels, (201, 205), (26, 14), 0, 0, 360, 4, -1)
    cv2.ellipse(labels, (311, 205), (26, 14), 0, 0, 360, 5, -1)
    cv2.ellipse(labels, (201, 178), (31, 7), 0, 0, 360, 6, -1)
    cv2.ellipse(labels, (311, 178), (31, 7), 0, 0, 360, 7, -1)
    cv2.ellipse(labels, (256, 265), (18, 32), 0, 0, 360, 2, -1)
    cv2.ellipse(labels, (256, 340), (42, 13), 0, 0, 360, 10, -1)
    cv2.ellipse(labels, (256, 330), (45, 7), 0, 0, 360, 11, -1)
    cv2.ellipse(labels, (256, 352), (45, 8), 0, 0, 360, 12, -1)
    source = np.full((512, 512, 3), (48, 71, 84), np.uint8)
    source[labels == 1] = (150, 111, 91)
    source[np.isin(labels, (4, 5, 10))] = (220, 220, 211)
    source[np.isin(labels, (11, 12))] = (144, 80, 76)
    raw = source.copy()
    raw[np.isin(labels, (11, 12))] = (198, 28, 48)
    raw[(labels == 1) & (np.indices(labels.shape)[0] < 215)] = (143, 89, 119)
    return source, raw, labels


@pytest.mark.parametrize("style", sorted(preserve.STYLE))
def test_transfer_keeps_every_protected_pixel_exact(style):
    source, raw, labels = fixture_face()
    output, masks, metrics = preserve.transfer(source, raw, labels, labels, style, enhance_eyes=True)
    assert np.array_equal(output[~masks["allowed"]], source[~masks["allowed"]])
    assert metrics["changed_outside_allowed"] == 0
    assert metrics["source_eye_pixels_changed"] == 0
    assert metrics["source_nose_pixels_changed"] == 0
    assert metrics["source_mouth_pixels_changed"] == 0
    assert np.any(output[masks["lips"]] != source[masks["lips"]])


def test_unknown_style_is_rejected():
    source, raw, labels = fixture_face()
    with pytest.raises(ValueError, match="Unknown Makeup style"):
        preserve.transfer(source, raw, labels, labels, "not_a_style")


@pytest.mark.parametrize("style", sorted(preserve_v4.STRENGTH))
def test_v4_local_transfer_keeps_all_protected_pixels(style):
    source, raw, labels = fixture_face()
    output, masks, metrics = preserve_v4.transfer(source, raw, labels, labels, style)
    assert np.array_equal(output[~masks["allowed"]], source[~masks["allowed"]])
    assert metrics["changed_outside_allowed"] == 0
    assert metrics["source_eye_pixels_changed"] == 0
    assert metrics["source_nose_pixels_changed"] == 0
    assert metrics["source_mouth_pixels_changed"] == 0
    assert np.any(output[masks["lip"] > 0] != source[masks["lip"] > 0])
