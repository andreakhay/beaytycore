"""Verify downloaded NAILS-001-LOCAL-v1 step-50 evidence and held-out pixels."""

import argparse
from collections import Counter, defaultdict
from hashlib import sha256
from io import BytesIO
import json
import math
from pathlib import Path
import re
import struct
import sys
from zipfile import ZipFile

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.nails001_local_evaluate import original_nail_mask


APPROVED_SHA = "d37b68bc3e06c6ea1b1b013424dd813aafbef83db222cf9223e229d33ad105bb"
LOCAL_SHA = "d7440f1cc1a8987c48235fed36f8ff23581c17719b219fc2a7e600ad867bcf90"
BASE_REVISION = "a3b4f4849157f664bdbc776fd7453c2783562f4d"
STYLES = ("classic_red", "nude_pink", "glossy_black", "french_tip", "pink_ombre")


def file_hash(path: Path) -> str:
    h = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def member_hash(archive: ZipFile, name: str) -> str:
    h = sha256()
    with archive.open(name) as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_image(archive: ZipFile, name: str, mode: str = "RGB") -> Image.Image:
    with Image.open(BytesIO(archive.read(name))) as image:
        result = image.convert(mode)
    if result.size != (512, 512):
        raise ValueError(f"Unexpected image dimensions: {name}")
    return result


def verify(evidence_path: Path, evaluation_path: Path, approved_path: Path,
           localized_path: Path) -> dict:
    if file_hash(approved_path) != APPROVED_SHA or file_hash(localized_path) != LOCAL_SHA:
        raise ValueError("Approved or localized data archive changed")
    with (ZipFile(evidence_path) as evidence, ZipFile(evaluation_path) as evaluation,
          ZipFile(approved_path) as approved, ZipFile(localized_path) as localized):
        for archive in (evidence, evaluation, approved, localized):
            if archive.testzip() is not None:
                raise ValueError("ZIP CRC failure")
        manifest = json.loads(evidence.read("evidence_manifest.json"))
        summary = json.loads(evidence.read("logs/training_summary.json"))
        preflight = json.loads(evidence.read("logs/preflight.json"))
        runtime = json.loads(evidence.read("logs/runtime.json"))
        meta = json.loads(evaluation.read("metadata.json"))
        qa = json.loads(localized.read("reports/qa.json"))
        rows = json.loads(localized.read("manifests/pairs.json"))
        by_id = {row["pair_id"]: row for row in rows}
        parents = {row["pair_id"]: row for row in json.loads(approved.read("manifests/pairs.json"))}
        if len(by_id) != len(rows) or len(rows) != 430:
            raise ValueError("Localized manifest is not 430 unique pairs")
        if (manifest["approved_data_sha256"], manifest["localized_data_sha256"]) != (APPROVED_SHA, LOCAL_SHA):
            raise ValueError("Evidence dataset provenance mismatch")
        if (preflight["train_pairs"], preflight["validation_pairs"]) != (340, 90):
            raise ValueError("Training split count mismatch")
        if runtime["base_revision"] != BASE_REVISION or runtime["dataset_sha256"] != LOCAL_SHA:
            raise ValueError("Training Base or data changed")
        if runtime["config_sha256"] != preflight["config_sha256"]:
            raise ValueError("Training config changed after preflight")
        if meta["base_revision"] != BASE_REVISION or meta["localized_archive_sha256"] != LOCAL_SHA:
            raise ValueError("Evaluation Base or data changed")
        names = {Path(name).name: name for name in evidence.namelist()}
        for basename, expected in manifest["evidence_file_hashes"].items():
            if member_hash(evidence, names[basename]) != expected:
                raise ValueError(f"Evidence member hash mismatch: {basename}")
        if manifest["evaluation_sha256"] != file_hash(evaluation_path):
            raise ValueError("Separate evaluation archive differs from evidence")
        if manifest["checkpoint_sha256"] != summary["checkpoint_sha256"] != meta["checkpoint_sha256"]:
            raise ValueError("Checkpoint hash mismatch")
        with evidence.open("checkpoint/nails001_local_v1.safetensors") as checkpoint_stream:
            header_length = struct.unpack("<Q", checkpoint_stream.read(8))[0]
            checkpoint_header = json.loads(checkpoint_stream.read(header_length))
        checkpoint_info = json.loads(checkpoint_header["__metadata__"]["training_info"])
        if checkpoint_info.get("step") != 50 or checkpoint_header["__metadata__"].get("ss_base_model_version") != "flux2_klein_4b":
            raise ValueError("Checkpoint header does not identify FLUX.2 Klein step 50")
        if summary["status"] != "CHECKPOINT_READY_REVIEW_REQUIRED" or summary["exit_code"] != 0:
            raise ValueError("Training did not report a successful checkpoint")
        trace = [json.loads(line) for line in evidence.read("logs/sample_trace.jsonl").decode().splitlines()]
        if [row["step"] for row in trace] != list(range(1, 51)):
            raise ValueError("Exact sample exposure is incomplete")
        exposure = Counter()
        for item in trace:
            row = by_id[item["pair_id"]]
            if row["split"] != "train" or (item["identity_id"], item["finger_id"], item["style_id"]) != (
                    row["identity_id"], row["finger_id"], row["style_id"]):
                raise ValueError("Trace includes a wrong or validation pair")
            exposure[row["style_id"]] += 1
        val_ids = set(preflight["validation_identities"])
        if len(val_ids) != 4 or val_ids & set(preflight["train_identities"]):
            raise ValueError("Identity split leakage")
        if len(meta["pairs"]) != 20 or len(meta["records"]) != 40:
            raise ValueError("Evaluation does not have 20 Base and adapter pairs")
        record_by_key = {(item["pair_id"], item["mode"]): item for item in meta["records"]}
        per_style = defaultdict(lambda: defaultdict(list))
        raw_outside_mae = defaultdict(list)
        final_outside_changed = 0
        for pair in meta["pairs"]:
            row = by_id[pair]
            if row["split"] != "validation" or row["identity_id"] not in val_ids:
                raise ValueError("Evaluation pair is not held out")
            parent = parents[row["parent_pair_id"]]
            if parent["identity_id"] != row["identity_id"] or parent["style_id"] != row["style_id"]:
                raise ValueError("Evaluation parent mismatch")
            reference = np.asarray(load_image(localized, f"validation/reference/{pair}.png"), dtype=np.int16)
            target = np.asarray(load_image(localized, f"validation/target/{pair}.png"), dtype=np.int16)
            nail = np.asarray(load_image(localized, f"validation/masks/{pair}.png", "L")) > 127
            if not nail.any():
                raise ValueError("Empty evaluation nail mask")
            for mode in ("base", "adapter"):
                member = f"{pair}/{mode}.png"
                record = record_by_key[(pair, mode)]
                if member_hash(evaluation, member) != record["output_sha256"]:
                    raise ValueError(f"Generated output hash mismatch: {member}")
                generated = np.asarray(load_image(evaluation, member), dtype=np.int16)
                mae = float(np.abs(generated - target)[nail].mean())
                if abs(mae - record["nail_target_mae"]) > 0.002:
                    raise ValueError(f"Nail MAE metadata mismatch: {member}")
                per_style[row["style_id"]][mode].append(mae)
                raw_outside_mae[mode].append(float(np.abs(generated - reference)[~nail].mean()))
            original = np.asarray(load_image(approved,
                f"validation/reference/{parent['pair_id']}.png"))
            full_mask = load_image(approved, f"validation/masks/{parent['pair_id']}.png", "L")
            selected_mask = np.asarray(original_nail_mask(full_mask, row["transform"])) > 127
            final = np.asarray(load_image(evaluation, f"{pair}/final_fullhand.png"))
            final_outside_changed += int(np.count_nonzero(np.any(original[~selected_mask] != final[~selected_mask], axis=1)))
        if final_outside_changed != 0:
            raise ValueError("A final composite changed outside-nail pixels")
        log = evidence.read("logs/train.log").decode(errors="replace")
        losses = [float(value) for value in re.findall(r"loss:\s*([+\-]?\d+(?:\.\d+)?(?:e[+\-]?\d+)?)", log, re.I)]
        if not losses or not all(math.isfinite(value) for value in losses):
            raise ValueError("Training loss missing or nonfinite")
        style_results = {}
        for style in STYLES:
            base, adapter = per_style[style]["base"], per_style[style]["adapter"]
            if len(base) != 4 or len(adapter) != 4:
                raise ValueError(f"Incomplete held-out style: {style}")
            style_results[style] = {"base_nail_mae_mean": round(float(np.mean(base)), 3),
                "adapter_nail_mae_mean": round(float(np.mean(adapter)), 3),
                "adapter_minus_base_mae": round(float(np.mean(adapter) - np.mean(base)), 3),
                "adapter_better_hands": sum(a < b for a, b in zip(adapter, base)),
                "pair_nail_mae": [{"identity_id": identity, "base": round(b, 3), "adapter": round(a, 3)}
                    for identity, b, a in zip(sorted(val_ids), base, adapter)]}
        return {"status": "ARTIFACTS_VERIFIED_VISUAL_REVIEW_REQUIRED",
            "evidence_sha256": file_hash(evidence_path), "evaluation_sha256": file_hash(evaluation_path),
            "checkpoint_sha256": manifest["checkpoint_sha256"],
            "steps": len(trace), "unique_training_pairs_seen": len({row["pair_id"] for row in trace}),
            "training_style_exposure": dict(exposure),
            "train_identities": len(preflight["train_identities"]), "validation_identities": sorted(val_ids),
            "training_seconds_including_load": summary["elapsed_seconds_including_load"],
            "gpu_peak_mib": summary["whole_gpu_peak_mib_observed"],
            "loss_observations": len(losses), "loss_first": losses[0], "loss_last": losses[-1],
            "raw_outside_nail_mae_mean": {mode: round(float(np.mean(values)), 3)
                                         for mode, values in raw_outside_mae.items()},
            "final_outside_nail_changed_pixels": final_outside_changed,
            "held_out_pairs": len(meta["pairs"]), "per_style": style_results,
            "runtime": runtime, "evaluation_settings": {key: meta[key]
                for key in ("seed", "inference_steps", "guidance")}}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--evaluation", type=Path, required=True)
    parser.add_argument("--approved", type=Path, required=True)
    parser.add_argument("--localized", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = verify(args.evidence, args.evaluation, args.approved, args.localized)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: result[key] for key in ("status", "steps", "unique_training_pairs_seen",
        "checkpoint_sha256", "training_style_exposure", "final_outside_nail_changed_pixels", "per_style")}, indent=2))


if __name__ == "__main__":
    main()
