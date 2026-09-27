"""Package the reviewed DATA-N001 fingertip representation for a bounded Kaggle run."""

import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import shutil
from zipfile import ZipFile, ZIP_DEFLATED

from train_n001_bundle import config


ORIGINAL_SHA = "d37b68bc3e06c6ea1b1b013424dd813aafbef83db222cf9223e229d33ad105bb"
BASE_REVISION = "a3b4f4849157f664bdbc776fd7453c2783562f4d"
TOOLKIT_COMMIT = "a8dfcf7d7e2b38ccc7b2fb68ece9c6358e61e7a7"
STYLE_IDS = ("classic_red", "nude_pink", "glossy_black", "french_tip", "pink_ombre")


def digest(path: Path) -> str:
    value = sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def training_config() -> str:
    text = config(50, 50)
    text = text.replace('name: "nails001_50step"', 'name: "nails001_local_v1"')
    text = text.replace("/kaggle/working/nails001/checkpoints", "/kaggle/working/nails001_local/checkpoints")
    text = text.replace("/kaggle/working/data_n001/train/", "/kaggle/working/data_n001_local/train/")
    text = text.replace("        steps: 50\n", "        steps: 50\n        gradient_accumulation: 1\n")
    text = text.replace("max_step_saves_to_keep: 3", "max_step_saves_to_keep: 10")
    for needed in ("nails001_local_v1", "gradient_accumulation: 1", "save_every: 50",
                   "data_n001_local/train/reference", "data_n001_local/train/target", BASE_REVISION):
        if needed not in text:
            raise ValueError(f"Localized training config missing {needed}")
    return text


def build(approved: Path, localized: Path, review: Path, destination: Path) -> dict:
    if destination.exists() or destination.with_suffix(".bin").exists():
        raise ValueError("Refusing to overwrite localized Kaggle bundle")
    if digest(approved) != ORIGINAL_SHA:
        raise ValueError("Approved DATA-N001 source archive hash changed")
    with ZipFile(localized) as archive:
        if archive.testzip() is not None:
            raise ValueError("Localized archive CRC failure")
        rows = json.loads(archive.read("manifests/pairs.json"))
        qa = json.loads(archive.read("reports/qa.json"))
    if len(rows) != qa["localized_pairs"] or qa["source_dataset_sha256"] != ORIGINAL_SHA:
        raise ValueError("Localized pair count or parent archive mismatch")
    if qa["localized_mask_pct"]["mean"] < 5 or qa["localized_mask_pct"]["min"] < 3:
        raise ValueError("Localized nail area not meaningfully increased")
    counts = Counter((row["split"], row["style_id"]) for row in rows)
    if any(counts[split, style] != qa["style_counts"][f"{split}/{style}"]
           for split in ("train", "validation") for style in STYLE_IDS):
        raise ValueError("Localized style balance changed")
    if any(len({counts[split, style] for style in STYLE_IDS}) != 1 for split in ("train", "validation")):
        raise ValueError("Localized styles are imbalanced")
    identities = {split: {row["identity_id"] for row in rows if row["split"] == split}
                  for split in ("train", "validation")}
    if len(identities["train"]) != 16 or len(identities["validation"]) != 4 or identities["train"] & identities["validation"]:
        raise ValueError("Localized identity split changed")
    decision = json.loads(review.read_text(encoding="utf-8"))
    if decision["localized_archive_sha256"] != digest(localized) or decision["status"] != "ACCEPT_FOR_CONTROLLED_EXPERIMENT":
        raise ValueError("Localized crop review not accepted for this exact archive")
    config_text = training_config()
    source = Path(__file__).resolve().parent
    repo = source.parent
    evidence = {"status": "PREPARED_NOT_TRAINED", "localized_archive_sha256": digest(localized),
                "localized_archive_bytes": localized.stat().st_size,
                "approved_archive_sha256": ORIGINAL_SHA, "toolkit_commit": TOOLKIT_COMMIT,
                "base_revision": BASE_REVISION, "steps": 50, "checkpoint_step": 50,
                "train_pairs": qa["train_pairs"], "validation_pairs": qa["validation_pairs"],
                "train_identities": sorted(identities["train"]),
                "validation_identities": sorted(identities["validation"]),
                "mask_pct": qa["localized_mask_pct"], "review": decision,
                "training_config_sha256": sha256(config_text.encode("utf-8")).hexdigest()}
    run_text = """NAILS-001-LOCAL-v1, private inference and training evidence only.

This bundle contains academic hand photos. Create a PRIVATE Kaggle Dataset with
only the .bin upload copy, attach it to a GPU T4 notebook, enable Internet,
and grant the Hugging Face FLUX.2 Klein Base model access if needed.

Cell 1, extract and verify the opaque upload:

from pathlib import Path
from hashlib import sha256
from zipfile import ZipFile
uploads = list(Path('/kaggle/input').rglob('NAILS-001-LOCAL-v1-step050-bundle.bin'))
assert len(uploads) == 1, uploads
upload = uploads[0]
print('upload SHA-256', sha256(upload.read_bytes()).hexdigest())
with ZipFile(upload) as bundle:
    assert bundle.testzip() is None
    bundle.extractall('/kaggle/working')

Cell 2, inspect and extract the exact approved data and localized derivative:

!python /kaggle/working/nails001_local_kaggle.py --phase prepare --root /kaggle/working

Cell 3, train ONLY to step 50 with exact per-step sample tracing:

!python /kaggle/working/nails001_local_kaggle.py --phase train --root /kaggle/working

Cell 4, fresh Python process, held-out evaluation:

!python /kaggle/working/nails001_local_evaluate.py --root /kaggle/working

Cell 5, package evidence:

!python /kaggle/working/nails001_local_package_evidence.py --root /kaggle/working

Download /kaggle/working/NAILS-001-LOCAL-v1-step050-evidence.zip and provide it
to the Implementation Engineer. DO NOT resume beyond step 50 until these
held-out visual results are reviewed. Keep this experimental adapter out of
the application.

Approved DATA-N001 SHA-256: {approved_sha}
Localized derivative SHA-256: {local_sha}
Pinned Base revision: {base_revision}
Pinned AI Toolkit commit: {toolkit_commit}
"""
    # The bundle SHA cannot be embedded in the bundle itself. The printed SHA
    # can be compared to the companion guide after creation.
    run_text = run_text.format(approved_sha=ORIGINAL_SHA, local_sha=digest(localized),
        base_revision=BASE_REVISION, toolkit_commit=TOOLKIT_COMMIT)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(destination, "w", ZIP_DEFLATED) as bundle:
        bundle.write(approved, "DATA-N001-final.zip")
        bundle.write(localized, "DATA-N001-LOCAL-v1.zip")
        bundle.writestr("train_config.yaml", config_text)
        bundle.writestr("local_bundle_evidence.json", json.dumps(evidence, indent=2) + "\n")
        bundle.writestr("RUN.txt", run_text)
        for name in ("nails001_kaggle_pilot.py", "nails001_local_kaggle.py",
                     "nails001_local_trace.py", "nails001_local_evaluate.py",
                     "nails001_local_package_evidence.py"):
            bundle.write(source / name, name)
        bundle.write(repo / "backend/app/nails/geometry.py", "backend/app/nails/geometry.py")
    with ZipFile(destination) as check:
        if check.testzip() is not None:
            raise ValueError("Localized Kaggle bundle CRC failure")
    upload = destination.with_suffix(".bin")
    shutil.copyfile(destination, upload)
    if digest(upload) != digest(destination):
        raise ValueError("Kaggle opaque upload differs from bundle")
    return {"status": "PREPARED_NOT_TRAINED", "bundle": str(destination),
            "upload": str(upload), "bundle_sha256": digest(destination),
            "localized_archive_sha256": digest(localized), "bytes": destination.stat().st_size,
            "train_pairs": qa["train_pairs"], "validation_pairs": qa["validation_pairs"],
            "original_mask_mean_pct": qa["original_mask_pct"]["mean"],
            "localized_mask_mean_pct": qa["localized_mask_pct"]["mean"]}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--approved", type=Path, required=True)
    parser.add_argument("--localized", type=Path, required=True)
    parser.add_argument("--review", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(build(args.approved, args.localized, args.review, args.output), indent=2))


if __name__ == "__main__":
    main()
