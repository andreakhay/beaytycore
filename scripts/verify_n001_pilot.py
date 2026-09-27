"""Verify the downloaded NAILS-001 pilot archive against approved DATA-N001."""

import argparse
from collections import Counter
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
from zipfile import ZipFile

import numpy as np
from PIL import Image


DATA_SHA256 = "d37b68bc3e06c6ea1b1b013424dd813aafbef83db222cf9223e229d33ad105bb"
BASE_REVISION = "a3b4f4849157f664bdbc776fd7453c2783562f4d"
TOOLKIT_COMMIT = "a8dfcf7d7e2b38ccc7b2fb68ece9c6358e61e7a7"
STYLES = {"classic_red", "nude_pink", "glossy_black", "french_tip", "pink_ombre"}


def digest(path: Path) -> str:
    value = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def member_digest(archive: ZipFile, name: str) -> str:
    value = sha256()
    with archive.open(name) as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def read_json(archive: ZipFile, name: str) -> dict:
    return json.loads(archive.read(name))


def image_array(archive: ZipFile, name: str, mode: str = "RGB") -> np.ndarray:
    with Image.open(BytesIO(archive.read(name))) as image:
        if image.size != (512, 512):
            raise ValueError(f"Wrong dimensions for {name}: {image.size}")
        return np.asarray(image.convert(mode)).copy()


def verify(artifact: Path, dataset: Path) -> dict:
    if digest(dataset) != DATA_SHA256:
        raise ValueError("Approved DATA-N001 ZIP hash mismatch")
    with ZipFile(artifact) as result, ZipFile(dataset) as data:
        if result.testzip() is not None or data.testzip() is not None:
            raise ValueError("Archive CRC failure")
        if any(Path(name).is_absolute() or ".." in Path(name).parts for name in result.namelist()):
            raise ValueError("Unexpected archive path")
        root = "nails001/"
        preflight = read_json(result, root + "preflight_data.json")
        runtime = read_json(result, root + "runtime.json")
        training = read_json(result, root + "training_summary.json")
        command = read_json(result, root + "training_command.json")
        evaluation = read_json(result, root + "evaluation/step025/metadata.json")
        manifest = read_json(data, "manifests/pairs.json")
        if preflight["dataset_archive_sha256"] != DATA_SHA256 or preflight["pairs"] != 100:
            raise ValueError("Training dataset preflight mismatch")
        if preflight["manifest_sha256"] != member_digest(data, "manifests/pairs.json"):
            raise ValueError("Training manifest hash mismatch")
        train_ids = {row["identity_id"] for row in manifest if row["split"] == "train"}
        val_rows = [row for row in manifest if row["split"] == "validation"]
        val_ids = {row["identity_id"] for row in val_rows}
        if len(train_ids) != 16 or len(val_ids) != 4 or train_ids & val_ids:
            raise ValueError("Identity split mismatch")
        if sorted(train_ids) != preflight["train_identities"] or sorted(val_ids) != preflight["validation_identities"]:
            raise ValueError("Training identities differ from approved manifest")
        if len(val_rows) != 20 or Counter(row["style_id"] for row in val_rows) != Counter({style: 4 for style in STYLES}):
            raise ValueError("Held-out style coverage mismatch")
        if runtime["toolkit_commit"] != TOOLKIT_COMMIT or runtime["base_revision"] != BASE_REVISION:
            raise ValueError("Pinned trainer or Base revision mismatch")
        if runtime["gpu"] != "Tesla T4" or runtime["dataset"] != preflight:
            raise ValueError("Runtime dataset or GPU mismatch")
        config_hash = member_digest(result, "train_config.yaml")
        if config_hash != preflight["training_config_sha256"] or config_hash != command["config_sha256"]:
            raise ValueError("Training config changed")
        if command["initial_rng_seed"] != 1977 or training["status"] != "TRAINING_FINISHED_REVIEW_REQUIRED":
            raise ValueError("Training seed or status mismatch")
        if training["exit_code"] != 0 or training["steps_planned"] != 25 or not training["last_step_observed"]:
            raise ValueError("Step-25 completion not established")
        if not training["final_checkpoint_and_optimizer_logged_after_last_step"]:
            raise ValueError("Final checkpoint was not logged")
        if member_digest(result, root + "train.log") != training["train_log_sha256"]:
            raise ValueError("Training log hash mismatch")
        if len(training["checkpoint_files"]) != 1 or len(training["optimizer_files"]) != 1:
            raise ValueError("Unexpected checkpoint/optimizer inventory")
        checkpoint = training["checkpoint_files"][0]
        checkpoint_name = root + "checkpoints/nails001_25step/nails001_25step.safetensors"
        optimizer_name = root + "checkpoints/nails001_25step/optimizer.pt"
        if checkpoint["step"] != 25 or member_digest(result, checkpoint_name) != checkpoint["sha256"]:
            raise ValueError("Checkpoint hash or step mismatch")
        if result.getinfo(checkpoint_name).file_size != checkpoint["bytes"]:
            raise ValueError("Checkpoint byte count mismatch")
        if member_digest(result, optimizer_name) != training["optimizer_files"][0]["sha256"]:
            raise ValueError("Optimizer hash mismatch")
        if evaluation["checkpoint_sha256"] != checkpoint["sha256"] or evaluation["base_revision"] != BASE_REVISION:
            raise ValueError("Evaluation model mismatch")
        if evaluation["validation_pairs"] != 20 or sorted(evaluation["validation_identities"]) != sorted(val_ids):
            raise ValueError("Evaluation identity mismatch")
        records = evaluation["records"]
        if len(records) != 40 or Counter(row["mode"] for row in records) != Counter({"base": 20, "adapter": 20}):
            raise ValueError("Expected 20 Base and 20 adapter outputs")
        record_by_key = {(row["pair_id"], row["mode"]): row for row in records}
        if len(record_by_key) != 40:
            raise ValueError("Duplicate evaluation record")
        metrics = []
        for row in val_rows:
            pair, split = row["pair_id"], row["split"]
            prefix = f"{split}/"
            source_name = prefix + f"reference/{pair}.png"
            target_name = prefix + f"target/{pair}.png"
            mask_name = prefix + f"masks/{pair}.png"
            for name, field in ((source_name, "reference_sha256"), (target_name, "target_sha256"),
                                (mask_name, "mask_sha256")):
                if member_digest(data, name) != row[field]:
                    raise ValueError(f"Approved pair hash mismatch: {name}")
            source = image_array(data, source_name)
            target = image_array(data, target_name)
            mask = image_array(data, mask_name, "L") > 127
            if not mask.any() or mask.all():
                raise ValueError(f"Invalid nail mask: {pair}")
            images = {}
            for mode in ("base", "adapter"):
                record = record_by_key[pair, mode]
                if (record["identity_id"] != row["identity_id"] or record["style_id"] != row["style_id"]
                        or record["prompt"] != row["caption"] or record["seed"] != 1977
                        or record["steps"] != 20 or record["guidance"] != 4.0):
                    raise ValueError(f"Evaluation settings mismatch: {pair}/{mode}")
                expected_checkpoint = checkpoint["sha256"] if mode == "adapter" else None
                if record["checkpoint_sha256"] != expected_checkpoint:
                    raise ValueError(f"Wrong adapter status: {pair}/{mode}")
                name = root + f"evaluation/step025/{pair}/{mode}.png"
                if member_digest(result, name) != record["output_sha256"]:
                    raise ValueError(f"Output hash mismatch: {name}")
                images[mode] = image_array(result, name)
            final_name = root + f"evaluation/step025/{pair}/adapter_composited.png"
            final = image_array(result, final_name)
            outside_changed = int(np.any(final[~mask] != source[~mask], axis=1).sum())
            if outside_changed:
                raise ValueError(f"Final changed {outside_changed} out-of-mask pixels: {pair}")
            if root + f"evaluation/step025/{pair}/comparison.jpg" not in result.namelist():
                raise ValueError(f"Missing comparison sheet: {pair}")
            target_nails = target[mask].astype(np.float32)
            base_nails = images["base"][mask].astype(np.float32)
            adapter_nails = images["adapter"][mask].astype(np.float32)
            metrics.append({"pair_id": pair, "identity_id": row["identity_id"],
                "style_id": row["style_id"], "mask_pixels": int(mask.sum()),
                "final_outside_mask_changed_pixels": outside_changed,
                "base_nail_mae_to_target": round(float(np.abs(base_nails - target_nails).mean()), 3),
                "adapter_nail_mae_to_target": round(float(np.abs(adapter_nails - target_nails).mean()), 3),
                "raw_adapter_outside_mask_changed_fraction": round(float(np.any(images["adapter"][~mask] != source[~mask], axis=1).mean()), 5),
                "target_nail_rgb": np.rint(target_nails.mean(axis=0)).astype(int).tolist(),
                "adapter_nail_rgb": np.rint(adapter_nails.mean(axis=0)).astype(int).tolist()})
    return {"status": "ARTIFACTS_VERIFIED_VISUAL_REVIEW_REQUIRED",
            "artifact_sha256": digest(artifact), "dataset_sha256": DATA_SHA256,
            "checkpoint_sha256": checkpoint["sha256"], "optimizer_sha256": training["optimizer_files"][0]["sha256"],
            "training_seconds_including_load": training["elapsed_seconds_including_load"],
            "observed_gpu_peak_mib": training["whole_gpu_peak_mib_observed"],
            "validation_pairs": len(metrics), "base_outputs": 20, "adapter_outputs": 20,
            "pairs": metrics}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact", type=Path, required=True)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = verify(args.artifact, args.dataset)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in report.items() if key != "pairs"}, indent=2))


if __name__ == "__main__":
    main()
