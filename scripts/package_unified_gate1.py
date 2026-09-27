"""Build a new private Gate 1 bundle from immutable adapters and existing references."""

import argparse
from hashlib import sha256
from io import BytesIO
import json
import os
from pathlib import Path
import sys
from zipfile import ZIP_DEFLATED, ZipFile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "backend"))
from scripts.unified_gate1 import MODEL_ID, REVISION, SCHEMA, digest, safe_path

SOURCES = (
    "scripts/unified_gate1.py", "scripts/unified_gate1_bootstrap.py", "scripts/unified_gate1_requirements.txt",
    "scripts/kaggle_inference_server.py", "scripts/makeup_inference_server.py", "scripts/nails001_local_inference_server.py",
    "backend/app/__init__.py", "backend/app/styles.py", "backend/app/registry.py", "backend/app/style_registry.json",
    "backend/app/makeup_contract.py", "backend/app/nails/__init__.py", "backend/app/nails/contract.py",
    "data/makeup/DATA-M001-paired/inference_presets.json",
)
HAIR_CASE = "CrewCut_26_to_original"
MAKEUP_ID = "054109"
NAILS_CASE = "0000045_classic_red__index"
LOCAL_DATA_SHA = "d7440f1cc1a8987c48235fed36f8ff23581c17719b219fc2a7e600ad867bcf90"


def read_runtime_bundle(path, schema):
    with ZipFile(path) as archive:
        if archive.testzip() is not None:
            raise ValueError("Source runtime bundle CRC failure")
        names = archive.namelist()
        if len(names) != len(set(names)):
            raise ValueError("Duplicate source runtime members")
        manifest = json.loads(archive.read("bundle.json"))
        if manifest.get("schema") != schema:
            raise ValueError("Wrong source runtime bundle schema")
        for name, expected in manifest["files"].items():
            safe_path(ROOT, name)
            if sha256(archive.read(name)).hexdigest() != expected:
                raise ValueError(f"Source runtime inventory mismatch: {name}")
        return {name: archive.read(name) for name in names if name.startswith("adapter/")}


def checked_image(raw, expected, label):
    from PIL import Image
    if sha256(raw).hexdigest() != expected:
        raise ValueError(f"Reference/input hash mismatch: {label}")
    with Image.open(BytesIO(raw)) as image:
        image.load()
        if image.size != (512, 512):
            raise ValueError(f"Expected fixed 512 image: {label}")
    return raw


def select_references(args):
    # Selection is fixed, not arbitrary user uploads or model-generated replacements.
    fixtures, references = {}, {}
    with ZipFile(args.hair_data) as data, ZipFile(args.hair_evaluation) as evaluation:
        rows = json.loads(data.read("manifests/pairs.json"))
        row = next(row for row in rows if Path(row["target"]).stem == HAIR_CASE)
        if row["split"] != "val" or row["review"]["status"] != "ACCEPT":
            raise ValueError("Hair input is not an accepted held-out case")
        meta = json.loads(evaluation.read("train001_250/evaluation/metadata.json"))
        record = next(row for row in meta["pairs"]["adapter"] if row["pair"] == HAIR_CASE)
        if meta["model"] != MODEL_ID or meta["model_revision"] != REVISION:
            raise ValueError("Hair evaluation uses the wrong Base")
        fixtures["hairstyle"] = checked_image(data.read(row["reference"]), row["generation_output_sha256"], "Hair source")
        references["hairstyle"] = (checked_image(evaluation.read(f"train001_250/evaluation/adapter/{HAIR_CASE}.png"),
                                                record["output_sha256"], "Hair output"), record,
            {"kind": "held-out TRAIN-001 evaluation, not current service capture", "case": HAIR_CASE,
             "input_origin": "Accepted DATA-001 generated validation portrait",
             "input_sha256": sha256(fixtures["hairstyle"]).hexdigest(),
             "recorded_environment": json.loads(evaluation.read("train001_250/runtime.json")),
             "dependency_versions_missing": ["diffusers", "transformers", "accelerate", "peft"]})
    with ZipFile(args.makeup_evaluation) as evaluation:
        meta = json.loads(evaluation.read("evaluation/metadata.json"))
        record = next(row for row in meta["records"] if row["mode"] == "adapter"
                      and row["identity_id"] == MAKEUP_ID and row["style_id"] == "natural_makeup")
        if record["model_id"] != MODEL_ID or record["model_revision"] != REVISION:
            raise ValueError("Makeup evaluation uses the wrong Base")
        fixtures["makeup"] = checked_image(args.makeup_source.read_bytes(), record["source_sha256"], "Makeup source")
        references["makeup"] = (checked_image(evaluation.read(f"evaluation/adapter/{MAKEUP_ID}/natural_makeup.png"),
                                              record["output_sha256"], "Makeup output"), record,
            {"kind": "reviewed MAKEUP-001 held-out evaluation, not corrected V2 service capture",
             "case": MAKEUP_ID, "input_origin": "Reviewed public FFHQ-Makeup bare portrait, academic use",
             "source_repository": "cyberagent/FFHQ-Makeup", "dataset_license": "CC BY-NC-SA 4.0",
             "source_photo_credit": next(row["source_photo"] for row in json.loads(args.makeup_credits.read_text(encoding="utf-8"))["pairs"]
                                          if row["identity_id"] == MAKEUP_ID and row["source_sha256"] == record["source_sha256"]),
             "input_sha256": record["source_sha256"],
             "recorded_environment": json.loads(evaluation.read("runtime.json")),
             "dependency_versions_missing": ["diffusers", "transformers", "accelerate", "peft"]})
    if digest(args.nails_data) != LOCAL_DATA_SHA:
        raise ValueError("Frozen localized Nails dataset changed")
    with ZipFile(args.nails_data) as data, ZipFile(args.nails_evaluation) as evaluation:
        row = next(row for row in json.loads(data.read("manifests/pairs.json")) if row["pair_id"] == NAILS_CASE)
        meta = json.loads(evaluation.read("metadata.json"))
        record = next(row for row in meta["records"] if row["pair_id"] == NAILS_CASE and row["mode"] == "adapter")
        if row["split"] != "validation" or meta["base_revision"] != REVISION or meta["localized_archive_sha256"] != LOCAL_DATA_SHA:
            raise ValueError("Nails reference provenance mismatch")
        fixtures["nails"] = checked_image(data.read(f"validation/reference/{NAILS_CASE}.png"), row["reference_sha256"], "Nails crop")
        enriched = {**record, "checkpoint_sha256": meta["checkpoint_sha256"], "prompt": row["caption"],
                    "seed": meta["seed"], "steps": meta["inference_steps"], "guidance": meta["guidance"]}
        references["nails"] = (checked_image(evaluation.read(f"{NAILS_CASE}/adapter.png"), record["output_sha256"], "Nails output"), enriched,
            {"kind": "verified step-50 held-out crop evaluation", "case": NAILS_CASE,
             "input_origin": "Prepared public 11K Hands index crop, academic use",
             "input_sha256": row["reference_sha256"], "transform": row["transform"],
             "recorded_environment": {name: meta[name] for name in ("torch", "diffusers", "gpu")},
             "dependency_versions_missing": ["transformers", "accelerate", "peft"]})
    return fixtures, references


def build(args):
    if args.output.exists():
        raise ValueError("Refusing to overwrite an existing experiment bundle")
    # Approved verifier imports are CPU only; no torch or diffusers model loading.
    os.environ["HAIRCAPSTONE_STYLE_REGISTRY_PATH"] = str(ROOT / "backend/app/style_registry.json")
    from scripts.kaggle_inference_server import read_adapter_metadata, REGISTRY
    from app.registry import styles_by_id
    from app.makeup_contract import ADAPTER_ID, ADAPTER_SHA256, GENERATOR, PRESETS_SHA256, PROMPTS
    from app.nails import contract as nails
    hair = read_adapter_metadata(args.hair_adapter)
    makeup = read_runtime_bundle(args.makeup_bundle, "MAKEUP-001-runtime-bundle-v1")
    nail_assets = read_runtime_bundle(args.nails_bundle, "NAILS-001-LOCAL-v1-runtime-v1")
    if sha256(makeup["adapter/adapter.safetensors"]).hexdigest() != ADAPTER_SHA256:
        raise ValueError("Not the approved Makeup checkpoint")
    makeup_meta = json.loads(makeup["adapter/metadata.json"])
    if makeup_meta.get("adapter_id") != ADAPTER_ID or makeup_meta.get("base_model_revision") != REVISION:
        raise ValueError("Makeup adapter identity changed")
    if sha256(nail_assets["adapter/nails001_local_v1.safetensors"]).hexdigest() != nails.ADAPTER_SHA256:
        raise ValueError("Not the approved Nails checkpoint")
    fixtures, references = select_references(args)
    files = {name: (ROOT / name).read_bytes() for name in SOURCES}
    files.update({"gate1/adapters/hairstyle/adapter.safetensors": (args.hair_adapter / "adapter.safetensors").read_bytes(),
                  "gate1/adapters/hairstyle/metadata.json": (args.hair_adapter / "metadata.json").read_bytes(),
                  "gate1/adapters/makeup/adapter.safetensors": makeup["adapter/adapter.safetensors"],
                  "gate1/adapters/makeup/metadata.json": makeup["adapter/metadata.json"],
                  "gate1/adapters/nails/nails001_local_v1.safetensors": nail_assets["adapter/nails001_local_v1.safetensors"]})
    expected = {
        "hairstyle": {"style_id": "crew_cut", "prompt": styles_by_id(REGISTRY)["crew_cut"]["prompt"], "adapter_id": "train001",
                      "adapter_sha256": hair["checkpoint_sha256"], "adapter_steps": 250, "generator": "flux2_klein_base_train001"},
        "makeup": {"style_id": "natural_makeup", "prompt": PROMPTS["natural_makeup"], "adapter_id": ADAPTER_ID,
                   "adapter_sha256": ADAPTER_SHA256, "adapter_steps": 250, "generator": GENERATOR,
                   "prompt_presets_sha256": PRESETS_SHA256, "feature": "makeup", "lora_active": True},
        "nails": {"style_id": "classic_red", "prompt": nails.PROMPTS["classic_red"], "adapter_id": nails.ADAPTER_ID,
                  "adapter_sha256": nails.ADAPTER_SHA256, "adapter_steps": 50, "generator": nails.GENERATOR,
                  "feature": "nails", "lora_active": True}}
    plan = {"schema": SCHEMA, "features": {}, "source_archive_hashes": {label: digest(path) for label, path in (
        ("hair_data", args.hair_data), ("hair_evaluation", args.hair_evaluation), ("makeup_bundle", args.makeup_bundle),
        ("makeup_evaluation", args.makeup_evaluation), ("nails_bundle", args.nails_bundle),
        ("nails_data", args.nails_data), ("nails_evaluation", args.nails_evaluation))}}
    for feature in ("hairstyle", "makeup", "nails"):
        reference, record, context = references[feature]
        contract = expected[feature]
        if (record.get("checkpoint_sha256") != contract["adapter_sha256"] or record["prompt"] != contract["prompt"]
                or (record["seed"], record["steps"], record["guidance"]) != (1977, 20, 4.0)):
            raise ValueError(f"Reference settings do not match current runtime: {feature}")
        # Do not publish historical machine paths; preserve relevant provenance fields.
        record = {key: value for key, value in record.items() if key not in {"output", "checkpoint"}}
        context["recorded_environment"] = {key: value for key, value in context["recorded_environment"].items()
            if key in {"python", "torch", "cuda", "gpu", "diffusers", "ai_toolkit_commit", "toolkit_commit", "base_model_revision"}}
        suffix = "jpg" if feature == "makeup" else "png"
        source_name = f"gate1/inputs/{feature}.{suffix}"
        reference_name = f"gate1/references/{feature}.png"
        record_name = f"gate1/references/{feature}.json"
        files[source_name] = fixtures[feature]
        files[reference_name] = reference
        files[record_name] = (json.dumps(record, indent=2) + "\n").encode()
        plan["features"][feature] = {"input": source_name, "reference": reference_name, "reference_record": record_name,
            "input_sha256": sha256(fixtures[feature]).hexdigest(), "reference_sha256": sha256(reference).hexdigest(),
            "expected": contract, "reference_context": context,
            "settings": {"width": 512, "height": 512, "steps": 20, "guidance": 4.0, "seed": 1977,
                         "dtype": "float16", "cpu_offload": True}}
    files["gate1_plan.json"] = (json.dumps(plan, indent=2) + "\n").encode()
    manifest = {"schema": SCHEMA, "base_revision": REVISION, "files": {name: sha256(raw).hexdigest() for name, raw in files.items()}}
    files["gate1_bundle.json"] = (json.dumps(manifest, indent=2) + "\n").encode()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(args.output, "x", ZIP_DEFLATED) as archive:
        for name, raw in sorted(files.items()):
            archive.writestr(name, raw)
    return {"bundle": str(args.output.resolve()), "bytes": args.output.stat().st_size,
            "sha256": digest(args.output), "member_count": len(files), "gate1_passed": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--hair-adapter", type=Path, default=ROOT / "artifacts/train001_adapter_bundle")
    parser.add_argument("--makeup-bundle", type=Path, default=ROOT / "artifacts/makeup001_kaggle_runtime_v2.zip")
    parser.add_argument("--nails-bundle", type=Path, default=ROOT / "data/nails/work/NAILS-001-LOCAL-v1-runtime-v2.bin")
    parser.add_argument("--hair-data", type=Path, default=Path("D:/Downloads/data001_final.zip"))
    parser.add_argument("--hair-evaluation", type=Path, default=Path("D:/Downloads/train001_250_with_evaluation.zip"))
    parser.add_argument("--makeup-source", type=Path, default=ROOT / ".tmp/data_m001/paired_selection/prepared_v1/originals/054109.jpg")
    parser.add_argument("--makeup-credits", type=Path, default=ROOT / ".tmp/data_m001/paired_selection/prepared_v1/candidate_manifest.json")
    parser.add_argument("--makeup-evaluation", type=Path, default=Path("C:/Users/Gigabyte/Downloads/makeup001_250_with_evaluation.zip"))
    parser.add_argument("--nails-data", type=Path, default=ROOT / "data/nails/work/NAILS-001-LOCAL-v1-sim-v2/DATA-N001-LOCAL-v1.zip")
    parser.add_argument("--nails-evaluation", type=Path, default=Path("D:/Downloads/NAILS-001-LOCAL-v1-step050-evaluation.zip"))
    parser.add_argument("--output", type=Path, default=ROOT / "artifacts/unified_gate1_20260928_v2.bin")
    print(json.dumps(build(parser.parse_args()), indent=2))


if __name__ == "__main__":
    main()
