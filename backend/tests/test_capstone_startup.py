"""Startup only, fake discovery/worker/app boundaries. No GPU inference."""

from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
import time

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts import capstone_discovery as discovery
from scripts import capstone_kaggle as kaggle
from scripts import capstone_launch as launch

KEY = 'LOCAL_TEST_KEY_NOT_A_REAL_SECRET_12345'
URL = 'https://' + 'startup-fixture' + '.trycloudflare.com'


def health():
    return {'status': 'ready', 'gpu_runtime_ready': True, 'base_model_loaded': True,
            'foundation_load_count': 1, 'base_model_revision': discovery.REVISION,
            'diagnostics_version': discovery.VERSION, 'gpu_busy': False,
            'supported_features': ['hairstyle', 'makeup', 'nails']}


def test_publish_discover_format_and_secret_exclusion(monkeypatch):
    record = discovery.make_record(KEY, 'ready', URL)
    calls = []
    def request(url, body=None, headers=None):
        calls.append((url, body, headers))
        event = {'event': 'message', 'message': discovery.canonical(record).decode()}
        return json.dumps(event).encode()
    monkeypatch.setattr(discovery, 'request', request)
    discovery.publish(record, KEY)
    assert discovery.discover(KEY) == (URL, record)
    assert KEY not in str(calls) and KEY not in json.dumps(record)
    assert calls[0][2] == {'Content-Type': 'text/plain; charset=utf-8'}
    assert 'since=latest' in calls[1][0]
    assert discovery.topic(KEY) == discovery.topic(KEY)
    assert discovery.topic(KEY) != discovery.topic(KEY + 'different')


@pytest.mark.parametrize('previous_state', ['empty', 'starting', 'failed', 'ready'])
def test_acknowledged_publication_waits_for_exact_cache_visibility(monkeypatch, previous_state):
    expected = discovery.make_record(KEY, 'ready', URL)
    previous = None if previous_state == 'empty' else discovery.make_record(
        KEY, previous_state, URL if previous_state == 'ready' else None)
    rows = iter([previous, previous, expected])
    monkeypatch.setattr(discovery, 'latest_record', lambda key: next(rows))
    waits = []
    monkeypatch.setattr(discovery.time, 'sleep', waits.append)
    assert discovery.confirm_publication(expected, KEY) == (URL, expected)
    assert waits == [2, 2]


def test_publication_never_accepts_old_ready_record_or_forgery(monkeypatch):
    expected = discovery.make_record(KEY, 'ready', URL)
    previous = discovery.make_record(KEY, 'ready', URL)
    monkeypatch.setattr(discovery, 'latest_record', lambda key: previous)
    with pytest.raises(discovery.StartupError, match='not visible'):
        discovery.confirm_publication(expected, KEY, timeout=0)
    monkeypatch.setattr(discovery, 'latest_record', lambda key: {**expected, 'signature': 'wrong'})
    with pytest.raises(discovery.StartupError, match='signature'):
        discovery.confirm_publication(expected, KEY)


def test_discovery_uses_fresh_cache_read_each_time(monkeypatch):
    record = discovery.make_record(KEY, 'ready', URL)
    calls = []
    def request(url, **kwargs):
        calls.append((url, kwargs))
        return json.dumps({'event': 'message', 'message': json.dumps(record)}).encode()
    monkeypatch.setattr(discovery, 'request', request)
    assert discovery.discover(KEY) == discovery.discover(KEY)
    assert calls[0][0] != calls[1][0]
    assert all(row[1]['headers']['Cache-Control'] == 'no-cache' for row in calls)


@pytest.mark.parametrize('change', ['expired', 'future', 'signature', 'runtime', 'bundle', 'unknown_field', 'starting', 'failed', 'identity'])
def test_invalid_or_stale_record_fails(change):
    record = discovery.make_record(KEY, 'ready', URL, now=1000)
    now = 1001
    if change == 'expired': now = 1000 + discovery.TTL
    if change == 'future': now = 0
    if change == 'signature': record['endpoint'] = URL.replace('fixture', 'wrong')
    if change == 'runtime': record['worker_version'] = 'wrong'
    if change == 'bundle': record['bundle_sha256'] = 'wrong'
    if change == 'unknown_field': record['secret'] = 'SHOULD_NOT_BE_ALLOWED'
    if change in ('starting', 'failed'): record = discovery.make_record(KEY, change, now=1000)
    if change == 'identity': record['publication_id'] = 'not-a-uuid'
    if change not in ('signature', 'expired', 'future'):
        record['signature'] = discovery.sign({k: v for k, v in record.items() if k != 'signature'}, KEY)
    with pytest.raises(discovery.StartupError):
        discovery.validate_record(record, KEY, now=now)


@pytest.mark.parametrize('bad', [None, 'http://localhost', 'https://private.invalid',
                               URL + '/path', URL + '?token=secret', URL + ':443',
                               URL.replace('https://', 'https://user:password@')])
def test_endpoint_rejects_credentials_paths_and_wrong_hosts(bad):
    with pytest.raises(discovery.StartupError): discovery.endpoint(bad)


def test_latest_invalid_never_falls_back_to_older(monkeypatch):
    good = discovery.make_record(KEY, 'ready', URL)
    bad = {**good, 'signature': 'wrong'}
    raw = '\n'.join(json.dumps({'event': 'message', 'message': json.dumps(v)}) for v in (good, bad)).encode()
    monkeypatch.setattr(discovery, 'request', lambda _, **kwargs: raw)
    with pytest.raises(discovery.StartupError, match='signature'):
        discovery.discover(KEY)


@pytest.mark.parametrize('raw', [b'', b'garbage', b'{"event":"message","message":"garbage"}'])
def test_empty_or_malformed_discovery(monkeypatch, raw):
    monkeypatch.setattr(discovery, 'request', lambda _, **kwargs: raw)
    with pytest.raises(discovery.StartupError): discovery.discover(KEY)


@pytest.mark.parametrize('change', ['version', 'not_ready', 'base_not_loaded', 'base_count', 'features', 'revision', 'busy'])
def test_wrong_worker_rejected_before_key_is_sent(monkeypatch, change):
    value = health()
    if change == 'version': value['diagnostics_version'] = 'wrong'
    if change == 'not_ready': value['gpu_runtime_ready'] = False
    if change == 'base_not_loaded': value['base_model_loaded'] = False
    if change == 'base_count': value['foundation_load_count'] = 2
    if change == 'features': value['supported_features'] = ['hairstyle']
    if change == 'revision': value['base_model_revision'] = 'wrong'
    if change == 'busy': value['gpu_busy'] = True
    calls = []
    def request(url, **kwargs):
        calls.append(kwargs)
        return json.dumps(value).encode()
    monkeypatch.setattr(discovery, 'request', request)
    with pytest.raises(discovery.StartupError): discovery.verify_worker(URL, KEY)
    assert calls == [{}]


def test_valid_worker_checks_auth_without_generation(monkeypatch):
    calls = []
    def request(url, **kwargs):
        calls.append((url, kwargs))
        return json.dumps(health()).encode()
    monkeypatch.setattr(discovery, 'request', request)
    assert discovery.verify_worker(URL, KEY)['foundation_load_count'] == 1
    assert [row[0].split('/')[-1] for row in calls] == ['health', 'status']
    assert calls[-1][1]['headers']['X-API-Key'] == KEY


@pytest.fixture
def local(monkeypatch, tmp_path):
    root = tmp_path / 'project'
    (root / 'backend').mkdir(parents=True)
    (root / 'backend/.env').write_text('AI_REMOTE_API_KEY=' + KEY + '\nAI_REMOTE_URL=https://old.invalid\nNAILS_INFERENCE_STEPS=8\n', encoding='utf-8')
    work = root / '.tmp/capstone'
    work.mkdir(parents=True)
    monkeypatch.setattr(launch, 'ROOT', root)
    monkeypatch.setattr(launch, 'WORK', work)
    monkeypatch.setattr(launch, 'STATE', work / 'control.json')
    monkeypatch.delenv('AI_REMOTE_API_KEY', raising=False)
    monkeypatch.setattr(launch, 'discover', lambda key: (URL, {'publication_id': 'fixture-publication'}))
    monkeypatch.setattr(launch, 'verify_worker', lambda url, key: health())
    return root


def test_process_environment_overrides_file_without_writing(local, monkeypatch):
    before = (local / 'backend/.env').read_bytes()
    monkeypatch.setenv('NAILS_INFERENCE_STEPS', '12')
    env = launch.process_env(URL)
    assert env['AI_REMOTE_URL'] == URL and env['AI_REMOTE_API_KEY'] == KEY
    assert env['NAILS_INFERENCE_STEPS'] == '12' and env['GENERATION_ENGINE'] == 'remote_flux'
    assert (local / 'backend/.env').read_bytes() == before


def test_launcher_owned_start_and_manual_override(local, monkeypatch, capsys):
    calls = []
    monkeypatch.setattr(launch, 'occupied', lambda _: False)
    monkeypatch.setattr(launch, 'discover', lambda _: pytest.fail('Manual override should not discover'))
    def spawn(command, **kwargs):
        calls.append((command, kwargs))
        launch.STATE.write_text(json.dumps({'session_id': kwargs['env']['CAPSTONE_LAUNCH_SESSION']}))
        return type('Child', (), {'poll': lambda _: None})()
    monkeypatch.setattr(launch.subprocess, 'Popen', spawn)
    monkeypatch.setattr(launch, 'control', lambda state: {'stage': 'ready', 'ready': True})
    before = (local / 'backend/.env').read_bytes()
    assert launch.start(URL) == 0
    assert calls[0][1]['env']['AI_REMOTE_URL'] == URL
    assert KEY not in str(calls[0][0]) and URL not in str(calls[0][0])
    assert 'CAPSTONE READY' in capsys.readouterr().out
    assert (local / 'backend/.env').read_bytes() == before


def test_unmanaged_ports_fail_without_killing_or_spawning(local, monkeypatch):
    monkeypatch.setattr(launch, 'occupied', lambda _: True)
    monkeypatch.setattr(launch.subprocess, 'Popen', lambda *a, **kw: pytest.fail('Unmanaged port must not spawn'))
    assert launch.start() == 1


def test_same_owned_session_reused(local, monkeypatch):
    env = launch.process_env(URL)
    launch.STATE.write_text(json.dumps({'session_id': 'owned'}))
    monkeypatch.setattr(launch, 'control', lambda _: {'identity': launch.identity(env), 'ready': True})
    monkeypatch.setattr(launch, 'wait_application', lambda *args, **kw: None)
    monkeypatch.setattr(launch.subprocess, 'Popen', lambda *a, **kw: pytest.fail('Should reuse'))
    assert launch.start() == 0


def test_stop_only_authenticated_controller(local, monkeypatch):
    launch.STATE.write_text(json.dumps({'session_id': 'owned'}))
    calls = []
    def control(state, action):
        calls.append(action)
        launch.STATE.unlink()
    monkeypatch.setattr(launch, 'control', control)
    launch.stop_owned()
    assert calls == ['stop'] and not launch.STATE.exists()


def test_unavailable_controller_and_ports_preserve_processes(local, monkeypatch):
    launch.STATE.write_text(json.dumps({'session_id': 'owned'}))
    monkeypatch.setattr(launch, 'control', lambda *args: (_ for _ in ()).throw(discovery.StartupError('missing')))
    monkeypatch.setattr(launch, 'occupied', lambda _: True)
    with pytest.raises(discovery.StartupError): launch.stop_owned()
    assert launch.STATE.exists()


@pytest.mark.parametrize('fail_stage', [None, 'backend_readiness', 'final_readiness'])
def test_supervisor_orchestrates_and_closes_owned_children(local, monkeypatch, fail_stage):
    next_script = local / 'frontend/node_modules/next/dist/bin/next'
    next_script.parent.mkdir(parents=True)
    next_script.write_text('fixture')
    env = launch.process_env(URL)
    env['CAPSTONE_LAUNCH_SESSION'] = 'supervisor-test'
    monkeypatch.setattr(launch.os, 'environ', env)
    monkeypatch.setattr(launch, 'occupied', lambda _: False)
    monkeypatch.setattr(launch.shutil, 'which', lambda _: 'node')
    spawned, waits, closed = [], [], []
    class Job:
        def close(self): closed.append(True)
    monkeypatch.setattr(launch, 'WindowsJob', Job)
    class Child:
        def wait(self, **kw): return 0
    def spawn(command, directory, child_env, log, job):
        spawned.append((command, child_env))
        return Child()
    monkeypatch.setattr(launch, 'start_child', spawn)
    def wait(processes, stopped, stage):
        waits.append(stage)
        if stage == fail_stage:
            raise discovery.StartupError('Controlled application startup failure')
        if stage == 'final_readiness': stopped.set()
    monkeypatch.setattr(launch, 'wait_application', wait)
    launch.supervise()
    assert len(spawned) == (1 if fail_stage == 'backend_readiness' else 2)
    assert spawned[0][0][1:4] == ['-m', 'uvicorn', 'app.main:app']
    assert all(row[1]['AI_REMOTE_URL'] == URL for row in spawned)
    if fail_stage != 'backend_readiness':
        assert spawned[-1][0][-3:] == ['dev', '--port', '3000']
    assert closed == [True] and not launch.STATE.exists()


def test_native_windows_job_kills_only_owned_process_tree():
    if os.name != 'nt': pytest.skip('Windows Job Object test')
    job = launch.WindowsJob()
    unrelated = subprocess.Popen([sys.executable, '-c', 'import time;time.sleep(30)'], creationflags=subprocess.CREATE_NO_WINDOW)
    owned = subprocess.Popen([sys.executable, '-c',
        'import subprocess,sys,time;time.sleep(.3);p=subprocess.Popen([sys.executable,"-c","import time;time.sleep(30)"]);print(p.pid,flush=True);time.sleep(30)'],
        stdout=subprocess.PIPE, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
    try:
        job.add(owned)
        child_pid = int(owned.stdout.readline())
        kernel = launch.ctypes.WinDLL('kernel32', use_last_error=True)
        kernel.OpenProcess.argtypes = [launch.wintypes.DWORD, launch.wintypes.BOOL, launch.wintypes.DWORD]
        kernel.OpenProcess.restype = launch.wintypes.HANDLE
        kernel.WaitForSingleObject.argtypes = [launch.wintypes.HANDLE, launch.wintypes.DWORD]
        kernel.CloseHandle.argtypes = [launch.wintypes.HANDLE]
        child_handle = kernel.OpenProcess(0x100000, False, child_pid)
        assert child_handle
        job.close()
        owned.wait(timeout=5)
        assert kernel.WaitForSingleObject(child_handle, 5000) == 0
        kernel.CloseHandle(child_handle)
        assert unrelated.poll() is None
    finally:
        job.close()
        unrelated.terminate()
        unrelated.wait(timeout=5)


def test_original_bundle_extract_no_runtime_changes(tmp_path):
    root = Path(__file__).resolve().parents[2]
    source = root / 'artifacts' / discovery.BUNDLE_NAME
    if not source.is_file(): pytest.skip('Private bundle not present on this checkout')
    target = tmp_path / 'runtime'
    kaggle.extract(source, target)
    kaggle.extract(source, target)
    assert (target / 'scripts/unified_gate3_server.py').read_bytes() == (root / 'scripts/unified_gate3_server.py').read_bytes().replace(b'\r\n', b'\n')
    assert sha256(source.read_bytes()).hexdigest() == discovery.BUNDLE_SHA


def test_kaggle_reentry_publishes_without_second_bootstrap(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(kaggle, 'WORK', tmp_path / 'work')
    monkeypatch.setattr(kaggle, 'ROOT', tmp_path / 'work/runtime')
    monkeypatch.setattr(kaggle, 'OUT', tmp_path / 'work/session')
    (tmp_path / discovery.BUNDLE_NAME).write_bytes(b'fixture')
    secrets_client = type('Secrets', (), {'get_secret': lambda self, name: KEY})
    monkeypatch.setitem(sys.modules, 'kaggle_secrets', type('Module', (), {'UserSecretsClient': secrets_client}))
    published, loads = [], []
    monkeypatch.setattr(kaggle, 'publish', lambda record, key: published.append(record))
    monkeypatch.setattr(kaggle, 'confirm_publication', lambda record, key: (URL, published[-1]))
    monkeypatch.setattr(kaggle, 'extract', lambda *args: None)
    monkeypatch.setattr(kaggle, 'verify_worker', lambda *args: health())
    def bootstrap(key):
        loads.append(True)
        kaggle.OUT.mkdir(parents=True)
        (kaggle.OUT / 'endpoint.json').write_text(json.dumps({'url': URL}))
        return URL
    monkeypatch.setattr(kaggle, 'run_bootstrap', bootstrap)
    assert kaggle.main(tmp_path) is True
    assert kaggle.main(tmp_path) is True
    assert loads == [True]
    assert [row['status'] for row in published] == ['starting', 'ready', 'starting', 'ready']
    assert KEY not in json.dumps(published)
    assert 'CAPSTONE_AI_READY' in capsys.readouterr().out


def test_kaggle_failure_stage_and_invalidation(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(kaggle, 'WORK', tmp_path / 'work')
    client = type('Secrets', (), {'get_secret': lambda self, name: KEY})
    monkeypatch.setitem(sys.modules, 'kaggle_secrets', type('Module', (), {'UserSecretsClient': client}))
    published = []
    monkeypatch.setattr(kaggle, 'publish', lambda record, key: published.append(record))
    assert kaggle.main(tmp_path) is False
    assert [row['status'] for row in published] == ['starting', 'failed']
    assert all('endpoint' not in row for row in published)
    text = capsys.readouterr().out
    assert 'stage=package_verification' in text and KEY not in text


def test_thin_notebook_pins_only_public_support():
    from scripts.make_capstone_notebook import notebook
    result, hashes = notebook('a' * 40)
    assert len(result['cells']) == 2
    start = ''.join(result['cells'][0]['source'])
    assert start.startswith('# START CAPSTONE') and len(start.splitlines()) < 35
    assert 'sha256(raw).hexdigest() != expected' in start
    assert set(hashes) == {'capstone_kaggle.py', 'capstone_discovery.py'}
    assert 'get_secret' not in start and KEY not in json.dumps(result)
    assert 'importlib.reload(capstone_discovery)' in start
    assert 'importlib.reload(capstone_kaggle)' in start


def test_publication_failure_leaves_worker_for_explicit_override(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(kaggle, 'WORK', tmp_path / 'work')
    monkeypatch.setattr(kaggle, 'ROOT', tmp_path / 'work/runtime')
    monkeypatch.setattr(kaggle, 'OUT', tmp_path / 'work/session')
    (tmp_path / discovery.BUNDLE_NAME).write_bytes(b'fixture')
    client = type('Secrets', (), {'get_secret': lambda self, name: KEY})
    monkeypatch.setitem(sys.modules, 'kaggle_secrets', type('Module', (), {'UserSecretsClient': client}))
    monkeypatch.setattr(kaggle, 'publish', lambda *args: (_ for _ in ()).throw(discovery.StartupError('Service unavailable')))
    monkeypatch.setattr(kaggle, 'extract', lambda *args: None)
    monkeypatch.setattr(kaggle, 'verify_worker', lambda *args: health())
    def bootstrap(key):
        kaggle.OUT.mkdir(parents=True)
        (kaggle.OUT / 'endpoint.json').write_text(json.dumps({'url': URL}))
        return URL
    monkeypatch.setattr(kaggle, 'run_bootstrap', bootstrap)
    assert kaggle.main(tmp_path) is False
    assert (kaggle.OUT / 'endpoint.json').is_file()
    text = capsys.readouterr().out
    assert 'CAPSTONE_AI_READY' not in text and 'stage=endpoint_publication' in text and KEY not in text
