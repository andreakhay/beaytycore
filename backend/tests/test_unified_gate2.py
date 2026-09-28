"""Gate 2 safety at fake model boundaries, never evidence of GPU switching."""
import asyncio
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
import struct
import sys
import threading
from types import SimpleNamespace
from zipfile import ZipFile

from PIL import Image
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from scripts import unified_gate1 as gate
from scripts import unified_gate2 as experiment
from scripts import unified_gate2_bootstrap as bootstrap
from scripts import package_unified_gate2 as packaging


class FakePipe:
    def __init__(self):
        for name in experiment.COMPONENTS:
            setattr(self, name, object())
        self.transformer=SimpleNamespace(named_parameters=lambda: [])
        self.loaded = None
        self.calls = []
        self.fail_load = False
        self.stale = False

    def unload_lora_weights(self):
        self.calls.append('unload')
        if not self.stale:
            self.loaded = None

    def load_lora_weights(self, directory, weight_name):
        self.calls.append(('load', directory, weight_name))
        if self.fail_load:
            raise RuntimeError('Injected loading failure')
        self.loaded = Path(directory) / weight_name

    def get_list_adapters(self):
        return {'transformer': ['default_0']} if self.loaded else {}

    def get_active_adapters(self):
        return ['default_0'] if self.loaded else []


def payload(feature, expected):
    stream = BytesIO()
    Image.new('RGB', (512, 512), (40, 50, 60)).save(stream, 'PNG')
    import base64
    meta = {k:v for k,v in expected.items() if k != 'generator'}
    meta.update(base_model_id=gate.MODEL_ID, base_model_revision=gate.REVISION, steps=20, guidance=4.0, seed=1977)
    return {'status':'completed', 'generator':expected['generator'], 'metadata':meta,
            'image':{'width':512,'height':512,'content_type':'image/png',
                     'data_url':'data:image/png;base64,'+base64.b64encode(stream.getvalue()).decode()}}


@pytest.fixture
def runtime(tmp_path):
    pipe = FakePipe()
    specs = {}
    for feature in gate.FEATURES:
        folder = tmp_path / feature
        folder.mkdir()
        path = folder / 'adapter.safetensors'
        path.write_bytes(feature.encode())
        invalid = folder / 'invalid.txt'
        invalid.write_text('invalid')
        specs[feature] = {'path':path,'verify':lambda: {},'missing':folder/'missing', 'invalid':invalid,
            'expected':{'style_id':feature+'_style','adapter_id':feature+'_adapter',
                        'adapter_sha256':gate.digest(path),'adapter_steps':250,'generator':feature+'_generator'}}
    def inspect(p, path, name):
        if p.loaded != path or p.get_active_adapters() != ['default_0']:
            raise RuntimeError('Wrong actual adapter')
        return {'library_adapter_name':'default_0','tensor_count':160,
                'converted_tensor_sha256':gate.digest(path),'tensor_equality_verified':True}
    def infer(feature):
        assert pipe.loaded == specs[feature]['path']
        return payload(feature, specs[feature]['expected'])
    return experiment.SharedExperiment(pipe, specs, infer, lambda: pipe.calls.append('sync'), inspect)


def test_primary_and_extra_sequence_use_one_foundation_and_correct_artifacts(runtime):
    async def run():
        values = [await runtime.generate(f, str(i)) for i,f in enumerate(experiment.PRIMARY+experiment.EXTRA_CYCLE)]
        assert [v['requested_feature'] for v in values] == list(experiment.PRIMARY+experiment.EXTRA_CYCLE)
        assert all(v['foundation_objects']==runtime.foundation for v in values)
        for v in values:
            assert v['active_feature']==v['requested_feature']
            assert v['adapter_sha256']==runtime.specs[v['requested_feature']]['expected']['adapter_sha256']
        assert [v['raw'] for v in values] == [values[0]['raw']]*len(values)
    asyncio.run(run())
    assert runtime.pipe.calls.count('unload') == len(experiment.PRIMARY+experiment.EXTRA_CYCLE)


@pytest.mark.parametrize('injection',['missing','invalid','after_unload','after_load','oom'])
def test_switch_failure_restores_previous_without_inference(runtime,injection):
    async def run():
        await runtime.generate('hairstyle','initial')
        count=len(runtime.completed)
        with pytest.raises(experiment.SwitchFailure,match='restored=True'):
            await runtime.generate('makeup','failed',inject=injection)
        assert len(runtime.completed)==count and runtime.active=='hairstyle' and runtime.ready
        value=await runtime.generate('hairstyle','restored')
        assert value['active_feature']=='hairstyle'
    asyncio.run(run())


def test_failed_restoration_explicitly_unready_blocks_later_inference(runtime):
    async def run():
        await runtime.generate('hairstyle','initial')
        runtime.pipe.fail_load=True
        with pytest.raises(experiment.SwitchFailure,match='ready=False'):
            await runtime.generate('makeup','failed')
        assert runtime.active is None and not runtime.ready
        with pytest.raises(experiment.SwitchFailure,match='unready'):
            await runtime.generate('nails','blocked')
        assert len(runtime.completed)==1
    asyncio.run(run())


def test_stale_adapter_after_unload_fails_closed(runtime):
    async def run():
        await runtime.generate('hairstyle','initial')
        runtime.pipe.stale=True
        with pytest.raises(experiment.SwitchFailure):
            await runtime.generate('makeup','bad')
        assert not runtime.ready and runtime.active is None and len(runtime.completed)==1
    asyncio.run(run())


def test_residual_tensors_after_reported_empty_unload_are_rejected(runtime):
    runtime.pipe.transformer.named_parameters=lambda:[('block.lora_A.hidden.weight',object())]
    with pytest.raises(experiment.SwitchFailure,match='residual'):
        asyncio.run(runtime.generate('makeup','bad'))
    assert not runtime.completed and not runtime.ready


def test_wrong_loaded_identity_never_generates(runtime):
    original=runtime.pipe.load_lora_weights
    def wrong(directory,weight_name):
        original(str(runtime.specs['nails']['path'].parent),weight_name)
    runtime.pipe.load_lora_weights=wrong
    with pytest.raises(experiment.SwitchFailure):
        asyncio.run(runtime.generate('hairstyle','bad'))
    assert not runtime.completed and not runtime.ready


def test_foundation_replacement_detected(runtime):
    runtime.pipe.vae=object()
    with pytest.raises(experiment.SwitchFailure,match='Foundation object changed'):
        asyncio.run(runtime.generate('hairstyle','bad'))
    assert not runtime.completed and not runtime.ready


def test_wrong_response_adapter_metadata_fails_closed(runtime):
    original=runtime.infer
    def wrong(feature):
        v=original(feature);v['metadata']['adapter_id']='wrong';return v
    runtime.infer=wrong
    with pytest.raises(ValueError,match='adapter_id'):
        asyncio.run(runtime.generate('hairstyle','bad'))
    assert not runtime.ready and not runtime.completed


def test_unknown_feature_does_not_touch_pipeline(runtime):
    with pytest.raises(ValueError,match='Unknown'):
        asyncio.run(runtime.generate('other','bad'))
    assert not runtime.pipe.calls


def test_mutated_read_only_artifact_rejected(runtime):
    runtime.specs['hairstyle']['path'].write_text('changed fixture')
    with pytest.raises(experiment.SwitchFailure,match='SHA'):
        asyncio.run(runtime.generate('hairstyle','bad'))
    assert not runtime.completed and not runtime.ready


@pytest.mark.parametrize('cancel',[False,True])
def test_competing_features_and_repeated_cancellation_hold_ownership(runtime,cancel):
    recorded=[]
    result=asyncio.run(experiment.competing_requests(runtime,lambda value,label:recorded.append((value,label)),cancel))
    assert result['serialized'] and len(recorded)==2
    assert [v['active_feature'] for v,_ in recorded]==['hairstyle','makeup']
    spans=[e['event'] for e in runtime.events if e['event'].startswith('ownership_')]
    assert spans==['ownership_start','ownership_end','ownership_start','ownership_end']


def test_cancelled_inference_error_is_drained_and_waiter_fails_closed(runtime):
    async def run():
        entered,release=threading.Event(),threading.Event()
        def failure(feature):
            entered.set();release.wait(3);raise RuntimeError('inference failure')
        runtime.infer=failure
        first=asyncio.create_task(runtime.generate('hairstyle','first'))
        await experiment.wait_started(entered)
        first.cancel()
        await asyncio.sleep(.02)
        assert runtime.owner.locked()
        second=asyncio.create_task(runtime.generate('makeup','second'))
        release.set()
        results=await asyncio.gather(first,second,return_exceptions=True)
        assert isinstance(results[0],asyncio.CancelledError)
        assert isinstance(results[1],experiment.SwitchFailure)
        assert not runtime.ready and not runtime.owner.locked()
    asyncio.run(run())


def test_cancelled_error_keeps_ownership_during_gpu_drain(runtime):
    async def run():
        pending,draining,release=threading.Event(),threading.Event(),threading.Event()
        def infer(feature):
            pending.set();raise RuntimeError('GPU work submitted before error')
        def synchronize():
            if pending.is_set():
                draining.set();assert release.wait(3)
        runtime.infer=infer;runtime.synchronize=synchronize
        first=asyncio.create_task(runtime.generate('hairstyle','first'))
        await experiment.wait_started(draining)
        first.cancel()
        second=asyncio.create_task(runtime.generate('makeup','second'))
        await asyncio.sleep(.03)
        assert runtime.owner.locked() and len([e for e in runtime.events if e['event']=='ownership_start'])==1
        release.set()
        results=await asyncio.gather(first,second,return_exceptions=True)
        assert isinstance(results[0],asyncio.CancelledError) and isinstance(results[1],experiment.SwitchFailure)
    asyncio.run(run())


def test_failed_gpu_drain_is_recorded_and_future_requests_fail_closed(runtime):
    def infer(feature):raise RuntimeError('inference failure')
    def sync():
        if not runtime.ready and runtime.active is None and runtime.pipe.loaded:
            raise RuntimeError('CUDA context cannot synchronize')
    runtime.infer=infer;runtime.synchronize=sync
    with pytest.raises(RuntimeError,match='inference failure'):
        asyncio.run(runtime.generate('hairstyle','bad'))
    assert not runtime.ready and any(e['event']=='gpu_drain_failed' for e in runtime.events)
    with pytest.raises(experiment.SwitchFailure,match='unready'):
        asyncio.run(runtime.generate('makeup','blocked'))


@pytest.mark.parametrize('field',['python','packages','diffusers_commit','torch','cuda','gpu'])
def test_exact_observed_environment_mismatch_is_rejected(field):
    expected=json.loads((ROOT/'docs/experiments/unified-kaggle-gate1-review.json').read_text())['environment']
    actual={**expected,field:'different'}
    with pytest.raises(ValueError,match=field):
        experiment.verify_environment(actual,expected)


def test_exact_observed_environment_accepted():
    env=json.loads((ROOT/'docs/experiments/unified-kaggle-gate1-review.json').read_text())['environment']
    assert experiment.verify_environment(env,env)==env


def test_original_runtime_view_reports_unavailable_peak_as_null(tmp_path,monkeypatch):
    class View:
        def generate(self,*args):return {'metadata':{'peak_gpu_mib':0}}
    def contract(feature):
        return View,lambda:{}, {'style_id':'fixed'}
    monkeypatch.setattr(gate,'feature_contract',contract)
    monkeypatch.setattr(experiment,'ROOT',tmp_path)
    monkeypatch.setattr(experiment,'adapter_path',lambda f:tmp_path/f/'adapter.safetensors')
    Image.new('RGB',(512,512)).save(tmp_path/'input.png')
    plan={'features':{f:{'input':'input.png'} for f in gate.FEATURES}}
    peak=lambda *args:0
    peak.unavailable=True
    torch=SimpleNamespace(cuda=SimpleNamespace(max_memory_allocated=peak,reset_peak_memory_stats=lambda *args:None))
    _,infer=experiment.runtime_views(object(),torch,plan)
    assert infer('hairstyle')['metadata']['peak_gpu_mib'] is None


class Tensor:
    dtype='float16'
    def __init__(self,value):self.value=value
    def detach(self):return self
    def cpu(self):return self
    def to(self,**kwargs):return self
    def contiguous(self):return self
    def numpy(self):return self
    def tobytes(self):return struct.pack('<f',self.value)


@pytest.mark.parametrize('failure',[None,'tensor','inventory','extra','active','disabled','merged','mixed_layer'])
def test_real_inspector_checks_converted_tensor_values_and_adapter_inventory(monkeypatch,failure):
    monkeypatch.setitem(sys.modules,'torch',SimpleNamespace(equal=lambda a,b:a.value==b.value))
    path=Path('adapter.safetensors')
    keys={'block.lora_A.default_0.weight':Tensor(1),'block.lora_B.default_0.weight':Tensor(2)}
    if failure=='tensor':keys['block.lora_B.default_0.weight']=Tensor(3)
    if failure=='extra':keys['block.lora_B.other.weight']=Tensor(2)
    module=SimpleNamespace(lora_A={'default_0':object()},lora_B={'default_0':object()},
                           active_adapters=['default_0'],disable_adapters=failure=='disabled',merged=failure=='merged')
    second=SimpleNamespace(lora_A={'default_0':object()},lora_B={'default_0':object()},
                           active_adapters=['other'] if failure=='mixed_layer' else ['default_0'],
                           disable_adapters=False,merged=False)
    pipe=SimpleNamespace(get_list_adapters=lambda: {'transformer':['default_0','other']} if failure=='inventory' else {'transformer':['default_0']},
        get_active_adapters=lambda:[] if failure=='active' else ['default_0'],
        lora_state_dict=lambda *args,**kwargs:{'transformer.block.lora_A.weight':Tensor(1),'transformer.block.lora_B.weight':Tensor(2)},
        transformer=SimpleNamespace(named_parameters=lambda:keys.items(),modules=lambda:[module,second]))
    if failure:
        with pytest.raises(RuntimeError):experiment.inspect_adapter(pipe,path)
    else:
        result=experiment.inspect_adapter(pipe,path)
        assert result['tensor_equality_verified'] and result['tensor_count']==2


def test_packager_refuses_unreviewed_or_overwritten_sources(tmp_path,monkeypatch):
    src=tmp_path/'src.bin';src.write_text('not approved')
    with pytest.raises(ValueError,match='reviewed Gate 1 bundle'):
        packaging.build(src,src,tmp_path/'out.bin')
    output=tmp_path/'out.bin';output.write_text('existing')
    with pytest.raises(ValueError,match='overwrite'):
        packaging.build(src,src,output)


def test_bootstrap_failure_still_produces_downloadable_evidence(tmp_path,monkeypatch):
    monkeypatch.setattr(bootstrap,'verify_experiment',lambda:(_ for _ in ()).throw(ValueError('controlled preflight')))
    output=tmp_path/'output'
    result=bootstrap.bootstrap(output)
    assert result['status']=='FAILED' and result['gate2_passed'] is False
    with ZipFile(output/'evidence.zip') as z:
        assert 'setup.json' in z.namelist() and 'gate1_review.json' in z.namelist()
    with pytest.raises(ValueError,match='fresh'):
        bootstrap.bootstrap(output)


def test_conditional_isolated_diagnostics_compare_only_affected_feature(tmp_path,monkeypatch):
    called=[]
    def command(args,output,filename,env):
        called.append(args[3])
        folder=Path(args[5])
        stream=BytesIO();Image.new('RGB',(512,512),(40,50,60)).save(stream,'PNG')
        (folder/'candidate.png').write_bytes(stream.getvalue())
        gate.save(folder/'report.json',{'comparison':{'rgb_pixels_equal':True}})
    monkeypatch.setattr(bootstrap,'command',command)
    shared=tmp_path/'results/01_nails';shared.mkdir(parents=True)
    stream=BytesIO();Image.new('RGB',(512,512),(40,50,60)).save(stream,'PNG')
    (shared/'candidate.png').write_bytes(stream.getvalue())
    bootstrap.isolated_diagnostics(tmp_path,['nails'],'model',{},
                                   {'results':[{'requested_feature':'nails','label':'01_nails'}]})
    assert called==['nails','nails']
    result=json.loads((tmp_path/'isolated_diagnostics.json').read_text())
    assert result[0]['isolated_repeat_comparison']['rgb_pixels_equal']
    assert all(row['rgb_pixels_equal'] for row in result[0]['shared_vs_each_isolated'])


@pytest.mark.parametrize('difference',[None,'nails'])
def test_complete_experiment_records_single_base_recovery_and_review_status(runtime,tmp_path,monkeypatch,difference):
    root=tmp_path/'bundle';root.mkdir()
    model=root/gate.REVISION;model.mkdir()
    (model/'model_index.json').write_text('{}')
    review={'environment':{'synthetic':'fake test only'},'base_model_index_sha256':gate.digest(model/'model_index.json')}
    plan={'features':{}}
    baseline={'features':{}}
    for feature in gate.FEATURES:
        raw=gate.validate_result(payload(feature,runtime.specs[feature]['expected']),runtime.specs[feature]['expected'])
        (root/f'{feature}.png').write_bytes(raw)
        plan['features'][feature]={'input':f'{feature}.png','settings':{'seed':1977}}
        baseline['features'][feature]={'output':f'{feature}.png'}
    monkeypatch.setattr(experiment,'ROOT',root)
    monkeypatch.setattr(experiment,'verify_experiment',lambda:(plan,baseline,review))
    monkeypatch.setattr(gate,'environment',lambda:review['environment'])
    monkeypatch.setattr(experiment,'verify_environment',lambda a,b:a)
    monkeypatch.setattr(gate,'memory',lambda *args:{})
    monkeypatch.setattr(experiment,'inspect_adapter',runtime.inspect)
    infer=runtime.infer
    if difference:
        def altered(feature):
            result=infer(feature)
            if feature==difference:
                import base64
                stream=BytesIO();Image.new('RGB',(512,512),(41,50,60)).save(stream,'PNG')
                result['image']['data_url']='data:image/png;base64,'+base64.b64encode(stream.getvalue()).decode()
            return result
    else:
        altered=infer
    monkeypatch.setattr(experiment,'runtime_views',lambda *args:(runtime.specs,altered))
    loads=[]
    runtime.pipe.enable_model_cpu_offload=lambda **kwargs:None
    def load(*args,**kwargs):loads.append(args);return runtime.pipe
    monkeypatch.setitem(sys.modules,'diffusers',SimpleNamespace(Flux2KleinPipeline=SimpleNamespace(from_pretrained=load)))
    torch=SimpleNamespace(float16='float16',cuda=SimpleNamespace(synchronize=lambda *args:None,
                            reset_peak_memory_stats=lambda *args:None,max_memory_allocated=lambda *args:0))
    monkeypatch.setitem(sys.modules,'torch',torch)
    class Sampler:
        def __init__(self,*args):self.samples=[];self.phase=''
        def __enter__(self):return self
        def __exit__(self,*args):pass
    monkeypatch.setattr(gate,'Sampler',Sampler)
    result=experiment.worker(model,root/'results')
    assert len(loads)==result['foundation_load_count']==1
    assert len(result['results'])==17 and len(result['recovery'])==7
    assert result['gate2_passed'] is False and result['gate3_started'] is False
    assert result['isolated_repeat_required_features']==([difference] if difference else [])
    assert result['status']==('SWITCHING_COMPLETED_ISOLATED_REPEATS_REQUIRED' if difference else 'SWITCHING_COMPLETED_REVIEW_REQUIRED')
    assert all(row['foundation_objects']==result['foundation_objects'] for row in result['results'])
