"""Exact Gate 1 environment, one persistent Gate 2 process, package partial evidence."""
import argparse
from importlib import metadata
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from zipfile import ZIP_DEFLATED, ZipFile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import unified_gate1 as gate
from scripts.unified_gate1_bootstrap import command
from scripts.unified_gate2 import verify_experiment


def isolated_diagnostics(output, features, model, env, shared):
    """Only on observed differences, after the persistent process has exited."""
    rows = []
    for feature in features:
        folders = []
        for index in (1, 2):
            folder = output / f'isolated_{feature}_{index}'
            folder.mkdir()
            # Original Gate 1 worker, no Gate 1 files/output paths overwritten.
            expression = ('import sys; from pathlib import Path; from scripts.unified_gate1 import worker; '
                          'sys.exit(worker(sys.argv[1], Path(sys.argv[2]), Path(sys.argv[3])))')
            command([sys.executable, '-c', expression, feature, model, str(folder)],
                    output, f'isolated_{feature}_{index}.log', env)
            folders.append(folder)
        comparison = gate.compare_images(folders[0] / 'candidate.png', folders[1] / 'candidate.png')
        rows.append({'feature': feature, 'design': 'two diagnostic fresh isolated processes, after shared process exit',
                     'isolated_repeat_comparison': comparison,
                     'each_vs_gate1': [json.loads((p / 'report.json').read_text())['comparison'] for p in folders],
                     'shared_vs_each_isolated': [gate.compare_images(p / 'candidate.png', output / 'results' / r['label'] / 'candidate.png')
                         for p in folders for r in shared['results'] if r['requested_feature'] == feature],
                     'attribution': 'Human review required; differences are not automatically attributed to switching.'})
    gate.save(output / 'isolated_diagnostics.json', rows)


def bootstrap(output):
    output = Path(output)
    if output.exists():
        raise ValueError('Use a fresh Gate 2 output directory')
    output.mkdir(parents=True)
    setup = {'schema': 'unified-gate2-setup-v1', 'status': 'FAILED', 'gate2_passed': False,
             'gate3_started': False, 'phase': 'artifact preflight', 'timing_seconds': {},
             'storage_before': gate.storage('/tmp')}
    started = time.monotonic()
    plan = baseline = None
    env = os.environ.copy()
    env.update(CUDA_VISIBLE_DEVICES='0', PYTHONUNBUFFERED='1', HF_HOME='/tmp/gate2-hf-cache')
    try:
        plan, baseline, review = verify_experiment()
        expected = review['environment']
        setup['bundle_manifest_sha256'] = gate.digest(ROOT / 'gate2_bundle.json')
        setup['phase'] = 'host Python/Torch/CUDA preflight'
        expression = "import json,platform,torch; print(json.dumps({'python':platform.python_version(),'torch':torch.__version__,'cuda':torch.version.cuda,'gpu':torch.cuda.get_device_name(0) if torch.cuda.is_available() else None}))"
        result = subprocess.run([sys.executable, '-c', expression], cwd=ROOT, env=env, capture_output=True, text=True)
        if result.returncode:
            raise RuntimeError('Host Torch import failed')
        host = json.loads(result.stdout.strip().splitlines()[-1])
        if any(host[k] != expected[k] for k in ('python', 'torch', 'cuda', 'gpu')):
            setup['observed_host'] = host
            raise ValueError('Host differs from Gate 1; stop before treating results as comparable')
        setup['host'] = host
        setup['phase'] = 'dependency setup'
        constraints = [f"torch=={expected['torch']}"]
        for name in ('torchvision', 'torchaudio'):
            try:
                constraints.append(f'{name}=={metadata.version(name)}')
            except metadata.PackageNotFoundError:
                pass
        constraint_path = output / 'torch_constraints.txt'
        constraint_path.write_text('\n'.join(constraints) + '\n')
        dependency_start = time.monotonic()
        try:
            version = metadata.version('torchao')
            if tuple(int(v) for v in version.split('.')[:2]) < (0, 16):
                command([sys.executable, '-m', 'pip', 'uninstall', '-y', 'torchao'], output, 'optional_torchao.log', env)
        except metadata.PackageNotFoundError:
            pass
        try:
            metadata.version('torchao')
        except metadata.PackageNotFoundError:
            pass
        else:
            raise ValueError('Optional torchao remains installed; Gate 1 environment had it removed')
        command([sys.executable, '-m', 'pip', 'install', '--constraint', str(constraint_path),
                 '-r', str(ROOT / 'scripts/unified_gate2_requirements.txt')], output, 'dependency_install.log', env)
        setup['timing_seconds']['dependency_setup'] = time.monotonic() - dependency_start
        setup['phase'] = 'exact environment check'
        command([sys.executable, str(ROOT / 'scripts/unified_gate2.py'), '--environment-only'], output, 'environment.log', env)
        setup['environment'] = json.loads((output / 'environment.log').read_text().strip().splitlines()[-1])
        command([sys.executable, str(ROOT / 'scripts/unified_gate2.py'), '--verify-only'], output, 'artifact_preflight.log', env)
        setup['phase'] = 'Base download'
        cache = Path('/tmp/gate2-hf-cache/hub')
        cache.parent.mkdir(parents=True, exist_ok=True)
        command([sys.executable, str(ROOT / 'scripts/unified_gate1_bootstrap.py'), '--download-only',
                 '--output', str(output / 'model.json'), '--cache', str(cache)], output, 'Base_download.log', env)
        model = json.loads((output / 'model.json').read_text())
        if model['model_index_sha256'] != review['base_model_index_sha256']:
            raise ValueError('Base index differs from Gate 1')
        setup['model'] = model
        setup['timing_seconds']['setup_before_persistent_process'] = time.monotonic() - started
        setup['phase'] = 'persistent pipeline switching'
        command([sys.executable, str(ROOT / 'scripts/unified_gate2.py'), '--model-dir', model['snapshot'],
                 '--output', str(output / 'results')], output, 'runner.log', env)
        summary = json.loads((output / 'results/summary.json').read_text())
        differing = summary['isolated_repeat_required_features']
        if differing:
            setup['phase'] = 'conditional isolated diagnostic repeats'
            isolated_diagnostics(output, differing, model['snapshot'], env, summary)
        setup.update(status='SWITCHING_COMPLETED_REVIEW_REQUIRED', phase='completed')
    except Exception as exc:
        setup.update(error={'type': type(exc).__name__, 'message': gate.sanitized(str(exc))})
    finally:
        setup['timing_seconds']['total_bootstrap_and_experiment'] = time.monotonic() - started
        setup['storage_after'] = gate.storage('/tmp')
        gate.save(output / 'setup.json', setup)
        with ZipFile(output / 'evidence.zip', 'x', ZIP_DEFLATED) as z:
            for path in sorted(output.rglob('*')):
                if path.is_file() and path.suffix != '.zip':
                    z.write(path, path.relative_to(output).as_posix())
            for feature, case in (plan or {}).get('features', {}).items():
                for field in ('input', 'reference', 'reference_record'):
                    z.write(ROOT / case[field], f'preserved/{feature}/{field}/{Path(case[field]).name}')
                if baseline:
                    z.write(ROOT / baseline['features'][feature]['output'], f'preserved/{feature}/gate1.png')
            z.write(ROOT / 'docs/experiments/unified-kaggle-gate1-review.json', 'gate1_review.json')
        print('GATE2 SETUP STATUS', setup['status'], flush=True)
        print('DOWNLOAD', output / 'evidence.zip', flush=True)
    return setup


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('/kaggle/working/unified_gate2'))
    result = bootstrap(parser.parse_args().output)
    sys.exit(0 if result['status'] == 'SWITCHING_COMPLETED_REVIEW_REQUIRED' else 1)
