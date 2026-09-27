"""Isolated, gated DATA-M001 FLUX.2 Klein Base inpainting pilot on Kaggle T4.

Run --phase verify first. Only --phase generate creates images; it requires a
successful verify record from the same Kaggle working directory.
"""

import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import shutil
import sys
import time
import traceback
from zipfile import ZIP_DEFLATED, ZipFile


STYLES = ("natural_makeup", "soft_glam", "smoky_glam", "classic_red_lip")
IDS = ("003025", "054109")
REVISION = "a3b4f4849157f664bdbc776fd7453c2783562f4d"


def digest(path):
    value = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def save(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def now():
    return datetime.now(timezone.utc).isoformat()


def archive(output):
    target = output.parent / f"{output.name}_results.zip"
    with ZipFile(target, "w", ZIP_DEFLATED) as zipped:
        for path in sorted(output.rglob("*")):
            if path.is_file():
                zipped.write(path, path.relative_to(output).as_posix())
    return target


def validate(inputs):
    plan_path = inputs / "plan.json"
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    if plan["model_id"] != "black-forest-labs/FLUX.2-klein-base-4B" or plan["model_revision"] != REVISION:
        raise ValueError("Unpinned or unexpected model")
    if plan["pipeline_class"] != "Flux2KleinInpaintPipeline" or plan["diffusers_version"] != "0.40.0":
        raise ValueError("Unexpected pipeline or Diffusers version")
    inf = plan["inference"]
    if inf["adapter_id"] is not None or inf["lora_active"] is not False:
        raise ValueError("LoRA must be inactive")
    if inf["width"] != 512 or inf["height"] != 512 or inf["steps"] != 20 or inf["guidance"] != 4.0:
        raise ValueError("Unexpected inference settings")
    jobs = plan["jobs"]
    if len(jobs) != 8 or {(j["identity_id"], j["style_id"]) for j in jobs} != {
        (identity, style) for identity in IDS for style in STYLES
    }:
        raise ValueError("Pilot must be exactly two identities by four styles")
    from PIL import Image
    for job in jobs:
        if job["split"] != "TRAIN":
            raise ValueError("Validation identity in pilot")
        for field, hash_field in (("source_path", "source_sha256"), ("mask_path", "mask_sha256")):
            path = inputs / job[field]
            if digest(path) != job[hash_field]:
                raise ValueError(f"Hash mismatch: {path}")
        with Image.open(inputs / job["source_path"]) as image:
            if image.size != (512, 512):
                raise ValueError("Source must be 512 square")
        with Image.open(inputs / job["mask_path"]) as mask:
            if mask.size != (512, 512) or mask.mode != "L":
                raise ValueError("Mask must be 512 square grayscale")
    return plan, digest(plan_path)


def load_pipeline(plan):
    import torch
    import diffusers
    from diffusers import Flux2KleinInpaintPipeline
    from diffusers.pipelines.flux2.image_processor import Flux2ImageProcessor

    if diffusers.__version__ != "0.40.0":
        raise RuntimeError(f"Expected Diffusers 0.40.0, got {diffusers.__version__}")
    if not torch.cuda.is_available() or "T4" not in torch.cuda.get_device_name(0):
        raise RuntimeError("This gate requires a Kaggle Tesla T4")
    started = time.monotonic()
    pipe = Flux2KleinInpaintPipeline.from_pretrained(
        plan["model_id"], revision=plan["model_revision"], torch_dtype=torch.float16,
        cache_dir="/tmp/hf-cache/hub")
    pipe.enable_model_cpu_offload(gpu_id=0)
    # Diffusers 0.40 defaults to do_binarize=True, which would erase the soft
    # parser values. Replace only the mask preprocessor, not model components.
    old = pipe.mask_processor
    pipe.mask_processor = Flux2ImageProcessor(
        vae_scale_factor=old.config.vae_scale_factor,
        vae_latent_channels=old.config.vae_latent_channels,
        do_normalize=False, do_binarize=False,
        do_convert_rgb=False, do_convert_grayscale=True)
    if pipe.mask_processor.config.do_binarize is not False:
        raise RuntimeError("Soft mask preprocessing did not stay enabled")
    runtime = {"success": True, "verified_utc": now(), "load_seconds": round(time.monotonic() - started, 2),
               "gpu": torch.cuda.get_device_name(0), "torch": torch.__version__,
               "diffusers": diffusers.__version__, "python": sys.version,
               "pipeline_class": type(pipe).__name__, "model_id": plan["model_id"],
               "model_revision": plan["model_revision"], "dtype": "float16",
               "cpu_offload": True, "mask_processor_do_binarize": False,
               "lora_active": False, "adapter_id": None}
    if runtime["pipeline_class"] != "Flux2KleinInpaintPipeline":
        raise RuntimeError("Wrong pipeline class loaded")
    return pipe, runtime


def sheet(output, identity, jobs):
    from PIL import Image, ImageDraw
    canvas = Image.new("RGB", (512 * 3, 548 * 4), "white")
    draw = ImageDraw.Draw(canvas)
    for row, job in enumerate(j for j in jobs if j["identity_id"] == identity):
        paths = (output / job["source_path"], output / job["mask_path"],
                 output / "targets" / identity / f"{job['style_id']}.png")
        for col, path in enumerate(paths):
            if path.is_file():
                with Image.open(path) as image:
                    canvas.paste(image.convert("RGB"), (col * 512, row * 548))
        draw.text((6, row * 548 + 516), f"{identity} | {job['style_name']} | PENDING HUMAN REVIEW", fill="black")
    dest = output / "review_sheets" / f"{identity}.jpg"
    dest.parent.mkdir(exist_ok=True)
    canvas.save(dest, quality=94)


def run(inputs, output, phase):
    plan, plan_hash = validate(inputs)
    output.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(inputs / "plan.json", output / "plan.json")
    for job in plan["jobs"]:
        for field in ("source_path", "mask_path"):
            destination = output / job[field]
            destination.parent.mkdir(parents=True, exist_ok=True)
            if not destination.exists():
                shutil.copyfile(inputs / job[field], destination)
    gate_path = output / "load_gate.json"
    if phase == "verify":
        if gate_path.exists():
            raise ValueError("Load gate exists; use a fresh output directory for a new verification")
        try:
            pipe, runtime = load_pipeline(plan)
            del pipe
            runtime["plan_sha256"] = plan_hash
            save(gate_path, runtime)
            print(json.dumps(runtime, indent=2))
        except Exception:
            save(gate_path, {"success": False, "plan_sha256": plan_hash, "failed_utc": now(),
                             "error": traceback.format_exc(), "lora_active": False})
            print("Load failed; no generations attempted. Artifacts:", archive(output))
            raise
        print("Load verified. No images generated. Artifacts:", archive(output))
        return
    gate = json.loads(gate_path.read_text(encoding="utf-8")) if gate_path.exists() else {}
    if gate.get("success") is not True or gate.get("plan_sha256") != plan_hash:
        raise ValueError("A successful load-only verification for this exact plan is required")
    save(output / "progress.json", {"phase": "LOADING_MODEL", "updated_utc": now(),
                                    "attempted": 0, "completed": 0, "total": len(plan["jobs"])})
    print("Loading pinned inpaint Base; no LoRA. This phase produces no target files.", flush=True)
    pipe, runtime = load_pipeline(plan)
    if runtime["gpu"] != gate["gpu"] or runtime["model_revision"] != gate["model_revision"]:
        raise ValueError("Verification/runtime mismatch")
    print("Model loaded. Starting exactly eight inpaint jobs.", flush=True)
    from PIL import Image
    import numpy as np
    import torch
    records = []
    for job in plan["jobs"]:
        identity, style_id = job["identity_id"], job["style_id"]
        dest = output / "targets" / identity / f"{style_id}.png"
        sidecar = dest.with_suffix(".json")
        if sidecar.exists() or dest.exists():
            raise ValueError(f"Refusing to overwrite existing attempt: {dest}")
        dest.parent.mkdir(parents=True, exist_ok=True)
        save(output / "progress.json", {"phase": "GENERATING", "updated_utc": now(),
                                        "identity_id": identity, "style_id": style_id,
                                        "attempted": len(records), "completed": len(records),
                                        "total": len(plan["jobs"])})
        print(f"Starting {identity} {style_id} ({len(records) + 1}/{len(plan['jobs'])})", flush=True)
        record = {**job, "model_id": plan["model_id"], "model_revision": plan["model_revision"],
                  "pipeline_class": "Flux2KleinInpaintPipeline", "inference": plan["inference"],
                  "started_utc": now(), "success": False, "review_state": "PENDING_HUMAN_REVIEW",
                  "lora_active": False, "adapter_id": None, "output_path": str(dest.relative_to(output)).replace("\\", "/")}
        tick = time.monotonic()
        try:
            with Image.open(inputs / job["source_path"]) as image:
                original = image.convert("RGB")
            with Image.open(inputs / job["mask_path"]) as image:
                mask = image.convert("L")
            generated = pipe(prompt=job["prompt"], image=original, mask_image=mask,
                             width=512, height=512, strength=plan["inference"]["strength"],
                             num_inference_steps=20, guidance_scale=4.0,
                             generator=torch.Generator(device="cpu").manual_seed(1977),
                             padding_mask_crop=None).images[0]
            generated.save(dest)
            delta = np.any(np.asarray(generated.convert("RGB"), np.int16) !=
                           np.asarray(original, np.int16), axis=2)
            outside = np.asarray(mask) == 0
            record.update(success=True, output_sha256=digest(dest),
                          changed_pixels_outside_zero_mask=int(np.count_nonzero(delta & outside)))
        except Exception:
            record["error"] = traceback.format_exc()
        finally:
            record["ended_utc"] = now()
            record["duration_seconds"] = round(time.monotonic() - tick, 2)
            save(sidecar, record)
            records.append(record)
            print(identity, style_id, "OK" if record["success"] else "FAILED", record["duration_seconds"], flush=True)
    for identity in IDS:
        sheet(output, identity, plan["jobs"])
    summary = {"attempted": len(records), "successful": sum(r["success"] for r in records),
               "failed": sum(not r["success"] for r in records),
               "review_state": "PENDING_HUMAN_REVIEW", "lora_active": False,
               "no_larger_generation_authorized": True}
    save(output / "summary.json", summary)
    save(output / "progress.json", {"phase": "COMPLETE", "updated_utc": now(), **summary})
    print(json.dumps(summary, indent=2))
    print("Download before ending Kaggle:", archive(output))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--inputs", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--phase", choices=("verify", "generate"), required=True)
    args = parser.parse_args()
    run(args.inputs, args.output, args.phase)
