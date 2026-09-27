import json
from pathlib import Path
import sys

from PIL import Image, ImageDraw
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from data_n001 import prepare, finalize
from train_n001_bundle import bundle


def make_selection(root: Path) -> Path:
    points = [(0.5, 0.8)] * 21
    for tip, base, x in ((4, 3, 85), (8, 7, 170), (12, 11, 255), (16, 15, 340), (20, 19, 425)):
        points[tip] = (x / 512, 120 / 512)
        points[base] = (x / 512, 200 / 512)
    rows = []
    for name, split in (("hand001", "train"), ("hand002", "validation")):
        photo = Image.new("RGB", (512, 512), (157, 122, 104) if split == "train" else (165, 118, 101))
        mask = Image.new("L", photo.size)
        draw = ImageDraw.Draw(mask)
        for x in (85, 170, 255, 340, 425):
            draw.ellipse((x-13, 120, x+13, 155), fill=255)
        photo.save(root / f"{name}.png")
        mask.save(root / f"{name}_mask.png")
        rows.append({"identity_id": name, "split": split, "source": f"{name}.png",
                     "mask": f"{name}_mask.png", "landmarks": points,
                     "source_credit": "synthetic test", "source_license": "test only"})
    selection = root / "selection.json"
    selection.write_text(json.dumps({"identities": rows}), encoding="utf-8")
    return selection


def test_dataset_review_gate_split_and_bundle(tmp_path):
    selection = make_selection(tmp_path)
    dataset = tmp_path / "data_n001"
    report = prepare(tmp_path, selection, dataset)
    assert report["pairs_rendered"] == 10
    with pytest.raises(ValueError, match="Explicit review"):
        finalize(dataset, tmp_path / "bad.zip")
    reviews_path = dataset / "manifests" / "reviews.json"
    reviews = json.loads(reviews_path.read_text(encoding="utf-8"))
    for row in reviews:
        row.update(state="ACCEPT", reviewer="test reviewer", note="test approval")
    reviews_path.write_text(json.dumps(reviews), encoding="utf-8")
    result = finalize(dataset, tmp_path / "data.zip")
    assert result["accepted_pairs"] == 10
    assert result["train_identities"] == 1
    assert result["validation_identities"] == 1
    training = bundle(dataset, tmp_path / "training.zip", 25, 10)
    assert training["status"] == "PREPARED_NOT_TRAINED"
