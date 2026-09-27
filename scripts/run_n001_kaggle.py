"""Run a prepared NAILS-001 pilot on Kaggle; never mark it deployable.

Example: python run_n001_kaggle.py --toolkit /kaggle/working/ai-toolkit
         --config /kaggle/working/train_config.yaml
         --output /kaggle/working/nails001
"""

import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import subprocess
import sys


TOOLKIT_COMMIT = "a8dfcf7d7e2b38ccc7b2fb68ece9c6358e61e7a7"
MODEL_REVISION = "a3b4f4849157f664bdbc776fd7453c2783562f4d"


def digest(path: Path) -> str:
    value = sha256()
    with path.open("rb") as file:
        for part in iter(lambda: file.read(1024 * 1024), b""):
            value.update(part)
    return value.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--toolkit", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    import torch
    from huggingface_hub import hf_hub_download
    if not torch.cuda.is_available():
        raise RuntimeError("NAILS-001 pilot requires a CUDA GPU")
    commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=args.toolkit,
                            capture_output=True, text=True, check=True).stdout.strip()
    if commit != TOOLKIT_COMMIT:
        raise RuntimeError(f"AI Toolkit commit differs: {commit}")
    model_file = Path(hf_hub_download(repo_id="black-forest-labs/FLUX.2-klein-base-4B",
        filename="flux-2-klein-base-4b.safetensors", revision=MODEL_REVISION,
        cache_dir="/tmp/hf-cache/hub"))
    if MODEL_REVISION not in model_file.parts:
        raise RuntimeError("Unexpected FLUX.2 Base snapshot")
    if args.output.exists() and (args.output / "train.log").exists():
        raise ValueError("Existing training log; refusing to overwrite the run")
    args.output.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env["HF_HOME"] = "/tmp/hf-cache"
    env["HF_HUB_CACHE"] = "/tmp/hf-cache/hub"
    command = [sys.executable, "run.py", str(args.config.resolve())]
    with (args.output / "train.log").open("w", encoding="utf-8") as log:
        process = subprocess.run(command, cwd=args.toolkit, env=env, stdout=log,
                                 stderr=subprocess.STDOUT)
    checkpoints = sorted((args.output / "checkpoints").rglob("*.safetensors"))
    log_text = (args.output / "train.log").read_text(encoding="utf-8", errors="replace")
    nonfinite = bool(re.search(r"\bloss\s*(?:is|:)\s*[+-]?(?:nan|inf)\b", log_text, re.I))
    summary = {"status": "TRAINING_FINISHED_REVIEW_REQUIRED" if process.returncode == 0 and checkpoints and not nonfinite else "FAILED",
               "exit_code": process.returncode, "toolkit_commit": commit,
               "model_revision": MODEL_REVISION, "model_sha256": digest(model_file),
               "config_sha256": digest(args.config), "gpu": torch.cuda.get_device_name(0),
               "nonfinite_loss_detected": nonfinite,
               "checkpoints": [{"path": str(path), "sha256": digest(path), "bytes": path.stat().st_size}
                               for path in checkpoints], "log_sha256": digest(args.output / "train.log")}
    (args.output / "run_summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))
    if summary["status"] == "FAILED":
        raise RuntimeError("NAILS-001 pilot failed; inspect train.log")


if __name__ == "__main__": main()
