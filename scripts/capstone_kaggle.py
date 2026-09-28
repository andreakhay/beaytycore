"""Thin notebook delegates here. Reuse the immutable Deployment-01 GPU bundle."""

from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
import sys
from uuid import uuid4
from zipfile import ZipFile, ZIP_DEFLATED

try:
    from scripts.capstone_discovery import (BUNDLE_NAME, BUNDLE_SHA, StartupError, make_record,
                                           publish, confirm_publication, verify_worker, verify_health, VERSION)
except ModuleNotFoundError:
    from capstone_discovery import (BUNDLE_NAME, BUNDLE_SHA, StartupError, make_record,
                                   publish, confirm_publication, verify_worker, verify_health, VERSION)

WORK = Path('/kaggle/working/capstone')
ROOT = WORK / 'runtime'
OUT = WORK / 'session'


def extract(source, target):
    if sha256(source.read_bytes()).hexdigest() != BUNDLE_SHA:
        raise StartupError('Wrong private Deployment-01 package hash')
    with ZipFile(source) as archive:
        names = archive.namelist()
        manifest = json.loads(archive.read('gate3_bundle.json'))
        if archive.testzip() or len(names) != len(set(names)) or set(names) != set(manifest['files']) | {'gate3_bundle.json'}:
            raise StartupError('Package CRC or inventory mismatch')
        entries = []
        for name in names:
            destination = (target / name).resolve()
            if '\\' in name or ':' in name or not destination.is_relative_to(target.resolve()):
                raise StartupError('Unsafe package member')
            raw = archive.read(name)
            if name != 'gate3_bundle.json' and sha256(raw).hexdigest() != manifest['files'][name]:
                raise StartupError('Package member hash mismatch')
            entries.append((destination, raw))
        if target.exists():
            if any(not path.is_file() or path.read_bytes() != raw for path, raw in entries):
                raise StartupError('Extracted package changed; use a fresh session')
            return
        for path, raw in entries:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw)


def run_bootstrap(key):
    env = {**os.environ, 'AI_REMOTE_API_KEY': key, 'PYTHONUNBUFFERED': '1'}
    # Original bootstrap retains all exact pins, verifier, Base cache, owner and stages.
    command = [sys.executable, str(ROOT / 'scripts/unified_gate3_bootstrap.py'), '--output', str(OUT)]
    with (WORK / 'bootstrap.log').open('w', encoding='utf-8') as log:
        process = subprocess.Popen(command, cwd=ROOT, env=env, stdout=subprocess.PIPE,
                                   stderr=subprocess.STDOUT, text=True)
        for line in process.stdout:
            log.write(line)
            log.flush()
            if line.startswith(('GATE3 STAGE', 'GATE3 STILL', 'GATE3 STARTUP')):
                print(line.rstrip(), flush=True)
        process.wait()
    report = json.loads((OUT / 'startup.json').read_text(encoding='utf-8'))
    if process.returncode or report.get('status') != 'READY_FOR_LIVE_ACCEPTANCE':
        error = StartupError('Original bootstrap failed; inspect bootstrap.log and stage log')
        error.stage = {'bundle verification': 'package_verification', 'host preflight': 'host_preflight',
                       'dependency setup': 'dependency_install', 'exact environment': 'environment_verification',
                       'Base download': 'base_download', 'server startup': 'worker_start',
                       'public tunnel': 'tunnel_start'}.get(report.get('phase'), 'bootstrap_process')
        raise error
    return json.loads((OUT / 'endpoint.json').read_text(encoding='utf-8'))['url']


def main(input_root=Path('/kaggle/input')):
    stage, key = 'secret_preflight', None
    WORK.mkdir(parents=True, exist_ok=True)
    try:
        from kaggle_secrets import UserSecretsClient
        key = UserSecretsClient().get_secret('AI_REMOTE_API_KEY') or ''
        state = make_record(key, 'starting')
        stage = 'publish_starting'
        try:
            publish(state, key)
        except StartupError:
            print('Discovery unavailable at stage=publish_starting; preparing worker for explicit emergency override.', flush=True)
        stage = 'package_verification'
        found = list(input_root.rglob(BUNDLE_NAME))
        if len(found) != 1:
            raise StartupError('Attach exactly one approved private Deployment-01 dataset')
        extract(found[0], ROOT)
        if OUT.exists():
            stage = 'existing_session_verification'
            url = json.loads((OUT / 'endpoint.json').read_text(encoding='utf-8'))['url']
            health = verify_worker(url, key)
            print('Reusing verified running worker; no second Base load.', flush=True)
        else:
            stage = 'exact_environment_and_worker_bootstrap'
            url = run_bootstrap(key)
            stage = 'public_readiness'
            health = verify_worker(url, key)
        stage = 'endpoint_publication'
        record = make_record(key, 'ready', url)
        publish(record, key)
        discovered, acknowledged = confirm_publication(record, key)
        if discovered != url or acknowledged['publication_id'] != record['publication_id']:
            raise StartupError('Publication readback did not match this startup')
        (OUT / 'capstone-startup.json').write_text(json.dumps({
            'status': 'CAPSTONE_AI_READY', 'publication_id': record['publication_id'],
            'worker_version': VERSION, 'bundle_sha256': BUNDLE_SHA,
            'foundation_load_count': health['foundation_load_count'],
            'supported_features': health['supported_features'], 'publication_success': True}, indent=2), encoding='utf-8')
        print('CAPSTONE_AI_READY', 'version=' + VERSION, 'Base=1',
              'features=hairstyle,makeup,nails', 'endpoint_published=True', flush=True)
        print('Now double-click START_CAPSTONE.bat on your laptop. No URL copying.', flush=True)
        return True
    except Exception as exc:
        stage = getattr(exc, 'stage', stage)
        # Never print an arbitrary exception body, Secret or private path.
        if key:
            try:
                publish(make_record(key, 'failed'), key)
            except Exception:
                pass
        result = {'status': 'CAPSTONE_STARTUP_FAILED', 'stage': stage, 'exception_type': type(exc).__name__}
        if isinstance(exc, StartupError):
            result['detail'] = str(exc)
        (WORK / ('failure-' + str(uuid4()) + '.json')).write_text(json.dumps(result, indent=2), encoding='utf-8')
        print('CAPSTONE_STARTUP_FAILED', 'stage=' + stage,
              str(exc) if isinstance(exc, StartupError) else type(exc).__name__, flush=True)
        print('Inspect capstone/bootstrap.log and session logs. Do not repeatedly start another worker.', flush=True)
        return False


def collect_evidence():
    """No generations. Preserve old Cell 4 safe probes and new startup evidence."""
    from kaggle_secrets import UserSecretsClient
    from capstone_discovery import request
    key = UserSecretsClient().get_secret('AI_REMOTE_API_KEY')
    base = 'http://127.0.0.1:8765'
    def status():
        return json.loads(request(base + '/status', headers={'X-API-Key': key}))
    before = status()
    verify_health(before)
    boundary = 'capstone-safe-probe'
    probes = {}
    from urllib.error import HTTPError
    from urllib.request import Request, urlopen
    for name, feature, style, auth in [('wrong_key', 'hairstyle', 'crew_cut', 'wrong'),
            ('unknown_feature', 'unknown', 'crew_cut', key), ('invalid_style', 'hairstyle', 'invalid', key),
            ('invalid_image', 'hairstyle', 'crew_cut', key)]:
        body = (f'--{boundary}\r\nContent-Disposition: form-data; name="style_id"\r\n\r\n{style}\r\n'
                f'--{boundary}\r\nContent-Disposition: form-data; name="image"; filename="bad.png"\r\n'
                f'Content-Type: image/png\r\n\r\nBAD\r\n--{boundary}--\r\n').encode()
        try:
            with urlopen(Request(base + '/' + feature + '/generate', data=body,
                    headers={'X-API-Key': auth, 'Content-Type': 'multipart/form-data; boundary=' + boundary}), timeout=20) as response:
                probes[name] = response.status
        except HTTPError as exc:
            probes[name] = exc.code
    if probes != {'wrong_key': 401, 'unknown_feature': 404, 'invalid_style': 400, 'invalid_image': 400}:
        raise StartupError('Unexpected safe HTTP probe results')
    after = status()
    verify_health(after)
    if len(after['requests']) != len(before['requests']):
        raise StartupError('Safe probes unexpectedly performed GPU work')
    (OUT / 'live_status.json').write_text(json.dumps(after, indent=2), encoding='utf-8')
    (OUT / 'http_probes.json').write_text(json.dumps(probes, indent=2), encoding='utf-8')
    with ZipFile(OUT / 'live-evidence.zip', 'x', ZIP_DEFLATED) as archive:
        for name in ('startup.json', 'model.json', 'endpoint.json', 'live_status.json', 'http_probes.json',
                     'environment.log', 'artifact_preflight.log', 'server.log', 'capstone-startup.json'):
            if (OUT / name).is_file():
                archive.write(OUT / name, name)
        archive.write(ROOT / 'deployment01_sources.json', 'deployment01_sources.json')
        for name in ('capstone_kaggle.py', 'capstone_discovery.py'):
            archive.write(Path(__file__).with_name(name), 'startup_sources/' + name)
    print('REHEARSAL_EVIDENCE_READY_FOR_REVIEW', 'Download /kaggle/working/capstone/session/live-evidence.zip')
