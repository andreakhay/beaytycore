"""Isolated FLUX.2 Klein Base makeup baseline, without any LoRA.

Use --phase plan locally. Run the three-style pilot on Kaggle, then stop for review.
Portraits stay outside Git. No output is accepted without human review.
"""

import argparse
from datetime import datetime, timezone
import faulthandler
import hashlib
import json
from pathlib import Path
import shutil
import sys
import time
import traceback


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from app.makeup_styles import MAKEUP_STYLES, base_prompt  # noqa: E402


MODEL = "black-forest-labs/FLUX.2-klein-base-4B"
MODEL_REVISION = "a3b4f4849157f664bdbc776fd7453c2783562f4d"
PILOT_STYLE_IDS = ("natural_makeup", "soft_glam", "smoky_glam")
SIZE, STEPS, GUIDANCE, SEED = 512, 20, 4.0, 1977
DEFAULT_OUTPUT = Path("/kaggle/working/makeup_base_001")


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def portrait_paths(directory: Path) -> list[Path]:
    from PIL import Image

    if not directory.is_dir():
        raise ValueError(f"Portrait directory does not exist: {directory}")
    paths = sorted(path for path in directory.iterdir()
                   if path.is_file() and path.suffix.lower() in {".jpg", ".jpeg", ".png"})
    if not paths:
        raise ValueError("Add at least one JPG or PNG portrait to the input directory")
    if len({path.stem.lower() for path in paths}) != len(paths):
        raise ValueError("Portrait filenames need distinct stems")
    if any(not path.stem.replace("_", "").replace("-", "").isalnum() for path in paths):
        raise ValueError("Portrait filename stems must contain only letters, numbers, _ or -")
    for path in paths:
        if path.stat().st_size == 0 or path.stat().st_size > 8 * 1024 * 1024:
            raise ValueError(f"Portrait must be between 1 byte and 8 MB: {path}")
        try:
            with Image.open(path) as image:
                if (image.format not in {"JPEG", "PNG"}
                        or not all(64 <= side <= 4096 for side in image.size)
                        or image.width * image.height > 16_777_216):
                    raise ValueError(f"Unsupported portrait format or dimensions: {path}")
                image.verify()
        except (OSError, SyntaxError) as exc:
            raise ValueError(f"Unreadable portrait: {path}") from exc
    return paths


def jobs(paths: list[Path], phase: str) -> list[tuple[Path, object]]:
    style_by_id = {style.id: style for style in MAKEUP_STYLES}
    chosen = [style_by_id[style_id] for style_id in PILOT_STYLE_IDS]
    return [(path, style) for path in paths for style in chosen]


def expected_metadata(path: Path, style, source_sha256: str) -> dict:
    return {
        "portrait_id": path.stem,
        "source_identity_id": path.stem,
        "style_id": style.id,
        "style_name": style.name,
        "style_status": style.status,
        "source_file_sha256": source_sha256,
        "prompt": base_prompt(style),
        "base_model_id": MODEL,
        "base_model_revision": MODEL_REVISION,
        "adapter_id": None,
        "lora_active": False,
        "seed": SEED,
        "width": SIZE,
        "height": SIZE,
        "steps": STEPS,
        "guidance": GUIDANCE,
        "dtype": "float16",
        "cpu_offload": True,
        "preprocessing": "EXIF transpose, RGB conversion, aspect-preserving pad to 512x512 with RGB(245,245,245)",
    }


def review_sheets(output: Path, paths: list[Path]) -> list[str]:
    from PIL import Image, ImageDraw, ImageOps

    if not any((output / path.stem / style_id / "generated.png").is_file()
               for path in paths for style_id in PILOT_STYLE_IDS):
        return []
    styles = {style.id: style for style in MAKEUP_STYLES}
    cell_width, cell_height = 320, 340
    sheet = Image.new("RGB", (cell_width * 4, cell_height * len(paths)), "white")
    draw = ImageDraw.Draw(sheet)
    for row, path in enumerate(paths):
        cells = [(output / path.stem / "source.png", "Original")]
        cells.extend((output / path.stem / style_id / "generated.png", styles[style_id].name)
                     for style_id in PILOT_STYLE_IDS)
        for column, (image_path, label) in enumerate(cells):
            x, y = column * cell_width, row * cell_height
            draw.text((x + 8, y + 6), f"{path.stem} | {label}", fill="black")
            if image_path.is_file():
                with Image.open(image_path) as image:
                    thumbnail = ImageOps.contain(image.convert("RGB"), (312, 300))
                sheet.paste(thumbnail, (x + (cell_width - thumbnail.width) // 2, y + 28))
            else:
                draw.text((x + 8, y + 40), "NOT GENERATED", fill="red")
    sheet_path = output / "review_sheets" / "pilot_contact_sheet.jpg"
    sheet_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(sheet_path, quality=90)
    return [str(sheet_path)]


def run(args: argparse.Namespace) -> None:
    paths = portrait_paths(args.inputs)
    if len(paths) != 3:
        raise ValueError(f"MAKEUP-BASE-001 pilot requires exactly 3 portraits; found {len(paths)}")
    selected = jobs(paths, args.phase)
    plan = {
        "experiment": "MAKEUP-BASE-001", "phase": args.phase,
        "base_model_id": MODEL, "base_model_revision": MODEL_REVISION,
        "adapter_id": None, "lora_active": False, "portrait_count": len(paths),
        "job_count": len(selected), "styles": list(PILOT_STYLE_IDS),
        "portraits": [{"id": path.stem, "file_sha256": digest(path)} for path in paths],
        "job_configurations": [expected_metadata(path, style, digest(path))
                               for path, style in selected],
    }
    if args.phase == "plan":
        print(json.dumps(plan, indent=2))
        return

    import torch
    import diffusers
    from diffusers import Flux2KleinPipeline
    from PIL import Image, ImageOps
    from transformers import logging as transformers_logging

    if not torch.cuda.is_available():
        raise RuntimeError("CUDA is unavailable. Run the pilot in a Kaggle GPU session")
    transformers_logging.disable_progress_bar()
    args.output.mkdir(parents=True, exist_ok=True)
    plan_path = args.output / f"plan_{args.phase}.json"
    if plan_path.exists():
        prior = json.loads(plan_path.read_text(encoding="utf-8"))
        if prior["portraits"] != plan["portraits"] or prior["base_model_revision"] != MODEL_REVISION:
            raise RuntimeError("Existing output belongs to different portraits or model revision")
    write_json(plan_path, plan)

    prepared = []
    for path, style in selected:
        folder = args.output / path.stem / style.id
        output_path = folder / "generated.png"
        metadata_path = folder / "generation.json"
        if (folder / "failure.json").exists():
            raise RuntimeError(f"Previous failure needs inspection before rerun: {folder}")
        expected = expected_metadata(path, style, digest(path))
        if output_path.exists() or metadata_path.exists():
            if not output_path.is_file() or not metadata_path.is_file():
                raise RuntimeError(f"Partial result; inspect before rerun: {folder}")
            recorded = json.loads(metadata_path.read_text(encoding="utf-8"))
            if (any(recorded.get(key) != value for key, value in expected.items())
                    or recorded.get("output_sha256") != digest(output_path)
                    or recorded.get("success") is not True):
                raise RuntimeError(f"Existing result failed provenance check: {folder}")
            continue
        prepared.append((path, style, folder, expected))
    if not prepared:
        print("All selected outputs already exist with matching hashes")
        print("Review sheets:", review_sheets(args.output, paths))
        return

    print(f"Loading Base for {len(prepared)} jobs. No adapter will be loaded.", flush=True)
    started = time.monotonic()
    trace_path = args.output / "base_load_trace.log"
    with trace_path.open("a", encoding="utf-8") as trace:
        trace.write(f"Base load started {datetime.now(timezone.utc).isoformat()}\n")
        trace.flush()
        faulthandler.dump_traceback_later(180, repeat=True, file=trace)
        try:
            pipe = Flux2KleinPipeline.from_pretrained(
                MODEL, revision=MODEL_REVISION, torch_dtype=torch.float16,
                cache_dir="/tmp/hf-cache/hub")
            pipe.enable_model_cpu_offload(gpu_id=0)
        except Exception:
            write_json(args.output / "base_load_failure.json", {
                "base_model_id": MODEL, "base_model_revision": MODEL_REVISION,
                "adapter_id": None, "lora_active": False, "success": False,
                "runtime_seconds": round(time.monotonic() - started, 2),
                "failed_utc": datetime.now(timezone.utc).isoformat(),
                "error": traceback.format_exc(),
            })
            raise
        finally:
            faulthandler.cancel_dump_traceback_later()
    write_json(args.output / "runtime.json", {
        "python": sys.version, "torch": torch.__version__, "diffusers": diffusers.__version__,
        "cuda": torch.version.cuda,
        "gpu": torch.cuda.get_device_name(0), "model_load_seconds": round(time.monotonic() - started, 2),
        "base_model_id": MODEL, "base_model_revision": MODEL_REVISION,
        "adapter_id": None, "lora_active": False,
        "created_utc": datetime.now(timezone.utc).isoformat(),
    })
    for path, style, folder, expected in prepared:
        folder.mkdir(parents=True, exist_ok=True)
        original_path = args.output / path.stem / f"original{path.suffix.lower()}"
        if original_path.exists():
            if digest(original_path) != expected["source_file_sha256"]:
                raise RuntimeError(f"Original portrait changed: {original_path}")
        else:
            shutil.copyfile(path, original_path)
        source_path = args.output / path.stem / "source.png"
        with Image.open(path) as raw:
            source = ImageOps.pad(ImageOps.exif_transpose(raw).convert("RGB"), (SIZE, SIZE),
                                  method=Image.Resampling.LANCZOS, color=(245, 245, 245))
        if source_path.exists():
            with Image.open(source_path) as previous:
                if previous.convert("RGB").tobytes() != source.tobytes():
                    raise RuntimeError(f"Normalized source changed: {source_path}")
        else:
            source.save(source_path)
        torch.cuda.reset_peak_memory_stats(0)
        start = time.monotonic()
        started_utc = datetime.now(timezone.utc).isoformat()
        try:
            result = pipe(
                prompt=expected["prompt"], image=source, width=SIZE, height=SIZE,
                num_inference_steps=STEPS, guidance_scale=GUIDANCE,
                generator=torch.Generator(device="cuda").manual_seed(SEED),
            ).images[0]
            output_path = folder / "generated.png"
            result.convert("RGB").save(output_path)
            write_json(folder / "generation.json", {
                **expected, "normalized_source_sha256": digest(source_path),
                "output_sha256": digest(output_path), "success": True,
                "source_original_path": str(original_path),
                "normalized_source_path": str(source_path),
                "generated_image_path": str(output_path),
                "started_utc": started_utc,
                "finished_utc": datetime.now(timezone.utc).isoformat(),
                "runtime_seconds": round(time.monotonic() - start, 2),
                "peak_gpu_allocated_bytes": torch.cuda.max_memory_allocated(0),
                "generated_utc": datetime.now(timezone.utc).isoformat(),
                "review_status": "PENDING_MANUAL_REVIEW",
            })
            print(f"{path.stem} {style.id}: {time.monotonic() - start:.1f}s", flush=True)
        except Exception:
            write_json(folder / "failure.json", {
                **expected, "success": False, "error": traceback.format_exc(),
                "source_original_path": str(original_path),
                "normalized_source_path": str(source_path),
                "normalized_source_sha256": digest(source_path),
                "generated_image_path": None,
                "started_utc": started_utc,
                "runtime_seconds": round(time.monotonic() - start, 2),
                "failed_utc": datetime.now(timezone.utc).isoformat(),
                "review_status": "GENERATION_FAILURE",
            })
            raise
        review_sheets(args.output, paths)
    print("Review sheets:", review_sheets(args.output, paths))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase", choices=("plan", "pilot"), required=True)
    parser.add_argument("--inputs", type=Path, required=True, help="Directory of consented portrait files")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    run(parser.parse_args())


if __name__ == "__main__":
    main()
