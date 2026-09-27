"""DATA-M001 safety gates without a model, GPU, or external dataset."""

from hashlib import sha256
import json
from pathlib import Path
import sys

import pytest
from PIL import Image


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "notebooks"))
sys.path.insert(0, str(ROOT / "scripts"))
from data_m001_generate_kaggle import jobs, load_input, prompt  # noqa: E402
from data_m001_finalize import finalize  # noqa: E402


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


def make_inputs(tmp_path):
    config = json.loads((ROOT / "data/makeup/DATA-M001/config.json").read_text(encoding="utf-8"))
    rows = []
    for index, identity in enumerate(config["train_ids"] + config["validation_ids"]):
        source = tmp_path / "sources" / f"{identity}.jpg"
        source.parent.mkdir(exist_ok=True)
        Image.new("RGB", (512, 512), (index * 17, index * 13, index * 7)).save(source)
        rows.append({"identity_id": identity, "split": "TRAIN" if identity in config["train_ids"] else "VALIDATION",
                     "source_path": f"sources/{identity}.jpg", "source_sha256": sha256(source.read_bytes()).hexdigest(),
                     "original_ffhq_photo": {"author": "fixture", "license": "fixture"}})
    write_json(tmp_path / "config.json", config)
    write_json(tmp_path / "source_manifest.json", {"identities": rows})
    return config, rows


def test_pilot_uses_two_train_identities_and_all_ten_fixed_prompts(tmp_path):
    config, rows = make_inputs(tmp_path)

    loaded_config, manifest = load_input(tmp_path)
    pilot = jobs(loaded_config, manifest, "pilot")
    remaining = jobs(loaded_config, manifest, "remaining")

    assert len(pilot) == 20
    assert len(remaining) == 100
    assert {row["identity_id"] for row, _ in pilot} == set(config["pilot_train_ids"])
    assert {row["split"] for row, _ in pilot} == {"TRAIN"}
    assert len({style["id"] for _, style in pilot}) == 10
    assert config["prompt_version"] == "global-v2-bounded-refinement"
    assert all("Edit the supplied photograph" in prompt(config, style) for _, style in pilot)
    assert len({row["identity_id"] for row in rows}) == 12


def test_input_rejects_source_tampering_or_adapter_activation(tmp_path):
    config, _ = make_inputs(tmp_path)
    config["inference"]["lora_active"] = True
    write_json(tmp_path / "config.json", config)
    with pytest.raises(ValueError, match="LoRA"):
        load_input(tmp_path)

    config["inference"]["lora_active"] = False
    write_json(tmp_path / "config.json", config)
    (tmp_path / "sources" / f"{config['train_ids'][0]}.jpg").write_bytes(b"changed")
    with pytest.raises(ValueError, match="hash mismatch"):
        load_input(tmp_path)


def test_finalizer_rejects_pending_reviews(tmp_path):
    config, rows = make_inputs(tmp_path)
    reviews = [{"identity_id": row["identity_id"], "style_id": style["id"],
                "attempt": 1, "state": "PENDING", "reviewer": None, "note": None}
               for row in rows for style in config["styles"]]
    write_json(tmp_path / "reviews.json", {"reviews": reviews})

    with pytest.raises(ValueError, match="human ACCEPT"):
        finalize(tmp_path, tmp_path / "reviews.json", tmp_path / "final")


def test_finalizer_rejects_identity_style_review_gap(tmp_path):
    config, rows = make_inputs(tmp_path)
    reviews = [{"identity_id": row["identity_id"], "style_id": style["id"],
                "attempt": 1, "state": "ACCEPT", "reviewer": "tester", "note": "pass"}
               for row in rows for style in config["styles"]]
    write_json(tmp_path / "reviews.json", {"reviews": reviews[:-1]})

    with pytest.raises(ValueError, match="120 identity/style"):
        finalize(tmp_path, tmp_path / "reviews.json", tmp_path / "final")


def test_finalizer_writes_balanced_directional_pairs_after_explicit_review(tmp_path):
    config, rows = make_inputs(tmp_path)
    reviews = []
    for row in rows:
        for style in config["styles"]:
            identity, style_id = row["identity_id"], style["id"]
            target = tmp_path / "targets" / identity / style_id / "attempt_1.png"
            target.parent.mkdir(parents=True)
            Image.new("RGB", (4, 4), (len(reviews), 3, 7)).save(target)
            write_json(target.with_suffix(".json"), {
                "success": True, "prompt": prompt(config, style), "lora_active": False,
                "adapter_id": None, "model_revision": config["model_revision"],
                "source_sha256": row["source_sha256"], "target_sha256": sha256(target.read_bytes()).hexdigest(),
                "seed": 1977, "model_id": config["model_id"],
                "config_sha256": sha256((tmp_path / "config.json").read_bytes()).hexdigest()})
            reviews.append({"identity_id": identity, "style_id": style_id, "attempt": 1,
                            "state": "ACCEPT", "reviewer": "human reviewer", "note": "Visual checks passed"})
    write_json(tmp_path / "reviews.json", {"reviews": reviews})

    report = finalize(tmp_path, tmp_path / "reviews.json", tmp_path / "final")

    assert report["train"] == 100
    assert report["validation"] == 20
    assert (tmp_path / "final/pairs/train/003025/natural_makeup/source.jpg").is_file()
    assert (tmp_path / "final/pairs/validation/057326/natural_makeup/target.png").is_file()
