"""Real FFHQ Makeup pair preparation and MAKEUP-001 CPU safety gates."""

from io import BytesIO
import json
from pathlib import Path
import sys
from zipfile import ZipFile

import pytest
from PIL import Image


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "notebooks"))
from data_m001_paired import digest, finalize, prepare, read_json, record_all_approval, write_json  # noqa: E402
from data_m001_package_training import package  # noqa: E402
import train_m001_kaggle as trainer  # noqa: E402
from train_m001_kaggle import prepare as prepare_training, validate_dataset  # noqa: E402
sys.path.insert(0, str(ROOT / "backend"))
from app.makeup_styles import MAKEUP_STYLES  # noqa: E402


@pytest.fixture
def inputs(tmp_path):
    ids = [f"{number:06d}" for number in range(1, 13)]
    archive = tmp_path / "FFHQ-Makeup.zip"
    metadata = {}
    with ZipFile(archive, "w") as output:
        for index, identity in enumerate(ids):
            metadata[str(int(identity))] = {"metadata": {
                "author": f"author {identity}", "photo_title": "test image",
                "photo_url": f"https://example.org/{identity}",
                "license": "Attribution License", "license_url": "https://creativecommons.org/licenses/by/2.0/"}}
            for variant_index, variant in enumerate(["bare", *(f"makeup_{n:02d}" for n in range(1, 6))]):
                image = Image.new("RGB", (512, 512),
                                  (index * 16, variant_index * 28, (index * 7 + variant_index * 9) % 255))
                stream = BytesIO()
                image.save(stream, format="JPEG")
                output.writestr(f"{identity}/{variant}.jpg", stream.getvalue())
    metadata_path = tmp_path / "ffhq.json"
    write_json(metadata_path, metadata)
    selection = {"train_ids": ids[:10], "validation_ids": ids[10:],
                 "variant_positions": [f"makeup_{n:02d}" for n in range(1, 6)],
                 "source_archive_sha256": digest(archive),
                 "ffhq_metadata_md5": digest(metadata_path, "md5"),
                 "source_dataset_license": "CC BY-NC-SA 4.0"}
    selection_path = tmp_path / "selection.json"
    write_json(selection_path, selection)
    return archive, metadata_path, selection_path


def test_preparation_keeps_identity_split_provenance_and_unlabeled_variants(inputs, tmp_path):
    archive, metadata, selection = inputs
    candidate = tmp_path / "candidate"

    result = prepare(archive, metadata, selection, candidate)
    rows = read_json(candidate / "candidate_manifest.json")["pairs"]

    assert result["pair_counts"] == {"train": 50, "validation": 10}
    assert result["split_leakage"] == "NONE"
    assert len(rows) == 60
    assert all(row["target_variant_is_style_class"] is False for row in rows)
    assert all(row["source_photo"]["author"] and row["source_photo"]["license"] for row in rows)
    assert len(list((candidate / "contact_sheets").glob("*.jpg"))) == 3
    assert {row["state"] for row in read_json(candidate / "reviews.json")["reviews"]} == {"PENDING_HUMAN_REVIEW"}


def test_finalization_requires_human_review_and_produces_trainer_layout(inputs, tmp_path):
    archive, metadata, selection = inputs
    candidate = tmp_path / "candidate"
    final = tmp_path / "final"
    prepare(archive, metadata, selection, candidate)

    with pytest.raises(ValueError, match="explicit human"):
        finalize(candidate, final)
    approval = record_all_approval(candidate, "Project Lead", "Approved fixture contact sheets")
    summary = finalize(candidate, final)

    assert approval["accepted"] == 60
    assert summary["train_pairs"] == 50
    assert summary["validation_pairs"] == 10
    assert len(list((final / "train" / "target").glob("*.txt"))) == 50
    assert len(list((final / "validation" / "target").glob("*.jpg"))) == 10
    with pytest.raises(ValueError, match="overwrite"):
        finalize(candidate, final)


def test_approval_cannot_overwrite_existing_decisions(inputs, tmp_path):
    archive, metadata, selection = inputs
    candidate = tmp_path / "candidate"
    prepare(archive, metadata, selection, candidate)
    record_all_approval(candidate, "Project Lead", "Approved fixture contact sheets")

    with pytest.raises(ValueError, match="overwrite"):
        record_all_approval(candidate, "other", "change decision")


def test_finalization_detects_tampered_target(inputs, tmp_path):
    archive, metadata, selection = inputs
    candidate = tmp_path / "candidate"
    prepare(archive, metadata, selection, candidate)
    record_all_approval(candidate, "Project Lead", "Approved fixture contact sheets")
    (candidate / "targets" / "000001" / "makeup_01.jpg").write_bytes(b"tampered")

    with pytest.raises(ValueError, match="hash mismatch"):
        finalize(candidate, tmp_path / "final")


def test_training_preflight_uses_only_final_reviewed_dataset_and_makeup_job(inputs, tmp_path, monkeypatch):
    archive, metadata, selection = inputs
    monkeypatch.setattr(trainer, "SOURCE_ARCHIVE_SHA256", digest(archive))
    candidate, final = tmp_path / "candidate", tmp_path / "final"
    prepare(archive, metadata, selection, candidate)
    record_all_approval(candidate, "Project Lead", "Approved fixture contact sheets")
    finalize(candidate, final)
    evidence = validate_dataset(final)
    result = prepare_training(final, tmp_path / "train")
    config = (tmp_path / "train" / "train_config.yaml").read_text(encoding="utf-8")

    assert evidence["pair_counts"] == {"train": 50, "validation": 10}
    assert result["status"] == "PREPARED_NOT_STARTED"
    assert 'name: "makeup001_250step"' in config
    assert "steps: 250" in config and 'dtype: "bf16"' in config
    assert f'name_or_path: "{trainer.MODEL_SNAPSHOT.as_posix()}"' in config
    assert "train001" not in config and "load_lora" not in config


def test_training_preflight_rejects_changed_review_and_bundle_is_makeup_only(inputs, tmp_path, monkeypatch):
    archive, metadata, selection = inputs
    monkeypatch.setattr(trainer, "SOURCE_ARCHIVE_SHA256", digest(archive))
    candidate, final = tmp_path / "candidate", tmp_path / "final"
    prepare(archive, metadata, selection, candidate)
    record_all_approval(candidate, "Project Lead", "Approved fixture contact sheets")
    finalize(candidate, final)
    reviews = read_json(final / "manifests" / "reviews.json")
    reviews[0]["state"] = "REJECT"
    write_json(final / "manifests" / "reviews.json", reviews)
    with pytest.raises(ValueError, match="Unreviewed"):
        validate_dataset(final)
    reviews[0]["state"] = "ACCEPT"
    write_json(final / "manifests" / "reviews.json", reviews)

    bundle = tmp_path / "makeup.zip"
    result = package(final, ROOT / "notebooks" / "train_m001_kaggle.py",
                     ROOT / "data" / "makeup" / "DATA-M001-paired" / "inference_presets.json", bundle)
    with ZipFile(bundle) as contents:
        names = contents.namelist()
    assert result["dataset_pairs"] == 60
    assert "train_m001_kaggle.py" in names
    assert not any("train001" in name or "hair" in name.lower() for name in names)


def test_inference_presets_keep_all_ten_makeup_ui_ids_without_training_classes():
    presets = read_json(ROOT / "data" / "makeup" / "DATA-M001-paired" / "inference_presets.json")
    ui_ids = {style.id for style in MAKEUP_STYLES}

    assert len(presets["styles"]) == 10
    assert {style["id"] for style in presets["styles"]} == ui_ids
    assert all(style["instruction"] and "makeup_0" not in style["instruction"] for style in presets["styles"])
    assert "identity" in presets["preservation_instruction"]
