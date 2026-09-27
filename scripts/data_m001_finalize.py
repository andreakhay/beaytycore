"""Finalize reviewed, identity-disjoint DATA-M001 bare-to-makeup pairs.

Run only after the pilot and remaining targets have human ACCEPT reviews.
"""

import argparse
from hashlib import sha256
import json
from pathlib import Path
import shutil
from collections import Counter


def digest(path: Path) -> str:
    hash_value = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            hash_value.update(chunk)
    return hash_value.hexdigest()


def finalize(results: Path, reviews_path: Path, output: Path) -> dict:
    config = json.loads((results / "config.json").read_text(encoding="utf-8"))
    sources = json.loads((results / "source_manifest.json").read_text(encoding="utf-8"))["identities"]
    reviews = json.loads(reviews_path.read_text(encoding="utf-8"))["reviews"]
    by_key = {}
    for review in reviews:
        key = (review["identity_id"], review["style_id"])
        if key in by_key:
            raise ValueError(f"Duplicate review: {key}")
        by_key[key] = review
    expected = {(source["identity_id"], style["id"]) for source in sources for style in config["styles"]}
    if set(by_key) != expected or len(expected) != 120:
        raise ValueError("Need exactly one review for each of 120 identity/style cells")
    if len(config["train_ids"]) != 10 or len(config["validation_ids"]) != 2:
        raise ValueError("Unexpected identity split")
    if set(config["train_ids"]) & set(config["validation_ids"]):
        raise ValueError("Train/validation identity leakage")
    configs = {}
    for path in [results / "config.json", *(results / "configs").glob("*.json")]:
        if path.is_file():
            configs[digest(path)] = json.loads(path.read_text(encoding="utf-8"))
    pilot_plan_path = results / "plan_pilot.json"
    pilot_prompts = {}
    if pilot_plan_path.is_file():
        pilot = json.loads(pilot_plan_path.read_text(encoding="utf-8"))
        pilot_prompts = {(job["identity_id"], job["style_id"]): job["prompt"]
                         for job in pilot.get("jobs", [])}
    rows, hashes, exclusions = [], set(), []
    for source in sources:
        identity = source["identity_id"]
        split = "train" if source["split"] == "TRAIN" else "validation"
        if identity not in config[f"{split}_ids"]:
            raise ValueError(f"Source split mismatch: {identity}")
        bare = results / "sources" / f"{identity}.jpg"
        if digest(bare) != source["source_sha256"]:
            raise ValueError(f"Source hash mismatch: {identity}")
        for style in config["styles"]:
            style_id = style["id"]
            review = by_key[(identity, style_id)]
            if review.get("state") not in {"ACCEPT", "REJECT"} or not review.get("reviewer") or not review.get("note"):
                raise ValueError(f"Explicit human ACCEPT or post-retry REJECT with reviewer and note required: {identity}/{style_id}")
            attempt = review.get("attempt")
            if attempt not in (1, 2):
                raise ValueError(f"Attempt must be 1 or 2: {identity}/{style_id}")
            record_path = results / "targets" / identity / style_id / f"attempt_{attempt}.json"
            if not record_path.is_file():
                raise ValueError(f"Reviewed attempt missing: {identity}/{style_id}")
            record = json.loads(record_path.read_text(encoding="utf-8"))
            if review["state"] == "REJECT":
                if attempt != 2 or not (results / "targets" / identity / style_id / "attempt_1.json").is_file():
                    raise ValueError(f"REJECT requires a recorded bounded retry: {identity}/{style_id}")
                exclusions.append({"identity_id": identity, "split": split, "style_id": style_id,
                                   "review": review, "record_path": str(record_path.relative_to(results)).replace("\\", "/")})
                continue
            target = results / "targets" / identity / style_id / f"attempt_{attempt}.png"
            record_config_hash = record.get("config_sha256")
            if record_config_hash:
                saved_config = configs.get(record_config_hash)
                if saved_config is None:
                    raise ValueError(f"Generation config provenance missing: {identity}/{style_id}")
                saved_style = next((item for item in saved_config["styles"] if item["id"] == style_id), None)
                if saved_style is None:
                    raise ValueError(f"Generation style missing from saved config: {identity}/{style_id}")
                exact_prompt = f"{saved_style['instruction']} {saved_config['preservation_instruction']}"
            else:
                exact_prompt = pilot_prompts.get((identity, style_id)) if attempt == 1 else None
            if not record.get("success") or record.get("prompt") != exact_prompt:
                raise ValueError(f"Unsuccessful generation or prompt drift: {identity}/{style_id}")
            if record.get("lora_active") is not False or record.get("adapter_id") is not None:
                raise ValueError(f"Adapter active: {identity}/{style_id}")
            if record.get("model_revision") != config["model_revision"]:
                raise ValueError(f"Model revision mismatch: {identity}/{style_id}")
            if record.get("source_sha256") != source["source_sha256"] or digest(target) != record.get("target_sha256"):
                raise ValueError(f"Image hash mismatch: {identity}/{style_id}")
            if record["target_sha256"] in hashes:
                raise ValueError(f"Duplicate generated target: {identity}/{style_id}")
            hashes.add(record["target_sha256"])
            rows.append({"identity_id": identity, "split": split, "style_id": style_id,
                         "style_name": style["name"], "source_sha256": source["source_sha256"],
                         "target_sha256": record["target_sha256"], "attempt": attempt,
                         "prompt": exact_prompt, "seed": record["seed"],
                         "model_id": record["model_id"], "model_revision": record["model_revision"],
                         "review": review, "source_credit": source["original_ffhq_photo"],
                         "config_sha256": record_config_hash,
                         "caption": exact_prompt})
    counts = Counter((row["split"], row["style_id"]) for row in rows)
    if any(counts[("train", style["id"])] == 0 or counts[("validation", style["id"])] == 0
           for style in config["styles"]):
        raise ValueError("Each Makeup style needs accepted train and held-out validation pairs")
    output.mkdir(parents=True, exist_ok=True)
    for row in rows:
        identity, style_id, split, attempt = row["identity_id"], row["style_id"], row["split"], row["attempt"]
        folder = output / "pairs" / split / identity / style_id
        folder.mkdir(parents=True, exist_ok=True)
        source_target = folder / "source.jpg"
        makeup_target = folder / "target.png"
        for origin, destination, expected_hash in (
            (results / "sources" / f"{identity}.jpg", source_target, row["source_sha256"]),
            (results / "targets" / identity / style_id / f"attempt_{attempt}.png", makeup_target, row["target_sha256"]),
        ):
            if destination.exists() and digest(destination) != expected_hash:
                raise ValueError(f"Existing finalized image differs: {destination}")
            if not destination.exists():
                shutil.copyfile(origin, destination)
        caption_path = folder / "caption.txt"
        if caption_path.exists() and caption_path.read_text(encoding="utf-8") != row["caption"] + "\n":
            raise ValueError(f"Existing caption differs: {caption_path}")
        caption_path.write_text(row["caption"] + "\n", encoding="utf-8")
        row["source_path"] = str(source_target.relative_to(output)).replace("\\", "/")
        row["target_path"] = str(makeup_target.relative_to(output)).replace("\\", "/")
        row["caption_path"] = str(caption_path.relative_to(output)).replace("\\", "/")
    final = {"schema": "DATA-M001-final-v1", "source_manifest_sha256": digest(results / "source_manifest.json"),
             "config_sha256": digest(results / "config.json"), "pair_count": len(rows),
             "train_pair_count": sum(row["split"] == "train" for row in rows),
             "validation_pair_count": sum(row["split"] == "validation" for row in rows),
             "training_identity_count": len({row["identity_id"] for row in rows if row["split"] == "train"}),
             "validation_identity_count": len({row["identity_id"] for row in rows if row["split"] == "validation"}),
             "excluded_pair_count": len(exclusions), "exclusions": exclusions, "pairs": rows}
    (output / "final_manifest.json").write_text(json.dumps(final, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    report = {"status": "PASS", "pairs": len(rows), "train": final["train_pair_count"],
              "validation": final["validation_pair_count"], "excluded": len(exclusions),
              "styles": {style["id"]: {"train": counts[("train", style["id"])],
                                        "validation": counts[("validation", style["id"])]}
                         for style in config["styles"]},
              "no_lora": True, "manual_review_required_and_present": True}
    (output / "qa_report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path, required=True)
    parser.add_argument("--reviews", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(finalize(args.results, args.reviews, args.output), indent=2))


if __name__ == "__main__":
    main()
