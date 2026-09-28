"""Add the approved Hair assets at the worker boundary, preserve Gate preflight."""

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import unified_gate3_bootstrap as original


def worker_environment(env, root=ROOT):
    config = json.loads((root / 'capstone_train002.json').read_text())
    registry = original.gate.safe_path(root, config['registry'])
    if original.gate.digest(registry) != config['registry_sha256']:
        raise ValueError('Expanded registry hash differs')
    if set(config['adapter_directories']) != {'train001', 'train002'}:
        raise ValueError('Expanded Hair adapter inventory differs')
    directories = {name: str(original.gate.safe_path(root, path))
                   for name, path in config['adapter_directories'].items()}
    return {**env, 'HAIRCAPSTONE_STYLE_REGISTRY_PATH': str(registry),
            'AI_HAIR_ADAPTER_DIRS': json.dumps(directories)}


def bootstrap(output):
    # The original Gate 1/2 checks intentionally import their historical registry.
    # Set the expanded registry only in the NEW worker subprocess environment.
    # Its existing adapter_configuration verifies both artifacts before Base load.
    start = original.start_server
    def start_with_hair(output, env):
        return start(output, worker_environment(env))
    original.start_server = start_with_hair
    try:
        return original.bootstrap(output)
    finally:
        original.start_server = start


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = bootstrap(args.output)
    sys.exit(0 if result['status'] == 'READY_FOR_LIVE_ACCEPTANCE' else 1)
