"""Prepare and run the temporary Kaggle FLUX GPU service from a fresh session.

The notebook cell obtains the repository; this script verifies its contents and
handles dependencies, model snapshot, adapter, server, tunnel and public health.
No training or inference request is made during setup.
"""

import argparse
from datetime import datetime, timezone
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys
import time
from urllib.error import URLError
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
OUT = Path("/kaggle/working/haircapstone_runtime")
CACHE = Path("/tmp/haircapstone-hf-cache")
MODEL = "black-forest-labs/FLUX.2-klein-base-4B"
MODEL_REVISION = "a3b4f4849157f664bdbc776fd7453c2783562f4d"
PORT = 8765
REQUIREMENTS = ROOT / "scripts/kaggle_inference_requirements.txt"
sys.path.insert(0, str(ROOT / "backend"))
from app.registry import enabled_styles, load_registry  # noqa: E402

REGISTRY = load_registry()
STYLES = {style["style_id"] for style in enabled_styles(REGISTRY)}


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def read_url(url: str, timeout: float = 10) -> dict:
    request = Request(url, headers={"User-Agent": "haircapstone-demo-health/1"})
    with urlopen(request, timeout=timeout) as response:
        return json.load(response)


def kaggle_secret(name: str) -> str:
    if os.environ.get(name):
        return os.environ[name]
    try:
        from kaggle_secrets import UserSecretsClient
        return UserSecretsClient().get_secret(name) or ""
    except Exception:
        return ""


def audit_environment() -> tuple[dict, str]:
    if not (ROOT / "backend/app/styles.py").is_file() or not REQUIREMENTS.is_file():
        raise RuntimeError("Project source is incomplete. Restore the code Input or clone the repository first.")
    import torch
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA is unavailable. Select a Kaggle GPU accelerator, start a new session, and rerun.")
    if not torch.version.cuda:
        raise RuntimeError("The notebook imported CPU-only PyTorch. Do not use /usr/bin/python3; use sys.executable.")
    key = kaggle_secret("HAIRCAPSTONE_API_KEY")
    if len(key) < 24:
        raise RuntimeError("Create a Kaggle Secret named HAIRCAPSTONE_API_KEY with a random value of at least 24 characters and enable it for this notebook.")
    token = kaggle_secret("HF_TOKEN")
    if token:
        os.environ["HF_TOKEN"] = token
    os.environ["HF_HOME"] = str(CACHE)
    os.environ["HF_HUB_CACHE"] = str(CACHE / "hub")
    os.environ["CUDA_VISIBLE_DEVICES"] = "0"
    CACHE.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)
    internet = {}
    for site in ("https://huggingface.co", "https://github.com"):
        try:
            with urlopen(Request(site, method="HEAD"), timeout=10) as response:
                internet[site] = response.status
        except (OSError, URLError) as exc:
            internet[site] = type(exc).__name__
    report = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "python": sys.version.split()[0], "python_executable": sys.executable,
        "torch": torch.__version__, "torch_cuda": torch.version.cuda,
        "gpu_count": torch.cuda.device_count(), "selected_gpu": torch.cuda.get_device_name(0),
        "selected_gpu_vram_gib": round(torch.cuda.get_device_properties(0).total_memory / 1024**3, 2),
        "working_free_gib": round(shutil.disk_usage("/kaggle/working").free / 1024**3, 2),
        "scratch_free_gib": round(shutil.disk_usage("/tmp").free / 1024**3, 2),
        "internet": internet,
    }
    write_json(OUT / "environment.json", report)
    print("ENVIRONMENT", json.dumps(report, indent=2), flush=True)
    if not isinstance(internet["https://huggingface.co"], int):
        raise RuntimeError("Hugging Face is unreachable. Enable Kaggle Internet and restart the session.")
    return report, key


def dependencies(torch_version: str, cuda_version: str) -> None:
    from packaging.requirements import Requirement
    from packaging.version import Version
    requirements = [Requirement(line.strip()) for line in REQUIREMENTS.read_text(encoding="utf-8").splitlines()
                    if line.strip() and not line.lstrip().startswith("#")]
    missing = []
    for requirement in requirements:
        try:
            version = importlib.metadata.version(requirement.name)
            if version not in requirement.specifier:
                missing.append(f"{requirement.name}=={version} outside {requirement.specifier}")
        except importlib.metadata.PackageNotFoundError:
            missing.append(f"{requirement.name} absent")
    if missing:
        print("INSTALLING inference dependencies:", missing, flush=True)
        constraints = OUT / "torch_constraints.txt"
        constraints.write_text(f"torch=={torch_version}\n", encoding="utf-8")
        with (OUT / "dependency_install.log").open("w", encoding="utf-8") as log:
            result = subprocess.run([sys.executable, "-m", "pip", "install", "--disable-pip-version-check",
                                     "--upgrade-strategy", "only-if-needed", "--constraint", str(constraints),
                                     "-r", str(REQUIREMENTS)], stdout=log, stderr=subprocess.STDOUT)
        if result.returncode:
            tail = "\n".join((OUT / "dependency_install.log").read_text(encoding="utf-8", errors="replace").splitlines()[-20:])
            raise RuntimeError(f"Inference dependency installation failed. See dependency_install.log; Torch was constrained to its original build.\n{tail}")
    else:
        print("Inference dependencies already satisfy constraints; skipping pip.", flush=True)
    try:
        torchao_version = importlib.metadata.version("torchao")
    except importlib.metadata.PackageNotFoundError:
        torchao_version = None
    if torchao_version and Version(torchao_version) < Version("0.16.0"):
        print(f"Removing optional torchao {torchao_version}: PEFT requires >=0.16.0 when torchao is installed.", flush=True)
        with (OUT / "torchao_remove.log").open("w", encoding="utf-8") as log:
            removed = subprocess.run([sys.executable, "-m", "pip", "uninstall", "-y", "torchao"],
                                     stdout=log, stderr=subprocess.STDOUT)
        if removed.returncode:
            raise RuntimeError("Could not remove incompatible optional torchao. See torchao_remove.log.")
        absent = subprocess.run([sys.executable, "-c", "import importlib.util; assert importlib.util.find_spec('torchao') is None"],
                                capture_output=True, text=True)
        if absent.returncode:
            raise RuntimeError("torchao is still importable after removal. See torchao_remove.log; restart the Kaggle session.")
    print("Checking FLUX.2 Klein imports (see dependency_check.log if this stalls).", flush=True)
    try:
        check = subprocess.run([sys.executable, "-c", "import json,torch; from diffusers import Flux2KleinPipeline; "
                                "print(json.dumps({'torch':torch.__version__,'cuda':torch.version.cuda,'available':torch.cuda.is_available()}))"],
                               capture_output=True, text=True, timeout=600)
    except subprocess.TimeoutExpired as exc:
        (OUT / "dependency_check.log").write_text(str(exc), encoding="utf-8")
        raise RuntimeError("Flux2KleinPipeline import exceeded 10 minutes; stop and inspect the Kaggle session") from exc
    (OUT / "dependency_check.log").write_text(check.stdout + check.stderr, encoding="utf-8")
    if check.returncode:
        raise RuntimeError("Flux2KleinPipeline import failed after dependency setup. See dependency_check.log.")
    actual = json.loads(check.stdout.strip().splitlines()[-1])
    if actual != {"torch": torch_version, "cuda": cuda_version, "available": True}:
        raise RuntimeError("Dependency setup changed or disabled Kaggle CUDA PyTorch. Stop and restart the session.")
    versions = {}
    for requirement in requirements:
        versions[requirement.name] = importlib.metadata.version(requirement.name)
    write_json(OUT / "dependencies.json", {"packages": versions, "torch": torch_version, "cuda": cuda_version})


def adapter_directories(explicit: list[str] | None) -> dict[str, tuple[Path, dict]]:
    sys.path.insert(0, str(ROOT / "scripts"))
    from kaggle_inference_server import read_adapter_metadata
    candidates = [Path(value) for value in explicit] if explicit else list(Path("/kaggle/input").rglob("metadata.json"))
    valid = {}
    for item in candidates:
        directory = item if item.is_dir() else item.parent
        if not (directory / "adapter.safetensors").is_file():
            continue
        raw = json.loads((directory / "metadata.json").read_text(encoding="utf-8"))
        adapter_id = raw.get("adapter_id", "train001" if raw.get("experiment") == "TRAIN-001" else None)
        if adapter_id not in REGISTRY["adapters"] or REGISTRY["adapters"][adapter_id]["status"] != "enabled":
            continue
        try:
            metadata = read_adapter_metadata(directory, adapter_id)
            if metadata.get("base_model_revision") != MODEL_REVISION:
                raise RuntimeError("Adapter Base revision differs from the pinned inference Base")
            if adapter_id in valid:
                raise RuntimeError(f"Duplicate enabled adapter bundle: {adapter_id}")
            valid[adapter_id] = (directory, metadata)
        except (RuntimeError, OSError, ValueError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"Adapter candidate at {directory} is invalid: {exc}") from exc
    expected = {key for key, value in REGISTRY["adapters"].items() if value["status"] == "enabled"}
    if set(valid) != expected:
        raise RuntimeError(f"Attach one verified bundle per enabled adapter. Expected {sorted(expected)}, found {sorted(valid)}")
    for key, (directory, metadata) in valid.items():
        print("VERIFIED ADAPTER", key, directory, metadata["checkpoint_sha256"], flush=True)
    return valid


def model_snapshot() -> Path:
    from huggingface_hub import HfApi, snapshot_download
    info = HfApi().model_info(MODEL, revision=MODEL_REVISION, files_metadata=True)
    if info.sha != MODEL_REVISION:
        raise RuntimeError(f"Base revision mismatch: {info.sha}")
    estimated_bytes = sum((s.size or 0) for s in info.siblings)
    needed = max(int(estimated_bytes * 1.3) + 5 * 1024**3, 40 * 1024**3)
    if shutil.disk_usage("/tmp").free < needed:
        raise RuntimeError(f"Scratch has insufficient space for Base snapshot: need about {needed / 1024**3:.0f} GiB.")
    print(f"DOWNLOADING/REUSING Base snapshot {MODEL}@{MODEL_REVISION} in {CACHE}", flush=True)
    path = Path(snapshot_download(repo_id=MODEL, revision=MODEL_REVISION, cache_dir=str(CACHE / "hub")))
    if path.name != MODEL_REVISION or not (path / "model_index.json").is_file():
        raise RuntimeError("Downloaded Base snapshot does not match the pinned revision")
    write_json(OUT / "model.json", {"model": MODEL, "revision": MODEL_REVISION,
                                     "snapshot": str(path), "repository_bytes_reported": estimated_bytes})
    return path


def local_health() -> dict | None:
    try:
        return read_url(f"http://127.0.0.1:{PORT}/health", 3)
    except (OSError, URLError, ValueError):
        return None


def expected_health(payload: dict | None, hashes: dict[str, str]) -> bool:
    # A V1 process started before the registry migration is still a valid
    # TRAIN-001-only fallback during an in-place Kaggle code update.
    available = payload.get("available_adapters") if payload else None
    if available is None and set(hashes) == {"train001"}:
        available = hashes
    return bool(payload and payload.get("status") == "ready" and payload.get("gpu_ready") is True
                and payload.get("base_model_loaded") is True and payload.get("lora_loaded") is True
                and payload.get("adapter_steps") == 250
                and payload.get("adapter_sha256") == hashes["train001"]
                and available == hashes
                and set(payload.get("supported_styles", [])) == STYLES)


def start_server(model: Path, adapters: dict[str, tuple[Path, dict]], key: str, hashes: dict[str, str]) -> None:
    if expected_health(local_health(), hashes):
        print("Reusing healthy GPU server on localhost.", flush=True)
        return
    if local_health() is not None:
        raise RuntimeError("Port 8765 is occupied by a server with the wrong model/adapter. Stop it before restarting.")
    process_file = OUT / "server_process.json"
    if process_file.is_file():
        prior_pid = json.loads(process_file.read_text(encoding="utf-8")).get("pid")
        if isinstance(prior_pid, int):
            try:
                os.kill(prior_pid, 0)
            except OSError:
                pass
            else:
                command_line = Path(f"/proc/{prior_pid}/cmdline")
                if not command_line.is_file() or b"kaggle_inference_server" not in command_line.read_bytes():
                    raise RuntimeError("Saved GPU server PID belongs to another process; inspect server_process.json")
                print("Waiting for the already starting GPU server PID:", prior_pid, flush=True)
                deadline = time.monotonic() + 900
                next_update = time.monotonic() + 30
                while time.monotonic() < deadline:
                    if expected_health(local_health(), hashes):
                        return
                    if time.monotonic() >= next_update:
                        print(f"Still waiting for GPU server; see {OUT / 'server.log'}", flush=True)
                        next_update = time.monotonic() + 30
                    time.sleep(3)
                raise RuntimeError(f"An existing GPU server has not become ready. See {OUT / 'server.log'}")
    env = os.environ.copy()
    env.update({"HAIRCAPSTONE_MODEL_DIR": str(model),
                "HAIRCAPSTONE_ADAPTER_DIRS": json.dumps({name: str(item[0]) for name, item in adapters.items()}),
                "HAIRCAPSTONE_API_KEY": key})
    log = (OUT / "server.log").open("a", encoding="utf-8")
    process = subprocess.Popen([sys.executable, "-m", "uvicorn", "scripts.kaggle_inference_server:app",
                                "--host", "127.0.0.1", "--port", str(PORT), "--workers", "1"],
                               cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
    write_json(process_file, {"pid": process.pid, "port": PORT})
    print("Loading Base + LoRA once. GPU server PID:", process.pid, flush=True)
    deadline = time.monotonic() + 900
    next_update = time.monotonic() + 30
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(f"GPU server exited {process.returncode}. See {OUT / 'server.log'}")
        if expected_health(local_health(), hashes):
            return
        if time.monotonic() >= next_update:
            print(f"Still loading Base + LoRA; see {OUT / 'server.log'}", flush=True)
            next_update = time.monotonic() + 30
        time.sleep(3)
    raise RuntimeError(f"GPU server did not become ready within 15 minutes. See {OUT / 'server.log'}")


def cloudflared_binary() -> Path:
    existing = shutil.which("cloudflared")
    if existing:
        return Path(existing)
    if platform.system() != "Linux" or platform.machine() not in {"x86_64", "AMD64"}:
        raise RuntimeError("This bootstrap supports Kaggle Linux x86_64 for cloudflared")
    binary = OUT / "cloudflared"
    if not binary.is_file():
        url = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64"
        temporary = binary.with_suffix(".download")
        with urlopen(url, timeout=90) as response, temporary.open("wb") as output:
            shutil.copyfileobj(response, output)
        temporary.replace(binary)
        binary.chmod(0o700)
    result = subprocess.run([str(binary), "--version"], capture_output=True, text=True, timeout=20)
    if result.returncode:
        raise RuntimeError("cloudflared binary did not start; check the official download")
    write_json(OUT / "tunnel_binary.json", {"version": result.stdout.strip(), "source": "official Cloudflare GitHub release"})
    return binary


def start_tunnel(hashes: dict[str, str]) -> str:
    prior = OUT / "endpoint.json"
    if prior.is_file():
        previous = json.loads(prior.read_text(encoding="utf-8"))
        try:
            if expected_health(read_url(previous["url"] + "/health", 10), hashes):
                print("Reusing healthy temporary tunnel.", flush=True)
                return previous["url"]
        except (OSError, URLError, ValueError):
            pass
    binary = cloudflared_binary()
    log_path = OUT / "tunnel.log"
    log = log_path.open("w", encoding="utf-8")
    process = subprocess.Popen([str(binary), "tunnel", "--url", f"http://127.0.0.1:{PORT}"],
                               cwd=OUT, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
    print("Starting Cloudflare Quick Tunnel PID:", process.pid, flush=True)
    url_pattern = re.compile(r"https://[a-z0-9-]+\.trycloudflare\.com")
    deadline = time.monotonic() + 120
    url = None
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(f"Tunnel exited {process.returncode}. See {log_path}")
        match = url_pattern.search(log_path.read_text(encoding="utf-8", errors="replace"))
        if match:
            url = match.group(0)
            break
        time.sleep(2)
    if not url:
        raise RuntimeError(f"Tunnel did not print a public URL within 2 minutes. See {log_path}")
    deadline = time.monotonic() + 120
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(f"Tunnel exited {process.returncode} before public health passed. See {log_path}")
        try:
            if expected_health(read_url(url + "/health", 12), hashes):
                write_json(prior, {"url": url, "pid": process.pid, "verified_utc": datetime.now(timezone.utc).isoformat()})
                return url
        except (OSError, URLError, ValueError):
            pass
        time.sleep(3)
    raise RuntimeError(f"Public /health did not verify through {url}. The tunnel may be blocked by Kaggle networking. See {log_path}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--adapter-dir", action="append", help="Adapter directory; repeat for each enabled adapter")
    parser.add_argument("--local-only", action="store_true", help="Start localhost service without public tunnel")
    args = parser.parse_args()
    report, key = audit_environment()
    dependencies(report["torch"], report["torch_cuda"])
    adapters = adapter_directories(args.adapter_dir)
    hashes = {name: metadata["checkpoint_sha256"] for name, (_, metadata) in adapters.items()}
    model = model_snapshot()
    start_server(model, adapters, key, hashes)
    url = f"http://127.0.0.1:{PORT}" if args.local_only else start_tunnel(hashes)
    print("\n=====================================\nHAIR CAPSTONE GPU SERVER READY", flush=True)
    print(f"GPU: {report['selected_gpu']}\nBase: {MODEL}@{MODEL_REVISION}", flush=True)
    print(f"Adapters: {', '.join(sorted(adapters))}\nStyles: {', '.join(sorted(STYLES))}", flush=True)
    print(f"Health: {url}/health\nLocal configuration:\nGENERATION_ENGINE=remote_flux\nFLUX_REMOTE_URL={url}", flush=True)
    print("FLUX_REMOTE_API_KEY=<same value as your Kaggle HAIRCAPSTONE_API_KEY Secret>", flush=True)
    print("=====================================", flush=True)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"BOOTSTRAP STOPPED: {type(exc).__name__}: {exc}", file=sys.stderr, flush=True)
        raise
