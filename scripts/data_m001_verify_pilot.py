"""Verify the downloaded DATA-M001 pilot without accepting visual quality."""

import argparse
from hashlib import sha256
import json
from pathlib import Path

from PIL import Image


def digest(path: Path) -> str:
    value = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def verify(root: Path) -> dict:
    config = json.loads((root / "config.json").read_text(encoding="utf-8"))
    manifest = json.loads((root / "source_manifest.json").read_text(encoding="utf-8"))
    plan = json.loads((root / "plan_pilot.json").read_text(encoding="utf-8"))
    runtime = json.loads((root / "runtime.json").read_text(encoding="utf-8"))
    summary = json.loads((root / "summary_pilot.json").read_text(encoding="utf-8"))
    expected = {(identity, style["id"]) for identity in config["pilot_train_ids"] for style in config["styles"]}
    if len(expected) != 20 or plan["job_count"] != 20 or not plan["no_lora_confirmation"]:
        raise ValueError("Unexpected pilot plan")
    if runtime["lora_active"] is not False or runtime["adapter_id"] is not None:
        raise ValueError("Runtime reported an active adapter")
    source_by_id = {item["identity_id"]: item for item in manifest["identities"]}
    results, failures = [], []
    for identity, style_id in sorted(expected):
        source = source_by_id[identity]
        if source["split"] != "TRAIN" or digest(root / source["source_path"]) != source["source_sha256"]:
            raise ValueError(f"Wrong split or source hash: {identity}")
        folder = root / "targets" / identity / style_id
        record = json.loads((folder / "attempt_1.json").read_text(encoding="utf-8"))
        style = next(item for item in config["styles"] if item["id"] == style_id)
        exact_prompt = f"{style['instruction']} {config['preservation_instruction']}"
        if record["prompt"] != exact_prompt or record["source_sha256"] != source["source_sha256"]:
            raise ValueError(f"Prompt or source mismatch: {identity}/{style_id}")
        for key in ("model_id", "model_revision"):
            if record[key] != config[key]:
                raise ValueError(f"Model mismatch: {identity}/{style_id}")
        for key in ("width", "height", "steps", "guidance", "seed", "dtype", "cpu_offload", "adapter_id", "lora_active"):
            if record[key] != config["inference"][key]:
                raise ValueError(f"Inference mismatch: {identity}/{style_id}/{key}")
        if not record["success"]:
            failures.append({"identity_id": identity, "style_id": style_id, "error": record.get("error")})
            continue
        image_path = folder / "attempt_1.png"
        if digest(image_path) != record["target_sha256"]:
            raise ValueError(f"Target hash mismatch: {identity}/{style_id}")
        with Image.open(image_path) as image:
            image.load()
            if image.format != "PNG" or image.size != (512, 512) or image.mode != "RGB":
                raise ValueError(f"Unexpected target format: {identity}/{style_id}")
        results.append({"identity_id": identity, "style_id": style_id,
                        "target_sha256": record["target_sha256"], "duration_seconds": record["duration_seconds"]})
    if len(results) != 20 or summary["attempted_this_run"] != 20 or summary["successful_this_run"] != 20:
        raise ValueError("Attempt or success count mismatch")
    if len({row["target_sha256"] for row in results}) != 20:
        raise ValueError("Duplicate target hash")
    return {"status": "TECHNICAL_PASS_VISUAL_REVIEW_PENDING", "attempted": 20, "successful": len(results),
            "failed": len(failures), "failures": failures, "runtime": runtime,
            "total_generation_seconds": round(sum(row["duration_seconds"] for row in results), 2),
            "results": results}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = verify(args.root)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in report.items() if key not in ("results", "runtime")}, indent=2))


if __name__ == "__main__":
    main()
