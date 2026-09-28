"""Build a separate private Gate 3 handoff from the exact reviewed Gate 2 bundle."""

import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys
from zipfile import ZIP_DEFLATED, ZipFile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import unified_gate1 as gate
GATE2_SHA = '0e5ffd854f394f86e5c1ca49d47b9b230b0088aae2da828d893601330d190feb'
NEW_FILES = ('scripts/unified_gate3_server.py', 'scripts/unified_gate3_bootstrap.py',
             'scripts/unified_gate3_requirements.txt',
             'docs/experiments/unified-kaggle-gate2-review.json')


def build(source, output):
    source, output = Path(source), Path(output)
    if output.exists():
        raise ValueError('Refusing to overwrite a private bundle')
    if gate.digest(source) != GATE2_SHA:
        raise ValueError('Gate 2 source bundle differs from reviewed artifact')
    review = json.loads((ROOT / NEW_FILES[-1]).read_text())
    if review['status'] != 'GATE_2_PASSED':
        raise ValueError('Gate 2 evidence is not accepted')
    with ZipFile(source) as archive:
        if archive.testzip() is not None:
            raise ValueError('Gate 2 source CRC failed')
        old = json.loads(archive.read('gate2_bundle.json'))
        if set(archive.namelist()) != set(old['files']) | {'gate2_bundle.json'}:
            raise ValueError('Gate 2 member inventory differs')
        files = {}
        for name in archive.namelist():
            gate.safe_path(ROOT, name)
            raw = archive.read(name)
            if name in old['files'] and sha256(raw).hexdigest() != old['files'][name]:
                raise ValueError(f'Gate 2 member SHA differs: {name}')
            files[name] = raw
    for name in NEW_FILES:
        files[name] = (ROOT / name).read_bytes()
    files['gate3_source_commit.txt'] = b'ec4f377643707d5413d9d82af14ee305fb9371ef\n'
    manifest = {'schema': 'unified-kaggle-gate3-v1', 'base_revision': gate.REVISION,
                'source_gate2_bundle_sha256': GATE2_SHA,
                'files': {name: sha256(raw).hexdigest() for name, raw in files.items()}}
    files['gate3_bundle.json'] = (json.dumps(manifest, indent=2) + '\n').encode()
    output.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(output, 'x', ZIP_DEFLATED) as archive:
        for name, raw in sorted(files.items()):
            archive.writestr(name, raw)
    return {'path': str(output.resolve()), 'bytes': output.stat().st_size,
            'sha256': gate.digest(output), 'members': len(files)}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=ROOT / 'artifacts/unified_gate2_20260928_v5.bin')
    parser.add_argument('--output', type=Path, default=ROOT / 'artifacts/unified_gate3_20260928_v2.bin')
    args = parser.parse_args()
    print(json.dumps(build(args.source, args.output), indent=2))
