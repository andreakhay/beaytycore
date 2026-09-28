"""Replace only the running Gate 3 worker, retaining its tunnel and cached Base."""

from hashlib import sha256
import json
import os
from pathlib import Path
import shutil
import signal
import sys
import time

FILES = ('scripts/unified_gate3_server.py', 'scripts/unified_gate3_nails.py',
         'backend/app/nails/inference_options.py')


def verify_payload(payload):
    if set(payload) != {'files', 'hashes'} or set(payload['files']) != set(FILES):
        raise ValueError('Unexpected update inventory')
    if set(payload['hashes']) != set(FILES):
        raise ValueError('Unexpected update hash inventory')
    for name in FILES:
        raw = payload['files'][name].encode('utf-8')
        if sha256(raw).hexdigest() != payload['hashes'][name]:
            raise ValueError('Update source hash differs')
        compile(raw, name, 'exec')


def prepare_worker(original, target, payload):
    verify_payload(payload)
    if target.exists():
        raise ValueError('Update directory already exists; keep its evidence and use a fresh name')
    # Model/adapter files remain in the verified original bundle, never copied.
    for name in ('scripts', 'backend', 'docs'):
        shutil.copytree(original / name, target / name,
                        ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    (target / 'gate1').symlink_to(original / 'gate1', target_is_directory=True)
    for name, value in payload['files'].items():
        (target / name).write_text(value, encoding='utf-8')
    (target / 'latency_sources.json').write_text(json.dumps(payload['hashes'], indent=2))


def running_worker(pid):
    """A reaped/orphan zombie no longer holds GPU ownership or its listening port."""
    root = Path('/proc') / str(pid)
    try:
        status = (root / 'status').read_text()
        return not any(line.startswith('State:') and 'Z' in line for line in status.splitlines())
    except FileNotFoundError:
        return False


def stop_worker(pid, timeout=900):
    if not running_worker(pid):
        raise RuntimeError('Recorded GPU worker is no longer running; restart via the original notebook')
    command = (Path('/proc') / str(pid) / 'cmdline').read_bytes()
    if b'uvicorn' not in command or b'scripts.unified_gate3_server:app' not in command:
        raise RuntimeError('Recorded PID is not the expected GPU worker; refusing to stop it')
    os.kill(pid, signal.SIGTERM)
    started = time.monotonic()
    while running_worker(pid):
        if time.monotonic() - started > timeout:
            raise RuntimeError('Worker is still draining; no replacement was started. Do not force stop it.')
        time.sleep(2)


def update(payload, original=Path('/kaggle/working/gate3_bundle'),
           previous=Path('/kaggle/working/unified_gate3')):
    verify_payload(payload)
    sys.path.insert(0, str(original))
    from scripts import unified_gate3_bootstrap as boot
    # Verify the untouched original bundle/assets before stopping anything.
    boot.verify_bundle(original)
    current = boot.health('http://127.0.0.1:8765')
    if not boot.ready(current):
        raise RuntimeError('Existing GPU worker must be ready and idle before updating')
    model = json.loads((previous / 'model.json').read_text())
    if not Path(model['snapshot']).is_dir():
        raise RuntimeError('Cached pinned Base is missing; original worker remains running')
    pid = int(json.loads((previous / 'server_process.json').read_text())['pid'])
    key = os.environ.get('AI_REMOTE_API_KEY', '')
    if not key:
        from kaggle_secrets import UserSecretsClient
        key = UserSecretsClient().get_secret('AI_REMOTE_API_KEY') or ''
    if len(key) < 24:
        raise RuntimeError('Enable the existing AI_REMOTE_API_KEY Secret')
    stamp = time.strftime('%Y%m%d-%H%M%S')
    target = previous.parent / ('nails_latency_worker_' + stamp)
    output = previous.parent / ('nails_latency_update_' + stamp)
    prepare_worker(original, target, payload)
    output.mkdir()
    env = os.environ.copy()
    env.update(AI_REMOTE_API_KEY=key, AI_MODEL_DIR=model['snapshot'], CUDA_VISIBLE_DEVICES='0',
               PYTHONUNBUFFERED='1', HF_HOME='/tmp/gate3-hf-cache')
    report = {'status': 'FAILED', 'source_hashes': payload['hashes'], 'startup_seconds': None}
    print('Stopping only the GPU worker gracefully. The existing tunnel stays running.', flush=True)
    stop_worker(pid)
    boot.ROOT = target
    try:
        print('Loading the cached Base once in the updated worker; no downloads or installs.', flush=True)
        result = boot.start_server(output, env)
        if result['health'].get('nails_inference_steps') != [8, 12, 20]:
            raise RuntimeError('Updated worker did not advertise the required step choices')
        report.update(status='READY_FOR_NAILS_LATENCY_COMPARE', health=result['health'],
                      startup_seconds=result['server_start_seconds'])
        # Keep the notebook's existing evidence/acceptance cells targeting the live PID.
        shutil.copyfile(output / 'server_process.json', previous / 'server_process.json')
    except Exception:
        # Drain a partially started worker before loading the original fallback.
        process_file = output / 'server_process.json'
        if process_file.exists():
            new_pid = int(json.loads(process_file.read_text())['pid'])
            if running_worker(new_pid):
                stop_worker(new_pid)
        boot.ROOT = original
        fallback = output / 'fallback'
        fallback.mkdir()
        restored = boot.start_server(fallback, env)
        shutil.copyfile(fallback / 'server_process.json', previous / 'server_process.json')
        report.update(status='ORIGINAL_20_STEP_WORKER_RESTORED', health=restored['health'])
        print('Update failed; the original 20-step worker is restored. Return the update log.', flush=True)
    finally:
        boot.ROOT = original
        (output / 'update.json').write_text(json.dumps(report, indent=2))
    print(report['status'], flush=True)
    print('Same tunnel URL and API key. Supported Nails steps:',
          report['health'].get('nails_inference_steps', [20]), flush=True)
    print('Evidence:', output / 'update.json', flush=True)
    return report
