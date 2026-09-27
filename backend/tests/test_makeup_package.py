"""Runtime packaging keeps Makeup evidence and excludes dataset portraits and Hair."""

from hashlib import sha256
import json
from pathlib import Path
import struct
import sys
from zipfile import ZipFile

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from scripts import package_makeup001_runtime as packaging


@pytest.fixture
def archive(tmp_path, monkeypatch):
    header = json.dumps({"lora.weight": {"dtype": "F16", "shape": [1], "data_offsets": [0, 2]}}).encode()
    checkpoint = struct.pack("<Q", len(header)) + header + b"\0\0"
    monkeypatch.setattr(packaging, "ADAPTER_BYTES", len(checkpoint))
    monkeypatch.setattr(packaging, "ADAPTER_SHA256", sha256(checkpoint).hexdigest())
    path = tmp_path / "training.zip"
    with ZipFile(path, "w") as z:
        z.writestr("training_summary.json", json.dumps({"success": True, "exit_code": 0,
            "highest_loss_step": 250, "final_save_logged_after_last_step": True,
            "losses": [{"step": 250, "loss": 0.1}]}))
        z.writestr("runtime.json", json.dumps({"base_model_id": packaging.MODEL_ID,
                                              "base_model_revision": packaging.MODEL_REVISION}))
        z.writestr("evaluation/metadata.json", json.dumps({"prompt_presets_sha256": packaging.PRESETS_SHA256,
                                                          "records": [{}] * 40}))
        z.writestr("train_config.yaml", "steps: 250")
        z.writestr("dataset_evidence.json", "{}")
        z.writestr("checkpoints/makeup001_250step/makeup001_250step.safetensors", checkpoint)
        z.writestr("irrelevant_hair_assets/do_not_copy.txt", "excluded")
    return path


def test_runtime_bundle_is_makeup_only_and_all_inventory_hashes_match(archive, tmp_path):
    output = tmp_path / "runtime.zip"
    result = packaging.package(archive, output)
    with ZipFile(output) as z:
        assert z.testzip() is None
        manifest = json.loads(z.read("bundle.json"))
        metadata = json.loads(z.read("adapter/metadata.json"))
        assert all(sha256(z.read(name)).hexdigest() == digest for name, digest in manifest["files"].items())
        assert metadata["training_objective"] == "general_makeup_edit"
        assert len(metadata["inference_style_ids"]) == 10
        assert "supported_style_ids" not in metadata
        assert "scripts/makeup_inference_bootstrap.py" in z.namelist()
        assert not any("hair_assets" in name or name.endswith("bare.jpg") for name in z.namelist())
    assert result["hair_assets_included"] is False
    with pytest.raises(ValueError, match="overwrite"):
        packaging.package(archive, output)


def test_runtime_package_rejects_corrupt_checkpoint(archive, tmp_path):
    with ZipFile(archive, "r") as z:
        contents = {name: z.read(name) for name in z.namelist()}
    name = "checkpoints/makeup001_250step/makeup001_250step.safetensors"
    contents[name] += b"tampered"
    with ZipFile(archive, "w") as z:
        for name, content in contents.items():
            z.writestr(name, content)
    with pytest.raises(ValueError, match="approved"):
        packaging.package(archive, tmp_path / "rejected.zip")
