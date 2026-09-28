"""Expanded assets and startup boundaries, no GPU inference."""

from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
import sys
from zipfile import ZipFile

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from scripts import capstone_discovery as discovery
from scripts import capstone_launch as launch
from scripts import capstone_kaggle as kaggle
from scripts import capstone_train002_bootstrap as wrapper
from scripts.make_capstone_notebook import notebook

KEY = 'train002-test-key-not-a-real-secret'
URL = 'https://' + 'expanded-fixture' + '.trycloudflare.com'


def test_signed_expanded_record_selects_catalog_without_secret():
    record = discovery.make_record(KEY, 'ready', URL, bundle_sha=discovery.TRAIN002_BUNDLE_SHA)
    assert discovery.validate_record(record, KEY) == URL
    assert discovery.BUNDLE_REGISTRIES[record['bundle_sha256']] == 'style_registry_train002_smoke.json'
    assert KEY not in json.dumps(record)
    with pytest.raises(discovery.StartupError):
        discovery.make_record(KEY, 'ready', URL, bundle_sha='unapproved')


def test_expanded_process_environment_preserves_file(monkeypatch, tmp_path):
    (tmp_path / 'backend').mkdir()
    config = tmp_path / 'backend/.env'
    config.write_text('AI_REMOTE_API_KEY=' + KEY)
    monkeypatch.setattr(launch, 'ROOT', tmp_path)
    before = config.read_bytes()
    env = launch.process_env(URL, discovery.TRAIN002_BUNDLE_SHA)
    assert env['HAIRCAPSTONE_STYLE_REGISTRY_PATH'] == str(tmp_path / 'backend/app/style_registry_train002_smoke.json')
    assert config.read_bytes() == before


def test_expanded_entry_is_separate_and_selects_exact_bundle():
    base, _ = notebook('a' * 40)
    candidate, _ = notebook('a' * 40, train002=True)
    assert 'TRAIN002_BUNDLE_SHA' not in ''.join(base['cells'][0]['source'])
    assert 'TRAIN002_BUNDLE_SHA' in ''.join(candidate['cells'][0]['source'])
    assert len(candidate['cells'][0]['source']) < 35


@pytest.fixture
def extracted(tmp_path):
    candidate = ROOT / 'artifacts' / discovery.TRAIN002_BUNDLE_NAME
    if not candidate.exists(): pytest.skip('Private expanded candidate not present')
    target = tmp_path / 'candidate'
    kaggle.extract(candidate, target, discovery.TRAIN002_BUNDLE_SHA)
    return target


def test_original_package_members_are_unchanged(extracted):
    with ZipFile(ROOT / 'artifacts' / discovery.BUNDLE_NAME) as old:
        for name in old.namelist():
            if name != 'gate3_bundle.json':
                assert (extracted / name).read_bytes() == old.read(name)
    assert sha256((extracted / 'gate1/adapters/hairstyle_train002/adapter.safetensors').read_bytes()).hexdigest() == '59d527217a68139bc2aaa4eedbfcd2d5789ef115f8ecb924410eea24a952939b'


def test_worker_environment_only_expands_worker_catalog(extracted):
    original = {'HF_HOME': 'original-cache', 'AI_MODEL_DIR': 'one-base'}
    expanded = wrapper.worker_environment(original, extracted)
    assert original == {'HF_HOME': 'original-cache', 'AI_MODEL_DIR': 'one-base'}
    assert expanded['AI_MODEL_DIR'] == original['AI_MODEL_DIR']
    assert set(json.loads(expanded['AI_HAIR_ADAPTER_DIRS'])) == {'train001', 'train002'}
    registry = json.loads(Path(expanded['HAIRCAPSTONE_STYLE_REGISTRY_PATH']).read_text())
    assert len(registry['styles']) == 13


def test_actual_extracted_preflight_and_adapter_contracts(extracted):
    env = {**os.environ, 'PYTHONPATH': str(extracted) + os.pathsep + str(extracted / 'backend')}
    code = 'from scripts.unified_gate3_bootstrap import verify_bundle; verify_bundle(); print("original preflight verified")'
    result = subprocess.run([sys.executable, '-c', code], cwd=extracted, env=env, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    env = wrapper.worker_environment(env, extracted)
    code = '''from pathlib import Path
from scripts.unified_gate3_server import adapter_configuration, selected_adapter, HAIR_STYLES
adapters=adapter_configuration()
assert set(adapters)=={'train001','train002'}
assert selected_adapter('hairstyle','bun')=='hairstyle:train002'
assert selected_adapter('hairstyle','crew_cut')=='hairstyle:train001'
assert len(HAIR_STYLES)==13
print('both real adapter hashes and thirteen style routes verified')
'''
    result = subprocess.run([sys.executable, '-c', code], cwd=extracted, env=env, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


def test_wrapper_preserves_original_bootstrap_and_restores_hook(monkeypatch):
    calls = []
    def start(output, env): calls.append(env)
    monkeypatch.setattr(wrapper.original, 'start_server', start)
    monkeypatch.setattr(wrapper, 'worker_environment', lambda env: {**env, 'expanded': True})
    def bootstrap(output):
        wrapper.original.start_server(output, {'base_loads': 1})
        return {'status': 'READY_FOR_LIVE_ACCEPTANCE'}
    monkeypatch.setattr(wrapper.original, 'bootstrap', bootstrap)
    assert wrapper.bootstrap('output')['status'] == 'READY_FOR_LIVE_ACCEPTANCE'
    assert calls == [{'base_loads': 1, 'expanded': True}]
    assert wrapper.original.start_server is start
