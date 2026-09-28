"""Generate one self-contained code-only Kaggle update cell; contains no private assets."""

import base64
from hashlib import sha256
import json
from pathlib import Path
import zlib

from scripts.nails_latency_update import FILES, verify_payload

ROOT = Path(__file__).resolve().parents[1]


def build(root=ROOT):
    files = {name: (root / name).read_text(encoding='utf-8') for name in FILES}
    payload = {'files': files, 'hashes': {name: sha256(value.encode()).hexdigest() for name, value in files.items()}}
    verify_payload(payload)
    controller = (root / 'scripts/nails_latency_update.py').read_text(encoding='utf-8')
    data = json.dumps({'payload': payload, 'controller': controller}, sort_keys=True).encode()
    encoded = base64.b64encode(zlib.compress(data, 9)).decode()
    source = (
        '# Paste this entire file into ONE NEW code cell in your RUNNING Gate 3 Kaggle notebook.\n'
        '# Wait until no generation is running. Do not rerun the original setup cells.\n'
        'import base64, hashlib, json, zlib\n'
        f'_update_bytes = zlib.decompress(base64.b64decode({encoded!r}))\n'
        f'assert hashlib.sha256(_update_bytes).hexdigest() == {sha256(data).hexdigest()!r}, "Update hash differs"\n'
        '_update = json.loads(_update_bytes)\n'
        '_namespace = {"__name__": "nails_latency_update_cell"}\n'
        'exec(compile(_update["controller"], "nails_latency_update.py", "exec"), _namespace)\n'
        '_latency_report = _namespace["update"](_update["payload"])\n'
    )
    compile(source, 'nails_latency_update_cell.py', 'exec')
    return source, payload['hashes']


if __name__ == '__main__':
    cell, hashes = build()
    path = ROOT / 'notebooks/nails_latency_update_cell.py'
    path.write_text(cell, encoding='utf-8')
    print(json.dumps({'cell': str(path), 'bytes': path.stat().st_size, 'source_hashes': hashes}, indent=2))
