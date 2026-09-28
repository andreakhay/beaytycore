"""One-time private demo packaging from the immutable accepted Gate 3 bundle."""

import json
from hashlib import sha256
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

ROOT = Path(__file__).resolve().parents[1]
SOURCE_NAME = 'unified_gate3_20260928_v2.bin'
SOURCE_SHA = 'a3d73ce4ac0995a17bfa6a7c48253e2a2fa7db9ae635941295804d60dcb03683'
FILES = ('scripts/unified_gate3_server.py', 'scripts/unified_gate3_nails.py',
         'backend/app/nails/inference_options.py', 'backend/app/generation/diagnostics.py')


def build(source, output):
    source, output = Path(source), Path(output)
    if output.exists():
        raise ValueError('Refuse to overwrite a private demo bundle')
    if sha256(source.read_bytes()).hexdigest() != SOURCE_SHA:
        raise ValueError('Source differs from accepted Gate 3 bundle')
    with ZipFile(source) as archive:
        if archive.testzip() is not None:
            raise ValueError('Source CRC mismatch')
        manifest = json.loads(archive.read('gate3_bundle.json'))
        names = archive.namelist()
        if len(names) != len(set(names)) or set(names) != set(manifest['files']) | {'gate3_bundle.json'}:
            raise ValueError('Source inventory mismatch')
        files = {name: archive.read(name) for name in manifest['files']}
        if any(sha256(files[name]).hexdigest() != digest for name, digest in manifest['files'].items()):
            raise ValueError('Source member hash mismatch')
    # All weights, approved methods, references and dependency pins stay byte-identical.
    for name in FILES:
        raw = (ROOT / name).read_bytes()
        compile(raw, name, 'exec')
        files[name] = raw
    provenance = {'schema': 'deployment-01-sources-v1', 'source_bundle_sha256': SOURCE_SHA,
                  'gate3_acceptance_commit': '1d1b5e6d39a145b5b68d211114d65bd8f1ea1740',
                  'source_hashes': {name: sha256(files[name]).hexdigest() for name in FILES}}
    files['deployment01_sources.json'] = (json.dumps(provenance, indent=2) + '\n').encode()
    manifest['files'] = {name: sha256(raw).hexdigest() for name, raw in files.items()}
    files['gate3_bundle.json'] = (json.dumps(manifest, indent=2) + '\n').encode()
    output.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(output, 'x', ZIP_DEFLATED) as archive:
        for name, raw in sorted(files.items()):
            archive.writestr(name, raw)
    return {'name': output.name, 'bytes': output.stat().st_size,
            'sha256': sha256(output.read_bytes()).hexdigest(), **provenance}


def notebook(bundle):
    original = json.loads((ROOT / 'notebooks/unified_gate3_kaggle.ipynb').read_text())
    cells = [''.join(cell['source']) for cell in original['cells']]
    cells[0] = cells[0].replace(SOURCE_NAME, bundle['name']).replace(SOURCE_SHA, bundle['sha256'])
    cells[0] = cells[0].replace('/kaggle/working/gate3_bundle', '/kaggle/working/deployment01-src')
    cells[0] = cells[0].replace('/kaggle/working/unified_gate3', '/kaggle/working/deployment01')
    cells[0] += '\n# Check required Secret before dependency setup. Never print its value.\nfrom kaggle_secrets import UserSecretsClient\nassert len(UserSecretsClient().get_secret("AI_REMOTE_API_KEY") or "") >= 24, "Enable AI_REMOTE_API_KEY Secret"\nprint("Required API key attached. Run Cell 2 next.")\n'
    cells[1] = cells[1].replace('/kaggle/working/unified_gate3', '/kaggle/working/deployment01')
    cells[2] = cells[2].replace('if (OUT / "endpoint.json").is_file():',
        'health = report.get("public_health", {})\nassert report["status"] == "READY_FOR_LIVE_ACCEPTANCE", "Setup did not become ready"\nassert health.get("gpu_runtime_ready") and health.get("foundation_load_count") == 1, "Worker is not ready"\nassert health.get("diagnostics_version") == "deployment-01", "Wrong worker version"\nif (OUT / "endpoint.json").is_file():')
    cells[2] = cells[2].replace('This setup is ready for live acceptance, not a Gate 3 pass.', 'DEPLOYMENT_01_SERVICE_READY, fresh application rehearsal still required.')
    cells[3] = cells[3].replace('("startup.json", "model.json", "endpoint.json", "live_status.json", "http_probes.json", "environment.log", "artifact_preflight.log")',
                               '("startup.json", "model.json", "endpoint.json", "live_status.json", "http_probes.json", "environment.log", "artifact_preflight.log", "server.log", "deployment01_sources.json")')
    cells[3] = cells[3].replace('with ZipFile(OUT / "live-evidence.zip",',
        '(OUT / "deployment01_sources.json").write_bytes((ROOT / "deployment01_sources.json").read_bytes())\nwith ZipFile(OUT / "live-evidence.zip",')
    cells[3] += '\nprint("DEPLOYMENT_01_REHEARSAL_REVIEW_REQUIRED, no automatic deployment pass.")\n'
    for i, cell in enumerate(cells):
        compile(cell, f'deployment01-cell-{i+1}', 'exec')
    original['cells'] = [{'cell_type': 'code', 'execution_count': None, 'metadata': {}, 'outputs': [],
                          'source': source.splitlines(keepends=True)} for source in cells]
    return original


if __name__ == '__main__':
    report = build(ROOT / 'artifacts' / SOURCE_NAME, ROOT / 'artifacts/deployment01_20260928_v2.bin')
    (ROOT / 'notebooks/deployment01_kaggle.ipynb').write_text(json.dumps(notebook(report), indent=1) + '\n')
    (ROOT / 'docs/experiments/deployment01-bundle.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))
