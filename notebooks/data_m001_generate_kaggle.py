"""DATA-M001 Base-only target generation on Kaggle T4.

Attach the prepared data_m001_kaggle_input.zip as Kaggle Input, extract it,
then run --phase plan and --phase pilot. No Hair code or LoRA is imported.
"""

import argparse
from datetime import datetime, timezone
import faulthandler
from hashlib import sha256
import json
from pathlib import Path
import shutil
import sys
import time
import traceback
from zipfile import ZIP_DEFLATED, ZipFile


def utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def digest(path: Path) -> str:
    value = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def save_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def load_input(inputs: Path) -> tuple[dict, dict]:
    config = json.loads((inputs / "config.json").read_text(encoding="utf-8"))
    manifest = json.loads((inputs / "source_manifest.json").read_text(encoding="utf-8"))
    identities = manifest["identities"]
    if len(identities) != 12 or len({row["identity_id"] for row in identities}) != 12:
        raise ValueError("Expected twelve unique frozen sources")
    if set(config["train_ids"]) & set(config["validation_ids"]):
        raise ValueError("Identity split leakage")
    if [style["id"] for style in config["styles"]] != [
        "natural_makeup", "no_makeup_makeup", "soft_glam", "smoky_glam", "dewy_peach",
        "rosy_pink", "bronze_golden_glam", "matte_nude", "classic_red_lip", "bold_evening_glam"
    ]:
        raise ValueError("Unrecognized style taxonomy")
    if config["inference"]["adapter_id"] is not None or config["inference"]["lora_active"] is not False:
        raise ValueError("DATA-M001 generation must not use any LoRA")
    for row in identities:
        if row["split"] != ("TRAIN" if row["identity_id"] in config["train_ids"] else "VALIDATION"):
            raise ValueError(f"Split mismatch: {row['identity_id']}")
        path = inputs / row["source_path"]
        if digest(path) != row["source_sha256"]:
            raise ValueError(f"Source hash mismatch: {path}")
    return config, manifest


def prompt(config: dict, style: dict) -> str:
    return f"{style['instruction']} {config['preservation_instruction']}"


def jobs(config: dict, manifest: dict, phase: str) -> list[tuple[dict, dict]]:
    by_id = {row["identity_id"]: row for row in manifest["identities"]}
    ids = config["pilot_train_ids"] if phase in {"pilot", "plan"} else [
        identity for identity in config["train_ids"] + config["validation_ids"]
        if identity not in config["pilot_train_ids"]
    ]
    return [(by_id[identity], style) for identity in ids for style in config["styles"]]


def validated_pilot_reviews(output: Path, config: dict, manifest: dict, reviews_path: Path,
                            *, require_resolved: bool) -> dict[tuple[str, str], dict]:
    data = json.loads(reviews_path.read_text(encoding="utf-8"))
    rows = data.get("reviews", [])
    expected = {(source["identity_id"], style["id"])
                for source, style in jobs(config, manifest, "pilot")}
    if len(rows) != len(expected):
        raise ValueError("Pilot needs one explicit review for each of 20 cells")
    by_key = {}
    for review in rows:
        key = (review.get("identity_id"), review.get("style_id"))
        if key not in expected or key in by_key:
            raise ValueError(f"Unknown or duplicate pilot review: {key}")
        state, attempt = review.get("state"), review.get("attempt")
        if state not in {"ACCEPT", "RETRY_ONCE", "REJECT"} or not review.get("reviewer") or not review.get("note"):
            raise ValueError(f"Explicit reviewer, note and valid state required: {key}")
        if (state == "RETRY_ONCE" and attempt != 1) or (state == "REJECT" and attempt != 2):
            raise ValueError(f"Retry once or reject attempt number invalid: {key}")
        if state == "ACCEPT" and attempt not in (1, 2):
            raise ValueError(f"Accepted attempt number invalid: {key}")
        if require_resolved and state == "RETRY_ONCE":
            raise ValueError(f"Pilot retry remains unresolved: {key}")
        folder = output / "targets" / key[0] / key[1]
        record_path = folder / f"attempt_{attempt}.json"
        image_path = folder / f"attempt_{attempt}.png"
        if not record_path.is_file():
            raise ValueError(f"Reviewed attempt record missing: {key}")
        record = json.loads(record_path.read_text(encoding="utf-8"))
        if record.get("identity_id") != key[0] or record.get("style_id") != key[1]:
            raise ValueError(f"Reviewed attempt provenance mismatch: {key}")
        if state == "ACCEPT" and (not record.get("success") or not image_path.is_file()
                                  or digest(image_path) != record.get("target_sha256")):
            raise ValueError(f"Accepted pilot image or hash invalid: {key}")
        if state == "REJECT" and not (folder / "attempt_1.json").is_file():
            raise ValueError(f"Rejected cell lacks recorded first attempt: {key}")
        by_key[key] = review
    return by_key


def review_sheet(output: Path, config: dict, identities: list[str]) -> None:
    from PIL import Image, ImageDraw, ImageOps

    width, height = 256, 284
    for identity in identities:
        sheet = Image.new("RGB", (width * 11, height), "white")
        draw = ImageDraw.Draw(sheet)
        cells = [(output / "sources" / f"{identity}.jpg", "Original")]
        cells += [(next((path for path in (
            output / "targets" / identity / style["id"] / "attempt_2.png",
            output / "targets" / identity / style["id"] / "attempt_1.png") if path.is_file()),
            output / "targets" / identity / style["id"] / "attempt_1.png"), style["name"])
            for style in config["styles"]]
        for index, (path, label) in enumerate(cells):
            x = index * width
            draw.text((x + 4, 4), f"{identity} {label}", fill="black")
            if path.is_file():
                with Image.open(path) as image:
                    thumb = ImageOps.contain(image.convert("RGB"), (250, 250))
                sheet.paste(thumb, (x + (width - thumb.width) // 2, 26))
            else:
                draw.text((x + 4, 40), "MISSING", fill="red")
        target = output / "review_sheets" / f"{identity}.jpg"
        target.parent.mkdir(parents=True, exist_ok=True)
        sheet.save(target, quality=90)


def archive_results(output: Path) -> Path:
    target = output.parent / f"{output.name}_results.zip"
    with ZipFile(target, "w", ZIP_DEFLATED) as archive:
        for path in sorted(output.rglob("*")):
            if path.is_file():
                archive.write(path, path.relative_to(output).as_posix())
    return target


def run(args: argparse.Namespace) -> dict:
    config, manifest = load_input(args.inputs)
    if args.phase == "retry":
        if not args.identity or not args.style or not args.pilot_reviews:
            raise ValueError("Retry needs --identity, --style, and --pilot-reviews")
        source = next((row for row in manifest["identities"] if row["identity_id"] == args.identity), None)
        style = next((item for item in config["styles"] if item["id"] == args.style), None)
        if source is None or style is None:
            raise ValueError("Unknown source identity or style")
        review = validated_pilot_reviews(args.output, config, manifest, args.pilot_reviews,
                                         require_resolved=False)[(args.identity, args.style)]
        if review["state"] != "RETRY_ONCE":
            raise ValueError("A reviewed RETRY_ONCE decision is required")
        selected = [(source, style)]
    else:
        selected = jobs(config, manifest, args.phase)
    plan = {"dataset_id": "DATA-M001", "phase": args.phase,
            "prompt_version": config.get("prompt_version", "global-v1"),
            "job_count": len(selected), "model_id": config["model_id"],
            "model_revision": config["model_revision"], "inference": config["inference"],
            "no_lora_confirmation": True,
            "jobs": [{"identity_id": row["identity_id"], "split": row["split"],
                      "source_sha256": row["source_sha256"], "style_id": style["id"],
                      "style_name": style["name"], "prompt": prompt(config, style)}
                     for row, style in selected]}
    if args.phase == "plan":
        return plan
    if args.phase == "remaining":
        if not args.pilot_reviews:
            raise ValueError("Remaining generation requires reviewed pilot decisions")
        validated_pilot_reviews(args.output, config, manifest, args.pilot_reviews,
                                require_resolved=True)
    import torch
    import diffusers
    from diffusers import Flux2KleinPipeline
    from PIL import Image, ImageOps
    from transformers import logging as transformers_logging

    if not torch.cuda.is_available():
        raise RuntimeError("CUDA unavailable; use a Kaggle T4 GPU session")
    transformers_logging.disable_progress_bar()
    args.output.mkdir(parents=True, exist_ok=True)
    plan_name = (f"plan_retry_{args.identity}_{args.style}.json" if args.phase == "retry"
                 else f"plan_{args.phase}.json")
    plan_path = args.output / plan_name
    if plan_path.exists() and json.loads(plan_path.read_text(encoding="utf-8")) != plan:
        raise ValueError(f"Existing generation plan differs: {plan_path}")
    save_json(plan_path, plan)
    shutil.copyfile(args.inputs / "source_manifest.json", args.output / "source_manifest.json")
    configs = args.output / "configs"
    configs.mkdir(exist_ok=True)
    existing_config = args.output / "config.json"
    if existing_config.is_file():
        old_hash = digest(existing_config)
        old_saved = configs / f"{old_hash}.json"
        if not old_saved.is_file():
            shutil.copyfile(existing_config, old_saved)
    current_hash = digest(args.inputs / "config.json")
    current_saved = configs / f"{current_hash}.json"
    if not current_saved.is_file():
        shutil.copyfile(args.inputs / "config.json", current_saved)
    shutil.copyfile(args.inputs / "config.json", args.output / "config.json")
    (args.output / "sources").mkdir(exist_ok=True)
    for row in manifest["identities"]:
        source = args.inputs / row["source_path"]
        target = args.output / "sources" / f"{row['identity_id']}.jpg"
        if target.exists() and digest(target) != row["source_sha256"]:
            raise ValueError(f"Previously copied original changed: {target}")
        if not target.exists():
            shutil.copyfile(source, target)
    load_started = time.monotonic()
    try:
        with (args.output / "generation.log").open("a", encoding="utf-8") as log:
            log.write(f"{utc()} Loading pinned Base, no adapter\n")
            log.flush()
            faulthandler.dump_traceback_later(180, repeat=True, file=log)
            try:
                pipe = Flux2KleinPipeline.from_pretrained(
                    config["model_id"], revision=config["model_revision"],
                    torch_dtype=torch.float16, cache_dir="/tmp/hf-cache/hub")
                pipe.enable_model_cpu_offload(gpu_id=0)
            finally:
                faulthandler.cancel_dump_traceback_later()
    except Exception:
        save_json(args.output / "load_failure.json", {"success": False, "error": traceback.format_exc(),
                  "model_id": config["model_id"], "model_revision": config["model_revision"],
                  "lora_active": False, "adapter_id": None, "failed_utc": utc()})
        archive_results(args.output)
        raise
    save_json(args.output / "runtime.json", {"python": sys.version, "torch": torch.__version__,
              "diffusers": diffusers.__version__, "gpu": torch.cuda.get_device_name(0),
              "model_load_seconds": round(time.monotonic() - load_started, 2),
              "model_revision": config["model_revision"], "lora_active": False, "adapter_id": None})
    attempted = succeeded = failed = 0
    for row, style in selected:
        identity, style_id = row["identity_id"], style["id"]
        folder = args.output / "targets" / identity / style_id
        folder.mkdir(parents=True, exist_ok=True)
        attempt = 2 if args.phase == "retry" else 1
        image_path, record_path = folder / f"attempt_{attempt}.png", folder / f"attempt_{attempt}.json"
        if attempt == 2 and not (folder / "attempt_1.json").is_file():
            raise ValueError(f"Retry requires a recorded first attempt: {folder}")
        if record_path.exists():
            previous = json.loads(record_path.read_text(encoding="utf-8"))
            if previous.get("success") and image_path.exists() and digest(image_path) == previous.get("target_sha256"):
                continue
            raise ValueError(f"Existing failed or partial attempt needs explicit review: {folder}")
        with Image.open(args.inputs / row["source_path"]) as original:
            source = ImageOps.pad(ImageOps.exif_transpose(original).convert("RGB"), (512, 512),
                                  method=Image.Resampling.LANCZOS, color=(245, 245, 245))
        started, tick = utc(), time.monotonic()
        record = {"identity_id": identity, "split": row["split"], "style_id": style_id,
                  "style_name": style["name"], "prompt": prompt(config, style),
                  "prompt_version": config.get("prompt_version", "global-v1"),
                  "source_sha256": row["source_sha256"], "source_path": f"sources/{identity}.jpg",
                  "config_sha256": current_hash,
                  "model_id": config["model_id"], "model_revision": config["model_revision"],
                  **config["inference"], "preprocessing": "EXIF transpose, RGB, aspect-preserving pad 512x512 RGB(245,245,245)",
                  "started_utc": started, "attempt": attempt, "review_state": "PENDING", "reviewer": None,
                  "review_note": None}
        if attempt == 2:
            record["seed"] = config["inference"]["seed"] + 1
        attempted += 1
        try:
            result = pipe(prompt=record["prompt"], image=source, width=512, height=512,
                          num_inference_steps=20, guidance_scale=4.0,
                          generator=torch.Generator(device="cuda").manual_seed(record["seed"])).images[0]
            result.convert("RGB").save(image_path)
            record.update(success=True, target_path=f"targets/{identity}/{style_id}/attempt_{attempt}.png",
                          target_sha256=digest(image_path))
            succeeded += 1
        except Exception:
            record.update(success=False, target_path=None, target_sha256=None,
                          error=traceback.format_exc(), review_state="GENERATION_FAILURE")
            failed += 1
        record.update(finished_utc=utc(), duration_seconds=round(time.monotonic() - tick, 2))
        save_json(record_path, record)
        with (args.output / "generation.log").open("a", encoding="utf-8") as log:
            log.write(f"{record['finished_utc']} {identity} {style_id} success={record['success']} duration={record['duration_seconds']}s\n")
        review_sheet(args.output, config, [identity])
    identities = list(dict.fromkeys(row["identity_id"] for row, _ in selected))
    review_sheet(args.output, config, identities)
    reviews = args.output / "reviews.json"
    review_data = json.loads(reviews.read_text(encoding="utf-8")) if reviews.exists() else {
        "schema": "DATA-M001-review-v1", "reviews": []}
    known = {(item["identity_id"], item["style_id"]) for item in review_data["reviews"]}
    for row, style in selected:
        key = (row["identity_id"], style["id"])
        if key not in known:
            review_data["reviews"].append({"identity_id": key[0], "style_id": key[1], "attempt": 1,
                                           "state": "PENDING", "reviewer": None, "note": None,
                                           "failure_tags": []})
    save_json(reviews, review_data)
    summary = {"attempted_this_run": attempted, "successful_this_run": succeeded,
               "failed_this_run": failed, "review_state": "PENDING_HUMAN_REVIEW",
               "results_zip": str(archive_results(args.output))}
    save_json(args.output / f"summary_{args.phase}.json", summary)
    archive_results(args.output)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase", choices=("plan", "pilot", "retry", "remaining"), required=True)
    parser.add_argument("--inputs", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("/kaggle/working/data_m001"))
    parser.add_argument("--pilot-reviews", type=Path)
    parser.add_argument("--identity")
    parser.add_argument("--style")
    print(json.dumps(run(parser.parse_args()), indent=2))


if __name__ == "__main__":
    main()
