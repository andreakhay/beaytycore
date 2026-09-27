"""Gate 1: unchanged feature runtimes, fresh sequential GPU processes, no server."""

import argparse
import base64
from contextlib import contextmanager
from hashlib import sha256
from io import BytesIO
from importlib import metadata
import json
import os
from pathlib import Path, PurePosixPath
import platform
import re
import secrets
import shutil
import subprocess
import sys
import threading
import time
import traceback
from urllib.parse import urlsplit, urlunsplit
from unittest.mock import patch
from zipfile import ZIP_DEFLATED, ZipFile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "backend"))
FEATURES = ("hairstyle", "makeup", "nails")
MODEL_ID = "black-forest-labs/FLUX.2-klein-base-4B"
REVISION = "a3b4f4849157f664bdbc776fd7453c2783562f4d"
DIFFUSERS_COMMIT = "c943837899b16cbae2f619b8dd4f7bb6f07dd81a"
PINS = {"diffusers": "0.39.0.dev0", "transformers": "5.5.3", "accelerate": "1.13.0",
        "peft": "0.18.1", "huggingface_hub": "1.23.0", "numpy": "1.26.4"}
PACKAGES = (*PINS, "torch", "safetensors", "Pillow", "fastapi", "uvicorn", "python-multipart")
SCHEMA = "unified-kaggle-gate1-v1"


def digest(path):
    value = sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def save(path, value):
    Path(path).write_text(json.dumps(value, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def safe_path(root, name):
    if not isinstance(name, str):
        raise ValueError("Unsafe bundle member path")
    posix = PurePosixPath(name)
    if ("\\" in name or ":" in name or posix.is_absolute()
            or not posix.parts or any(part in {"..", "."} for part in posix.parts)):
        raise ValueError("Unsafe bundle member path")
    path = (Path(root) / name).resolve()
    if not path.is_relative_to(Path(root).resolve()):
        raise ValueError("Bundle member escapes its root")
    return path


def verify_bundle(root=None):
    root = Path(root or ROOT)
    manifest = json.loads((root / "gate1_bundle.json").read_text(encoding="utf-8"))
    if manifest.get("schema") != SCHEMA or manifest.get("base_revision") != REVISION:
        raise ValueError("Unexpected Gate 1 bundle or Base revision")
    if not isinstance(manifest.get("files"), dict) or not manifest["files"]:
        raise ValueError("Empty Gate 1 inventory")
    for name, expected in manifest["files"].items():
        if digest(safe_path(root, name)) != expected:
            raise ValueError(f"Bundle integrity mismatch: {name}")
    plan = json.loads((root / "gate1_plan.json").read_text(encoding="utf-8"))
    if plan.get("schema") != SCHEMA or set(plan.get("features", {})) != set(FEATURES):
        raise ValueError("Gate 1 requires exactly the three approved feature cases")
    for feature, case in plan["features"].items():
        for field in ("input", "reference", "reference_record"):
            name = case[field]
            if name not in manifest["files"]:
                raise ValueError(f"Uninventoried {feature} {field}")
            safe_path(root, name)
        if (case["input_sha256"] != manifest["files"][case["input"]]
                or case["reference_sha256"] != manifest["files"][case["reference"]]):
            raise ValueError(f"Input/reference hash differs from plan: {feature}")
    return plan


def feature_contract(feature):
    # Explicit experiment cases, not a production registry or adapter switcher.
    if feature == "hairstyle":
        os.environ["HAIRCAPSTONE_STYLE_REGISTRY_PATH"] = str(ROOT / "backend/app/style_registry.json")
        from scripts.kaggle_inference_server import FluxRuntime, read_adapter_metadata, REGISTRY
        from app.registry import styles_by_id
        style = styles_by_id(REGISTRY)["crew_cut"]
        return FluxRuntime, lambda: read_adapter_metadata(ROOT / "gate1/adapters/hairstyle"), {
            "style_id": "crew_cut", "prompt": style["prompt"], "adapter_id": "train001",
            "adapter_sha256": REGISTRY["adapters"]["train001"]["checkpoint_sha256"],
            "adapter_steps": 250, "generator": "flux2_klein_base_train001"}
    if feature == "makeup":
        from scripts.makeup_inference_server import MakeupRuntime
        from app.makeup_contract import ADAPTER_ID, ADAPTER_SHA256, GENERATOR, PROMPTS, PRESETS_SHA256, verify_adapter
        return MakeupRuntime, lambda: verify_adapter(ROOT / "gate1/adapters/makeup"), {
            "style_id": "natural_makeup", "prompt": PROMPTS["natural_makeup"], "adapter_id": ADAPTER_ID,
            "adapter_sha256": ADAPTER_SHA256, "adapter_steps": 250, "generator": GENERATOR,
            "prompt_presets_sha256": PRESETS_SHA256, "feature": "makeup", "lora_active": True}
    if feature == "nails":
        from scripts.nails001_local_inference_server import NailsRuntime
        from app.nails.contract import ADAPTER_ID, ADAPTER_SHA256, GENERATOR, PROMPTS, verify_adapter
        return NailsRuntime, lambda: verify_adapter(ROOT / "gate1/adapters/nails/nails001_local_v1.safetensors"), {
            "style_id": "classic_red", "prompt": PROMPTS["classic_red"], "adapter_id": ADAPTER_ID,
            "adapter_sha256": ADAPTER_SHA256, "adapter_steps": 50, "generator": GENERATOR,
            "feature": "nails", "lora_active": True}
    raise ValueError("Unknown Gate 1 feature")


def verify_case(case, expected):
    for name, value in expected.items():
        if case["expected"].get(name) != value:
            raise ValueError(f"Experiment case differs from approved contract: {name}")
    if case["settings"] != {"width": 512, "height": 512, "steps": 20, "guidance": 4.0,
                             "seed": 1977, "dtype": "float16", "cpu_offload": True}:
        raise ValueError("Gate 1 inference settings changed")


def environment(require_cuda=True):
    result = {"python": platform.python_version(), "packages": {name: metadata.version(name) for name in PACKAGES}}
    for name, version in PINS.items():
        if result["packages"][name] != version:
            raise ValueError(f"Candidate dependency mismatch: {name}")
    direct = metadata.distribution("diffusers").read_text("direct_url.json")
    commit = json.loads(direct or "{}").get("vcs_info", {}).get("commit_id")
    if commit != DIFFUSERS_COMMIT:
        raise ValueError("Diffusers is not installed from the evaluated Git commit")
    # Import in a fresh process, never in a notebook kernel carrying old NumPy.
    import numpy, torch, diffusers, transformers, accelerate, peft, huggingface_hub, safetensors
    from diffusers import Flux2KleinPipeline  # noqa: F401
    result.update({"diffusers_commit": commit, "torch": torch.__version__, "cuda": torch.version.cuda,
                   "cuda_available": torch.cuda.is_available()})
    if require_cuda and not result["cuda_available"]:
        raise RuntimeError("CUDA unavailable, select a Kaggle GPU")
    if result["cuda_available"]:
        result["gpu"] = torch.cuda.get_device_name(0)
        result["gpu_total_bytes"] = torch.cuda.get_device_properties(0).total_memory
    return result


def storage(path):
    stat = shutil.disk_usage(path)
    return {"free_bytes": stat.free, "total_bytes": stat.total}


def directory_bytes(path):
    # Report logical files and unique backing files (HF snapshot symlinks).
    seen, total = set(), 0
    for file in Path(path).rglob("*"):
        if file.is_file():
            actual = file.resolve()
            if actual not in seen:
                seen.add(actual)
                total += actual.stat().st_size
    return total


def memory(torch=None):
    result = {"process_rss_bytes": None, "process_peak_rss_bytes": None,
              "system_ram_bytes": {}, "torch_gpu_bytes": {}, "device_memory_mib": None, "warnings": []}
    try:
        lines = Path("/proc/self/status").read_text().splitlines()
        fields = {line.split(":", 1)[0]: line.split(":", 1)[1] for line in lines if ":" in line}
        result["process_rss_bytes"] = int(fields["VmRSS"].split()[0]) * 1024
        result["process_peak_rss_bytes"] = int(fields["VmHWM"].split()[0]) * 1024
    except (OSError, KeyError, ValueError):
        result["warnings"].append("Linux process RSS unavailable")
    try:
        fields = {line.split(":", 1)[0]: int(line.split(":", 1)[1].split()[0]) * 1024
                  for line in Path("/proc/meminfo").read_text().splitlines()}
        result["system_ram_bytes"] = {key: fields[key] for key in ("MemTotal", "MemAvailable")}
    except (OSError, KeyError, ValueError):
        result["warnings"].append("Linux system RAM unavailable")
    if torch is not None:
        for label, method in (("allocated", "memory_allocated"), ("reserved", "memory_reserved"),
                              ("peak_allocated", "max_memory_allocated"), ("peak_reserved", "max_memory_reserved")):
            try:
                metric = getattr(torch.cuda, method)
                result["torch_gpu_bytes"][label] = metric(0)
                if getattr(metric, "unavailable", False):
                    result["torch_gpu_bytes"][label] = None
            except Exception:
                result["torch_gpu_bytes"][label] = None
                result["warnings"].append(f"PyTorch {label} unavailable")
    try:
        query = subprocess.run(["nvidia-smi", "--query-gpu=index,memory.used,memory.total",
                                "--format=csv,noheader,nounits"], capture_output=True, text=True, timeout=3)
        if query.returncode:
            raise ValueError("nvidia-smi failed")
        result["device_memory_mib"] = [dict(zip(("index", "used", "total"),
            (int(item.strip()) for item in line.split(",")))) for line in query.stdout.splitlines()]
    except (OSError, ValueError, subprocess.TimeoutExpired):
        result["warnings"].append("Whole device telemetry unavailable")
    return result


class Sampler:
    def __init__(self, torch):
        self.torch, self.phase, self.samples = torch, "before_model_load", []
        self.stop = threading.Event()
        self.thread = threading.Thread(target=self.collect, daemon=True)

    def collect(self):
        while not self.stop.is_set():
            self.samples.append({"phase": self.phase, "monotonic": time.monotonic(), **memory(self.torch)})
            self.stop.wait(1)

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, *_):
        self.stop.set()
        self.thread.join(timeout=4)


@contextmanager
def optional_runtime_telemetry(torch, warnings):
    # Hair's unchanged generate method calls optional telemetry without a guard.
    # Guard only those measurements in this experiment; generation is untouched.
    reset, peak = torch.cuda.reset_peak_memory_stats, torch.cuda.max_memory_allocated
    def safe_reset(*args, **kwargs):
        try:
            return reset(*args, **kwargs)
        except Exception:
            warnings.append("Runtime peak reset unavailable")
    def safe_peak(*args, **kwargs):
        try:
            return peak(*args, **kwargs)
        except Exception:
            warnings.append("Runtime peak allocated unavailable")
            safe_peak.unavailable = True
            return 0  # Replaced with null in evidence, never claimed as measured zero.
    with patch.object(torch.cuda, "reset_peak_memory_stats", safe_reset), patch.object(torch.cuda, "max_memory_allocated", safe_peak):
        yield


def validate_result(payload, expected):
    from PIL import Image
    if payload.get("status") != "completed" or payload.get("generator") != expected["generator"]:
        raise ValueError("Wrong generation status or generator")
    meta = payload.get("metadata", {})
    checks = {key: value for key, value in expected.items() if key not in {"generator", "prompt"}}
    checks.update({"base_model_id": MODEL_ID, "base_model_revision": REVISION,
                   "seed": 1977, "steps": 20, "guidance": 4.0})
    for key, value in checks.items():
        if meta.get(key) != value:
            raise ValueError(f"Wrong output provenance: {key}")
    if "prompt" in meta and meta["prompt"] != expected["prompt"]:
        raise ValueError("Wrong output prompt")
    image = payload["image"]
    prefix = "data:image/png;base64,"
    if (image.get("width"), image.get("height"), image.get("content_type")) != (512, 512, "image/png"):
        raise ValueError("Wrong output image envelope")
    if not image["data_url"].startswith(prefix):
        raise ValueError("Output is not a PNG data URL")
    raw = base64.b64decode(image["data_url"][len(prefix):], validate=True)
    with Image.open(BytesIO(raw)) as opened:
        opened.load()
        if opened.format != "PNG" or opened.size != (512, 512) or opened.mode != "RGB":
            raise ValueError("Output is not 512x512 RGB PNG")
    return raw


def compare_images(reference, candidate):
    from PIL import Image, ImageChops
    with Image.open(reference) as a, Image.open(candidate) as b:
        a, b = a.convert("RGB"), b.convert("RGB")
        if a.size != b.size:
            raise ValueError("Reference dimensions differ")
        difference = ImageChops.difference(a, b)
        histogram = difference.histogram()
        return {"file_hash_equal": digest(reference) == digest(candidate),
                "rgb_pixels_equal": a.tobytes() == b.tobytes(),
                "changed_pixels": sum(pixel != (0, 0, 0) for pixel in difference.getdata()),
                "mean_absolute_channel_difference": sum((i % 256) * n for i, n in enumerate(histogram)) / (a.width * a.height * 3),
                "max_channel_difference": max(high for _, high in difference.getextrema()),
                "quality_judgment": "NOT_AUTOMATED, HUMAN_REVIEW_REQUIRED", "acceptance_tolerance": None}


def comparison_sheet(source, reference, candidate, destination):
    from PIL import Image, ImageDraw, ImageOps
    sheet = Image.new("RGB", (1536, 548), "white")
    draw = ImageDraw.Draw(sheet)
    for index, (path, label) in enumerate(((source, "Input"), (reference, "Historical reference"), (candidate, "Candidate"))):
        with Image.open(path) as image:
            sheet.paste(ImageOps.pad(image.convert("RGB"), (512, 512)), (index * 512, 36))
        draw.text((index * 512 + 10, 10), label, fill="black")
    sheet.save(destination)


def configure_runtime(feature, model):
    # No external service is started. Ephemeral keys satisfy runtime preconditions.
    key = secrets.token_urlsafe(32)
    if feature == "hairstyle":
        os.environ.update(HAIRCAPSTONE_MODEL_DIR=str(model), HAIRCAPSTONE_API_KEY=key,
                          HAIRCAPSTONE_ADAPTER_DIRS=json.dumps({"train001": str(ROOT / "gate1/adapters/hairstyle")}))
    elif feature == "makeup":
        os.environ.update(MAKEUP001_MODEL_DIR=str(model), MAKEUP001_API_KEY=key,
                          MAKEUP001_ADAPTER_DIR=str(ROOT / "gate1/adapters/makeup"))
    else:
        os.environ.update(NAILS001_MODEL_DIR=str(model), NAILS001_API_KEY=key,
                          NAILS001_ADAPTER_PATH=str(ROOT / "gate1/adapters/nails/nails001_local_v1.safetensors"))


def failure_category(phase, exc):
    if any(text in str(exc).lower() for text in ("out of memory", "cuda error", "cuda unavailable")) or type(exc).__name__ == "OutOfMemoryError":
        return "CUDA/resource"
    if isinstance(exc, (ImportError, ModuleNotFoundError)) or phase == "dependency/import":
        return "dependency/import"
    return phase


def sanitized(text):
    for name in ("HF_TOKEN", "HUGGING_FACE_HUB_TOKEN", "HAIRCAPSTONE_API_KEY", "MAKEUP001_API_KEY", "NAILS001_API_KEY"):
        value = os.environ.get(name)
        if value:
            text = text.replace(value, "<redacted>")
    def redact_url(match):
        try:
            parts = urlsplit(match.group(0))
            if parts.query or parts.username or parts.password:
                return urlunsplit((parts.scheme, parts.hostname or "<host>", parts.path, "<redacted>", ""))
        except ValueError:
            return "<URL redacted>"
        return match.group(0)
    return re.sub(r"https?://[^\s\"'<>]+", redact_url, text)


def worker(feature, model, output):
    report = {"feature": feature, "status": "FAILED", "phase": "experiment harness", "timing_seconds": {}, "measurements": {}}
    sampler = None
    def checkpoint():
        save(output / "progress.json", report)
    try:
        plan = verify_bundle()
        case = plan["features"][feature]
        report.update(style_id=case["expected"]["style_id"], input_sha256=case["input_sha256"], reference=case["reference_context"])
        report["phase"] = "dependency/import"
        checkpoint()
        report["environment"] = environment()
        import torch
        from diffusers import Flux2KleinPipeline
        runtime_class, verify_adapter, expected = feature_contract(feature)
        report["phase"] = "adapter validation"
        checkpoint()
        verify_case(case, expected)
        verify_adapter()
        configure_runtime(feature, model)
        runtime = runtime_class()
        report["phase"] = "Base loading"
        checkpoint()
        if model.name != REVISION or not (model / "model_index.json").is_file():
            raise ValueError("Base snapshot revision/path mismatch")
        report.update(base_model_id=MODEL_ID, base_model_revision=REVISION,
                      model_index_sha256=digest(model / "model_index.json"), approved_prompt=expected["prompt"], settings=case["settings"])
        report["measurements"]["before_model_load"] = memory(torch)
        original_load = Flux2KleinPipeline.from_pretrained
        def timed_base(*args, **kwargs):
            started = time.monotonic()
            pipe = original_load(*args, **kwargs)
            report["timing_seconds"]["Base_load"] = time.monotonic() - started
            report["measurements"]["after_Base_load"] = memory(torch)
            original_adapter = pipe.load_lora_weights
            def timed_adapter(*args, **kwargs):
                report["phase"] = "adapter loading"
                checkpoint()
                sampler.phase = "adapter_loading"
                started = time.monotonic()
                value = original_adapter(*args, **kwargs)
                report["timing_seconds"]["adapter_load"] = time.monotonic() - started
                return value
            pipe.load_lora_weights = timed_adapter
            return pipe
        with Sampler(torch) as sampler:
            sampler.phase = "Base_loading"
            started = time.monotonic()
            with patch.object(Flux2KleinPipeline, "from_pretrained", side_effect=timed_base):
                runtime.load()  # Original verification, FP16, offload and LoRA loading calls.
            report["timing_seconds"]["runtime_load_including_verification_offload"] = time.monotonic() - started
            report["measurements"]["after_adapter_load"] = memory(torch)
            report["phase"] = "preprocessing"
            checkpoint()
            from PIL import Image, ImageOps
            with Image.open(ROOT / case["input"]) as image:
                image.load()
                source = ImageOps.exif_transpose(image).convert("RGB")
            if feature == "nails" and source.size != (512, 512):
                raise ValueError("Nails input must remain a prepared 512 crop")
            # Portrait padding remains in the original generate methods.
            report["phase"] = "inference"
            checkpoint()
            sampler.phase = "inference"
            warnings = []
            started = time.monotonic()
            with optional_runtime_telemetry(torch, warnings):
                torch.cuda.reset_peak_memory_stats(0)
                payload = runtime.generate(source, expected["style_id"])
            report["timing_seconds"]["inference_call"] = time.monotonic() - started
            if warnings and "peak_gpu_mib" in payload["metadata"]:
                payload["metadata"]["peak_gpu_mib"] = None
            report["telemetry_warnings"] = sorted(set(warnings))
            report["inference_peak_reset_succeeded"] = not any("reset" in value for value in warnings)
            report["measurements"]["after_inference"] = memory(torch)
            report["phase"] = "output/provenance"
            checkpoint()
            raw = validate_result(payload, expected)
            image_path = output / "candidate.png"
            image_path.write_bytes(raw)
            save(output / "response.json", payload)
            report.update(output_sha256=sha256(raw).hexdigest(), output_dimensions=[512, 512], provenance=payload["metadata"])
            report["comparison"] = compare_images(ROOT / case["reference"], image_path)
            comparison_sheet(ROOT / case["input"], ROOT / case["reference"], image_path, output / "comparison.png")
            report.update(status="INFERENCE_COMPLETED_REVIEW_REQUIRED", phase="completed")
    except Exception as exc:
        report["failure_category"] = failure_category(report["phase"], exc)
        report["error"] = {"type": type(exc).__name__, "message": sanitized(str(exc))}
        (output / "failure.txt").write_text(sanitized(traceback.format_exc()), encoding="utf-8")
    finally:
        if sampler is not None:
            save(output / "memory_samples.json", sampler.samples)
            device_samples = [device["used"] for sample in sampler.samples
                for device in sample.get("device_memory_mib") or [] if device["index"] == 0]
            report["sampled_peak_device0_used_mib"] = max(device_samples) if device_samples else None
            report["device_peak_scope"] = "one-second sampled maximum, not an exact continuous peak"
        save(output / "report.json", report)
    # Process exit releases the entire pipeline, CPU weights, offload hooks and CUDA context.
    return 0 if report["status"] == "INFERENCE_COMPLETED_REVIEW_REQUIRED" else 1


def run(model, output, setup_report=None, launch=subprocess.run):
    plan = verify_bundle()
    if output.exists() or output.with_suffix(".zip").exists():
        raise ValueError("Refusing to overwrite Gate 1 evidence; use a fresh output directory")
    output.mkdir(parents=True)
    summary = {"schema": SCHEMA, "status": "IN_PROGRESS", "gate1_passed": False,
               "live_inference": True, "design": "fresh sequential process/pipeline per feature",
               "base_revision": REVISION, "plan": plan, "results": []}
    if setup_report is not None:
        summary["setup"] = json.loads(setup_report.read_text(encoding="utf-8"))
    started = time.monotonic()
    for feature in FEATURES:
        print("GATE1 FEATURE", feature, "starting fresh process", flush=True)
        folder = output / feature
        folder.mkdir()
        save(output / "summary.json", summary)
        env = os.environ.copy()
        env.update(CUDA_VISIBLE_DEVICES="0", PYTHONUNBUFFERED="1")
        with (folder / "worker.log").open("w", encoding="utf-8") as log:
            try:
                child = launch([sys.executable, str(ROOT / "scripts/unified_gate1.py"), "--worker", feature,
                                "--model-dir", str(model), "--output", str(folder)],
                               cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT, timeout=1800)
                exit_code = child.returncode
            except subprocess.TimeoutExpired:
                exit_code = "timeout"  # subprocess.run kills and waits before another feature starts.
            except OSError as exc:
                exit_code = "launch_failed"
                log.write(sanitized(f"{type(exc).__name__}: {exc}"))
        report_path = folder / "report.json"
        progress_path = folder / "progress.json"
        report = json.loads(report_path.read_text()) if report_path.exists() else {
            "feature": feature, "status": "FAILED", "failure_category": "CUDA/resource" if exit_code == "timeout" else "experiment harness",
            "error": {"message": "Worker terminated without report; inspect worker.log", "exit_code": exit_code}}
        if not report_path.exists() and progress_path.exists():
            report["last_progress"] = json.loads(progress_path.read_text())
        report["worker_exit_code"] = exit_code
        if exit_code != 0:
            report["status"] = "FAILED"
        summary["results"].append(report)
        print("GATE1 FEATURE", feature, report["status"], flush=True)
    success = all(row["status"] == "INFERENCE_COMPLETED_REVIEW_REQUIRED" for row in summary["results"])
    environments = [row.get("environment") for row in summary["results"]]
    if success and not all(value == environments[0] for value in environments):
        success = False
        summary["environment_error"] = "Features did not report the same candidate environment"
    summary.update(status="INDIVIDUAL_INFERENCE_COMPLETED_REVIEW_REQUIRED" if success else "GATE_1_INFERENCE_FAILED",
                   inference_paths_completed=success, total_feature_seconds=time.monotonic() - started,
                   resource_review="REQUIRED", output_review="REQUIRED", gate2_started=False)
    save(output / "summary.json", summary)
    with ZipFile(output.with_suffix(".zip"), "w", ZIP_DEFLATED) as archive:
        for file in sorted(output.rglob("*")):
            if file.is_file():
                archive.write(file, file.relative_to(output).as_posix())
        for feature, case in plan["features"].items():
            for name in ("input", "reference", "reference_record"):
                archive.write(ROOT / case[name], f"preserved/{feature}/{name}/{Path(case[name]).name}")
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify-only", action="store_true")
    parser.add_argument("--environment-only", action="store_true")
    parser.add_argument("--worker", choices=FEATURES)
    parser.add_argument("--model-dir", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--setup-report", type=Path)
    args = parser.parse_args()
    if args.environment_only:
        print(json.dumps(environment()))
        return
    if args.verify_only:
        plan = verify_bundle()
        for feature in FEATURES:
            _, verify, expected = feature_contract(feature)
            verify_case(plan["features"][feature], expected)
            verify()
        print("GATE_1_ARTIFACT_PREFLIGHT_OK (no model load or inference)")
        return
    if args.model_dir is None or args.output is None:
        parser.error("--model-dir and --output are required for inference")
    if args.worker:
        sys.exit(worker(args.worker, args.model_dir, args.output))
    summary = run(args.model_dir, args.output, args.setup_report)
    print(summary["status"], args.output.with_suffix(".zip"), flush=True)
    sys.exit(0 if summary["inference_paths_completed"] else 1)


if __name__ == "__main__":
    main()
