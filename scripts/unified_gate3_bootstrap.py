"""Reproduce Gate 2 environment, start one unified GPU worker and one tunnel."""

import argparse
from importlib import metadata
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys
import time
from urllib.request import urlopen
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import unified_gate1 as gate

PORT = 8765


def verify_bundle(root=ROOT):
    manifest = json.loads((root / 'gate3_bundle.json').read_text())
    if manifest.get('schema') != 'unified-kaggle-gate3-v1' or manifest.get('base_revision') != gate.REVISION:
        raise ValueError('Wrong Gate 3 bundle manifest')
    for name, expected in manifest['files'].items():
        if gate.digest(gate.safe_path(root, name)) != expected:
            raise ValueError(f'Gate 3 bundle member differs: {name}')
    from scripts.unified_gate2 import verify_experiment
    verify_experiment(root)
    review = json.loads((root / 'docs/experiments/unified-kaggle-gate2-review.json').read_text())
    if review['status'] != 'GATE_2_PASSED' or review['trusted_bundle_sha256'] != manifest['source_gate2_bundle_sha256']:
        raise ValueError('Gate 2 review is missing or inconsistent')
    return manifest, review


def run(args, output, name, env):
    print('GATE3 STAGE', name, 'started', flush=True)
    started = time.monotonic()
    with (output / name).open('w', encoding='utf-8') as log:
        process = subprocess.Popen(args, cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT)
        while process.poll() is None:
            try:
                process.wait(timeout=60)
            except subprocess.TimeoutExpired:
                print('GATE3 STILL RUNNING', name, round(time.monotonic() - started),
                      'seconds; log bytes:', (output / name).stat().st_size, flush=True)
    if process.returncode:
        raise RuntimeError(f'{name} failed; inspect its log')
    print('GATE3 STAGE', name, 'completed', flush=True)


def health(base):
    try:
        with urlopen(base + '/health', timeout=12) as response:
            return json.load(response)
    except (OSError, ValueError):
        return None


def ready(value):
    return (isinstance(value, dict) and value.get('status') == 'ready'
            and value.get('base_model_loaded') is True
            and value.get('foundation_load_count') == 1
            and value.get('base_model_revision') == gate.REVISION
            and set(value.get('supported_features', [])) == set(gate.FEATURES))


def start_server(output, env):
    if health(f'http://127.0.0.1:{PORT}') is not None:
        raise RuntimeError('Gate 3 port is already in use; refuse a second server')
    started = time.monotonic()
    next_update = started + 30
    with (output / 'server.log').open('w', encoding='utf-8') as log:
        process = subprocess.Popen([sys.executable, '-m', 'uvicorn', 'scripts.unified_gate3_server:app',
            '--host', '127.0.0.1', '--port', str(PORT), '--workers', '1'], cwd=ROOT, env=env,
            stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
    gate.save(output / 'server_process.json', {'pid': process.pid, 'port': PORT})
    while time.monotonic() - started < 900:
        if process.poll() is not None:
            raise RuntimeError('Unified server exited; inspect server.log')
        response = health(f'http://127.0.0.1:{PORT}')
        if ready(response):
            return {'server_start_seconds': time.monotonic() - started, 'health': response}
        if response is not None and response.get('status') == 'unready':
            raise RuntimeError('Unified server loaded but is unready; inspect server.log')
        if time.monotonic() >= next_update:
            print('GATE3 STILL LOADING one Base; server.log bytes:',
                  (output / 'server.log').stat().st_size, flush=True)
            next_update = time.monotonic() + 30
        time.sleep(3)
    raise RuntimeError('Unified Base load exceeded 15 minutes; inspect server.log')


def tunnel(output):
    if platform.system() != 'Linux' or platform.machine() not in ('x86_64', 'AMD64'):
        raise RuntimeError('Cloudflare Quick Tunnel requires Kaggle Linux x86_64')
    binary = output / 'cloudflared'
    if not binary.exists():
        with urlopen('https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64',
                     timeout=90) as source, binary.open('wb') as target:
            shutil.copyfileobj(source, target)
        binary.chmod(0o700)
    with (output / 'tunnel.log').open('w', encoding='utf-8') as log:
        process = subprocess.Popen([str(binary), 'tunnel', '--url', f'http://127.0.0.1:{PORT}'],
                                   cwd=output, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
    pattern = re.compile(r'https://[a-z0-9-]+\.trycloudflare\.com')
    started = time.monotonic()
    while time.monotonic() - started < 240:
        if process.poll() is not None:
            raise RuntimeError('Tunnel exited; inspect tunnel.log')
        match = pattern.search((output / 'tunnel.log').read_text(encoding='utf-8', errors='replace'))
        if match:
            public = match.group(0)
            response = health(public)
            if ready(response):
                return {'url': public, 'pid': process.pid,
                        'public_health': response, 'tunnel_ready_seconds': time.monotonic() - started}
        time.sleep(3)
    raise RuntimeError('Public unified health not ready; inspect tunnel.log')


def bootstrap(output, local_only=False):
    output = Path(output)
    if output.exists():
        raise ValueError('Choose a fresh Gate 3 output directory')
    output.mkdir(parents=True)
    report = {'schema': 'unified-kaggle-gate3-startup-v1', 'status': 'FAILED',
              'phase': 'bundle verification', 'gate3_passed': False, 'timing_seconds': {}}
    started = time.monotonic()
    try:
        manifest, review = verify_bundle()
        report['manifest_sha256'] = gate.digest(ROOT / 'gate3_bundle.json')
        env = os.environ.copy()
        env.update(CUDA_VISIBLE_DEVICES='0', PYTHONUNBUFFERED='1', HF_HOME='/tmp/gate3-hf-cache')
        expected = review['environment']
        report['phase'] = 'host preflight'
        check = subprocess.run([sys.executable, '-c',
            "import json,platform,torch;print(json.dumps({'python':platform.python_version(),'torch':torch.__version__,'cuda':torch.version.cuda,'gpu':torch.cuda.get_device_name(0) if torch.cuda.is_available() else None}))"],
            cwd=ROOT, env=env, capture_output=True, text=True)
        if check.returncode:
            raise RuntimeError('Host Python/Torch/CUDA preflight failed')
        host = json.loads(check.stdout.strip().splitlines()[-1])
        if any(host[k] != expected[k] for k in ('python','torch','cuda','gpu')):
            report['observed_host'] = host
            raise ValueError('Host differs from reviewed Gate 2 environment')
        report['host'] = host
        report['phase'] = 'dependency setup'
        constraints = [f"torch=={expected['torch']}"]
        for name in ('torchvision','torchaudio'):
            try:
                constraints.append(f'{name}=={metadata.version(name)}')
            except metadata.PackageNotFoundError:
                pass
        path = output / 'torch_constraints.txt'
        path.write_text('\n'.join(constraints) + '\n')
        try:
            version = metadata.version('torchao')
            if tuple(int(v) for v in version.split('.')[:2]) < (0,16):
                run([sys.executable,'-m','pip','uninstall','-y','torchao'],output,'optional_torchao.log',env)
        except metadata.PackageNotFoundError:
            pass
        try:
            metadata.version('torchao')
        except metadata.PackageNotFoundError:
            pass
        else:
            raise ValueError('Optional torchao remains installed; reviewed environment removed it')
        run([sys.executable,'-m','pip','install','--constraint',str(path),'-r',
             str(ROOT/'scripts/unified_gate3_requirements.txt')],output,'dependency_install.log',env)
        report['phase'] = 'exact environment'
        run([sys.executable,str(ROOT/'scripts/unified_gate2.py'),'--environment-only'],output,'environment.log',env)
        report['environment'] = json.loads((output/'environment.log').read_text().strip().splitlines()[-1])
        if any(report['environment'].get(k) != expected.get(k) for k in ('python','packages','diffusers_commit','torch','cuda','gpu')):
            raise ValueError('Resolved packages differ from reviewed Gate 2 environment')
        run([sys.executable,str(ROOT/'scripts/unified_gate2.py'),'--verify-only'],output,'artifact_preflight.log',env)
        report['phase'] = 'Base download'
        cache = Path('/tmp/gate3-hf-cache/hub')
        cache.parent.mkdir(parents=True, exist_ok=True)
        run([sys.executable,str(ROOT/'scripts/unified_gate1_bootstrap.py'),'--download-only',
             '--output',str(output/'model.json'),'--cache',str(cache)],output,'base_download.log',env)
        model = json.loads((output/'model.json').read_text())
        if model['model_index_sha256'] != review['base_model_index_sha256']:
            raise ValueError('Base index differs from reviewed Gate 2')
        report['model'] = {k:v for k,v in model.items() if k != 'snapshot'}
        key = env.get('AI_REMOTE_API_KEY','')
        if not key:
            from kaggle_secrets import UserSecretsClient
            key = UserSecretsClient().get_secret('AI_REMOTE_API_KEY') or ''
        if len(key) < 24:
            raise RuntimeError('Attach AI_REMOTE_API_KEY Kaggle Secret of at least 24 characters')
        env.update(AI_REMOTE_API_KEY=key, AI_MODEL_DIR=model['snapshot'])
        report['phase'] = 'server startup'
        server = start_server(output, env)
        report['timing_seconds'].update(server_startup=server['server_start_seconds'],
                                         Base_and_first_adapter_load=server['health']['load_seconds'])
        report['local_health'] = server['health']
        report['phase'] = 'public tunnel'
        endpoint = {'url':'http://127.0.0.1:'+str(PORT),
                    'public_health':server['health']} if local_only else tunnel(output)
        gate.save(output/'endpoint.json',endpoint)
        report['public_health'] = endpoint['public_health']
        report['timing_seconds']['tunnel_ready'] = endpoint.get('tunnel_ready_seconds')
        report['phase'],report['status'] = 'completed','READY_FOR_LIVE_ACCEPTANCE'
        print('ONE UNIFIED URL:',endpoint['url'],flush=True)
        print('Health:',endpoint['url']+'/health',flush=True)
        print('Supported features: hairstyle, makeup, nails; Base loads:',
              report['public_health']['foundation_load_count'],flush=True)
        print('Set AI_REMOTE_URL to this URL and AI_REMOTE_API_KEY to the same Kaggle Secret in the local backend.',flush=True)
    except Exception as exc:
        report['error'] = {'type':type(exc).__name__, 'message':gate.sanitized(str(exc))}
    finally:
        report['timing_seconds']['total_bootstrap'] = time.monotonic()-started
        gate.save(output/'startup.json',report)
        print('GATE3 STARTUP:',report['status'],'phase:',report['phase'],flush=True)
        print('Evidence:',output/'startup.json',flush=True)
    return report


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=Path('/kaggle/working/unified_gate3'))
    parser.add_argument('--local-only',action='store_true')
    args=parser.parse_args()
    result=bootstrap(args.output,args.local_only)
    sys.exit(0 if result['status']=='READY_FOR_LIVE_ACCEPTANCE' else 1)
