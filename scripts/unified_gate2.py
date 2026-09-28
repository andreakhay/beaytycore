"""Isolated Gate 2, one foundation, ordinary adapter unload/load, no server."""

import argparse
import asyncio
from hashlib import sha256
import json
from pathlib import Path
import sys
import threading
import time
import traceback

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'backend'))
from scripts import unified_gate1 as gate

SCHEMA = 'unified-kaggle-gate2-v1'
PRIMARY = ('hairstyle', 'makeup', 'nails', 'hairstyle', 'makeup')
EXTRA_CYCLE = ('nails', 'hairstyle', 'makeup')
COMPONENTS = ('transformer', 'text_encoder', 'vae', 'scheduler', 'tokenizer')


def verify_environment(actual, expected):
    # These are the observed Gate 1 values, not ranges or current latest versions.
    for name in ('python', 'packages', 'diffusers_commit', 'torch', 'cuda', 'gpu'):
        if actual.get(name) != expected.get(name):
            raise ValueError(f'Gate 1 environment cannot be reproduced: {name}')
    if not actual.get('cuda_available'):
        raise RuntimeError('Select a Kaggle T4 GPU')
    return actual


def verify_experiment(root=None):
    root = Path(root or ROOT)
    manifest = json.loads((root / 'gate2_bundle.json').read_text())
    if manifest.get('schema') != SCHEMA or manifest.get('base_revision') != gate.REVISION:
        raise ValueError('Wrong Gate 2 manifest')
    if not manifest.get('files'):
        raise ValueError('Empty Gate 2 manifest')
    for name, expected in manifest['files'].items():
        if gate.digest(gate.safe_path(root, name)) != expected:
            raise ValueError(f'Gate 2 inventory mismatch: {name}')
    plan = gate.verify_bundle(root)
    baseline = json.loads((root / 'gate2_baseline.json').read_text())
    if baseline.get('schema') != SCHEMA or set(baseline['features']) != set(gate.FEATURES):
        raise ValueError('Wrong Gate 2 baseline')
    review = json.loads((root / 'docs/experiments/unified-kaggle-gate1-review.json').read_text())
    if review['status'] != 'GATE_1_PASSED' or baseline['evidence_sha256'] != review['evidence_sha256']:
        raise ValueError('Unreviewed Gate 1 evidence')
    for feature, case in plan['features'].items():
        _, verifier, expected = gate.feature_contract(feature)
        gate.verify_case(case, expected)
        verifier()
        row = baseline['features'][feature]
        if (gate.digest(gate.safe_path(root, row['output'])) != case['reference_sha256']
                or row['output_sha256'] != case['reference_sha256']):
            raise ValueError('Gate 1 output does not match reviewed fixed reference')
    return plan, baseline, review


def fingerprint(pipe):
    return {'pipeline': id(pipe), **{name: id(getattr(pipe, name)) for name in COMPONENTS}}


def adapter_path(feature):
    name = 'nails001_local_v1.safetensors' if feature == 'nails' else 'adapter.safetensors'
    return ROOT / 'gate1/adapters' / feature / name


def inspect_adapter(pipe, path, expected_name=None):
    """Verify real PEFT state and exact converted LoRA tensors, not just a label."""
    import torch
    inventory = pipe.get_list_adapters()
    names = inventory.get('transformer', [])
    if (set(inventory) - {'transformer'} or len(names) != 1
            or pipe.get_active_adapters() != names or (expected_name and names != [expected_name])):
        raise RuntimeError('Loaded adapter inventory or active adapter is uncertain')
    name = names[0]
    layers = 0
    for module in pipe.transformer.modules():
        if hasattr(module, 'lora_A'):
            layers += 1
            if (set(module.lora_A) != {name} or set(module.lora_B) != {name}
                    or list(module.active_adapters) != [name]
                    or module.disable_adapters or module.merged):
                raise RuntimeError('A LoRA layer is disabled, merged or has uncertain active state')
    if not layers:
        raise RuntimeError('No active LoRA layers found')
    state = pipe.lora_state_dict(str(path.parent), weight_name=path.name, local_files_only=True)
    actual = {}
    for key, tensor in pipe.transformer.named_parameters():
        if '.lora_A.' in key or '.lora_B.' in key:
            suffix = f'.{name}.weight'
            if not key.endswith(suffix):
                raise RuntimeError('Unexpected additional adapter tensor')
            actual['transformer.' + key[:-len(suffix)] + '.weight'] = tensor
    if not state or set(actual) != set(state):
        raise RuntimeError('Active LoRA tensor inventory differs from verified artifact')
    digest = sha256()
    for key in sorted(state):
        value = actual[key].detach().cpu()
        expected = state[key].to(dtype=value.dtype, device='cpu')
        if not torch.equal(value, expected):
            raise RuntimeError('Active LoRA tensor differs from verified artifact')
        digest.update(key.encode())
        digest.update(value.contiguous().numpy().tobytes())
    return {'library_adapter_name': name, 'tensor_count': len(state), 'verified_layer_count': layers,
            'converted_tensor_sha256': digest.hexdigest(), 'tensor_equality_verified': True}


class SwitchFailure(RuntimeError):
    pass


class SharedExperiment:
    """Only experiment ownership/state, original methods still perform generation."""
    def __init__(self, pipe, specs, infer, synchronize, inspect, measure=lambda: {}, events=None):
        self.pipe, self.specs, self.infer = pipe, specs, infer
        self.synchronize, self.inspect, self.measure = synchronize, inspect, measure
        self.owner = asyncio.Lock()
        self.ready, self.active, self.active_state = True, None, None
        self.foundation = fingerprint(pipe)
        self.events = events if events is not None else []
        self.sequence = 0
        self.completed = {}
        self.phase = lambda value: None

    def event(self, kind, **values):
        if kind == 'ownership_start':
            self.phase(values['label'])
        self.events.append({'event': kind, 'time': time.monotonic(), **values})

    def assert_foundation(self):
        if fingerprint(self.pipe) != self.foundation:
            self.ready, self.active = False, None
            raise RuntimeError('Foundation object changed')

    def verify_artifact(self, feature, override=None):
        spec = self.specs[feature]
        path = Path(override or spec['path'])
        if gate.digest(path) != spec['expected']['adapter_sha256']:
            raise ValueError('Adapter SHA differs from approved artifact')
        if override is None:
            spec['verify']()
        return path

    def assert_active(self, feature):
        try:
            self.assert_foundation()
            if not self.ready or self.active != feature or self.active_state is None:
                raise RuntimeError('Requested feature has no verified active adapter')
            path = self.verify_artifact(feature)
            state = self.inspect(self.pipe, path, self.active_state['library_adapter_name'])
            if state != self.active_state:
                raise RuntimeError('Active adapter verification changed')
            return state
        except Exception:
            self.ready, self.active, self.active_state = False, None, None
            raise

    def clear(self):
        self.ready, self.active, self.active_state = False, None, None
        self.synchronize()
        self.pipe.unload_lora_weights()
        if any(self.pipe.get_list_adapters().values()) or self.pipe.get_active_adapters():
            raise RuntimeError('Adapter unload did not clear PEFT state')
        if any('.lora_A.' in key or '.lora_B.' in key for key, _ in self.pipe.transformer.named_parameters()):
            raise RuntimeError('Adapter unload left residual LoRA tensors')
        self.assert_foundation()
        self.event('adapter_cleared')

    def load_verified(self, feature):
        path = self.verify_artifact(feature)
        # Same ordinary loading mechanism as all original runtime load methods.
        self.pipe.load_lora_weights(str(path.parent), weight_name=path.name)
        state = self.inspect(self.pipe, path, None)
        self.assert_foundation()
        self.ready, self.active, self.active_state = True, feature, state
        self.event('adapter_verified', feature=feature, **state)

    def switch(self, feature, inject=None):
        previous = self.active if self.ready else None
        started = time.monotonic()
        self.event('switch_start', requested=feature, previous=previous, injection=inject)
        try:
            self.assert_foundation()
            if not self.ready:
                raise RuntimeError('Experiment runtime is explicitly unready')
            if inject in ('missing', 'invalid'):
                self.verify_artifact(feature, self.specs[feature][inject])
            else:
                self.verify_artifact(feature)
            if self.active != feature or inject:
                self.clear()
                if inject == 'after_unload':
                    raise SwitchFailure('Controlled switch exception after unload')
                if inject == 'oom':
                    # Simulated only. No allocation and no real CUDA OOM induced.
                    raise SwitchFailure('Injected OOM recovery path, not an actual CUDA failure')
                self.load_verified(feature)
                if inject == 'after_load':
                    raise SwitchFailure('Controlled switch exception after adapter load')
            self.assert_active(feature)
        except Exception as exc:
            self.ready, self.active, self.active_state = False, None, None
            restored = False
            if previous is not None:
                try:
                    self.clear()
                    self.load_verified(previous)
                    self.assert_active(previous)
                    restored = True
                except Exception as recovery:
                    self.ready, self.active, self.active_state = False, None, None
                    self.event('restoration_failed', error=gate.sanitized(str(recovery)))
            self.event('switch_failed', requested=feature, restored=restored,
                       active=self.active, ready=self.ready, error=gate.sanitized(str(exc)))
            raise SwitchFailure(f'Switch failed, restored={restored}, ready={self.ready}: {gate.sanitized(str(exc))}') from exc
        finally:
            self.event('switch_end', requested=feature, active=self.active,
                       seconds=time.monotonic() - started, memory=self.measure())

    def operate(self, feature, label, inject=None, started=None, release=None):
        self.sequence += 1
        self.event('ownership_start', label=label, sequence=self.sequence)
        try:
            self.switch(feature, inject)
            state = self.assert_active(feature)
            begin = time.monotonic()
            self.event('inference_start', feature=feature, label=label, memory=self.measure())
            if started is not None:
                started.set()
            try:
                payload = self.infer(feature)
                if release is not None and not release.wait(timeout=30):
                    raise RuntimeError('Controlled completion latch timed out')
                self.synchronize()
                raw = gate.validate_result(payload, self.specs[feature]['expected'])
                self.assert_active(feature)
            except Exception:
                self.ready, self.active, self.active_state = False, None, None
                try:
                    self.synchronize()
                except Exception as drain:
                    self.event('gpu_drain_failed', error=gate.sanitized(str(drain)), ready=False)
                raise
            self.event('inference_end', feature=feature, label=label, seconds=time.monotonic() - begin)
            spec = self.specs[feature]['expected']
            result = {'payload': payload, 'raw': raw, 'ownership_sequence': self.sequence, 'label': label,
                    'requested_feature': feature, 'requested_style': spec['style_id'],
                    'active_feature': self.active, 'active_adapter_id': spec['adapter_id'],
                    'adapter_sha256': spec['adapter_sha256'], 'Base_revision': gate.REVISION,
                    'adapter_state': state, 'foundation_objects': self.foundation,
                    'memory_after': self.measure()}
            self.completed[label] = result
            return result
        finally:
            self.event('ownership_end', label=label)

    async def generate(self, feature, label, **kwargs):
        if feature not in self.specs:
            raise ValueError('Unknown experiment feature')
        async with self.owner:
            task = asyncio.create_task(asyncio.to_thread(self.operate, feature, label, **kwargs))
            cancelled = False
            while True:
                try:
                    result = await asyncio.shield(task)
                    break
                except asyncio.CancelledError:
                    # Repeated disconnect/cancel cannot release ownership early.
                    cancelled = True
                    if task.cancelled():
                        self.ready, self.active, self.active_state = False, None, None
                        raise
                except Exception:
                    if cancelled:
                        raise asyncio.CancelledError() from None
                    raise
            if cancelled:
                raise asyncio.CancelledError()
            return result


def runtime_views(pipe, torch, plan):
    views, specs = {}, {}
    for feature in gate.FEATURES:
        cls, verify, expected = gate.feature_contract(feature)
        view = cls()
        view.pipe, view.torch, view.ready = pipe, torch, True
        if feature == 'hairstyle':
            meta = verify()
            view.adapters = {'train001': (adapter_path(feature).parent, meta)}
            view.metadata, view.active_adapter = meta, 'train001'
        specs[feature] = {'path': adapter_path(feature), 'verify': verify, 'expected': expected}
        views[feature] = view
    def infer(feature):
        from PIL import Image
        with Image.open(ROOT / plan['features'][feature]['input']) as image:
            source = image.convert('RGB')
        # Optional measurement only; original Nails method does not reset peaks.
        if feature == 'nails':
            torch.cuda.reset_peak_memory_stats(0)
        payload = views[feature].generate(source, specs[feature]['expected']['style_id'])
        if getattr(torch.cuda.max_memory_allocated, 'unavailable', False):
            if 'peak_gpu_mib' in payload.get('metadata', {}):
                payload['metadata']['peak_gpu_mib'] = None
        return payload
    return specs, infer


async def wait_started(event):
    deadline = time.monotonic() + 30
    while not event.is_set():
        if time.monotonic() >= deadline:
            raise RuntimeError('Experimental request did not reach controlled latch')
        await asyncio.sleep(0.01)


async def recovery_probes(runtime, record):
    rows = []
    for injection in ('missing', 'invalid', 'after_unload', 'after_load', 'oom'):
        previous = runtime.active
        count = sum(e['event'] == 'inference_start' for e in runtime.events)
        target = 'nails' if previous != 'nails' else 'makeup'
        try:
            await runtime.generate(target, f'failure_{injection}', inject=injection)
        except SwitchFailure as exc:
            blocked = count == sum(e['event'] == 'inference_start' for e in runtime.events)
            row = {'probe': injection, 'inference_blocked': blocked, 'previous': previous,
                   'restored_feature': runtime.active, 'ready': runtime.ready, 'error': gate.sanitized(str(exc))}
            rows.append(row)
            if not blocked or not runtime.ready or runtime.active != previous:
                raise RuntimeError('Controlled failure did not restore verified adapter')
            record(await runtime.generate(previous, f'recovery_{injection}'), f'recovery_{injection}')
        else:
            raise RuntimeError('Controlled adapter failure unexpectedly succeeded')
    return rows


async def competing_requests(runtime, record, cancel=False):
    entered, release = threading.Event(), threading.Event()
    label = 'cancellation' if cancel else 'concurrency'
    first = asyncio.create_task(runtime.generate('hairstyle', label + '_first', started=entered, release=release))
    second = None
    try:
        await wait_started(entered)
        boundary = len(runtime.events)
        second = asyncio.create_task(runtime.generate('makeup', label + '_second'))
        if cancel:
            first.cancel()
        await asyncio.sleep(0.1)
        if cancel:
            first.cancel()  # Exercise repeated cancellation while the GPU owner waits.
        await asyncio.sleep(0.1)
        serialized = runtime.owner.locked() and len(runtime.events) == boundary and runtime.active == 'hairstyle'
        if not serialized:
            raise RuntimeError('Competing request changed active adapter while owner was working')
    finally:
        release.set()
        # Drain both tasks even when a probe assertion fails.
        outcomes = await asyncio.gather(first, *([second] if second else []), return_exceptions=True)
    if cancel:
        if not isinstance(outcomes[0], asyncio.CancelledError):
            raise RuntimeError('Cancelled caller did not receive cancellation')
        record(runtime.completed[label + '_first'], label + '_first')
    else:
        if isinstance(outcomes[0], BaseException):
            raise outcomes[0]
        record(outcomes[0], label + '_first')
    if second is None or isinstance(outcomes[1], BaseException):
        raise RuntimeError('Waiting feature request failed')
    record(outcomes[1], label + '_second')
    return {'probe': label, 'serialized': serialized, 'cancelled_caller': cancel,
            'boundary': 'Actual original inference runs inside shielded ownership; completion latch also covers fast fakes.'}


def worker(model, output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    report = {'schema': SCHEMA, 'status': 'FAILED', 'gate2_passed': False, 'gate3_started': False,
              'phase': 'artifact preflight', 'results': [], 'recovery': [], 'timing_seconds': {},
              'events': [], 'telemetry_warnings': [], 'foundation_load_count': 0}
    sampler = runtime = None
    started = time.monotonic()
    def checkpoint():
        gate.save(output / 'summary.json', report)
    try:
        plan, baseline, review = verify_experiment()
        report['phase'] = 'exact environment'
        checkpoint()
        report['environment'] = verify_environment(gate.environment(), review['environment'])
        import torch
        from diffusers import Flux2KleinPipeline
        model = Path(model)
        if model.name != gate.REVISION or gate.digest(model / 'model_index.json') != review['base_model_index_sha256']:
            raise ValueError('Base snapshot differs from reviewed Gate 1')
        sampler = gate.Sampler(torch)
        with sampler, gate.optional_runtime_telemetry(torch, report['telemetry_warnings']):
            report['before_Base_load'] = gate.memory(torch)
            report['phase'] = 'Base loading'
            checkpoint()
            load_start = time.monotonic()
            pipe = Flux2KleinPipeline.from_pretrained(str(model), torch_dtype=torch.float16, local_files_only=True)
            report['foundation_load_count'] += 1
            pipe.enable_model_cpu_offload(gpu_id=0)
            report['timing_seconds']['Base_load'] = time.monotonic() - load_start
            report['after_Base_load'] = gate.memory(torch)
            specs, infer = runtime_views(pipe, torch, plan)
            for feature, spec in specs.items():
                spec['missing'] = output / 'does_not_exist' / feature
                invalid = output / f'invalid_probe_{feature}.txt'
                invalid.write_text('Controlled invalid artifact, not a model weight.\n')
                spec['invalid'] = invalid
            runtime = SharedExperiment(pipe, specs, infer, lambda: torch.cuda.synchronize(0), inspect_adapter,
                                       lambda: gate.memory(torch), report['events'])
            runtime.phase = lambda value: setattr(sampler, 'phase', value)
            first_outputs = {}
            def record(result, label):
                feature = result['requested_feature']
                folder = output / label
                folder.mkdir()
                (folder / 'candidate.png').write_bytes(result.pop('raw'))
                gate.save(folder / 'response.json', result.pop('payload'))
                result['label'] = label
                result['output_sha256'] = gate.digest(folder / 'candidate.png')
                result['settings'] = plan['features'][feature]['settings']
                result['versus_gate1'] = gate.compare_images(ROOT / baseline['features'][feature]['output'], folder / 'candidate.png')
                result['versus_first_shared'] = (gate.compare_images(first_outputs[feature], folder / 'candidate.png')
                                                if feature in first_outputs else None)
                first_outputs.setdefault(feature, folder / 'candidate.png')
                gate.comparison_sheet(ROOT / plan['features'][feature]['input'], ROOT / baseline['features'][feature]['output'],
                                      folder / 'candidate.png', folder / 'comparison.png')
                gate.save(folder / 'report.json', result)
                report['results'].append(result)
                checkpoint()
            async def experiment():
                report['phase'] = 'primary switching'
                for index, feature in enumerate(PRIMARY + EXTRA_CYCLE):
                    label = f'{index + 1:02d}_{feature}'
                    sampler.phase = label
                    record(await runtime.generate(feature, label), label)
                report['phase'] = 'controlled recovery'
                report['recovery'] = await recovery_probes(runtime, record)
                report['phase'] = 'concurrency'
                report['recovery'].append(await competing_requests(runtime, record))
                report['phase'] = 'cancellation'
                report['recovery'].append(await competing_requests(runtime, record, cancel=True))
            asyncio.run(experiment())
            report['phase'] = 'equivalence review'
            differing = {r['requested_feature'] for r in report['results']
                         if not r['versus_gate1']['rgb_pixels_equal'] or (r['versus_first_shared']
                         and not r['versus_first_shared']['rgb_pixels_equal'])}
            report['isolated_repeat_required_features'] = sorted(differing)
            # Persistent foundation has to be released before any diagnostic fresh Base.
            report['foundation_objects'] = runtime.foundation
            report['after_experiment'] = gate.memory(torch)
            report['ready_after_experiment'] = runtime.ready
            report['memory_observations_by_feature'] = {feature: [
                {'label': r['label'], 'memory_after': r['memory_after']} for r in report['results']
                if r['requested_feature'] == feature] for feature in gate.FEATURES}
            report['resource_review'] = 'REQUIRED, compare same feature observations and memory samples; no invented leak threshold'
            report['status'] = ('SWITCHING_COMPLETED_ISOLATED_REPEATS_REQUIRED' if differing
                                else 'SWITCHING_COMPLETED_REVIEW_REQUIRED')
            report['phase'] = 'completed'
    except Exception as exc:
        report.update(error={'type': type(exc).__name__, 'message': gate.sanitized(str(exc))},
                      failure_category=gate.failure_category(report['phase'], exc))
        (output / 'failure.log').write_text(gate.sanitized(traceback.format_exc()))
    finally:
        report['timing_seconds']['persistent_process_total'] = time.monotonic() - started
        if sampler:
            gate.save(output / 'memory_samples.json', sampler.samples)
        checkpoint()
    print('GATE2 STATUS', report['status'], flush=True)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--verify-only', action='store_true')
    parser.add_argument('--environment-only', action='store_true')
    parser.add_argument('--model-dir', type=Path)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    if args.verify_only:
        verify_experiment()
        print('GATE_2_ARTIFACT_PREFLIGHT_OK (no model load)', flush=True)
    elif args.environment_only:
        review = json.loads((ROOT / 'docs/experiments/unified-kaggle-gate1-review.json').read_text())
        print(json.dumps(verify_environment(gate.environment(), review['environment'])))
    else:
        result = worker(args.model_dir, args.output)
        sys.exit(0 if result['status'].startswith('SWITCHING_COMPLETED') else 1)


if __name__ == '__main__':
    main()
