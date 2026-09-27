"""Run the first bounded NAILS-001-LOCAL-v1 edit-LoRA stage on Kaggle T4.

The stage stops at step 50 for held-out visual review. It never continues from
or overwrites the original NAILS-001 step-25 checkpoint, and never serves the app.
"""

import argparse
from collections import Counter
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import threading
import time
from zipfile import ZipFile

from nails001_kaggle_pilot import (TOOLKIT_COMMIT, MODEL_REVISION, checked, digest,
    model_preflight, peak_sampler, save_json, version)


DATA_SHA = "d37b68bc3e06c6ea1b1b013424dd813aafbef83db222cf9223e229d33ad105bb"
LOCAL_NAME = "nails001_local_v1"
STEPS = 50
TRACE_SOURCE_SHA_NORMALIZED_LF = "c152ef68477bb941338d0051b5e4190427e9b285485256840e5ee1c777c765d7"
ANCHOR = "                    batch_list.append(batch)\n                    batch_step += 1"
INSERT = "                    batch_list.append(batch)\n                    from nails001_local_trace import trace_batch\n                    trace_batch(step + 1, b, batch)\n                    batch_step += 1"


def verify_localized(root: Path) -> dict:
    bundle_evidence = json.loads((root / "local_bundle_evidence.json").read_text(encoding="utf-8"))
    archive = root / "DATA-N001-LOCAL-v1.zip"
    original = root / "DATA-N001-final.zip"
    if digest(archive) != bundle_evidence["localized_archive_sha256"] or digest(original) != DATA_SHA:
        raise ValueError("Localized or approved DATA-N001 archive SHA-256 mismatch")
    with ZipFile(archive) as zip_local, ZipFile(original) as zip_original:
        if zip_local.testzip() is not None or zip_original.testzip() is not None:
            raise ValueError("Dataset ZIP CRC failed")
        rows = json.loads(zip_local.read("manifests/pairs.json"))
        qa = json.loads(zip_local.read("reports/qa.json"))
        source_rows = json.loads(zip_original.read("manifests/pairs.json"))
        parent = {row["pair_id"]: row for row in source_rows}
        expected_pairs = bundle_evidence["train_pairs"] + bundle_evidence["validation_pairs"]
        if qa["source_dataset_sha256"] != DATA_SHA or qa["localized_pairs"] != expected_pairs:
            raise ValueError("Localized dataset provenance or count changed")
        if len(rows) != expected_pairs or len({row["pair_id"] for row in rows}) != expected_pairs:
            raise ValueError("Localized pair count or uniqueness changed")
        identities = {"train": set(), "validation": set()}
        counts = Counter()
        for row in rows:
            pair, split = row["pair_id"], row["split"]
            if split not in identities or row["parent_pair_id"] not in parent:
                raise ValueError(f"Invalid localized pair: {pair}")
            src = parent[row["parent_pair_id"]]
            if (src["split"], src["identity_id"], src["style_id"]) != (
                    split, row["identity_id"], row["style_id"]):
                raise ValueError(f"Localized split/identity/style mismatch: {pair}")
            if row["finger_id"] not in ("thumb", "index", "middle", "ring", "little"):
                raise ValueError(f"Invalid finger: {pair}")
            for role, key in (("reference", "reference_sha256"), ("target", "target_sha256"),
                              ("masks", "mask_sha256")):
                content = zip_local.read(f"{split}/{role}/{pair}.png")
                if sha256(content).hexdigest() != row[key]:
                    raise ValueError(f"Localized {role} hash mismatch: {pair}")
            caption = zip_local.read(f"{split}/target/{pair}.txt").decode("utf-8").strip()
            if caption != row["caption"]:
                raise ValueError(f"Caption mismatch: {pair}")
            identities[split].add(row["identity_id"])
            counts[split, row["style_id"]] += 1
        if identities["train"] & identities["validation"]:
            raise ValueError("Validation identity leakage")
        if (len(identities["train"]), len(identities["validation"])) != (16, 4):
            raise ValueError("Frozen identity counts changed")
        if any(counts[split, style] != qa["style_counts"][f"{split}/{style}"]
               for split in ("train", "validation")
               for style in ("classic_red", "nude_pink", "glossy_black", "french_tip", "pink_ombre")):
            raise ValueError("Localized style counts changed")
        if sum(counts["train", style] for style in ("classic_red", "nude_pink", "glossy_black", "french_tip", "pink_ombre")) != bundle_evidence["train_pairs"] or sum(counts["validation", style] for style in ("classic_red", "nude_pink", "glossy_black", "french_tip", "pink_ombre")) != bundle_evidence["validation_pairs"]:
            raise ValueError("Localized train/validation counts changed")
        if qa["localized_mask_pct"]["mean"] < 5 or qa["localized_mask_pct"]["min"] < 3:
            raise ValueError("Localized nail signal insufficient")
        destination = root / "data_n001_local"
        if destination.exists():
            raise ValueError("Localized extraction already exists; refusing to overwrite")
        destination.mkdir()
        zip_local.extractall(destination)
    config = (root / "train_config.yaml").read_text(encoding="utf-8")
    for required in (f"steps: {STEPS}", "save_every: 50", "gradient_accumulation: 1",
                     "data_n001_local/train/target", "data_n001_local/train/reference",
                     "flux2_klein_4b", MODEL_REVISION, LOCAL_NAME):
        if required not in config:
            raise ValueError(f"Training config missing {required}")
    (root / "nails001_local").mkdir(exist_ok=True)
    summary = {"status": "PREFLIGHT_PASS_NOT_TRAINED", "localized_archive_sha256": digest(archive),
               "approved_archive_sha256": DATA_SHA, "train_pairs": bundle_evidence["train_pairs"], "validation_pairs": bundle_evidence["validation_pairs"],
               "train_identities": sorted(identities["train"]),
               "validation_identities": sorted(identities["validation"]),
               "mask_pct": qa["localized_mask_pct"], "config_sha256": digest(root / "train_config.yaml")}
    save_json(root / "nails001_local" / "preflight.json", summary)
    return summary


def patch_trace(toolkit: Path, root: Path) -> dict:
    trainer = toolkit / "jobs/process/BaseSDTrainProcess.py"
    content = trainer.read_text(encoding="utf-8")
    original_sha = sha256(content.encode("utf-8")).hexdigest()
    if original_sha != TRACE_SOURCE_SHA_NORMALIZED_LF:
        raise ValueError(f"Pinned trainer source hash changed: {original_sha}")
    if content.count(ANCHOR) != 1:
        raise ValueError("Cannot uniquely locate training batch fetch anchor")
    trainer.write_text(content.replace(ANCHOR, INSERT), encoding="utf-8")
    shutil.copy2(root / "nails001_local_trace.py", toolkit / "nails001_local_trace.py")
    compile(trainer.read_text(encoding="utf-8"), str(trainer), "exec")
    return {"toolkit_commit": TOOLKIT_COMMIT, "original_trainer_sha256_normalized_lf": original_sha,
            "patched_trainer_sha256": digest(trainer),
            "trace_module_sha256": digest(toolkit / "nails001_local_trace.py"),
            "patch": "One call after batch_list.append(batch), before model forward"}


def install_toolkit_local(root: Path) -> dict:
    toolkit = root / "ai-toolkit"
    out = root / "nails001_local"
    if toolkit.exists():
        raise ValueError("AI Toolkit checkout already exists; fresh isolated run required")
    toolkit.mkdir()
    checked(["git", "init"], cwd=toolkit, log=out / "git_init.log")
    checked(["git", "remote", "add", "origin", "https://github.com/ostris/ai-toolkit.git"], cwd=toolkit)
    checked(["git", "fetch", "--depth", "1", "origin", TOOLKIT_COMMIT], cwd=toolkit,
            log=out / "toolkit_fetch.log")
    checked(["git", "checkout", "--detach", "FETCH_HEAD"], cwd=toolkit)
    commit = checked(["git", "rev-parse", "HEAD"], cwd=toolkit)
    if commit != TOOLKIT_COMMIT:
        raise ValueError("Wrong AI Toolkit commit")
    import torch
    torch_before, cuda_before = version("torch"), torch.version.cuda
    if not torch.cuda.is_available():
        raise RuntimeError("Kaggle GPU accelerator required")
    pinned = [f"torch=={torch_before}"]
    for package in ("torchvision", "torchaudio"):
        observed = version(package)
        if observed:
            pinned.append(f"{package}=={observed}")
    constraints = out / "kaggle_torch_constraints.txt"
    constraints.write_text("\n".join(pinned) + "\n", encoding="utf-8")
    checked([sys.executable, "-m", "pip", "install", "--constraint", str(constraints),
             "-r", str(toolkit / "requirements.txt")], log=out / "toolkit_install.log")
    observed_runtime = json.loads(checked([sys.executable, "-c", "import json,torch; print(json.dumps("
        "{'torch':torch.__version__,'cuda':torch.version.cuda,'available':torch.cuda.is_available()}))"])
        .splitlines()[-1])
    if observed_runtime != {"torch": torch_before, "cuda": cuda_before, "available": True}:
        raise RuntimeError("Dependency installation changed Kaggle Torch/CUDA")
    return {"toolkit_commit": commit, "torch_before": torch_before, "cuda_before": cuda_before,
            "constraints": pinned, "packages": {name: version(name) for name in
            ("torch", "diffusers", "transformers", "accelerate", "peft", "huggingface-hub", "bitsandbytes")}}


def validate_prepared_toolkit(root: Path) -> dict:
    """Reuse only the exact completed setup after a pre-training parent-process error."""
    toolkit = root / "ai-toolkit"
    commit = checked(["git", "rev-parse", "HEAD"], cwd=toolkit)
    if commit != TOOLKIT_COMMIT:
        raise ValueError("Existing AI Toolkit checkout has the wrong commit")
    trainer = toolkit / "jobs/process/BaseSDTrainProcess.py"
    content = trainer.read_text(encoding="utf-8")
    if content.count(INSERT) != 1 or sha256(content.replace(INSERT, ANCHOR).encode("utf-8")).hexdigest() != TRACE_SOURCE_SHA_NORMALIZED_LF:
        raise ValueError("Existing trainer trace patch differs from the guarded pinned source")
    trace_module = toolkit / "nails001_local_trace.py"
    if digest(trace_module) != digest(root / "nails001_local_trace.py"):
        raise ValueError("Existing sample trace module differs from the bundle")
    compile(content, str(trainer), "exec")
    constraints = (root / "nails001_local/kaggle_torch_constraints.txt").read_text(encoding="utf-8").splitlines()
    return {"toolkit_commit": commit, "constraints": constraints,
            "packages": {name: version(name) for name in
            ("torch", "diffusers", "transformers", "accelerate", "peft", "huggingface-hub", "bitsandbytes")},
            "trace_patch": {"original_trainer_sha256_normalized_lf": TRACE_SOURCE_SHA_NORMALIZED_LF,
                            "patched_trainer_sha256": digest(trainer),
                            "trace_module_sha256": digest(trace_module),
                            "patch": "Validated existing guarded batch trace hook"},
            "reused_completed_setup": True}


def fresh_import_runtime() -> dict:
    """Avoid NumPy ABI conflicts after pip changes packages in the parent process."""
    program = ("import json,numpy,torch,diffusers; print(json.dumps({"
               "'numpy':numpy.__version__,'torch':torch.__version__,"
               "'diffusers':diffusers.__version__,'cuda':torch.version.cuda,"
               "'available':torch.cuda.is_available(),"
               "'gpu':torch.cuda.get_device_name(0) if torch.cuda.is_available() else None}))")
    observed = json.loads(checked([sys.executable, "-c", program]).splitlines()[-1])
    if not observed["available"]:
        raise RuntimeError("Fresh Python process cannot access the Kaggle GPU")
    return observed


def train(root: Path) -> dict:
    if root.as_posix() != "/kaggle/working":
        raise ValueError("GPU training must run from /kaggle/working")
    out = root / "nails001_local"
    if not (out / "preflight.json").is_file():
        raise ValueError("Run the prepare phase first")
    if (out / "train.log").exists() or (out / "sample_trace.jsonl").exists():
        raise ValueError("Training evidence exists; refusing to overwrite")
    preflight = json.loads((out / "preflight.json").read_text(encoding="utf-8"))
    if (digest(root / "DATA-N001-LOCAL-v1.zip") != preflight["localized_archive_sha256"]
            or digest(root / "train_config.yaml") != preflight["config_sha256"]):
        raise ValueError("Dataset or training config changed since preflight")
    os.environ["HF_HOME"] = "/tmp/hf-cache"
    os.environ["HF_HUB_CACHE"] = "/tmp/hf-cache/hub"
    os.environ["CUDA_VISIBLE_DEVICES"] = "0"
    existing_toolkit = (root / "ai-toolkit").exists()
    runtime = validate_prepared_toolkit(root) if existing_toolkit else install_toolkit_local(root)
    runtime.update(model_preflight())
    if not existing_toolkit:
        runtime["trace_patch"] = patch_trace(root / "ai-toolkit", root)
    imported = fresh_import_runtime()
    runtime.update({"timestamp_utc": datetime.now(timezone.utc).isoformat(),
                    "gpu": imported["gpu"], "cuda_runtime": imported["cuda"],
                    "numpy_import_version": imported["numpy"],
                    "torch_import_version": imported["torch"],
                    "diffusers_import_version": imported["diffusers"],
                    "dataset_sha256": digest(root / "DATA-N001-LOCAL-v1.zip"),
                    "config_sha256": digest(root / "train_config.yaml"),
                    "nvidia_smi": subprocess.check_output(["nvidia-smi"], text=True)[:3000]})
    save_json(out / "runtime.json", runtime)
    seed_launcher = ("import random,runpy,sys,numpy,torch; "
                     "random.seed(1977); numpy.random.seed(1977); "
                     "torch.manual_seed(1977); torch.cuda.manual_seed_all(1977); "
                     "sys.argv=['run.py',sys.argv[1]]; "
                     "runpy.run_path('run.py',run_name='__main__')")
    command = [sys.executable, "-c", seed_launcher, str(root / "train_config.yaml")]
    environment = os.environ.copy()
    environment.update({"PYTHONHASHSEED": "1977",
        "NAILS001_LOCAL_MANIFEST": str(root / "data_n001_local/manifests/pairs.json"),
        "NAILS001_LOCAL_TARGET_ROOT": str(root / "data_n001_local/train/target"),
        "NAILS001_LOCAL_TRACE": str(out / "sample_trace.jsonl")})
    save_json(out / "training_command.json", {"command": command,
              "cwd": str(root / "ai-toolkit"), "config_sha256": digest(root / "train_config.yaml"),
              "seed": 1977, "trace_path": str(out / "sample_trace.jsonl")})
    stop, peak = threading.Event(), [0]
    monitor = threading.Thread(target=peak_sampler, args=(stop, peak), daemon=True)
    monitor.start()
    started = time.monotonic()
    with (out / "train.log").open("w", encoding="utf-8") as log:
        process = subprocess.Popen(command, cwd=root / "ai-toolkit", env=environment,
                                   stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                   text=True, bufsize=1)
        assert process.stdout is not None
        for line in process.stdout:
            log.write(line)
            log.flush()
            print(line, end="", flush=True)
            if re.search(r"(?:loss\s+is|loss\s*:)\s*[+-]?(?:nan|inf)\b", line, re.I):
                process.terminate()
                break
        code = process.wait()
    stop.set()
    monitor.join(timeout=5)
    trace_path = out / "sample_trace.jsonl"
    traced = ([json.loads(line) for line in trace_path.read_text(encoding="utf-8").splitlines()]
              if trace_path.is_file() else [])
    expected_steps = list(range(1, STEPS + 1))
    actual_steps = [row["step"] for row in traced]
    checkpoint = out / "checkpoints" / LOCAL_NAME / f"{LOCAL_NAME}.safetensors"
    optimizer = checkpoint.parent / "optimizer.pt"
    success = (code == 0 and actual_steps == expected_steps and checkpoint.is_file()
               and optimizer.is_file() and "Saved checkpoint to " in (out / "train.log").read_text())
    summary = {"status": "CHECKPOINT_READY_REVIEW_REQUIRED" if success else "TRAINING_INCOMPLETE",
        "exit_code": code, "steps_planned": STEPS, "sample_trace_count": len(traced),
        "trace_step_sequence_valid": actual_steps == expected_steps,
        "elapsed_seconds_including_load": round(time.monotonic() - started, 2),
        "whole_gpu_peak_mib_observed": peak[0],
        "checkpoint_sha256": digest(checkpoint) if checkpoint.is_file() else None,
        "optimizer_sha256": digest(optimizer) if optimizer.is_file() else None,
        "trace_sha256": digest(trace_path) if trace_path.is_file() else None,
        "train_log_sha256": digest(out / "train.log")}
    save_json(out / "training_summary.json", summary)
    if not success:
        raise RuntimeError("Training or exact sample exposure trace incomplete; inspect logs")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase", required=True, choices=("prepare", "train"))
    parser.add_argument("--root", type=Path, default=Path("/kaggle/working"))
    args = parser.parse_args()
    result = verify_localized(args.root) if args.phase == "prepare" else train(args.root)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
