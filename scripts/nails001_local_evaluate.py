"""Evaluate the step-50 localized adapter on four held-out hands and five styles.

Inference only. Full-hand previews invoke the existing unchanged nail compositor
after mapping one generated fingernail back to its approved source geometry.
"""

import argparse
from hashlib import sha256
from io import BytesIO
import json
import os
from pathlib import Path
import sys
import time
from zipfile import ZipFile, ZIP_DEFLATED

import numpy as np
from PIL import Image, ImageDraw

from nails001_local_kaggle import DATA_SHA, LOCAL_NAME, MODEL_REVISION, digest


STYLES = ("french_tip", "pink_ombre", "nude_pink", "classic_red", "glossy_black")
SEED = 1977
STEPS = 20
GUIDANCE = 4.0


def image_member(archive: ZipFile, member: str, expected_sha: str, mode: str) -> Image.Image:
    content = archive.read(member)
    if sha256(content).hexdigest() != expected_sha:
        raise ValueError(f"Image hash mismatch: {member}")
    with Image.open(BytesIO(content)) as image:
        result = image.convert(mode)
    if result.size != (512, 512):
        raise ValueError(f"Wrong image dimensions: {member}")
    return result


def selected_rows(local: ZipFile) -> list[dict]:
    rows = json.loads(local.read("manifests/pairs.json"))
    selected = [row for row in rows if row["split"] == "validation" and row["finger_id"] == "index"]
    identities = sorted({row["identity_id"] for row in selected})
    if len(selected) != 20 or len(identities) != 4:
        raise ValueError("Expected one index fingernail, all five styles, four held-out identities")
    return sorted(selected, key=lambda row: (STYLES.index(row["style_id"]), row["identity_id"]))


def restore_crop(generated: Image.Image, mapping: dict) -> Image.Image:
    side = mapping["crop_side_px"]
    canvas = Image.new("RGB", (512, 512), "white")
    canvas.paste(generated.convert("RGB").resize((side, side), Image.Resampling.BICUBIC),
                 tuple(mapping["crop_box_rotated"]))
    angle = mapping["angle_degrees"]
    return (canvas.rotate(-angle, resample=Image.Resampling.BICUBIC,
            center=tuple(mapping["rotation_center_original"]), fillcolor=(255, 255, 255))
            if angle else canvas)


def original_nail_mask(full_mask: Image.Image, mapping: dict) -> Image.Image:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from backend.app.nails.geometry import nail_components
    groups = nail_components(np.asarray(full_mask) > 127)
    center = np.asarray(mapping["center"])
    group = min(groups, key=lambda part: np.linalg.norm(
        np.asarray([part[:, 1].mean(), part[:, 0].mean()]) - center))
    if np.linalg.norm(np.asarray([group[:, 1].mean(), group[:, 0].mean()]) - center) > 3:
        raise ValueError("Cannot restore original nail component")
    pixels = np.zeros((512, 512), dtype=np.uint8)
    pixels[group[:, 0], group[:, 1]] = 255
    return Image.fromarray(pixels, "L")


def run(root: Path, *, preflight_only: bool = False) -> dict:
    output = root / "nails001_local" / "evaluation_step050"
    if not preflight_only and output.exists():
        raise ValueError("Evaluation output already exists; refusing to overwrite")
    local_path, original_path = root / "DATA-N001-LOCAL-v1.zip", root / "DATA-N001-final.zip"
    bundle = json.loads((root / "local_bundle_evidence.json").read_text(encoding="utf-8"))
    if digest(local_path) != bundle["localized_archive_sha256"] or digest(original_path) != DATA_SHA:
        raise ValueError("Dataset hash changed")
    summary = json.loads((root / "nails001_local/training_summary.json").read_text(encoding="utf-8"))
    checkpoint = root / "nails001_local/checkpoints" / LOCAL_NAME / f"{LOCAL_NAME}.safetensors"
    if summary["status"] != "CHECKPOINT_READY_REVIEW_REQUIRED" or digest(checkpoint) != summary["checkpoint_sha256"]:
        raise ValueError("Step-50 checkpoint missing or changed")
    with ZipFile(local_path) as local, ZipFile(original_path) as original:
        if local.testzip() is not None or original.testzip() is not None:
            raise ValueError("Dataset ZIP CRC failure")
        rows = selected_rows(local)
        parent = {row["pair_id"]: row for row in json.loads(original.read("manifests/pairs.json"))}
        for row in rows:
            pair, split = row["pair_id"], row["split"]
            source = parent[row["parent_pair_id"]]
            if source["split"] != "validation" or source["identity_id"] != row["identity_id"]:
                raise ValueError(f"Validation split mismatch: {pair}")
            for role in ("reference", "target", "masks"):
                image_member(local, f"{split}/{role}/{pair}.png", row[f"{role if role != 'masks' else 'mask'}_sha256"],
                             "L" if role == "masks" else "RGB")
            if local.read(f"{split}/target/{pair}.txt").decode("utf-8").strip() != row["caption"]:
                raise ValueError(f"Localized caption mismatch: {pair}")
        if preflight_only:
            return {"status": "EVALUATION_PREFLIGHT_PASS", "pairs": len(rows),
                    "identities": sorted({row["identity_id"] for row in rows}),
                    "styles": list(STYLES), "checkpoint_sha256": summary["checkpoint_sha256"]}
        import torch
        import diffusers
        from diffusers import Flux2KleinPipeline
        from backend.app.nails.geometry import NailCrop, composite_nails
        if not torch.cuda.is_available():
            raise RuntimeError("Kaggle GPU required for evaluation")
        training_runtime = json.loads((root / "nails001_local/runtime.json").read_text(encoding="utf-8"))
        if torch.__version__ != training_runtime["torch_import_version"] or diffusers.__version__ != training_runtime["diffusers_import_version"]:
            raise RuntimeError("Evaluation Torch/Diffusers differ from the recorded training runtime")
        if not os.environ.get("HF_TOKEN"):
            try:
                from kaggle_secrets import UserSecretsClient
                token = UserSecretsClient().get_secret("HF_TOKEN")
                if token:
                    os.environ["HF_TOKEN"] = token
            except Exception:
                pass
        output.mkdir(parents=True)
        pipe = Flux2KleinPipeline.from_pretrained(
            "black-forest-labs/FLUX.2-klein-base-4B", revision=MODEL_REVISION,
            torch_dtype=torch.float16, cache_dir="/tmp/hf-cache/hub")
        pipe.enable_model_cpu_offload(gpu_id=0)
        records = []
        for mode in ("base", "adapter"):
            if mode == "adapter":
                pipe.load_lora_weights(str(checkpoint.parent), weight_name=checkpoint.name)
            for row in rows:
                pair = row["pair_id"]
                reference = image_member(local, f"validation/reference/{pair}.png", row["reference_sha256"], "RGB")
                target = image_member(local, f"validation/target/{pair}.png", row["target_sha256"], "RGB")
                mask = image_member(local, f"validation/masks/{pair}.png", row["mask_sha256"], "L")
                started = time.monotonic()
                result = pipe(prompt=row["caption"], image=reference, width=512, height=512,
                              num_inference_steps=STEPS, guidance_scale=GUIDANCE,
                              generator=torch.Generator(device="cuda").manual_seed(SEED)).images[0].convert("RGB")
                folder = output / pair
                folder.mkdir(exist_ok=True)
                result_path = folder / f"{mode}.png"
                result.save(result_path)
                hard = np.asarray(mask) > 127
                mae = float(np.abs(np.asarray(result, dtype=np.int16) -
                                   np.asarray(target, dtype=np.int16))[hard].mean())
                records.append({"pair_id": pair, "identity_id": row["identity_id"],
                    "finger_id": row["finger_id"], "style_id": row["style_id"],
                    "mode": mode, "nail_target_mae": round(mae, 3),
                    "output_sha256": digest(result_path),
                    "seconds": round(time.monotonic() - started, 2)})
                print(mode, pair, round(mae, 3), flush=True)
        for row in rows:
            pair = row["pair_id"]
            folder = output / pair
            source = parent[row["parent_pair_id"]]
            full_original = image_member(original,
                f"validation/reference/{source['pair_id']}.png", source["reference_sha256"], "RGB")
            full_mask = image_member(original,
                f"validation/masks/{source['pair_id']}.png", source["mask_sha256"], "L")
            single_mask = original_nail_mask(full_mask, row["transform"])
            with Image.open(folder / "adapter.png") as image:
                adapter = image.convert("RGB")
            restored = restore_crop(adapter, row["transform"])
            # Existing compositor, unchanged, with one reviewed nail island.
            final = composite_nails(full_original, restored,
                NailCrop((0, 0, 512, 512), full_original, single_mask))
            hard = np.asarray(single_mask) > 127
            if np.any(np.asarray(final)[~hard] != np.asarray(full_original)[~hard]):
                raise ValueError(f"Composite changed full-hand pixels outside nail: {pair}")
            final.save(folder / "final_fullhand.png")
            reference = image_member(local, f"validation/reference/{pair}.png", row["reference_sha256"], "RGB")
            target = image_member(local, f"validation/target/{pair}.png", row["target_sha256"], "RGB")
            with Image.open(folder / "base.png") as image:
                base = image.convert("RGB")
            sheet = Image.new("RGB", (3072, 540), "white")
            draw = ImageDraw.Draw(sheet)
            for index, (label, image) in enumerate((("Original fingertip", reference),
                ("Approved target", target), ("Base", base), ("LOCAL step 50", adapter),
                ("Original hand", full_original), ("Nail-only full hand", final))):
                sheet.paste(image, (index * 512, 0))
                draw.text((index * 512 + 5, 518), label, fill="black")
            sheet.save(folder / "comparison.jpg", quality=94)
        metadata = {"status": "PENDING_VISUAL_REVIEW", "checkpoint_sha256": summary["checkpoint_sha256"],
            "localized_archive_sha256": digest(local_path), "approved_archive_sha256": DATA_SHA,
            "base_revision": MODEL_REVISION, "torch": torch.__version__, "diffusers": diffusers.__version__,
            "gpu": torch.cuda.get_device_name(0), "seed": SEED, "inference_steps": STEPS,
            "guidance": GUIDANCE, "pairs": [row["pair_id"] for row in rows], "records": records,
            "fullhand_composite_outside_nail_changed_pixels": 0}
        (output / "metadata.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    zip_path = root / "NAILS-001-LOCAL-v1-step050-evaluation.zip"
    if zip_path.exists():
        raise ValueError("Evaluation archive exists; refusing to overwrite")
    with ZipFile(zip_path, "w", ZIP_DEFLATED) as result:
        for path in sorted(output.rglob("*")):
            if path.is_file():
                result.write(path, path.relative_to(output).as_posix())
    return {"status": "PENDING_VISUAL_REVIEW", "evaluation_zip": str(zip_path),
            "evaluation_sha256": digest(zip_path), "pairs": len(rows),
            "checkpoint_sha256": summary["checkpoint_sha256"]}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("/kaggle/working"))
    parser.add_argument("--preflight-only", action="store_true")
    args = parser.parse_args()
    print(json.dumps(run(args.root, preflight_only=args.preflight_only), indent=2))


if __name__ == "__main__":
    main()
