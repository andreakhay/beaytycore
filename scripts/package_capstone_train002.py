"""One new private candidate, adding approved TRAIN-002 without changing originals."""

from hashlib import sha256
import json
from pathlib import Path
import struct
from zipfile import ZipFile, ZIP_DEFLATED

ROOT = Path(__file__).resolve().parents[1]
SOURCE_SHA = '68f6c9eb2bc0ce12b2c9c6d89e33f22898fb201b33a792887f6c5967ad16ec4e'
ADAPTER_SHA = '59d527217a68139bc2aaa4eedbfcd2d5789ef115f8ecb924410eea24a952939b'
NAME = 'capstone_train002_20260928_v1.bin'


def build(source, adapter, output):
    source, adapter, output = Path(source), Path(adapter), Path(output)
    if output.exists():
        raise ValueError('Refusing to overwrite a private candidate')
    if sha256(source.read_bytes()).hexdigest() != SOURCE_SHA:
        raise ValueError('Original Deployment-01 package differs')
    with ZipFile(source) as archive:
        manifest = json.loads(archive.read('gate3_bundle.json'))
        if archive.testzip() or set(archive.namelist()) != set(manifest['files']) | {'gate3_bundle.json'}:
            raise ValueError('Source package inventory or CRC differs')
        files = {name: archive.read(name) for name in manifest['files']}
        if any(sha256(files[name]).hexdigest() != digest for name, digest in manifest['files'].items()):
            raise ValueError('Original package member differs')
    registry_raw = (ROOT / 'backend/app/style_registry_train002_smoke.json').read_bytes().replace(b'\r\n', b'\n')
    registry = json.loads(registry_raw)
    metadata_raw = (adapter / 'metadata.json').read_bytes()
    metadata = json.loads(metadata_raw)
    weights = (adapter / 'adapter.safetensors').read_bytes()
    original_registry = json.loads(files['backend/app/style_registry.json'])
    if (registry['base_model_revision'] != original_registry['base_model_revision']
            or registry['adapters']['train001'] != original_registry['adapters']['train001']
            or [v for v in registry['styles'] if v['adapter_id'] == 'train001'] != original_registry['styles']):
        raise ValueError('Original Hair definitions changed')
    definition = registry['adapters']['train002']
    declared = {v['style_id'] for v in registry['styles'] if v['adapter_id'] == 'train002'}
    if (sha256(weights).hexdigest() != ADAPTER_SHA or definition['checkpoint_sha256'] != ADAPTER_SHA
            or metadata['checkpoint_sha256'] != ADAPTER_SHA or metadata['checkpoint_bytes'] != len(weights)
            or metadata['adapter_id'] != 'train002' or metadata['training_steps'] != definition['training_steps']
            or metadata['experiment'] != definition['experiment']
            or metadata['dataset_version'] != definition['dataset_version']
            or metadata['base_model_revision'] != registry['base_model_revision']
            or metadata['base_model_id'] != registry['base_model_id']
            or set(metadata['supported_style_ids']) != declared):
        raise ValueError('TRAIN-002 artifact or style provenance differs')
    size = struct.unpack('<Q', weights[:8])[0]
    if not 0 < size < 8 * 1024 * 1024:
        raise ValueError('Invalid safetensors header')
    header = json.loads(weights[8:8 + size])
    if not any('lora' in key.lower() for key in header):
        raise ValueError('No LoRA tensors')
    additions = {
        'gate1/adapters/hairstyle_train002/adapter.safetensors': weights,
        'gate1/adapters/hairstyle_train002/metadata.json': metadata_raw,
        'backend/app/style_registry_train002_smoke.json': registry_raw,
        'scripts/capstone_train002_bootstrap.py': (ROOT / 'scripts/capstone_train002_bootstrap.py').read_bytes().replace(b'\r\n', b'\n')}
    config = {'schema': 'capstone-train002-v1', 'source_bundle_sha256': SOURCE_SHA,
              'adapter_sha256': ADAPTER_SHA, 'registry': 'backend/app/style_registry_train002_smoke.json',
              'registry_sha256': sha256(registry_raw).hexdigest(),
              'adapter_directories': {'train001': 'gate1/adapters/hairstyle',
                                      'train002': 'gate1/adapters/hairstyle_train002'}}
    additions['capstone_train002.json'] = (json.dumps(config, indent=2) + '\n').encode()
    if set(additions) & set(files):
        raise ValueError('Refusing to replace original package members')
    files.update(additions)
    manifest['files'] = {name: sha256(raw).hexdigest() for name, raw in files.items()}
    files['gate3_bundle.json'] = (json.dumps(manifest, indent=2) + '\n').encode()
    output.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(output, 'x', ZIP_DEFLATED) as archive:
        for name, raw in sorted(files.items()): archive.writestr(name, raw)
    return {'name': output.name, 'bytes': output.stat().st_size,
            'sha256': sha256(output.read_bytes()).hexdigest(), **config,
            'hairstyle_styles': [v['style_id'] for v in registry['styles']],
            'status': 'LOCAL_PREPARED_GPU_NOT_TESTED'}


if __name__ == '__main__':
    report = build(ROOT / 'artifacts/deployment01_20260928_v2.bin',
                   ROOT / 'artifacts/train002_adapter_bundle', ROOT / 'artifacts' / NAME)
    (ROOT / 'docs/experiments/capstone-train002-bundle.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))
