"""Isolated MAKEUP-001 training and held out Base versus LoRA evaluation.

Uses DATA-M001 real paired edits. This never loads or switches Hair adapters.
"""

import argparse
from collections import Counter
from datetime import datetime, timezone
from hashlib import sha256
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import threading
import time
from zipfile import ZIP_DEFLATED, ZipFile


TOOLKIT_COMMIT = "a8dfcf7d7e2b38ccc7b2fb68ece9c6358e61e7a7"
MODEL = "black-forest-labs/FLUX.2-klein-base-4B"
MODEL_REVISION = "a3b4f4849157f664bdbc776fd7453c2783562f4d"
MODEL_FILENAME = "flux-2-klein-base-4b.safetensors"
MODEL_SNAPSHOT = Path("/tmp/hf-cache/hub/models--black-forest-labs--FLUX.2-klein-base-4B/snapshots") / MODEL_REVISION
SOURCE_ARCHIVE_SHA256 = "c15fd40199b4d46050dc864eaed647b0ad41921507c2f99cb1cfec2b46922c6a"
STEPS = 250


def digest(path: Path) -> str:
    value = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def read_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def validate_dataset(dataset: Path) -> dict:
    from PIL import Image

    qa = read_json(dataset / "reports" / "qa.json")
    rows = read_json(dataset / "manifests" / "pairs.json")
    reviews = read_json(dataset / "manifests" / "reviews.json")
    selection = read_json(dataset / "manifests" / "selection.json")
    if (qa.get("status") != "FINALIZED" or qa.get("train_pairs") != 50
            or qa.get("validation_pairs") != 10 or qa.get("review_mode") != "explicit_human_review"
            or qa.get("source_archive_sha256") != SOURCE_ARCHIVE_SHA256):
        raise ValueError("DATA-M001 final QA report is missing or incompatible")
    if len(rows) != 60 or len(reviews) != 60:
        raise ValueError("Expected 60 reviewed directional pairs")
    if selection.get("variant_positions") != [f"makeup_{n:02d}" for n in range(1, 6)]:
        raise ValueError("Archive variant positions changed")
    decisions = {row["pair_id"]: row for row in reviews}
    groups = {"train": set(), "validation": set()}
    count = Counter()
    source_hashes = {}
    target_hashes = set()
    for row in rows:
        pair_id, split, identity = row["pair_id"], row["split"], row["identity_id"]
        if (split not in groups or identity not in selection[f"{split}_ids"]
                or row["target_variant_position"] not in selection["variant_positions"]
                or row.get("target_variant_is_style_class") is not False
                or decisions.get(pair_id, {}).get("state") != "ACCEPT"
                or not decisions[pair_id].get("reviewer") or not decisions[pair_id].get("note")):
            raise ValueError(f"Unreviewed, mislabeled or split leaking pair: {pair_id}")
        groups[split].add(identity)
        count[split] += 1
        source_hashes.setdefault(identity, row["source_sha256"])
        if source_hashes[identity] != row["source_sha256"] or row["target_sha256"] in target_hashes:
            raise ValueError(f"Duplicate or inconsistent source or target hash: {pair_id}")
        target_hashes.add(row["target_sha256"])
        for field, hash_field in (("reference", "source_sha256"), ("target", "target_sha256")):
            path = dataset / row[field]
            if digest(path) != row[hash_field]:
                raise ValueError(f"Image hash mismatch: {path}")
            with Image.open(path) as image:
                if image.format != "JPEG" or image.mode != "RGB" or image.size != (512, 512):
                    raise ValueError(f"Invalid training image: {path}")
        caption = dataset / row["caption_path"]
        if caption.read_text(encoding="utf-8").strip() != row["caption"] or "preserving" not in row["caption"]:
            raise ValueError(f"Caption mismatch: {pair_id}")
    if groups["train"] & groups["validation"] or len(groups["train"]) != 10 or len(groups["validation"]) != 2:
        raise ValueError("Identity split is not 10/2 and disjoint")
    if count != {"train": 50, "validation": 10}:
        raise ValueError(f"Pair counts changed: {count}")
    return {"qa_sha256": digest(dataset / "reports" / "qa.json"),
            "pairs_sha256": digest(dataset / "manifests" / "pairs.json"),
            "reviews_sha256": digest(dataset / "manifests" / "reviews.json"),
            "selection_sha256": digest(dataset / "manifests" / "selection.json"),
            "identity_counts": {split: len(values) for split, values in groups.items()},
            "pair_counts": dict(count), "source_archive_sha256": SOURCE_ARCHIVE_SHA256}


def training_config(dataset: Path, output: Path) -> str:
    """The proven TRAIN-001 T4 configuration with only job and dataset paths changed."""
    return f'''job: "extension"
config:
  name: "makeup001_{STEPS}step"
  process:
    - type: "diffusion_trainer"
      training_folder: "{(output / 'checkpoints').as_posix()}"
      device: "cuda:0"
      performance_log_every: 5
      network:
        type: "lora"
        linear: 16
        linear_alpha: 16
        conv: 8
        conv_alpha: 8
      save:
        dtype: "float16"
        save_every: 125
        max_step_saves_to_keep: 2
      datasets:
        - folder_path: "{(dataset / 'train' / 'target').as_posix()}"
          control_path: "{(dataset / 'train' / 'reference').as_posix()}"
          caption_ext: "txt"
          resolution: [512]
      train:
        batch_size: 1
        steps: {STEPS}
        lr: 0.0001
        optimizer: "adamw8bit"
        noise_scheduler: "flowmatch"
        gradient_checkpointing: true
        dtype: "bf16"
        train_unet: true
        train_text_encoder: false
        timestep_type: "weighted"
        content_or_style: "balanced"
      model:
        arch: "flux2_klein_4b"
        name_or_path: "{MODEL_SNAPSHOT.as_posix()}"
        quantize: true
        low_vram: true
meta:
  name: "makeup001_{STEPS}step"
  version: "1.0"
'''


def prepare(dataset: Path, output: Path) -> dict:
    evidence = validate_dataset(dataset)
    output.mkdir(parents=True, exist_ok=True)
    config = training_config(dataset.resolve(), output.resolve())
    path = output / "train_config.yaml"
    if path.exists() and path.read_text(encoding="utf-8") != config:
        raise ValueError("Existing MAKEUP-001 config differs; refusing overwrite")
    evidence_path = output / "dataset_evidence.json"
    if evidence_path.exists() and read_json(evidence_path) != evidence:
        raise ValueError("DATA-M001 changed since the existing MAKEUP-001 preparation")
    path.write_text(config, encoding="utf-8")
    save_json(evidence_path, evidence)
    return {"status": "PREPARED_NOT_STARTED", "config": str(path), "config_sha256": digest(path), **evidence}


def preflight(toolkit: Path) -> dict:
    os.environ["CUDA_VISIBLE_DEVICES"] = "0"
    os.environ["HF_HOME"] = "/tmp/hf-cache"
    os.environ["HF_HUB_CACHE"] = "/tmp/hf-cache/hub"
    import torch
    from huggingface_hub import HfApi, hf_hub_download
    if not torch.cuda.is_available():
        raise RuntimeError("MAKEUP-001 training requires CUDA")
    if shutil.disk_usage("/tmp").free < 30 * 1024**3:
        raise RuntimeError("Insufficient /tmp space for pinned Base and AI Toolkit")
    commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=toolkit, check=True,
                            capture_output=True, text=True).stdout.strip()
    if commit != TOOLKIT_COMMIT:
        raise RuntimeError(f"Wrong AI Toolkit commit: {commit}")
    model_revision = HfApi().model_info(MODEL, revision=MODEL_REVISION).sha
    if model_revision != MODEL_REVISION:
        raise RuntimeError(f"Wrong Base model revision: {model_revision}")
    transformer = Path(hf_hub_download(repo_id=MODEL, filename=MODEL_FILENAME,
                                       revision=MODEL_REVISION, cache_dir="/tmp/hf-cache/hub"))
    if transformer.parent != MODEL_SNAPSHOT or not transformer.is_file():
        raise RuntimeError("Pinned Base transformer did not resolve to the expected snapshot")
    return {"timestamp_utc": datetime.now(timezone.utc).isoformat(), "python": sys.version,
            "torch": torch.__version__, "cuda": torch.version.cuda,
            "gpu": torch.cuda.get_device_name(0), "toolkit_commit": commit,
            "base_model_id": MODEL, "base_model_revision": model_revision,
            "transformer_path": str(transformer), "transformer_sha256": digest(transformer),
            "dataset_adapter": None, "hair_adapter_loaded": False}


def whole_gpu_peak_sampler(stop: threading.Event, peak: list[int]) -> None:
    while not stop.is_set():
        result = subprocess.run(["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"],
                                capture_output=True, text=True)
        if result.returncode == 0:
            for line in result.stdout.splitlines():
                try:
                    peak[0] = max(peak[0], int(line.strip()))
                except ValueError:
                    pass
        stop.wait(2)


def execute(dataset: Path, output: Path, toolkit: Path) -> dict:
    current = validate_dataset(dataset)
    if read_json(output / "dataset_evidence.json") != current:
        raise ValueError("Final DATA-M001 changed since training preparation")
    if (output / "train.log").exists():
        raise ValueError("Existing MAKEUP-001 train.log; refusing to overwrite run")
    runtime = preflight(toolkit)
    save_json(output / "runtime.json", runtime)
    config = output / "train_config.yaml"
    command = [sys.executable, "run.py", str(config)]
    save_json(output / "command.json", {"command": command, "cwd": str(toolkit),
                                        "config_sha256": digest(config)})
    stop, peak = threading.Event(), [0]
    monitor = threading.Thread(target=whole_gpu_peak_sampler, args=(stop, peak), daemon=True)
    monitor.start()
    start = time.monotonic()
    losses = []
    stopped_for = None
    try:
        with (output / "train.log").open("w", encoding="utf-8") as log:
            process = subprocess.Popen(command, cwd=toolkit, stdout=subprocess.PIPE,
                                       stderr=subprocess.STDOUT, text=True, bufsize=1)
            assert process.stdout is not None
            for line in process.stdout:
                log.write(line)
                log.flush()
                print(line, end="", flush=True)
                if re.search(r"(?:loss\s+is|loss\s*:)\s*[+-]?(?:nan|inf)\b", line, re.I):
                    stopped_for = "nonfinite loss"
                    process.terminate()
                    break
                for match in re.finditer(rf"\b(\d+)/{STEPS}\b[^\r\n]*?loss:\s*([+-]?\d+(?:\.\d+)?e[+-]?\d+)", line, re.I):
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
    checkpoints = sorted((output / "checkpoints").rglob("*.safetensors"))
    optimizers = sorted((output / "checkpoints").rglob("optimizer.pt"))
    log_text = (output / "train.log").read_text(encoding="utf-8", errors="replace")
    progress = max((match.start() for match in re.finditer(rf"\b{STEPS}/{STEPS}\b", log_text)), default=-1)
    final_save = (progress >= 0 and log_text.rfind("Saved checkpoint to ") > progress
                  and log_text.rfind("Saved optimizer to ") > progress)
    success = (code == 0 and not stopped_for and max((row["step"] for row in losses), default=0) == STEPS
               and bool(checkpoints) and bool(optimizers) and final_save)
    summary = {"success": success, "exit_code": code, "stop_reason": stopped_for,
               "elapsed_seconds_including_load": round(time.monotonic() - start, 2),
               "whole_gpu_peak_mib_observed": peak[0], "highest_loss_step": max((row["step"] for row in losses), default=0),
               "losses": losses, "final_save_logged_after_last_step": final_save,
               "checkpoints": [{"path": str(path), "bytes": path.stat().st_size,
                                "sha256": digest(path)} for path in checkpoints],
               "optimizer_states": [{"path": str(path), "bytes": path.stat().st_size,
                                     "sha256": digest(path)} for path in optimizers]}
    save_json(output / "training_summary.json", summary)
    if not success:
        raise RuntimeError("MAKEUP-001 did not complete with finite loss, final checkpoint and optimizer evidence")
    return summary


def evaluate(dataset: Path, output: Path, checkpoint: Path, prompts_path: Path) -> dict:
    import torch
    from PIL import Image, ImageDraw, ImageOps
    import diffusers
    from diffusers import Flux2KleinPipeline

    if not read_json(output / "training_summary.json").get("success"):
        raise ValueError("Successful MAKEUP-001 training is required before evaluation")
    if not checkpoint.is_file() or checkpoint.suffix != ".safetensors":
        raise ValueError("MAKEUP-001 checkpoint missing")
    if read_json(output / "dataset_evidence.json") != validate_dataset(dataset):
        raise ValueError("DATA-M001 changed since training")
    prompts = read_json(prompts_path)
    styles = prompts["styles"]
    if len(styles) != 10 or len({style["id"] for style in styles}) != 10:
        raise ValueError("Expected ten unique inference prompt presets")
    if any(not style.get("instruction") for style in styles) or not prompts.get("preservation_instruction"):
        raise ValueError("Every style requires an instruction and a shared preservation instruction")
    validation = read_json(dataset / "manifests" / "selection.json")["validation_ids"]
    if len(validation) != 2:
        raise ValueError("Expected two held out identities")
    sources = {row["identity_id"]: dataset / row["reference"] for row in
               read_json(dataset / "manifests" / "pairs.json") if row["split"] == "validation"}
    if set(sources) != set(validation):
        raise ValueError("Validation sources differ from frozen split")
    folder = output / "evaluation"
    if folder.exists() and any(folder.iterdir()):
        raise ValueError("Refusing to overwrite evaluation images")
    folder.mkdir(parents=True)
    pipe = Flux2KleinPipeline.from_pretrained(MODEL, revision=MODEL_REVISION,
                                              torch_dtype=torch.float16, cache_dir="/tmp/hf-cache/hub")
    pipe.enable_model_cpu_offload(gpu_id=0)
    records = []
    for mode in ("base", "adapter"):
        if mode == "adapter":
            pipe.load_lora_weights(str(checkpoint.parent), weight_name=checkpoint.name)
        for identity in validation:
            with Image.open(sources[identity]) as image:
                source = image.convert("RGB")
            for style in styles:
                destination = folder / mode / identity / f"{style['id']}.png"
                destination.parent.mkdir(parents=True, exist_ok=True)
                start = time.monotonic()
                prompt = style["instruction"] + " " + prompts["preservation_instruction"]
                result = pipe(prompt=prompt, image=source, width=512, height=512,
                              num_inference_steps=20, guidance_scale=4.0,
                              generator=torch.Generator(device="cuda").manual_seed(1977)).images[0]
                result.save(destination)
                records.append({"mode": mode, "identity_id": identity, "style_id": style["id"],
                                "prompt": prompt, "seed": 1977, "steps": 20, "guidance": 4.0,
                                "model_id": MODEL, "model_revision": MODEL_REVISION,
                                "lora_active": mode == "adapter",
                                "checkpoint_sha256": digest(checkpoint) if mode == "adapter" else None,
                                "source_sha256": digest(sources[identity]), "output": str(destination),
                                "output_sha256": digest(destination),
                                "runtime_seconds": round(time.monotonic() - start, 2),
                                "review_state": "PENDING_HUMAN_REVIEW"})
    for identity in validation:
        sheet = Image.new("RGB", (3 * 256, 10 * 285), "white")
        draw = ImageDraw.Draw(sheet)
        for index, style in enumerate(styles):
            for column, path in enumerate((sources[identity], folder / "base" / identity / f"{style['id']}.png",
                                           folder / "adapter" / identity / f"{style['id']}.png")):
                with Image.open(path) as image:
                    sheet.paste(ImageOps.contain(image.convert("RGB"), (256, 256)),
                                (column * 256, index * 285))
            draw.text((5, index * 285 + 260), f"{identity} {style['id']} | Original / Base / MAKEUP-001", fill="black")
        sheet.save(folder / f"comparison_{identity}.jpg", quality=93)
    metadata = {"status": "PENDING_HUMAN_REVIEW", "attempted": len(records),
                "base_outputs": 20, "adapter_outputs": 20, "records": records,
                "torch": torch.__version__, "diffusers": diffusers.__version__,
                "prompt_presets_sha256": digest(prompts_path)}
    save_json(folder / "metadata.json", metadata)
    return {key: value for key, value in metadata.items() if key != "records"}


def package(output: Path, destination: Path) -> dict:
    if destination.exists():
        raise ValueError(f"Refusing to overwrite artifact ZIP: {destination}")
    with ZipFile(destination, "w", ZIP_DEFLATED) as archive:
        for path in sorted(output.rglob("*")):
            if path.is_file():
                archive.write(path, path.relative_to(output).as_posix())
    with ZipFile(destination) as archive:
        if archive.testzip() is not None:
            raise ValueError("Artifact ZIP CRC failed")
    return {"artifact_zip": str(destination), "bytes": destination.stat().st_size,
            "sha256": digest(destination)}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase", choices=("prepare", "execute", "evaluate", "package"), required=True)
    parser.add_argument("--dataset", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--toolkit", type=Path, default=Path("/tmp/exp001-ai-toolkit"))
    parser.add_argument("--checkpoint", type=Path)
    parser.add_argument("--prompts", type=Path)
    parser.add_argument("--zip", type=Path)
    args = parser.parse_args()
    if args.phase != "package" and not args.dataset:
        parser.error("--dataset is required")
    if args.phase == "prepare":
        result = prepare(args.dataset, args.out)
    elif args.phase == "execute":
        result = execute(args.dataset, args.out, args.toolkit)
    elif args.phase == "evaluate":
        if not args.checkpoint or not args.prompts:
            parser.error("evaluate requires --checkpoint and --prompts")
        result = evaluate(args.dataset, args.out, args.checkpoint, args.prompts)
    else:
        if not args.zip:
            parser.error("package requires --zip")
        result = package(args.out, args.zip)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
