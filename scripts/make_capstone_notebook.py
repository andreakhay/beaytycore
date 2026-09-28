"""One-time public support pinning; never rebuilds a model bundle."""

import argparse
from hashlib import sha256
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
SUPPORT = ('capstone_discovery.py', 'capstone_kaggle.py')


def notebook(commit, train002=False):
    if not re.fullmatch('[0-9a-f]{40}', commit):
        raise ValueError('Pin an exact public support commit')
    hashes = {name: sha256((ROOT / 'scripts' / name).read_bytes().replace(b'\r\n', b'\n')).hexdigest()
              for name in SUPPORT}
    entry = '''# START CAPSTONE
# One-time notebook settings: approved private dataset, T4, Internet, API Secret.
from pathlib import Path
from hashlib import sha256
from urllib.request import urlopen
import sys
import importlib
COMMIT = "COMMIT_VALUE"
HASHES = HASH_VALUE
SUPPORT = Path("/kaggle/working/capstone-entry")
SUPPORT.mkdir(exist_ok=True)
try:
    for name, expected in HASHES.items():
        url = f"https://raw.githubusercontent.com/mark-juswa/CometicsAI/{COMMIT}/scripts/{name}"
        with urlopen(url, timeout=30) as response:
            raw = response.read(65537)
        if len(raw) > 65536 or sha256(raw).hexdigest() != expected:
            raise RuntimeError("Pinned startup support hash mismatch")
        (SUPPORT / name).write_bytes(raw)
    sys.path.insert(0, str(SUPPORT))
    import capstone_discovery
    importlib.reload(capstone_discovery)
    import capstone_kaggle
    importlib.reload(capstone_kaggle)
    capstone_kaggle.main()
except Exception as error:
    print("CAPSTONE_STARTUP_FAILED stage=startup_support", type(error).__name__)
    print("Check Internet and imported notebook version. No GPU worker was started by this entry failure.")
'''.replace('COMMIT_VALUE', commit).replace('HASH_VALUE', repr(hashes))
    if train002:
        entry = entry.replace('capstone_kaggle.main()', 'capstone_kaggle.main(bundle_name=capstone_discovery.TRAIN002_BUNDLE_NAME, bundle_sha=capstone_discovery.TRAIN002_BUNDLE_SHA)')
    evidence = '# COLLECT REHEARSAL EVIDENCE, only after local application smoke finishes\ncapstone_kaggle.collect_evidence()\n'
    for source in (entry, evidence): compile(source, 'capstone-cell', 'exec')
    return {'cells': [{'cell_type': 'code', 'execution_count': None, 'metadata': {}, 'outputs': [],
                       'source': text.splitlines(keepends=True)} for text in (entry, evidence)],
            'metadata': {'kernelspec': {'display_name': 'Python 3', 'language': 'python', 'name': 'python3'},
                         'language_info': {'name': 'python'}}, 'nbformat': 4, 'nbformat_minor': 5}, hashes


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--commit', required=True)
    parser.add_argument('--train002', action='store_true', help='Prepare the separate expanded Hair candidate notebook')
    args = parser.parse_args()
    result, hashes = notebook(args.commit, train002=args.train002)
    stem = 'capstone_start_train002' if args.train002 else 'capstone_start'
    cell = 'START_CAPSTONE_TRAIN002_cell.py' if args.train002 else 'START_CAPSTONE_cell.py'
    pins = 'capstone-train002-sources.json' if args.train002 else 'capstone-startup-sources.json'
    (ROOT / 'notebooks' / (stem + '.ipynb')).write_text(json.dumps(result, indent=1) + '\n', encoding='utf-8')
    (ROOT / 'notebooks' / cell).write_text(''.join(result['cells'][0]['source']), encoding='utf-8')
    (ROOT / 'docs/experiments' / pins).write_text(json.dumps({
        'support_commit': args.commit, 'support_sha256': hashes,
        'private_bundle': 'capstone_train002_20260928_v1.bin' if args.train002 else 'deployment01_20260928_v2.bin'}, indent=2) + '\n', encoding='utf-8')
