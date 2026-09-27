"""Prepare a gated, isolated AI Toolkit edit LoRA bundle for Kaggle.

This script does not train. The Supervisor runs the emitted config only after
DATA-N001 review and checks validation results before enabling the adapter.
"""

import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED


MODEL = "black-forest-labs/FLUX.2-klein-base-4B"
MODEL_REVISION = "a3b4f4849157f664bdbc776fd7453c2783562f4d"
TOOLKIT_COMMIT = "a8dfcf7d7e2b38ccc7b2fb68ece9c6358e61e7a7"


def digest(path: Path) -> str:
    value = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def validate(dataset: Path) -> dict:
    root = dataset / "final"
    qa = json.loads((root / "reports" / "qa.json").read_text(encoding="utf-8"))
    rows = json.loads((root / "manifests" / "pairs.json").read_text(encoding="utf-8"))
    if qa.get("status") != "FINALIZED_REVIEWED" or qa.get("review_mode") != "explicit_human_review":
        raise ValueError("DATA-N001 has no accepted review gate")
    if len(rows) != qa["accepted_pairs"]:
        raise ValueError("Final manifest and QA pair counts differ")
    identities = {"train": set(), "validation": set()}
    styles = Counter()
    source_by_identity = {}
    source_owners = {}
    for row in rows:
        split, pair_id = row["split"], row["pair_id"]
        if split not in identities or row["review_status"] != "ACCEPT":
            raise ValueError("Unreviewed or invalid split in final manifest")
        identities[split].add(row["identity_id"])
        styles[(split, row["style_id"])] += 1
        source_by_identity.setdefault(row["identity_id"], row["source_sha256"])
        if source_by_identity[row["identity_id"]] != row["source_sha256"]:
            raise ValueError("Source hash changed for one identity")
        owner = source_owners.setdefault(row["source_sha256"], row["identity_id"])
        if owner != row["identity_id"]:
            raise ValueError("One source photo belongs to multiple identities")
        for role, expected in (("reference", row["reference_sha256"]), ("target", row["target_sha256"]), ("masks", row["mask_sha256"])):
            path = root / split / role / f"{pair_id}.png"
            if digest(path) != expected:
                raise ValueError(f"Pair hash mismatch: {path}")
        caption = (root / split / "target" / f"{pair_id}.txt").read_text(encoding="utf-8").strip()
        if caption != row["caption"] or "preserv" not in caption.lower():
            raise ValueError(f"Invalid edit instruction: {pair_id}")
    if identities["train"] & identities["validation"]:
        raise ValueError("Identity leakage")
    if not identities["train"] or not identities["validation"]:
        raise ValueError("Both train and validation identities are required")
    return {"accepted_pairs": len(rows), "train_identities": len(identities["train"]),
            "validation_identities": len(identities["validation"]),
            "style_counts": {f"{split}/{style}": count for (split, style), count in sorted(styles.items())},
            "qa_sha256": digest(root / "reports" / "qa.json"),
            "pairs_sha256": digest(root / "manifests" / "pairs.json")}


def config(steps: int, save_every: int) -> str:
    return f'''job: "extension"
config:
  name: "nails001_{steps}step"
  process:
    - type: "diffusion_trainer"
      training_folder: "/kaggle/working/nails001/checkpoints"
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
        save_every: {save_every}
        max_step_saves_to_keep: 3
      datasets:
        - folder_path: "/kaggle/working/data_n001/train/target"
          control_path: "/kaggle/working/data_n001/train/reference"
          caption_ext: "txt"
          resolution: [512]
      train:
        batch_size: 1
        steps: {steps}
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
        name_or_path: "/tmp/hf-cache/hub/models--black-forest-labs--FLUX.2-klein-base-4B/snapshots/{MODEL_REVISION}"
        quantize: true
        low_vram: true
meta:
  name: "nails001_{steps}step"
  version: "1.0"
'''


def bundle(dataset: Path, output: Path, steps: int, save_every: int) -> dict:
    if steps < 10 or save_every < 1 or save_every > steps:
        raise ValueError("Choose a short positive pilot and a checkpoint interval within it")
    evidence = validate(dataset)
    if output.exists():
        raise ValueError("Refusing to overwrite training bundle")
    output.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(output, "w", ZIP_DEFLATED) as archive:
        for path in sorted((dataset / "final").rglob("*")):
            if path.is_file():
                archive.write(path, (Path("data_n001") / path.relative_to(dataset / "final")).as_posix())
        archive.writestr("train_config.yaml", config(steps, save_every))
        archive.write(Path(__file__).with_name("run_n001_kaggle.py"), "run_n001_kaggle.py")
        archive.write(Path(__file__).with_name("evaluate_n001_kaggle.py"), "evaluate_n001_kaggle.py")
        archive.writestr("bundle_evidence.json", json.dumps({**evidence, "model": MODEL,
            "model_revision": MODEL_REVISION, "toolkit_commit": TOOLKIT_COMMIT,
            "pilot_steps": steps, "checkpoint_interval": save_every}, indent=2))
        archive.writestr("RUN.txt", "Use an authenticated Kaggle T4 session. Pin AI Toolkit to " + TOOLKIT_COMMIT +
            ". Verify the FLUX.2 Klein Base revision " + MODEL_REVISION +
            ". Extract this ZIP into /kaggle/working. Run python /kaggle/working/run_n001_kaggle.py --toolkit /kaggle/working/ai-toolkit --config /kaggle/working/train_config.yaml --output /kaggle/working/nails001. "
            "Inspect saved checkpoint hashes and held out validation contact sheets before any continuation or app integration.\n")
    with ZipFile(output) as archive:
        if archive.testzip() is not None:
            raise ValueError("Training ZIP failed CRC")
    return {"status": "PREPARED_NOT_TRAINED", "bundle": str(output), "sha256": digest(output), **evidence}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--steps", type=int, default=75)
    parser.add_argument("--save-every", type=int, default=25)
    args = parser.parse_args()
    print(json.dumps(bundle(args.dataset, args.output, args.steps, args.save_every), indent=2))


if __name__ == "__main__": main()
