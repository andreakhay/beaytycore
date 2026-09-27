"""Install the Gate 1 candidate in a NEW Kaggle notebook, then run isolated probes."""

import argparse
from importlib import metadata
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from zipfile import ZIP_DEFLATED, ZipFile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.unified_gate1 import (MODEL_ID, REVISION, digest, directory_bytes, sanitized,
                                   save, storage, verify_bundle)


def download_model(output, cache):
    # Called as a fresh subprocess AFTER package installation.
    from huggingface_hub import snapshot_download
    if not os.environ.get("HF_TOKEN"):
        try:
            from kaggle_secrets import UserSecretsClient
            token = UserSecretsClient().get_secret("HF_TOKEN")
            if token:
                os.environ["HF_TOKEN"] = token
        except Exception:
            pass
    started = time.monotonic()
    before = storage(cache.parent)
    if before["free_bytes"] < 30 * 1024**3:
        raise RuntimeError("Less than 30 GiB scratch available for pinned Base, no model download started")
    snapshot = Path(snapshot_download(repo_id=MODEL_ID, revision=REVISION, cache_dir=str(cache),
        allow_patterns=["model_index.json", "scheduler/*", "tokenizer/*", "text_encoder/*", "transformer/*", "vae/*"])).resolve()
    if snapshot.name != REVISION or not (snapshot / "model_index.json").is_file():
        raise ValueError("Incorrect Base snapshot")
    index = json.loads((snapshot / "model_index.json").read_text())
    expected = {"_class_name": "Flux2KleinPipeline", "transformer": ["diffusers", "Flux2Transformer2DModel"],
                "vae": ["diffusers", "AutoencoderKLFlux2"], "text_encoder": ["transformers", "Qwen3ForCausalLM"],
                "scheduler": ["diffusers", "FlowMatchEulerDiscreteScheduler"]}
    if any(index.get(key) != value for key, value in expected.items()):
        raise ValueError("Downloaded Base component index differs")
    for component in ("transformer", "text_encoder", "vae"):
        if not list((snapshot / component).glob("*.safetensors")):
            raise ValueError(f"Base weights missing: {component}")
    save(output, {"snapshot": str(snapshot), "model_id": MODEL_ID, "revision": REVISION,
                  "model_index_sha256": digest(snapshot / "model_index.json"),
                  "download_or_cache_reuse_seconds": time.monotonic() - started,
                  "snapshot_unique_backing_bytes": directory_bytes(snapshot), "cache_bytes": directory_bytes(cache),
                  "scratch_before": before, "scratch_after": storage(cache.parent)})


def command(args, output, filename, env):
    print("GATE1 STAGE", filename, "started", flush=True)
    started = time.monotonic()
    with (output / filename).open("w", encoding="utf-8") as log:
        process = subprocess.Popen(args, cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT)
        while process.poll() is None:
            try:
                process.wait(timeout=60)
            except subprocess.TimeoutExpired:
                print("GATE1 STILL RUNNING", filename, round(time.monotonic() - started), "seconds", flush=True)
    if process.returncode:
        raise RuntimeError(f"Command exited {process.returncode}; inspect {filename}")
    print("GATE1 STAGE", filename, "completed", flush=True)


def bootstrap(output):
    if output.exists():
        raise ValueError("Use a fresh output directory, prior Gate 1 evidence will not be overwritten")
    output.mkdir(parents=True)
    setup = {"schema": "unified-gate1-setup-v1", "status": "IN_PROGRESS", "gate1_passed": False,
             "phase": "artifact preflight", "timing_seconds": {}, "storage_before_setup": storage("/tmp")}
    env = os.environ.copy()
    env.update(CUDA_VISIBLE_DEVICES="0", PYTHONUNBUFFERED="1", HF_HOME="/tmp/gate1-hf-cache")
    started = time.monotonic()
    plan = None
    try:
        plan = verify_bundle()
        setup["extracted_bundle_bytes"] = directory_bytes(ROOT)
        setup["bundle_manifest_sha256"] = digest(ROOT / "gate1_bundle.json")
        setup["phase"] = "CUDA preflight"
        probe = subprocess.run([sys.executable, "-c", "import json,torch; print(json.dumps({'torch':torch.__version__, 'cuda':torch.version.cuda, 'available':torch.cuda.is_available()}))"],
                               cwd=ROOT, env=env, capture_output=True, text=True)
        if probe.returncode:
            raise RuntimeError("Kaggle Torch import failed before installation")
        host = json.loads(probe.stdout.strip().splitlines()[-1])
        setup["host_torch"] = host
        if not host["available"]:
            raise RuntimeError("No CUDA GPU, select T4 in the NEW notebook settings")
        pins = [f"torch=={host['torch']}"]
        for name in ("torchvision", "torchaudio"):
            try:
                pins.append(f"{name}=={metadata.version(name)}")
            except metadata.PackageNotFoundError:
                pass
        constraints = output / "torch_constraints.txt"
        constraints.write_text("\n".join(pins) + "\n", encoding="utf-8")
        setup["phase"] = "dependency setup"
        dependency_start = time.monotonic()
        # Reuse the evidence-supported Hair/Makeup safeguard in this candidate only.
        try:
            version = metadata.version("torchao")
            if tuple(int(part) for part in version.split(".")[:2]) < (0, 16):
                command([sys.executable, "-m", "pip", "uninstall", "-y", "torchao"], output, "optional_torchao.log", env)
                setup["removed_optional_torchao"] = version
        except metadata.PackageNotFoundError:
            pass
        command([sys.executable, "-m", "pip", "install", "--constraint", str(constraints),
                 "-r", str(ROOT / "scripts/unified_gate1_requirements.txt")], output, "dependency_install.log", env)
        setup["timing_seconds"]["dependency_setup"] = time.monotonic() - dependency_start
        setup["phase"] = "candidate imports/version check"
        command([sys.executable, str(ROOT / "scripts/unified_gate1.py"), "--environment-only"], output, "environment.log", env)
        environment = json.loads((output / "environment.log").read_text().strip().splitlines()[-1])
        if environment["torch"] != host["torch"]:
            raise ValueError("Candidate installation changed Kaggle Torch")
        setup["environment"] = environment
        command([sys.executable, str(ROOT / "scripts/unified_gate1.py"), "--verify-only"], output, "artifact_preflight.log", env)
        setup["phase"] = "Base download"
        cache = Path("/tmp/gate1-hf-cache/hub")
        cache.parent.mkdir(parents=True, exist_ok=True)
        command([sys.executable, str(ROOT / "scripts/unified_gate1_bootstrap.py"), "--download-only",
                 "--output", str(output / "model.json"), "--cache", str(cache)], output, "Base_download.log", env)
        model = json.loads((output / "model.json").read_text())
        setup["model"] = model
        setup["timing_seconds"]["setup_before_feature_loads"] = time.monotonic() - started
        setup["phase"] = "individual feature inference"
        save(output / "setup.json", setup)
        command([sys.executable, str(ROOT / "scripts/unified_gate1.py"), "--model-dir", model["snapshot"],
                 "--output", str(output / "results"), "--setup-report", str(output / "setup.json")], output, "runner.log", env)
        setup.update(status="INFERENCE_COMPLETED_REVIEW_REQUIRED", phase="completed")
    except Exception as exc:
        categories = {"CUDA preflight": "CUDA/resource", "dependency setup": "dependency/import",
                      "candidate imports/version check": "dependency/import", "Base download": "Base loading",
                      "artifact preflight": "artifact validation", "individual feature inference": "see feature reports"}
        setup.update(status="FAILED", failure_category=categories.get(setup["phase"], "experiment harness"),
                     error={"type": type(exc).__name__, "message": sanitized(str(exc))})
    finally:
        setup["timing_seconds"]["total_bootstrap_and_probes"] = time.monotonic() - started
        setup["storage_after"] = storage("/tmp")
        save(output / "setup.json", setup)
        # Include failures, versions and partial outputs, not caches or model weights.
        with ZipFile(output / "evidence.zip", "x", ZIP_DEFLATED) as archive:
            for path in sorted(output.rglob("*")):
                if path.is_file() and path.suffix != ".zip":
                    archive.write(path, path.relative_to(output).as_posix())
            for feature, case in (plan or {}).get("features", {}).items():
                for field in ("input", "reference", "reference_record"):
                    archive.write(ROOT / case[field], f"preserved/{feature}/{field}/{Path(case[field]).name}")
        print("STATUS", setup["status"], flush=True)
        print("DOWNLOAD", output / "evidence.zip", flush=True)
    return setup


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("/kaggle/working/unified_gate1"))
    parser.add_argument("--download-only", action="store_true")
    parser.add_argument("--cache", type=Path)
    args = parser.parse_args()
    if args.download_only:
        try:
            download_model(args.output, args.cache)
        except Exception as exc:
            print(sanitized(f"Base download failed: {type(exc).__name__}: {exc}"), file=sys.stderr)
            sys.exit(1)
    else:
        status = bootstrap(args.output)
        sys.exit(0 if status["status"] == "INFERENCE_COMPLETED_REVIEW_REQUIRED" else 1)


if __name__ == "__main__":
    main()
