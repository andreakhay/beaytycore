"""Nails step tuning cannot silently alter other features or accept wrong provenance."""

import asyncio
from io import BytesIO
from pathlib import Path
import sys
from types import SimpleNamespace

import httpx
from PIL import Image
import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[2]))

from app.nails.inference_options import configured_steps, validate_steps
from app.nails.remote import RemoteLocalizedNails, NailsGenerationError
from app.nails.styles import NAIL_STYLE_BY_ID
from scripts.unified_gate3_nails import NailsRuntime
from scripts import unified_gate3_server as server
from scripts.nails_latency_update import FILES, prepare_worker, verify_payload, stop_worker
from scripts.package_nails_latency_cell import build
from test_unified_gate3 import fake_server, KEY


@pytest.mark.parametrize('steps',[20,12,8])
def test_runtime_changes_only_requested_step_count(steps):
    calls=[]
    class Pipe:
        def __call__(self,**kwargs):
            calls.append(kwargs)
            return SimpleNamespace(images=[Image.new('RGB',(512,512),'red')])
    class Generator:
        def __init__(self,device):
            assert device=='cuda'
        def manual_seed(self,value):
            assert value==1977
            return self
    runtime=NailsRuntime()
    runtime.pipe=Pipe()
    runtime.torch=SimpleNamespace(Generator=Generator)
    source=Image.new('RGB',(512,512),'white')
    payload=runtime.generate(source,'classic_red',inference_steps=steps)
    assert len(calls)==1 and calls[0]['num_inference_steps']==steps
    assert calls[0]['image'] is source and calls[0]['guidance_scale']==4.0
    assert calls[0]['width']==calls[0]['height']==512
    server.validate_result(payload,server.expected_contract('nails','classic_red'),steps)
    assert payload['metadata']['steps']==steps  # validator must not rewrite the response


def test_steps_configuration_is_bounded_and_default_is_20(monkeypatch):
    monkeypatch.delenv('NAILS_INFERENCE_STEPS',raising=False)
    assert configured_steps()==20
    for value in ('0','1','17','21','12.5',12.5,True):
        with pytest.raises(ValueError):
            validate_steps(value)
    monkeypatch.setenv('NAILS_INFERENCE_STEPS','12')
    assert configured_steps()==12
    monkeypatch.setenv('NAILS_INFERENCE_STEPS','fast')
    with pytest.raises(RuntimeError):
        configured_steps()


def test_http_steps_are_nails_only_and_fail_before_gpu(fake_server):
    owner,pipe,_,_=fake_server
    image=BytesIO()
    Image.new('RGB',(512,512),'white').save(image,'PNG')
    async def check():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=server.app),base_url='http://test') as client:
            for feature,style,steps in [('hairstyle','crew_cut',12),('makeup','natural_makeup',8),('nails','classic_red',17)]:
                r=await client.post(f'/{feature}/generate',data={'style_id':style,'inference_steps':str(steps)},
                    files={'image':('nail.png',image.getvalue(),'image/png')},headers={'X-API-Key':KEY})
                assert r.status_code==400
            assert owner.sequence==0 and len(pipe.loads)==1
    asyncio.run(check())


def test_remote_client_sends_requested_steps_and_rejects_old_worker(monkeypatch):
    image=Image.new('RGB',(512,512),'white')
    runtime=NailsRuntime()
    runtime.pipe=lambda **kwargs:SimpleNamespace(images=[image])
    runtime.torch=SimpleNamespace(Generator=lambda **kwargs:SimpleNamespace(manual_seed=lambda _:None))
    payload=runtime.generate(image,'classic_red',inference_steps=12)
    real_client=httpx.AsyncClient
    def transport(request):
        if request.method=='GET':
            return httpx.Response(200,json={'nails_inference_steps':[8,12,20]})
        assert b'name="inference_steps"' in request.content and b'\r\n12\r\n' in request.content
        return httpx.Response(200,json=payload)
    monkeypatch.setattr(httpx,'AsyncClient',lambda *args,**kwargs:real_client(*args,**kwargs,transport=httpx.MockTransport(transport)))
    client=RemoteLocalizedNails('https://test.invalid/nails',KEY,inference_steps=12)
    generated=asyncio.run(client.generate(image,NAIL_STYLE_BY_ID['classic_red']))
    assert generated.info['inference_steps']==12
    payload['metadata']['steps']=20
    with pytest.raises(NailsGenerationError,match='invalid image or model response'):
        asyncio.run(client.generate(image,NAIL_STYLE_BY_ID['classic_red']))


def test_fast_client_rejects_old_service_before_any_gpu_call(monkeypatch):
    calls=[]
    original=httpx.AsyncClient
    def transport(request):
        calls.append(request.method)
        return httpx.Response(200,json={'status':'ready'})
    monkeypatch.setattr(httpx,'AsyncClient',lambda *args,**kwargs:original(*args,**kwargs,transport=httpx.MockTransport(transport)))
    client=RemoteLocalizedNails('https://test.invalid/nails',KEY,inference_steps=8)
    with pytest.raises(NailsGenerationError,match='Update the unified'):
        asyncio.run(client.generate(Image.new('RGB',(512,512)),NAIL_STYLE_BY_ID['classic_red']))
    assert calls==['GET']


def test_update_cell_sources_are_verified_and_assets_remain_in_original(tmp_path):
    root=Path(__file__).resolve().parents[2]
    source,hashes=build(root)
    compile(source,'update_cell.py','exec')
    from hashlib import sha256
    payload={'files':{name:(root/name).read_text(encoding='utf-8') for name in FILES},'hashes':hashes}
    verify_payload(payload)
    original=tmp_path/'original'
    for name in ('scripts','backend/app/nails','docs','gate1/adapters'):
        (original/name).mkdir(parents=True)
    (original/'gate1/adapters/read_only.safetensors').write_bytes(b'fake asset')
    target=tmp_path/'new'
    # Windows CI need not grant symlink creation privileges; assert the intended
    # target and create a marker instead. Linux Kaggle uses the real symlink.
    links=[]
    def link(path,destination,**kwargs):
        links.append((path,destination))
    from unittest.mock import patch
    with patch.object(Path,'symlink_to',link):
        prepare_worker(original,target,payload)
    assert links==[(target/'gate1',original/'gate1')]
    assert (original/'gate1/adapters/read_only.safetensors').read_bytes()==b'fake asset'
    assert not (target/'gate1/adapters/read_only.safetensors').exists()
    assert sha256((target/FILES[0]).read_text(encoding='utf-8').encode()).hexdigest()==hashes[FILES[0]]
    with pytest.raises(ValueError,match='already exists'):
        prepare_worker(original,target,payload)
    payload['files'][FILES[0]]+='\n# altered'
    with pytest.raises(ValueError,match='hash differs'):
        verify_payload(payload)


def test_update_refuses_unrelated_pid_without_sending_signal(monkeypatch):
    from scripts import nails_latency_update as update
    calls=[]
    monkeypatch.setattr(update,'running_worker',lambda pid:True)
    monkeypatch.setattr(Path,'read_bytes',lambda path:b'other-service')
    monkeypatch.setattr(update.os,'kill',lambda *args:calls.append(args))
    with pytest.raises(RuntimeError,match='not the expected'):
        stop_worker(123)
    assert calls==[]


@pytest.mark.parametrize('fail_start',[False,True])
def test_notebook_update_reuses_cache_and_restores_original_on_failure(tmp_path,monkeypatch,fail_start):
    from scripts import nails_latency_update as update, unified_gate3_bootstrap as boot
    import json
    from hashlib import sha256
    source,hashes=build()
    root=Path(__file__).resolve().parents[2]
    payload={'files':{name:(root/name).read_text(encoding='utf-8') for name in FILES},'hashes':hashes}
    original,previous=tmp_path/'bundle',tmp_path/'unified_gate3'
    original.mkdir()
    previous.mkdir()
    model=tmp_path/'cached_base'
    model.mkdir()
    (previous/'model.json').write_text(json.dumps({'snapshot':str(model)}))
    (previous/'server_process.json').write_text(json.dumps({'pid':123,'port':8765}))
    monkeypatch.setenv('AI_REMOTE_API_KEY',KEY)
    monkeypatch.setattr(boot,'verify_bundle',lambda path:None)
    monkeypatch.setattr(boot,'health',lambda url:{'status':'ready'})
    monkeypatch.setattr(boot,'ready',lambda value:True)
    monkeypatch.setattr(update,'prepare_worker',lambda *args:None)
    monkeypatch.setattr(update,'running_worker',lambda pid:True)
    stopped=[]
    monkeypatch.setattr(update,'stop_worker',lambda pid:stopped.append(pid))
    attempts=[]
    def start(output,env):
        attempts.append(boot.ROOT)
        assert env['AI_MODEL_DIR']==str(model) and env['AI_REMOTE_API_KEY']==KEY
        (output/'server_process.json').write_text(json.dumps({'pid':200+len(attempts),'port':8765}))
        if fail_start and len(attempts)==1:
            raise RuntimeError('Controlled failed startup')
        return {'health':{'nails_inference_steps':[8,12,20]},'server_start_seconds':1.0}
    monkeypatch.setattr(boot,'start_server',start)
    monkeypatch.setattr(boot,'ROOT',original)
    report=update.update(payload,original,previous)
    assert stopped==([123,201] if fail_start else [123])
    assert len(attempts)==(2 if fail_start else 1)
    if fail_start:
        assert attempts[-1]==original and report['status']=='ORIGINAL_20_STEP_WORKER_RESTORED'
    else:
        assert report['status']=='READY_FOR_NAILS_LATENCY_COMPARE'
    assert json.loads((previous/'server_process.json').read_text())['pid']==200+len(attempts)
    assert KEY not in json.dumps(report)
