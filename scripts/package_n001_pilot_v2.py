"""Package the immutable DATA-N001 archive with a 25-step Kaggle pilot runner."""

import argparse
from hashlib import sha256
import json
from pathlib import Path
import shutil
from zipfile import ZipFile, ZIP_DEFLATED

from train_n001_bundle import config, validate


DATA_SHA256 = "d37b68bc3e06c6ea1b1b013424dd813aafbef83db222cf9223e229d33ad105bb"
TOOLKIT_COMMIT = "a8dfcf7d7e2b38ccc7b2fb68ece9c6358e61e7a7"
MODEL_REVISION = "a3b4f4849157f664bdbc776fd7453c2783562f4d"


def digest(path: Path) -> str:
    value = sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def build(dataset: Path, archive: Path, destination: Path) -> dict:
    if destination.exists():
        raise ValueError("Refusing to overwrite a pilot bundle")
    if digest(archive) != DATA_SHA256:
        raise ValueError("Approved DATA-N001 archive hash mismatch")
    with ZipFile(archive) as source:
        if source.testzip() is not None:
            raise ValueError("DATA-N001 archive CRC failed")
    evidence = validate(dataset)
    if evidence["accepted_pairs"] != 100 or evidence["train_identities"] != 16 or evidence["validation_identities"] != 4:
        raise ValueError("Approved identity or pair count changed")
    pilot_config = config(25, 25).replace("        steps: 25\n", "        steps: 25\n        gradient_accumulation: 1\n")
    if "gradient_accumulation: 1" not in pilot_config:
        raise ValueError("Unable to set explicit accumulation")
    upload = destination.with_name(destination.stem + "-upload.bin")
    if upload.exists():
        raise ValueError("Refusing to overwrite the Kaggle upload copy")
    run = """NAILS-001 EXPERIMENTAL 25-STEP PILOT — NO APPLICATION INFERENCE

Requirements: authenticated Kaggle notebook, GPU accelerator (T4), Internet on,
and permission to download black-forest-labs/FLUX.2-klein-base-4B from Hugging Face.
If the Base model requires a token, add HF_TOKEN as a Kaggle secret and attach the
secret to the notebook. Keep this bundle private: it contains hand photographs.

1. Create a PRIVATE Kaggle Dataset containing the single file
   {upload_name}. It is the exact ZIP bytes with a .bin extension,
   preventing Kaggle's Dataset upload from auto-extracting the archive. Attach
   that private Dataset to the notebook as input.
2. Run this Python cell (it requires exactly one matching input file):

from pathlib import Path
from zipfile import ZipFile
matches = list(Path('/kaggle/input').rglob('{upload_name}'))
assert len(matches) == 1, matches
with ZipFile(matches[0]) as bundle:
    assert bundle.testzip() is None
    bundle.extractall('/kaggle/working')

3. Run the bounded pilot. It verifies the approved DATA-N001 SHA-256 and frozen
   identity split, installs the pinned AI Toolkit while constraining Kaggle Torch,
   checks the pinned Base revision, trains 25 steps, then evaluates all 20 held-out
   pairs with fixed prompts/seeds against Base and NAILS-001. It packages evidence.

!python /kaggle/working/nails001_kaggle_pilot.py --phase all --root /kaggle/working

4. Download /kaggle/working/NAILS-001-pilot-step025-evidence.zip and provide it to
   the Implementation Engineer for visual review. The runner never marks this
   model deployable. Do not continue training until the 25-step sheets are reviewed.

If a phase fails after training, inspect /kaggle/working/nails001/*.json and
train.log. To rerun only evaluation or packaging after correcting an environment
issue, use --phase evaluate or --phase package; do not rerun --phase train against
an existing train.log. Preserve all outputs for diagnosis.

Pinned AI Toolkit commit: """.replace("{upload_name}", upload.name) + TOOLKIT_COMMIT + "\nPinned Base revision: " + MODEL_REVISION + "\nApproved DATA-N001 SHA-256: " + DATA_SHA256 + "\n"
    runner = Path(__file__).with_name("nails001_kaggle_pilot.py")
    with ZipFile(destination, "w", ZIP_DEFLATED) as bundle:
        bundle.write(archive, "DATA-N001-final.zip")
        bundle.write(runner, "nails001_kaggle_pilot.py")
        bundle.writestr("train_config.yaml", pilot_config)
        bundle.writestr("RUN.txt", run)
        bundle.writestr("bundle_evidence.json", json.dumps({**evidence,
            "data_archive_sha256": DATA_SHA256, "toolkit_commit": TOOLKIT_COMMIT,
            "base_revision": MODEL_REVISION, "pilot_steps": 25,
            "checkpoint_interval": 25, "status": "PREPARED_NOT_TRAINED"}, indent=2) + "\n")
    with ZipFile(destination) as bundle:
        if bundle.testzip() is not None:
            raise ValueError("Pilot bundle CRC failed")
    shutil.copyfile(destination, upload)
    if digest(upload) != digest(destination):
        raise ValueError("Kaggle upload copy changed")
    return {"bundle": str(destination), "kaggle_upload": str(upload),
            "bytes": destination.stat().st_size,
            "sha256": digest(destination), "data_archive_sha256": DATA_SHA256,
            "status": "PREPARED_NOT_TRAINED"}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, required=True,
                        help="DATA-N001 candidate work directory containing final/")
    parser.add_argument("--archive", type=Path, required=True,
                        help="Immutable approved DATA-N001-final.zip")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(build(args.dataset, args.archive, args.output), indent=2))


if __name__ == "__main__":
    main()
