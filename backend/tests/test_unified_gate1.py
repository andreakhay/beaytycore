"""Gate 1 contract, artifact safety, independent workers and optional telemetry."""

import base64
from io import BytesIO
import json
import os
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace
from zipfile import ZipFile

from PIL import Image
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from scripts import unified_gate1 as gate
from scripts import package_unified_gate1 as packaging
from scripts import unified_gate1_bootstrap as bootstrap


def png(color=(40, 50, 60)):
    stream = BytesIO()
    Image.new("RGB", (512, 512), color).save(stream, "PNG")
    return stream.getvalue()


@pytest.fixture
def bundle(tmp_path, monkeypatch):
    # Runtime reuse configures process env; contain it within each harness test.
    for name in ("HAIRCAPSTONE_STYLE_REGISTRY_PATH", "HAIRCAPSTONE_MODEL_DIR", "HAIRCAPSTONE_API_KEY",
                 "HAIRCAPSTONE_ADAPTER_DIRS", "MAKEUP001_MODEL_DIR", "MAKEUP001_API_KEY", "MAKEUP001_ADAPTER_DIR",
                 "NAILS001_MODEL_DIR", "NAILS001_API_KEY", "NAILS001_ADAPTER_PATH"):
        monkeypatch.setenv(name, os.environ.get(name, ""))
    plan = {"schema": gate.SCHEMA, "features": {}}
    files = {}
    for feature in gate.FEATURES:
        _, _, expected = gate.feature_contract(feature)
        source, reference, record = f"inputs/{feature}.png", f"references/{feature}.png", f"references/{feature}.json"
        for name, content in ((source, png()), (reference, png((70, 80, 90))), (record, b"{}")):
            path = tmp_path / name
            path.parent.mkdir(exist_ok=True)
            path.write_bytes(content)
            files[name] = gate.digest(path)
        plan["features"][feature] = {"input": source, "reference": reference, "reference_record": record,
            "input_sha256": files[source], "reference_sha256": files[reference], "expected": expected,
            "reference_context": {"kind": "synthetic unit fixture, never GPU evidence"},
            "settings": {"width": 512, "height": 512, "steps": 20, "guidance": 4.0, "seed": 1977,
                         "dtype": "float16", "cpu_offload": True}}
    gate.save(tmp_path / "gate1_plan.json", plan)
    files["gate1_plan.json"] = gate.digest(tmp_path / "gate1_plan.json")
    gate.save(tmp_path / "gate1_bundle.json", {"schema": gate.SCHEMA, "base_revision": gate.REVISION, "files": files})
    monkeypatch.setattr(gate, "ROOT", tmp_path)
    return tmp_path, plan


def test_bundle_verifies_fixed_inputs_and_detects_tampering(bundle):
    root, _ = bundle
    assert set(gate.verify_bundle(root)["features"]) == set(gate.FEATURES)
    (root / "inputs/nails.png").write_bytes(b"corrupt")
    with pytest.raises(ValueError, match="integrity"):
        gate.verify_bundle(root)


@pytest.mark.parametrize("name", ["../weights.bin", "/etc/passwd", "C:/file", "folder\\file", 123])
def test_bundle_paths_cannot_escape_root(tmp_path, name):
    with pytest.raises(ValueError, match="Unsafe"):
        gate.safe_path(tmp_path, name)


def test_runtime_source_bundle_rejects_manifest_mismatch(tmp_path):
    path = tmp_path / "input.bin"
    with ZipFile(path, "w") as archive:
        archive.writestr("adapter/adapter.safetensors", b"incorrect")
        archive.writestr("bundle.json", json.dumps({"schema": "test", "files": {"adapter/adapter.safetensors": "0" * 64}}))
    with pytest.raises(ValueError, match="inventory mismatch"):
        packaging.read_runtime_bundle(path, "test")


@pytest.mark.parametrize("mismatch", [None, "version", "commit"])
def test_candidate_environment_requires_the_evaluated_versions_and_git_commit(monkeypatch, mismatch):
    versions = {**gate.PINS, **{name: "test-version" for name in gate.PACKAGES if name not in gate.PINS}}
    if mismatch == "version":
        versions["transformers"] = "5.0.0"
    monkeypatch.setattr(gate.metadata, "version", versions.__getitem__)
    origin = {"vcs_info": {"commit_id": "wrong" if mismatch == "commit" else gate.DIFFUSERS_COMMIT}}
    monkeypatch.setattr(gate.metadata, "distribution", lambda *_: SimpleNamespace(read_text=lambda *_: json.dumps(origin)))
    for name in ("numpy", "diffusers", "transformers", "accelerate", "peft", "huggingface_hub", "safetensors"):
        monkeypatch.setitem(sys.modules, name, SimpleNamespace(Flux2KleinPipeline=object))
    torch = SimpleNamespace(__version__="test-version", version=SimpleNamespace(cuda="test-cuda"),
        cuda=SimpleNamespace(is_available=lambda: True, get_device_name=lambda *_: "fake GPU",
                             get_device_properties=lambda *_: SimpleNamespace(total_memory=1)))
    monkeypatch.setitem(sys.modules, "torch", torch)
    if mismatch:
        with pytest.raises(ValueError, match="mismatch|Git commit"):
            gate.environment()
    else:
        assert gate.environment()["diffusers_commit"] == gate.DIFFUSERS_COMMIT


def response(expected, raw=None):
    raw = raw or png()
    return {"status": "completed", "generator": expected["generator"],
        "image": {"data_url": "data:image/png;base64," + base64.b64encode(raw).decode(),
                  "content_type": "image/png", "width": 512, "height": 512},
        "metadata": {**{k: v for k, v in expected.items() if k != "generator"},
                     "base_model_id": gate.MODEL_ID, "base_model_revision": gate.REVISION,
                     "seed": 1977, "steps": 20, "guidance": 4.0}}


@pytest.mark.parametrize("feature", gate.FEATURES)
def test_result_requires_correct_feature_adapter_settings_and_png(feature):
    _, _, expected = gate.feature_contract(feature)
    payload = response(expected)
    assert gate.validate_result(payload, expected) == png()
    payload["metadata"]["adapter_id"] = "another-feature-adapter"
    with pytest.raises(ValueError, match="provenance"):
        gate.validate_result(payload, expected)


def test_comparison_records_differences_without_a_quality_threshold(tmp_path):
    a, b = tmp_path / "a.png", tmp_path / "b.png"
    a.write_bytes(png())
    b.write_bytes(png((41, 50, 60)))
    report = gate.compare_images(a, b)
    assert report["changed_pixels"] == 512 * 512
    assert report["mean_absolute_channel_difference"] == pytest.approx(1 / 3)
    assert report["acceptance_tolerance"] is None
    assert report["rgb_pixels_equal"] is False


@pytest.mark.parametrize("failed_feature", [None, *gate.FEATURES])
def test_orchestrator_runs_sequential_workers_and_never_hides_a_failure(bundle, failed_feature):
    root, _ = bundle
    order = []
    def launch(args, **kwargs):
        feature = args[args.index("--worker") + 1]
        output = Path(args[args.index("--output") + 1])
        order.append(feature)
        failed = feature == failed_feature
        gate.save(output / "report.json", {"feature": feature,
            "status": "FAILED" if failed else "INFERENCE_COMPLETED_REVIEW_REQUIRED", "environment": {"test": "fake subprocess"}})
        return SimpleNamespace(returncode=1 if failed else 0)
    result = gate.run(Path("unused"), root / "output", launch=launch)
    assert order == list(gate.FEATURES)
    assert result["inference_paths_completed"] is (failed_feature is None)
    assert result["gate1_passed"] is False
    assert result["gate2_started"] is False
    with ZipFile(root / "output.zip") as archive:
        assert "preserved/nails/input/nails.png" in archive.namelist()
        assert "preserved/nails/reference/nails.png" in archive.namelist()
        assert len(archive.namelist()) == len(set(archive.namelist()))
    with pytest.raises(ValueError, match="overwrite"):
        gate.run(Path("unused"), root / "output", launch=launch)


def test_timeout_is_recorded_and_next_feature_can_still_be_tested(bundle):
    root, _ = bundle
    order = []
    def launch(args, **kwargs):
        feature = args[args.index("--worker") + 1]
        order.append(feature)
        if feature == "hairstyle":
            raise subprocess.TimeoutExpired(args, kwargs["timeout"])
        output = Path(args[args.index("--output") + 1])
        gate.save(output / "report.json", {"feature": feature, "status": "INFERENCE_COMPLETED_REVIEW_REQUIRED"})
        return SimpleNamespace(returncode=0)
    result = gate.run(Path("unused"), root / "output", launch=launch)
    assert order == list(gate.FEATURES)
    assert result["results"][0]["worker_exit_code"] == "timeout"
    assert result["inference_paths_completed"] is False


def test_optional_peak_telemetry_failure_does_not_block_or_claim_zero():
    def fails(*args):
        raise RuntimeError("Invalid device argument")
    cuda = SimpleNamespace(reset_peak_memory_stats=fails, max_memory_allocated=fails)
    torch = SimpleNamespace(cuda=cuda)
    warnings = []
    with gate.optional_runtime_telemetry(torch, warnings):
        cuda.reset_peak_memory_stats(0)
        assert cuda.max_memory_allocated(0) == 0  # Only compatibility placeholder.
        assert gate.memory(torch)["torch_gpu_bytes"]["peak_allocated"] is None
    assert warnings
    assert cuda.reset_peak_memory_stats is fails


@pytest.mark.parametrize("corrupt", [False, True])
def test_bootstrap_preserves_failure_evidence_before_gpu_setup(bundle, monkeypatch, corrupt):
    root, _ = bundle
    monkeypatch.setattr(bootstrap, "ROOT", root)
    monkeypatch.setattr(bootstrap, "storage", lambda *_: {"free_bytes": 100 * 1024**3})
    calls = []
    def cuda_probe(args, **kwargs):
        calls.append(args)
        return SimpleNamespace(returncode=0, stdout=json.dumps({"torch": "fake", "cuda": None, "available": False}))
    monkeypatch.setattr(bootstrap.subprocess, "run", cuda_probe)
    if corrupt:
        (root / "inputs/nails.png").write_bytes(b"tampered")
    result = bootstrap.bootstrap(root / "bootstrap_output")
    assert result["status"] == "FAILED" and result["gate1_passed"] is False
    assert result["failure_category"] == ("artifact validation" if corrupt else "CUDA/resource")
    assert len(calls) == (0 if corrupt else 1)
    with ZipFile(root / "bootstrap_output/evidence.zip") as archive:
        assert "setup.json" in archive.namelist()
        assert len(archive.namelist()) == len(set(archive.namelist()))
        assert not any(name.endswith(".safetensors") for name in archive.namelist())


@pytest.mark.parametrize("phase,message,category", [
    ("inference", "CUDA out of memory", "CUDA/resource"),
    ("Base loading", "invalid snapshot", "Base loading"),
    ("adapter loading", "unexpected adapter keys", "adapter loading"),
    ("output/provenance", "wrong hash", "output/provenance"),
])
def test_failure_category_preserves_the_failed_boundary(phase, message, category):
    assert gate.failure_category(phase, RuntimeError(message)) == category


def test_failure_evidence_redacts_secret_values(monkeypatch):
    monkeypatch.setenv("HF_TOKEN", "test-secret-not-a-real-token")
    assert "test-secret-not-a-real-token" not in gate.sanitized("failed: test-secret-not-a-real-token")
    message = gate.sanitized("https://user:password@example.test/file?signature=private")
    assert "password" not in message and "private" not in message


@pytest.mark.parametrize("feature", gate.FEATURES)
@pytest.mark.parametrize("failed_phase", [None, "Base loading", "adapter loading", "inference"])
def test_worker_reuses_actual_feature_runtime_calls_with_a_fake_gpu(bundle, monkeypatch, feature, failed_phase):
    root, plan = bundle
    runtime_class, _, expected = gate.feature_contract(feature)
    # True GPU/artifact boundaries are faked; generate and its response stay real.
    calls = []
    class Pipe:
        @classmethod
        def from_pretrained(cls, model, **kwargs):
            if failed_phase == "Base loading":
                raise RuntimeError("fake Base compatibility failure")
            calls.append(("Base", kwargs))
            return cls()
        def enable_model_cpu_offload(self, **kwargs):
            calls.append(("offload", kwargs))
        def load_lora_weights(self, *args, **kwargs):
            if failed_phase == "adapter loading":
                raise RuntimeError("fake adapter compatibility failure")
            calls.append(("adapter", kwargs))
        def __call__(self, **kwargs):
            if failed_phase == "inference":
                raise RuntimeError("fake inference compatibility failure")
            calls.append(("inference", kwargs))
            return SimpleNamespace(images=[Image.new("RGB", (512, 512), (70, 80, 90))])
    class Generator:
        def __init__(self, device):
            assert device == "cuda"
        def manual_seed(self, seed):
            assert seed == 1977
            return self
    cuda = SimpleNamespace(is_available=lambda: True, reset_peak_memory_stats=lambda *_: None,
        max_memory_allocated=lambda *_: 100, memory_allocated=lambda *_: 100,
        memory_reserved=lambda *_: 200, max_memory_reserved=lambda *_: 200)
    torch = SimpleNamespace(cuda=cuda, float16="FP16", Generator=Generator)
    monkeypatch.setitem(sys.modules, "torch", torch)
    monkeypatch.setitem(sys.modules, "diffusers", SimpleNamespace(Flux2KleinPipeline=Pipe))
    monkeypatch.setattr(gate, "environment", lambda: {"test": "fake GPU, not live evidence"})
    monkeypatch.setattr(gate, "feature_contract", lambda name: (runtime_class, lambda: None, expected))
    if feature == "hairstyle":
        import scripts.kaggle_inference_server as server
        monkeypatch.setattr(server, "read_adapter_metadata", lambda *_: {
            "supported_style_ids": ["crew_cut"], "base_model_id": gate.MODEL_ID,
            "base_model_revision": gate.REVISION, "experiment": "TRAIN-001", "training_steps": 250,
            "checkpoint_sha256": expected["adapter_sha256"]})
    elif feature == "makeup":
        import scripts.makeup_inference_server as server
        monkeypatch.setattr(server, "verify_adapter", lambda *_: None)
    else:
        import scripts.nails001_local_inference_server as server
        monkeypatch.setattr(server, "verify_adapter", lambda *_: None)
    model = root / gate.REVISION
    model.mkdir()
    (model / "model_index.json").write_text("{}")
    output = root / "worker_output"
    output.mkdir()
    exit_code = gate.worker(feature, model, output)
    report = json.loads((output / "report.json").read_text())
    if failed_phase:
        assert exit_code == 1
        assert report["status"] == "FAILED"
        assert report["failure_category"] == failed_phase
        assert not (output / "candidate.png").exists()
        return
    assert exit_code == 0
    assert report["status"] == "INFERENCE_COMPLETED_REVIEW_REQUIRED"
    inference = next(value for kind, value in calls if kind == "inference")
    assert inference["prompt"] == expected["prompt"]
    assert inference["num_inference_steps"] == 20 and inference["guidance_scale"] == 4.0
    assert sum(kind == "Base" for kind, _ in calls) == 1
    assert next(value for kind, value in calls if kind == "Base") == {"torch_dtype": "FP16", "local_files_only": True}
    assert next(value for kind, value in calls if kind == "offload") == {"gpu_id": 0}
    assert "Base_load" in report["timing_seconds"] and "adapter_load" in report["timing_seconds"]
