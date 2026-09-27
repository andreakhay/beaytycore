"""Run the bounded NAILS-001 edit-LoRA pilot in an authenticated Kaggle GPU notebook.

The input is the immutable DATA-N001-final.zip inside the pilot handoff archive.
This script never publishes an adapter or changes the application runtime.
"""

import argparse
from collections import Counter
from datetime import datetime, timezone
from hashlib import sha256
import importlib.metadata
import json
import math
import os
from pathlib import Path
import re
import subprocess
import sys
import threading
import time
from zipfile import ZipFile, ZIP_DEFLATED


DATA_SHA256 = "d37b68bc3e06c6ea1b1b013424dd813aafbef83db222cf9223e229d33ad105bb"
TOOLKIT_COMMIT = "a8dfcf7d7e2b38ccc7b2fb68ece9c6358e61e7a7"
MODEL = "black-forest-labs/FLUX.2-klein-base-4B"
MODEL_REVISION = "a3b4f4849157f664bdbc776fd7453c2783562f4d"
STYLES = {"classic_red", "nude_pink", "glossy_black", "french_tip", "pink_ombre"}
STEPS = 25
EVAL_SEED = 1977


def digest(path: Path) -> str:
    value = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def save_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def version(name: str) -> str | None:
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return None


def checked(command: list[str], *, cwd: Path | None = None, log: Path | None = None) -> str:
    result = subprocess.run(command, cwd=cwd, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, text=True)
    if log:
        log.write_text(result.stdout, encoding="utf-8")
    if result.returncode:
        raise RuntimeError(f"Command failed ({result.returncode}): {command[:3]}; see {log}")
    return result.stdout.strip()


def inspect_data(root: Path) -> dict:
    manifest = root / "manifests" / "pairs.json"
    qa_path = root / "reports" / "qa.json"
    rows, qa = read_json(manifest), read_json(qa_path)
    if qa.get("status") != "FINALIZED_REVIEWED" or qa.get("review_mode") != "explicit_human_review":
        raise ValueError("DATA-N001 review gate is not accepted")
    if len(rows) != 100 or qa.get("accepted_pairs") != 100:
        raise ValueError("Approved DATA-N001 pair count changed")
    identities = {"train": set(), "validation": set()}
    counts: Counter = Counter()
    image_hashes: dict[tuple[str, str], str] = {}
    for row in rows:
        split, identity, style, pair = (row[key] for key in ("split", "identity_id", "style_id", "pair_id"))
        if split not in identities or style not in STYLES or row["review_status"] != "ACCEPT":
            raise ValueError(f"Invalid split, style, or review status: {pair}")
        identities[split].add(identity)
        counts[split, style] += 1
        source_key = (split, identity)
        if source_key in image_hashes and image_hashes[source_key] != row["reference_sha256"]:
            raise ValueError(f"Multiple source images for identity {identity}")
        image_hashes[source_key] = row["reference_sha256"]
        for folder, field in (("reference", "reference_sha256"), ("target", "target_sha256"),
                              ("masks", "mask_sha256")):
            path = root / split / folder / f"{pair}.png"
            if not path.is_file() or digest(path) != row[field]:
                raise ValueError(f"Missing or changed {folder}: {pair}")
        caption = (root / split / "target" / f"{pair}.txt").read_text(encoding="utf-8").strip()
        if caption != row["caption"] or "preserv" not in caption.lower():
            raise ValueError(f"Invalid edit caption: {pair}")
    if len(identities["train"]) != 16 or len(identities["validation"]) != 4:
        raise ValueError("Frozen identity counts changed")
    if identities["train"] & identities["validation"]:
        raise ValueError("Training and validation identities overlap")
    if any(counts[split, style] != expected for split, expected in (("train", 16), ("validation", 4))
           for style in STYLES):
        raise ValueError("Five-style identity coverage changed")
    return {"dataset_archive_sha256": DATA_SHA256, "pairs": len(rows),
            "train_identities": sorted(identities["train"]),
            "validation_identities": sorted(identities["validation"]),
            "style_counts": {f"{split}/{style}": counts[split, style]
                             for split in ("train", "validation") for style in sorted(STYLES)},
            "manifest_sha256": digest(manifest), "qa_sha256": digest(qa_path)}


def prepare(root: Path) -> dict:
    archive = root / "DATA-N001-final.zip"
    if digest(archive) != DATA_SHA256:
        raise ValueError("Approved DATA-N001 archive SHA-256 mismatch")
    with ZipFile(archive) as source:
        if source.testzip() is not None:
            raise ValueError("Approved DATA-N001 archive CRC failed")
        names = source.namelist()
        if any(Path(name).is_absolute() or ".." in Path(name).parts for name in names):
            raise ValueError("Unexpected archive path")
        destination = root / "data_n001"
        if not (destination / "manifests" / "pairs.json").is_file():
            destination.mkdir(exist_ok=True)
            source.extractall(destination)
    data = root / "data_n001"
    evidence = inspect_data(data)
    config = root / "train_config.yaml"
    if not config.is_file():
        raise ValueError("Bundled training config missing")
    config_text = config.read_text(encoding="utf-8")
    for required in (f"steps: {STEPS}", "save_every: 25", "control_path:",
                     "flux2_klein_4b", MODEL_REVISION):
        if required not in config_text:
            raise ValueError(f"Training config missing {required}")
    for source_path, expected_path in (("data_n001/train/target", "data_n001/train/target"),
                                       ("data_n001/train/reference", "data_n001/train/reference")):
        if source_path not in config_text or not (root / expected_path).is_dir():
            raise ValueError(f"Training dataset path mismatch: {source_path}")
    evidence["training_config_sha256"] = digest(config)
    save_json(root / "nails001" / "preflight_data.json", evidence)
    return evidence


def install_toolkit(root: Path) -> dict:
    toolkit = root / "ai-toolkit"
    if not toolkit.exists():
        toolkit.mkdir()
        checked(["git", "init"], cwd=toolkit, log=root / "nails001" / "git_init.log")
        checked(["git", "remote", "add", "origin", "https://github.com/ostris/ai-toolkit.git"], cwd=toolkit)
        checked(["git", "fetch", "--depth", "1", "origin", TOOLKIT_COMMIT], cwd=toolkit,
                log=root / "nails001" / "toolkit_fetch.log")
        checked(["git", "checkout", "--detach", "FETCH_HEAD"], cwd=toolkit)
    commit = checked(["git", "rev-parse", "HEAD"], cwd=toolkit)
    if commit != TOOLKIT_COMMIT:
        raise ValueError(f"Wrong AI Toolkit revision: {commit}")
    torch_before = version("torch")
    import torch
    cuda_before = torch.version.cuda
    if not torch.cuda.is_available():
        raise RuntimeError("Kaggle GPU accelerator is required")
    constraints = root / "nails001" / "kaggle_torch_constraints.txt"
    pinned = [f"torch=={torch_before}"]
    for package in ("torchvision", "torchaudio"):
        observed = version(package)
        if observed:
            pinned.append(f"{package}=={observed}")
    constraints.write_text("\n".join(pinned) + "\n", encoding="utf-8")
    checked([sys.executable, "-m", "pip", "install", "--constraint", str(constraints),
             "-r", str(toolkit / "requirements.txt")], log=root / "nails001" / "toolkit_install.log")
    checked_runtime = json.loads(checked([sys.executable, "-c", "import json,torch; print(json.dumps("
        "{'torch':torch.__version__,'cuda':torch.version.cuda,'available':torch.cuda.is_available()}))"])
        .splitlines()[-1])
    if checked_runtime != {"torch": torch_before, "cuda": cuda_before, "available": True}:
        raise RuntimeError("Toolchain installation changed PyTorch/CUDA; stop before training")
    return {"toolkit_commit": commit, "torch_before": torch_before, "cuda_before": cuda_before,
            "constraints": pinned, "packages": {name: version(name) for name in
            ("torch", "diffusers", "transformers", "accelerate", "peft", "huggingface-hub", "bitsandbytes")}}


def model_preflight() -> dict:
    if not os.environ.get("HF_TOKEN"):
        try:
            from kaggle_secrets import UserSecretsClient
            token = UserSecretsClient().get_secret("HF_TOKEN")
            if token:
                os.environ["HF_TOKEN"] = token
        except Exception:  # Missing or ungranted Kaggle secret; public access may still work.
            pass
    from huggingface_hub import HfApi, hf_hub_download
    revision = HfApi().model_info(MODEL, revision=MODEL_REVISION).sha
    if revision != MODEL_REVISION:
        raise ValueError("Base revision mismatch")
    model_file = Path(hf_hub_download(repo_id=MODEL, filename="flux-2-klein-base-4b.safetensors",
                                      revision=MODEL_REVISION, cache_dir="/tmp/hf-cache/hub"))
    if MODEL_REVISION not in model_file.parts:
        raise ValueError("Base weight file is not in the pinned snapshot")
    return {"base_model": MODEL, "base_revision": revision,
            "base_weight_sha256": digest(model_file), "base_weight_path": str(model_file)}


def peak_sampler(stop: threading.Event, peak: list[int]) -> None:
    while not stop.is_set():
        result = subprocess.run(["nvidia-smi", "--query-gpu=memory.used",
                                 "--format=csv,noheader,nounits"], capture_output=True, text=True)
        if result.returncode == 0:
            for line in result.stdout.splitlines():
                try:
                    peak[0] = max(peak[0], int(line.strip()))
                except ValueError:
                    pass
        stop.wait(2)


def train(root: Path) -> dict:
    data_evidence = prepare(root)
    out = root / "nails001"
    if (out / "train.log").exists():
        raise ValueError("Existing train.log; refusing to overwrite pilot")
    os.environ["HF_HOME"] = "/tmp/hf-cache"
    os.environ["HF_HUB_CACHE"] = "/tmp/hf-cache/hub"
    os.environ["CUDA_VISIBLE_DEVICES"] = "0"
    runtime = install_toolkit(root)
    runtime.update(model_preflight())
    import torch
    runtime.update({"timestamp_utc": datetime.now(timezone.utc).isoformat(),
                    "python": sys.version, "gpu": torch.cuda.get_device_name(0),
                    "cuda_runtime": torch.version.cuda,
                    "nvidia_smi": checked(["nvidia-smi"], log=out / "nvidia_smi.txt")[:2000],
                    "dataset": data_evidence})
    save_json(out / "runtime.json", runtime)
    seed_launcher = ("import random,runpy,sys,numpy,torch; "
                     "random.seed(1977); numpy.random.seed(1977); "
                     "torch.manual_seed(1977); torch.cuda.manual_seed_all(1977); "
                     "sys.argv=['run.py',sys.argv[1]]; "
                     "runpy.run_path('run.py',run_name='__main__')")
    command = [sys.executable, "-c", seed_launcher, str((root / "train_config.yaml").resolve())]
    os.environ["PYTHONHASHSEED"] = "1977"
    save_json(out / "training_command.json", {"command": command,
        "cwd": str((root / "ai-toolkit").resolve()), "config_sha256": digest(root / "train_config.yaml"),
        "initial_rng_seed": 1977, "seed_scope": "Python, NumPy and Torch before AI Toolkit entrypoint"})
    stop, peak = threading.Event(), [0]
    monitor = threading.Thread(target=peak_sampler, args=(stop, peak), daemon=True)
    monitor.start()
    start = time.monotonic()
    losses = []
    stopped_for = None
    try:
        with (out / "train.log").open("w", encoding="utf-8") as log:
            process = subprocess.Popen(command, cwd=root / "ai-toolkit", env=os.environ.copy(),
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
            assert process.stdout is not None
            for line in process.stdout:
                log.write(line)
                log.flush()
                print(line, end="", flush=True)
                if re.search(r"(?:loss\s+is|loss\s*:)\s*[+-]?(?:nan|inf)\b", line, re.I):
                    stopped_for = "nonfinite loss"
                    process.terminate()
                    break
                for match in re.finditer(rf"\b(\d+)/{STEPS}\b[^\r\n]*?loss:\s*([+-]?\d+(?:\.\d+)?(?:e[+-]?\d+)?)", line, re.I):
                    value = float(match.group(2))
                    if math.isfinite(value):
                        losses.append({"step": int(match.group(1)), "loss": value,
                                       "elapsed_seconds": round(time.monotonic() - start, 2)})
            try:
                code = process.wait(timeout=30 if stopped_for else None)
            except subprocess.TimeoutExpired:
                process.kill()
                code = process.wait()
    finally:
        stop.set()
        monitor.join(timeout=5)
    checkpoints = sorted((out / "checkpoints").rglob("*.safetensors"))
    optimizers = sorted((out / "checkpoints").rglob("optimizer.pt"))
    log_text = (out / "train.log").read_text(encoding="utf-8", errors="replace")
    last_progress = max((match.start() for match in re.finditer(rf"\b{STEPS}/{STEPS}\b", log_text)), default=-1)
    reached_step = last_progress >= 0 and max((row["step"] for row in losses), default=0) == STEPS
    final_save = (last_progress >= 0 and log_text.rfind("Saved checkpoint to ") > last_progress
                  and log_text.rfind("Saved optimizer to ") > last_progress)
    summary = {"status": "TRAINING_FINISHED_REVIEW_REQUIRED" if code == 0 and checkpoints and
               optimizers and reached_step and final_save and not stopped_for else "FAILED",
               "exit_code": code, "stop_reason": stopped_for,
               "elapsed_seconds_including_load": round(time.monotonic() - start, 2),
               "whole_gpu_peak_mib_observed": peak[0], "losses": losses,
               "steps_planned": STEPS, "last_step_observed": reached_step,
               "final_checkpoint_and_optimizer_logged_after_last_step": final_save,
               "checkpoint_files": [{"path": str(path), "sha256": digest(path),
                                     "bytes": path.stat().st_size, "step": STEPS if final_save else None}
                                    for path in checkpoints],
               "optimizer_files": [{"path": str(path), "sha256": digest(path)} for path in optimizers],
               "train_log_sha256": digest(out / "train.log")}
    save_json(out / "training_summary.json", summary)
    if summary["status"] == "FAILED":
        raise RuntimeError("Training failed; inspect retained nails001/train.log")
    return summary


def evaluate(root: Path) -> dict:
    from PIL import Image, ImageDraw, ImageFilter, ImageOps
    import numpy as np
    import torch
    import diffusers
    from diffusers import Flux2KleinPipeline

    data_evidence = prepare(root)
    out = root / "nails001"
    training = read_json(out / "training_summary.json")
    if training["status"] != "TRAINING_FINISHED_REVIEW_REQUIRED":
        raise ValueError("Completed pilot required before evaluation")
    checkpoints = [Path(item["path"]) for item in training["checkpoint_files"]]
    if len(checkpoints) != 1 or digest(checkpoints[0]) != training["checkpoint_files"][0]["sha256"]:
        raise ValueError("Expected one intact step-25 checkpoint")
    checkpoint = checkpoints[0]
    folder = out / "evaluation" / "step025"
    if folder.exists() and any(folder.iterdir()):
        raise ValueError("Evaluation exists; refusing overwrite")
    folder.mkdir(parents=True)
    rows = [row for row in read_json(root / "data_n001" / "manifests" / "pairs.json")
            if row["split"] == "validation"]
    if len(rows) != 20 or set(data_evidence["validation_identities"]) != {row["identity_id"] for row in rows}:
        raise ValueError("Held-out validation split changed")
    pipe = Flux2KleinPipeline.from_pretrained(MODEL, revision=MODEL_REVISION,
        torch_dtype=torch.float16, cache_dir="/tmp/hf-cache/hub")
    pipe.enable_model_cpu_offload(gpu_id=0)
    records = []
    for mode in ("base", "adapter"):
        if mode == "adapter":
            pipe.load_lora_weights(str(checkpoint.parent), weight_name=checkpoint.name)
        for row in rows:
            pair = row["pair_id"]
            source_path = root / "data_n001" / "validation" / "reference" / f"{pair}.png"
            target_path = root / "data_n001" / "validation" / "target" / f"{pair}.png"
            mask_path = root / "data_n001" / "validation" / "masks" / f"{pair}.png"
            if any(digest(path) != row[field] for path, field in
                   ((source_path, "reference_sha256"), (target_path, "target_sha256"),
                    (mask_path, "mask_sha256"))):
                raise ValueError(f"Held-out pair changed: {pair}")
            with Image.open(source_path) as image:
                source = image.convert("RGB")
            start = time.monotonic()
            generated = pipe(prompt=row["caption"], image=source, width=512, height=512,
                num_inference_steps=20, guidance_scale=4.0,
                generator=torch.Generator(device="cuda").manual_seed(EVAL_SEED)).images[0].convert("RGB")
            pair_folder = folder / pair
            pair_folder.mkdir(exist_ok=True)
            output_path = pair_folder / f"{mode}.png"
            generated.save(output_path)
            records.append({"pair_id": pair, "identity_id": row["identity_id"],
                "style_id": row["style_id"], "mode": mode, "prompt": row["caption"],
                "seed": EVAL_SEED, "steps": 20, "guidance": 4.0,
                "elapsed_seconds": round(time.monotonic() - start, 2),
                "output_sha256": digest(output_path), "checkpoint_sha256": digest(checkpoint) if mode == "adapter" else None})
    for row in rows:
        pair = row["pair_id"]
        pair_folder = folder / pair
        with Image.open(root / "data_n001" / "validation" / "reference" / f"{pair}.png") as image:
            original = image.convert("RGB")
        with Image.open(root / "data_n001" / "validation" / "target" / f"{pair}.png") as image:
            target = image.convert("RGB")
        with Image.open(root / "data_n001" / "validation" / "masks" / f"{pair}.png") as image:
            mask = image.convert("L")
        with Image.open(pair_folder / "base.png") as image:
            base = image.convert("RGB")
        with Image.open(pair_folder / "adapter.png") as image:
            adapter = image.convert("RGB")
        hard = mask.point(lambda value: 255 if value > 127 else 0)
        feather = Image.fromarray(np.minimum(np.asarray(hard), np.asarray(hard.filter(ImageFilter.GaussianBlur(1.2)))))
        final = Image.composite(adapter, original, feather)
        final.save(pair_folder / "adapter_composited.png")
        sheet = Image.new("RGB", (5 * 512, 540), "white")
        draw = ImageDraw.Draw(sheet)
        for index, (label, image) in enumerate((("Original", original), ("Target", target),
                ("Base", base), ("NAILS-001 crop", adapter), ("Nail-only composite", final))):
            sheet.paste(ImageOps.contain(image, (512, 512)), (index * 512, 0))
            draw.text((index * 512 + 5, 518), label, fill="black")
        sheet.save(pair_folder / "comparison.jpg", quality=94)
    metadata = {"status": "PENDING_HUMAN_REVIEW", "checkpoint_sha256": digest(checkpoint),
                "base_revision": MODEL_REVISION, "diffusers": diffusers.__version__,
                "torch": torch.__version__, "validation_pairs": len(rows),
                "validation_identities": data_evidence["validation_identities"],
                "records": records}
    save_json(folder / "metadata.json", metadata)
    return {key: value for key, value in metadata.items() if key != "records"}


def package(root: Path) -> dict:
    out = root / "nails001"
    if not (out / "training_summary.json").is_file():
        raise ValueError("No training evidence to package")
    destination = root / "NAILS-001-pilot-step025-evidence.zip"
    if destination.exists():
        raise ValueError("Evidence archive already exists")
    with ZipFile(destination, "w", ZIP_DEFLATED) as archive:
        for path in sorted(out.rglob("*")):
            if path.is_file():
                archive.write(path, path.relative_to(root).as_posix())
        archive.write(root / "train_config.yaml", "train_config.yaml")
    with ZipFile(destination) as archive:
        if archive.testzip() is not None:
            raise ValueError("Evidence archive CRC failed")
    return {"status": "EXPERIMENTAL_REVIEW_REQUIRED", "path": str(destination),
            "bytes": destination.stat().st_size, "sha256": digest(destination)}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase", choices=("prepare", "train", "evaluate", "package", "all"), required=True)
    parser.add_argument("--root", type=Path, default=Path("/kaggle/working"))
    args = parser.parse_args()
    root = args.root.resolve()
    if args.phase == "all":
        # Training may pip-install a new NumPy on disk while the parent interpreter
        # still holds the old module. Start each phase with a fresh interpreter.
        for phase in ("prepare", "train", "evaluate", "package"):
            subprocess.run([sys.executable, str(Path(__file__).resolve()),
                            "--phase", phase, "--root", str(root)], check=True)
        return
    if args.phase == "prepare":
        print(json.dumps(prepare(root), indent=2), flush=True)
    if args.phase == "train":
        print(json.dumps(train(root), indent=2), flush=True)
    if args.phase == "evaluate":
        print(json.dumps(evaluate(root), indent=2), flush=True)
    if args.phase == "package":
        print(json.dumps(package(root), indent=2), flush=True)


if __name__ == "__main__":
    main()
