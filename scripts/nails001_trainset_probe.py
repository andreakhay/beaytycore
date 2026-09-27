"""Inference-only NAILS-001 step-25 probe on selected DATA-N001 train pairs.

No pair is asserted to have been sampled during training: the original run did
not retain sampler indices. This probe must never be used to claim memorization.
"""

import argparse
from hashlib import sha256
from io import BytesIO
import json
import os
from pathlib import Path
import time
from zipfile import ZipFile, ZIP_DEFLATED

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

DATA_SHA = "d37b68bc3e06c6ea1b1b013424dd813aafbef83db222cf9223e229d33ad105bb"
CHECKPOINT_SHA = "34bf82238dfcc8e6365cd9fa6b63d36700312780f2e396dc6d91f7cc3f829c91"
MODEL = "black-forest-labs/FLUX.2-klein-base-4B"
REVISION = "a3b4f4849157f664bdbc776fd7453c2783562f4d"
IDENTITIES = ("0000000", "0000055", "0000514", "0001021")
STYLES = ("classic_red", "nude_pink", "glossy_black", "french_tip", "pink_ombre")
SEED = 1977
STEPS = 20
GUIDANCE = 4.0


def digest(path):
    h = sha256()
    with Path(path).open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def image_from_archive(archive, member, expected_sha, mode):
    data = archive.read(member)
    if sha256(data).hexdigest() != expected_sha:
        raise ValueError(f"DATA-N001 member hash mismatch: {member}")
    with Image.open(BytesIO(data)) as image:
        value = image.convert(mode)
    if value.size != (512, 512):
        raise ValueError(f"Wrong image size: {member}")
    return value


def masked_mae(actual, target, mask):
    pixels = np.asarray(actual.convert("RGB"), dtype=np.int16)
    expected = np.asarray(target.convert("RGB"), dtype=np.int16)
    return round(float(np.abs(pixels - expected)[mask].mean()), 3)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, required=True, help="Unmodified DATA-N001-final.zip")
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("/kaggle/working/nails001-trainset-probe"))
    parser.add_argument("--preflight-only", action="store_true")
    args = parser.parse_args()
    if not args.preflight_only and args.output.exists() and any(args.output.iterdir()):
        raise ValueError("Output exists; refusing to overwrite probe evidence")
    if digest(args.data) != DATA_SHA or digest(args.checkpoint) != CHECKPOINT_SHA:
        raise ValueError("Approved dataset or step-25 checkpoint hash mismatch")
    with ZipFile(args.data) as archive:
        if archive.testzip() is not None:
            raise ValueError("DATA-N001 CRC failure")
        manifest = json.loads(archive.read("manifests/pairs.json"))
        rows = [row for row in manifest if row["split"] == "train"
                and row["identity_id"] in IDENTITIES and row["style_id"] in STYLES]
        if len(rows) != 20 or {row["identity_id"] for row in rows} != set(IDENTITIES):
            raise ValueError("Selected diagnostic train pairs are missing")
        if any(row["review_status"] != "ACCEPT" for row in rows):
            raise ValueError("Unapproved diagnostic pair")
        rows.sort(key=lambda row: (IDENTITIES.index(row["identity_id"]), STYLES.index(row["style_id"])))
        for row in rows:
            pair = row["pair_id"]
            image_from_archive(archive, f"train/reference/{pair}.png", row["reference_sha256"], "RGB")
            image_from_archive(archive, f"train/target/{pair}.png", row["target_sha256"], "RGB")
            image_from_archive(archive, f"train/masks/{pair}.png", row["mask_sha256"], "L")
            if archive.read(f"train/target/{pair}.txt").decode("utf-8").strip() != row["caption"]:
                raise ValueError(f"Caption mismatch: {pair}")
        if args.preflight_only:
            print(json.dumps({"status": "PREFLIGHT_ONLY", "pairs": [row["pair_id"] for row in rows],
                              "exposure_status": "UNKNOWN_UNLOGGED_SAMPLER"}, indent=2))
            return
        import torch
        import diffusers
        from diffusers import Flux2KleinPipeline
        if not torch.cuda.is_available():
            raise RuntimeError("CUDA GPU required for inference-only probe")
        if diffusers.__version__ != "0.39.0.dev0" or torch.__version__ != "2.10.0+cu128":
            raise RuntimeError("Expected the step-25 evaluation Torch/Diffusers runtime")
        if not os.environ.get("HF_TOKEN"):
            try:
                from kaggle_secrets import UserSecretsClient
                token = UserSecretsClient().get_secret("HF_TOKEN")
                if token:
                    os.environ["HF_TOKEN"] = token
            except Exception:
                pass
        args.output.mkdir(parents=True)
        pipe = Flux2KleinPipeline.from_pretrained(
            MODEL, revision=REVISION, torch_dtype=torch.float16, cache_dir="/tmp/hf-cache/hub")
        pipe.enable_model_cpu_offload(gpu_id=0)
        records = []
        for mode in ("base", "adapter"):
            if mode == "adapter":
                pipe.load_lora_weights(str(args.checkpoint.parent), weight_name=args.checkpoint.name)
            for row in rows:
                pair = row["pair_id"]
                original = image_from_archive(archive, f"train/reference/{pair}.png", row["reference_sha256"], "RGB")
                target = image_from_archive(archive, f"train/target/{pair}.png", row["target_sha256"], "RGB")
                mask = image_from_archive(archive, f"train/masks/{pair}.png", row["mask_sha256"], "L")
                caption_bytes = archive.read(f"train/target/{pair}.txt")
                if caption_bytes.decode("utf-8").strip() != row["caption"]:
                    raise ValueError(f"Caption mismatch: {pair}")
                start = time.monotonic()
                generated = pipe(prompt=row["caption"], image=original, width=512, height=512,
                                 num_inference_steps=STEPS, guidance_scale=GUIDANCE,
                                 generator=torch.Generator(device="cuda").manual_seed(SEED)).images[0].convert("RGB")
                folder = args.output / pair
                folder.mkdir(exist_ok=True)
                path = folder / f"{mode}.png"
                generated.save(path)
                hard = np.asarray(mask) > 127
                records.append({"pair_id": pair, "identity_id": row["identity_id"], "style_id": row["style_id"],
                                "mode": mode, "target_masked_mae": masked_mae(generated, target, hard),
                                "output_sha256": digest(path), "seconds": round(time.monotonic() - start, 2)})
                print(f"{mode} {pair}: {records[-1]['target_masked_mae']} nail MAE", flush=True)
        for row in rows:
            pair = row["pair_id"]
            folder = args.output / pair
            original = image_from_archive(archive, f"train/reference/{pair}.png", row["reference_sha256"], "RGB")
            target = image_from_archive(archive, f"train/target/{pair}.png", row["target_sha256"], "RGB")
            mask = image_from_archive(archive, f"train/masks/{pair}.png", row["mask_sha256"], "L")
            with Image.open(folder / "base.png") as image:
                base = image.convert("RGB")
            with Image.open(folder / "adapter.png") as image:
                adapter = image.convert("RGB")
            hard = mask.point(lambda value: 255 if value > 127 else 0)
            feather = Image.fromarray(np.minimum(np.asarray(hard), np.asarray(hard.filter(ImageFilter.GaussianBlur(1.2)))))
            final = Image.composite(adapter, original, feather)
            if np.any(np.asarray(final)[np.asarray(mask) <= 127] != np.asarray(original)[np.asarray(mask) <= 127]):
                raise ValueError(f"Composite changed non-nail pixels: {pair}")
            final.save(folder / "final.png")
            sheet = Image.new("RGB", (2560, 540), "white")
            draw = ImageDraw.Draw(sheet)
            for index, (label, image) in enumerate((("Original", original), ("Approved target", target),
                    ("Base result", base), ("Step-25 adapter", adapter), ("Final nail-only composite", final))):
                sheet.paste(image, (index * 512, 0))
                draw.text((index * 512 + 5, 518), label, fill="black")
            sheet.save(folder / "comparison.jpg", quality=94)
        metadata = {"status": "PENDING_VISUAL_REVIEW", "exposure_status": "UNKNOWN_UNLOGGED_SAMPLER",
                    "dataset_sha256": DATA_SHA, "checkpoint_sha256": CHECKPOINT_SHA,
                    "base_revision": REVISION, "torch": torch.__version__, "diffusers": diffusers.__version__,
                    "gpu": torch.cuda.get_device_name(0), "seed": SEED, "steps": STEPS, "guidance": GUIDANCE,
                    "identities": IDENTITIES, "pairs": [row["pair_id"] for row in rows], "records": records}
        (args.output / "metadata.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    archive_out = args.output.parent / "NAILS-001-step025-trainset-probe-results.zip"
    if archive_out.exists():
        raise ValueError("Results ZIP exists; refusing to overwrite")
    with ZipFile(archive_out, "w", ZIP_DEFLATED) as output:
        for file in sorted(args.output.rglob("*")):
            if file.is_file():
                output.write(file, file.relative_to(args.output).as_posix())
    print(json.dumps({"status": "PENDING_VISUAL_REVIEW", "results_zip": str(archive_out),
                      "results_sha256": digest(archive_out), "pairs": len(rows)}, indent=2))


if __name__ == "__main__":
    main()
