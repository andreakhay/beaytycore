"""New Gate 2 bundle, reuse immutable Gate 1 assets, never overwrite either gate."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys
from zipfile import ZIP_DEFLATED, ZipFile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import unified_gate1 as gate
from scripts.unified_gate2 import SCHEMA

SOURCE_SHA = '8ed784714d534ff767dd261bd5d440d643b526cfac60f2d8dccd47e2c9d44293'
NEW_SOURCES = ('scripts/unified_gate2.py', 'scripts/unified_gate2_bootstrap.py',
               'scripts/unified_gate2_requirements.txt', 'docs/experiments/unified-kaggle-gate1-review.json')


def build(source, evidence, output):
    source, evidence, output = map(Path, (source, evidence, output))
    if output.exists():
        raise ValueError('Refusing to overwrite an existing bundle')
    if gate.digest(source) != SOURCE_SHA:
        raise ValueError('Not the reviewed Gate 1 bundle')
    review = json.loads((ROOT / NEW_SOURCES[-1]).read_text())
    if review['status'] != 'GATE_1_PASSED' or gate.digest(evidence) != review['evidence_sha256']:
        raise ValueError('Not the reviewed Gate 1 evidence')
    with ZipFile(source) as b, ZipFile(evidence) as e:
        if b.testzip() or e.testzip():
            raise ValueError('Source archive CRC failure')
        for archive in (b, e):
            if len(archive.namelist()) != len(set(archive.namelist())):
                raise ValueError('Duplicate archive member')
            for name in archive.namelist():
                gate.safe_path(ROOT, name)
        old = json.loads(b.read('gate1_bundle.json'))
        if set(b.namelist()) != set(old['files']) | {'gate1_bundle.json'}:
            raise ValueError('Unexpected source bundle member')
        for name, expected in old['files'].items():
            if sha256(b.read(name)).hexdigest() != expected:
                raise ValueError('Gate 1 inventory mismatch')
        files = {name: b.read(name) for name in b.namelist()}
        baseline = {'schema': SCHEMA, 'evidence_sha256': gate.digest(evidence), 'features': {}}
        for row in review['features']:
            feature = row['feature']
            raw = e.read(f'results/{feature}/candidate.png')
            if sha256(raw).hexdigest() != row['output_sha256']:
                raise ValueError('Reviewed candidate hash differs')
            name = f'gate2/gate1_outputs/{feature}.png'
            files[name] = raw
            baseline['features'][feature] = {'output': name, 'output_sha256': row['output_sha256']}
        for name in NEW_SOURCES:
            files[name] = (ROOT / name).read_bytes()
        files['gate2_baseline.json'] = (json.dumps(baseline, indent=2) + '\n').encode()
        manifest = {'schema': SCHEMA, 'base_revision': gate.REVISION, 'source_gate1_bundle_sha256': SOURCE_SHA,
                    'files': {name: sha256(raw).hexdigest() for name, raw in files.items()}}
        files['gate2_bundle.json'] = (json.dumps(manifest, indent=2) + '\n').encode()
        output.parent.mkdir(parents=True, exist_ok=True)
        with ZipFile(output, 'x', ZIP_DEFLATED) as z:
            for name, raw in sorted(files.items()):
                z.writestr(name, raw)
    return {'bundle': str(output.resolve()), 'bytes': output.stat().st_size,
            'sha256': gate.digest(output), 'members': len(files), 'gate2_passed': False}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=ROOT / 'artifacts/unified_gate1_20260928_v2.bin')
    parser.add_argument('--evidence', type=Path, default=ROOT / '.tmp/gate1-review-20260928/evidence.zip')
    parser.add_argument('--output', type=Path, default=ROOT / 'artifacts/unified_gate2_20260928_v1.bin')
    args = parser.parse_args()
    print(json.dumps(build(args.source, args.evidence, args.output), indent=2))
