"""Generate held out NAILS-001 review sheets; human approval remains required."""

import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys

from PIL import Image, ImageDraw, ImageOps

sys.path.insert(0, str(Path(__file__).resolve().parent))
from run_n001_kaggle import MODEL_REVISION, digest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=Path("/kaggle/working/data_n001"))
    parser.add_argument("--run", type=Path, default=Path("/kaggle/working/nails001"))
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("/kaggle/working/nails001/evaluation"))
    args = parser.parse_args()
    summary = json.loads((args.run / "run_summary.json").read_text(encoding="utf-8"))
    if summary.get("status") != "TRAINING_FINISHED_REVIEW_REQUIRED":
        raise ValueError("A completed training run is required")
    checkpoint_hash = digest(args.checkpoint)
    if checkpoint_hash not in {row["sha256"] for row in summary["checkpoints"]}:
        raise ValueError("Checkpoint is not listed in the training summary")
    if args.output.exists() and any(args.output.iterdir()):
        raise ValueError("Refusing to overwrite existing evaluation")
    args.output.mkdir(parents=True)
    import torch
    from diffusers import Flux2KleinPipeline
    model_path = Path("/tmp/hf-cache/hub/models--black-forest-labs--FLUX.2-klein-base-4B/snapshots") / MODEL_REVISION
    pipe = Flux2KleinPipeline.from_pretrained(str(model_path), torch_dtype=torch.float16)
    pipe.enable_model_cpu_offload(gpu_id=0)
    pipe.load_lora_weights(str(args.checkpoint.parent), weight_name=args.checkpoint.name)
    rows = json.loads((args.dataset / "manifests" / "pairs.json").read_text(encoding="utf-8"))
    records = []
    for row in rows:
        if row["split"] != "validation": continue
        pair_id = row["pair_id"]
        source_path = args.dataset / "validation" / "reference" / f"{pair_id}.png"
        mask_path = args.dataset / "validation" / "masks" / f"{pair_id}.png"
        if digest(source_path) != row["reference_sha256"] or digest(mask_path) != row["mask_sha256"]:
            raise ValueError(f"Validation source or mask changed: {pair_id}")
        with Image.open(source_path) as image, Image.open(mask_path) as mask_image:
            source = image.convert("RGB")
            mask = mask_image.convert("L")
        # The training pair is 512 square; inference uses the same source plus mask.
        model_output = pipe(prompt=row["caption"], image=source, width=512, height=512,
                            num_inference_steps=20, guidance_scale=4.0,
                            generator=torch.Generator(device="cuda").manual_seed(1977)).images[0].convert("RGB")
        hard = mask.point(lambda value: 255 if value > 127 else 0)
        from PIL import ImageFilter
        import numpy as np
        feather = Image.fromarray(np.minimum(np.asarray(hard), np.asarray(hard.filter(ImageFilter.GaussianBlur(1.2)))))
        final = Image.composite(model_output, source, feather)
        folder = args.output / pair_id
        folder.mkdir()
        model_output.save(folder / "model_crop_output.png")
        final.save(folder / "final_composited.png")
        sheet = Image.new("RGB", (2048, 540), "white")
        for index, image in enumerate((source, Image.merge("RGB", (mask, mask, mask)), model_output, final)):
            sheet.paste(image, (index * 512, 0))
        draw = ImageDraw.Draw(sheet)
        for index, label in enumerate(("Original", "Nail Mask", "Model Crop Output", "Final Composited Result")):
            draw.text((index * 512 + 5, 518), label, fill="black")
        sheet.save(folder / "review.jpg", quality=94)
        records.append({"pair_id": pair_id, "identity_id": row["identity_id"],
                        "style_id": row["style_id"], "source_sha256": row["reference_sha256"],
                        "model_output_sha256": digest(folder / "model_crop_output.png"),
                        "final_sha256": digest(folder / "final_composited.png"),
                        "review_status": "PENDING_HUMAN_REVIEW"})
    (args.output / "metadata.json").write_text(json.dumps({"checkpoint_sha256": checkpoint_hash,
        "model_revision": MODEL_REVISION, "records": records}, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": "PENDING_HUMAN_REVIEW", "sheets": len(records)}, indent=2))


if __name__ == "__main__": main()
