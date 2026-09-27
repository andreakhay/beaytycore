"""Independently verify the NAILS-001 step-25 inference-only train-set probe."""

from collections import Counter, defaultdict
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
from statistics import mean
from zipfile import ZipFile

import numpy as np
from PIL import Image, ImageFilter


ROOT = Path(__file__).resolve().parents[1]
RESULT = ROOT / "data/nails/work/NAILS-001-step025-trainset-probe-results.zip"
DATA = ROOT / "data/nails/work/DATA-N001-final.zip"
OUTPUT = ROOT / "docs/experiments/NAILS-001-step025-trainset-qa.json"
RESULT_SHA = "b8a3e052c8256c6cd4dee9575efc87491a8e9088d7d7b538ac6db50a7535c48f"
DATA_SHA = "d37b68bc3e06c6ea1b1b013424dd813aafbef83db222cf9223e229d33ad105bb"
CHECKPOINT_SHA = "34bf82238dfcc8e6365cd9fa6b63d36700312780f2e396dc6d91f7cc3f829c91"


def digest(path):
    h = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read_image(archive, member, mode):
    with Image.open(BytesIO(archive.read(member))) as image:
        value = image.convert(mode)
    if value.size != (512, 512):
        raise ValueError(f"Unexpected image size: {member}")
    return value


def run():
    if digest(RESULT) != RESULT_SHA or digest(DATA) != DATA_SHA:
        raise ValueError("Results or approved dataset archive hash mismatch")
    with ZipFile(RESULT) as results, ZipFile(DATA) as data:
        if results.testzip() is not None or data.testzip() is not None:
            raise ValueError("ZIP CRC failure")
        members = results.namelist()
        if any(Path(member).is_absolute() or ".." in Path(member).parts for member in members):
            raise ValueError("Unsafe result ZIP member")
        meta = json.loads(results.read("metadata.json"))
        if meta["dataset_sha256"] != DATA_SHA or meta["checkpoint_sha256"] != CHECKPOINT_SHA:
            raise ValueError("Probe metadata uses wrong dataset or adapter")
        if meta["base_revision"] != "a3b4f4849157f664bdbc776fd7453c2783562f4d":
            raise ValueError("Wrong Base revision")
        if (meta["seed"], meta["steps"], meta["guidance"]) != (1977, 20, 4.0):
            raise ValueError("Evaluation settings changed")
        manifest = {row["pair_id"]: row for row in json.loads(data.read("manifests/pairs.json"))}
        ids = meta["pairs"]
        if len(ids) != 20 or len(set(ids)) != 20 or len(meta["records"]) != 40:
            raise ValueError("Expected 20 pairs and 40 generated outputs")
        if any(manifest[pair]["split"] != "train" for pair in ids):
            raise ValueError("Probe includes non-training pair")
        actual_members = {"metadata.json"} | {f"{pair}/{name}" for pair in ids
            for name in ("base.png", "adapter.png", "final.png", "comparison.jpg")}
        if set(members) != actual_members:
            raise ValueError("Unexpected or missing result ZIP members")
        records = {(item["pair_id"], item["mode"]): item for item in meta["records"]}
        if len(records) != 40:
            raise ValueError("Duplicate metadata record")
        checked = []
        for pair in ids:
            row = manifest[pair]
            source = read_image(data, f"train/reference/{pair}.png", "RGB")
            target = read_image(data, f"train/target/{pair}.png", "RGB")
            mask = read_image(data, f"train/masks/{pair}.png", "L")
            for role, image in (("reference", source), ("target", target), ("masks", mask)):
                content = data.read(f"train/{role}/{pair}.png")
                key = {"reference": "reference_sha256", "target": "target_sha256", "masks": "mask_sha256"}[role]
                if sha256(content).hexdigest() != row[key]:
                    raise ValueError(f"Approved data member mismatch: {pair} {role}")
            if data.read(f"train/target/{pair}.txt").decode("utf-8").strip() != row["caption"]:
                raise ValueError(f"Caption mismatch: {pair}")
            hard = np.asarray(mask) > 127
            metrics = {}
            for mode in ("base", "adapter"):
                record = records[pair, mode]
                if (record["identity_id"], record["style_id"]) != (row["identity_id"], row["style_id"]):
                    raise ValueError(f"Result metadata mismatch: {pair}")
                content = results.read(f"{pair}/{mode}.png")
                if sha256(content).hexdigest() != record["output_sha256"]:
                    raise ValueError(f"Generated PNG hash mismatch: {pair} {mode}")
                generated = read_image(results, f"{pair}/{mode}.png", "RGB")
                mae = round(float(np.abs(np.asarray(generated, dtype=np.int16) -
                                         np.asarray(target, dtype=np.int16))[hard].mean()), 3)
                if mae != record["target_masked_mae"]:
                    raise ValueError(f"Nail-only MAE mismatch: {pair} {mode}")
                metrics[mode] = mae
            adapter = read_image(results, f"{pair}/adapter.png", "RGB")
            hard_image = mask.point(lambda value: 255 if value > 127 else 0)
            feather = Image.fromarray(np.minimum(np.asarray(hard_image),
                np.asarray(hard_image.filter(ImageFilter.GaussianBlur(1.2)))))
            expected_final = Image.composite(adapter, source, feather)
            final = read_image(results, f"{pair}/final.png", "RGB")
            if not np.array_equal(np.asarray(final), np.asarray(expected_final)):
                raise ValueError(f"Final composite mismatch: {pair}")
            if np.any(np.asarray(final)[~hard] != np.asarray(source)[~hard]):
                raise ValueError(f"Final composite changed outside nail mask: {pair}")
            with Image.open(BytesIO(results.read(f"{pair}/comparison.jpg"))) as sheet:
                if sheet.size != (2560, 540):
                    raise ValueError(f"Wrong comparison sheet size: {pair}")
            checked.append({"pair_id": pair, "identity_id": row["identity_id"],
                            "style_id": row["style_id"], "base_nail_mae": metrics["base"],
                            "adapter_nail_mae": metrics["adapter"],
                            "adapter_minus_base_mae": round(metrics["adapter"] - metrics["base"], 3),
                            "adapter_closer": metrics["adapter"] < metrics["base"],
                            "mask_pct": round(float(hard.mean() * 100), 4),
                            "outside_mask_changed_pixels": 0})
        by_style = defaultdict(list)
        for item in checked:
            by_style[item["style_id"]].append(item)
        report = {"status": "STRUCTURAL_QA_PASS_VISUAL_REVIEW_PENDING",
                  "result_zip_sha256": RESULT_SHA, "data_archive_sha256": DATA_SHA,
                  "checkpoint_sha256": CHECKPOINT_SHA, "pairs": len(checked),
                  "styles": dict(Counter(item["style_id"] for item in checked)),
                  "identities": sorted({item["identity_id"] for item in checked}),
                  "adapter_closer_count": sum(item["adapter_closer"] for item in checked),
                  "mean_nail_mae": {mode: round(mean(item[f"{mode}_nail_mae"] for item in checked), 3)
                                    for mode in ("base", "adapter")},
                  "by_style": {style: {"adapter_closer": sum(item["adapter_closer"] for item in group),
                                       "base_mean_mae": round(mean(item["base_nail_mae"] for item in group), 3),
                                       "adapter_mean_mae": round(mean(item["adapter_nail_mae"] for item in group), 3)}
                               for style, group in sorted(by_style.items())},
                  "records": checked}
        OUTPUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        return report


if __name__ == "__main__":
    result = run()
    print(json.dumps({key: value for key, value in result.items() if key != "records"}, indent=2))
