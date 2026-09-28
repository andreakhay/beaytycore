"""Gate 3 HTTP contract and shared ownership with fake GPU boundaries."""

import asyncio
import base64
from io import BytesIO
import os
from pathlib import Path
import sys
import threading
from types import SimpleNamespace
from unittest.mock import patch

import httpx
from fastapi.testclient import TestClient
from PIL import Image
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from scripts import unified_gate1 as gate
from scripts import unified_gate3_server as server
from app import main
from app.generation.remote_destination import destination
from app.generation.remote_flux import RemoteFluxEngine
from app.generation.remote_makeup import RemoteMakeupEngine
from app.nails.remote import RemoteLocalizedNails
from central_remote_fixture import CentralRemoteScenario, png

KEY = 'gate3-test-key-is-not-a-production-secret'


class FakePipe:
    def __init__(self):
        for name in ('transformer','text_encoder','vae','scheduler','tokenizer'):
            setattr(self,name,object())
        self.transformer=SimpleNamespace(named_parameters=lambda:[])
        self.loaded=None
        self.loads=[]
        self.fail_load=False

    def unload_lora_weights(self):
        self.loaded=None

    def load_lora_weights(self,directory,weight_name):
        if self.fail_load:
            raise RuntimeError('simulated switch failure with private path /tmp/private')
        self.loaded=Path(directory)/weight_name
        self.loads.append(self.loaded)

    def get_list_adapters(self):
        return {'transformer':['default_0']} if self.loaded else {}

    def get_active_adapters(self):
        return ['default_0'] if self.loaded else []

    def enable_model_cpu_offload(self,gpu_id):
        assert gpu_id==0


class FakeView:
    def __init__(self,feature,pipe,expected_by_key,gate_event=None,release=None):
        self.feature,self.pipe,self.expected_by_key=feature,pipe,expected_by_key
        self.gate_event,self.release=gate_event,release
        self.fail=False

    def generate(self,image,style_id):
        assert image.mode=='RGB'
        adapter_key=server.selected_adapter(self.feature,style_id)
        assert self.pipe.loaded==self.expected_by_key[adapter_key]
        if self.gate_event:
            self.gate_event.set()
            assert self.release.wait(5)
        if self.fail:
            raise RuntimeError('simulated private inference exception /tmp/private')
        if self.feature=='hairstyle':
            _,meta=self.hair_adapters[adapter_key.split(':')[1]]
            expected=server.expected_contract(self.feature,style_id,adapter_key.split(':')[1],meta)
        else:
            expected=server.expected_contract(self.feature,style_id)
        stream=BytesIO()
        Image.new('RGB',(512,512),'red').save(stream,'PNG')
        metadata={k:v for k,v in expected.items() if k not in ('generator','prompt')}
        metadata.update(base_model_id=gate.MODEL_ID,base_model_revision=gate.REVISION,
                        seed=1977,steps=20,guidance=4.0,prompt=expected['prompt'])
        return {'status':'completed','generator':expected['generator'],'metadata':metadata,
                'image':{'content_type':'image/png','width':512,'height':512,
                         'data_url':'data:image/png;base64,'+base64.b64encode(stream.getvalue()).decode()}}


@pytest.fixture
def fake_server(tmp_path,monkeypatch):
    pipe=FakePipe()
    paths={}
    for key in ('hairstyle:train001','makeup','nails'):
        folder=tmp_path/key.replace(':','_')
        folder.mkdir()
        path=folder/'adapter.safetensors'
        path.write_bytes(key.encode())
        paths[key]=path
    hair={'train001':(paths['hairstyle:train001'].parent,
                     {'checkpoint_sha256':gate.digest(paths['hairstyle:train001']),
                      'training_steps':250,'experiment':'TRAIN-001','supported_style_ids':list(server.HAIR_STYLES),
                      'base_model_id':gate.MODEL_ID,'base_model_revision':gate.REVISION})}
    specs={key:{'path':path,'verify':lambda:None,
                'expected':{'adapter_sha256':gate.digest(path)}} for key,path in paths.items()}
    views={feature:FakeView(feature,pipe,paths) for feature in server.FEATURES}
    views['hairstyle'].hair_adapters=hair
    def inspect(actual,path,name):
        assert actual.loaded==path
        return {'library_adapter_name':'default_0','tensor_count':200,
                'verified_layer_count':100,'converted_tensor_sha256':gate.digest(path),
                'tensor_equality_verified':True}
    monkeypatch.setattr(server,'inspect_adapter',inspect)
    monkeypatch.setattr(server.gate,'memory',lambda _: {})
    torch=SimpleNamespace(cuda=SimpleNamespace(synchronize=lambda _:None,reset_peak_memory_stats=lambda _:None,
                                                max_memory_allocated=lambda _:0))
    owner=server.ServingOwner(pipe,torch,specs,views,hair)
    owner.load_verified('hairstyle:train001')
    old=server.runtime
    server.runtime=SimpleNamespace(ready=True,owner=owner,base_loaded=True,foundation_load_count=1,
        load_seconds=1.0,health=lambda: {'status':'ready','foundation_load_count':1,
                                         'supported_features':list(server.FEATURES)},
        status=lambda:{'status':'ready','requests':owner.audit})
    monkeypatch.setenv('AI_REMOTE_API_KEY',KEY)
    yield owner,pipe,views,paths
    server.runtime=old


def post(client,feature,style,raw=None):
    return client.post(f'/{feature}/generate',data={'style_id':style},
                       files={'image':('image.png',raw or png(Image.new('RGB',(512,512),'white')),'image/png')},
                       headers={'X-API-Key':KEY})


def test_server_routes_switch_and_reuse(fake_server):
    owner,pipe,_,paths=fake_server
    async def check():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=server.app),base_url='http://test') as client:
            assert (await client.get('/health')).json()['foundation_load_count']==1
            assert (await client.get('/status')).status_code==401
            for feature,style in [('hairstyle','crew_cut'),('hairstyle','bob_hair'),
                                  ('makeup','natural_makeup'),('nails','classic_red'),
                                  ('hairstyle','crew_cut')]:
                response=await client.post(f'/{feature}/generate',data={'style_id':style},
                    files={'image':('input.png',png(Image.new('RGB',(512,512),'white')),'image/png')},
                    headers={'X-API-Key':KEY})
                assert response.status_code==200,response.text
                assert response.json()['metadata']['style_id']==style
            assert len(pipe.loads)==4  # initial Hair, Makeup, Nails, restored Hair
            assert owner.active=='hairstyle:train001'
            observed=(await client.get('/status',headers={'X-API-Key':KEY})).json()['requests']
            assert [item['feature'] for item in observed]==['hairstyle','hairstyle','makeup','nails','hairstyle']
    asyncio.run(check())


def test_server_errors_and_no_private_details(fake_server):
    owner,pipe,views,_=fake_server
    async def check():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=server.app),base_url='http://test') as client:
            image=png(Image.new('RGB',(512,512),'white'))
            def req(feature,style,raw=image,key=KEY):
                return client.post(f'/{feature}/generate',data={'style_id':style},
                    files={'image':('input.png',raw,'image/png')},headers={'X-API-Key':key})
            assert (await req('hairstyle','crew_cut',key='bad')).status_code==401
            assert (await req('unknown','crew_cut')).status_code==404
            assert (await req('makeup','crew_cut')).status_code==400
            assert (await req('nails','classic_red',raw=b'bad')).status_code==400
            assert (await client.post('/nails/generate',headers={'X-API-Key':KEY})).status_code==422
            pipe.fail_load=True
            failed=await req('makeup','natural_makeup')
            assert failed.status_code==503 and '/tmp/private' not in failed.text
            assert owner.ready is False
            assert (await req('hairstyle','crew_cut')).status_code==503
    asyncio.run(check())


def test_server_recovers_from_switch_failure(fake_server):
    owner,pipe,_,_=fake_server
    original=pipe.load_lora_weights
    state={'fail_once':True}
    def one_failure(directory,weight_name):
        if state['fail_once']:
            state['fail_once']=False
            raise RuntimeError('injected')
        return original(directory,weight_name)
    pipe.load_lora_weights=one_failure
    async def check():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=server.app),base_url='http://test') as client:
            image=png(Image.new('RGB',(512,512),'white'))
            async def req(feature,style):
                return await client.post(f'/{feature}/generate',data={'style_id':style},
                   files={'image':('input.png',image,'image/png')},headers={'X-API-Key':KEY})
            assert (await req('makeup','natural_makeup')).status_code==503
            assert owner.ready and owner.active=='hairstyle:train001'
            assert (await req('hairstyle','crew_cut')).status_code==200
    asyncio.run(check())


def test_inference_failure_fails_closed(fake_server):
    owner,_,views,_=fake_server
    views['hairstyle'].fail=True
    async def check():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=server.app),base_url='http://test') as client:
            image=png(Image.new('RGB',(512,512),'white'))
            response=await client.post('/hairstyle/generate',data={'style_id':'crew_cut'},
                files={'image':('input.png',image,'image/png')},headers={'X-API-Key':KEY})
            assert response.status_code==500 and '/tmp/private' not in response.text
            assert not owner.ready
    asyncio.run(check())


def test_disconnection_cannot_release_gpu_owner(fake_server):
    owner,pipe,views,_=fake_server
    entered,released=threading.Event(),threading.Event()
    views['hairstyle'].gate_event,views['hairstyle'].release=entered,released
    async def check():
        image=Image.new('RGB',(512,512),'white')
        first=asyncio.create_task(owner.generate('hairstyle:train001','first',image=image,style_id='crew_cut'))
        while not entered.is_set():
            await asyncio.sleep(.01)
        first.cancel()
        second=asyncio.create_task(owner.generate('makeup','second',image=image,style_id='natural_makeup'))
        await asyncio.sleep(.05)
        assert not second.done() and owner.active=='hairstyle:train001'
        released.set()
        result=await asyncio.gather(first,second,return_exceptions=True)
        assert isinstance(result[0],asyncio.CancelledError)
        assert result[1]['metadata']['feature']=='makeup'
    asyncio.run(check())


def test_http_competing_request_is_busy_without_switching(fake_server):
    owner,_,views,_=fake_server
    entered,released=threading.Event(),threading.Event()
    views['hairstyle'].gate_event,views['hairstyle'].release=entered,released
    image=png(Image.new('RGB',(512,512),'white'))
    async def check():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=server.app),base_url='http://test') as client:
            def req(feature,style):
                return client.post(f'/{feature}/generate',data={'style_id':style},
                   files={'image':('input.png',image,'image/png')},headers={'X-API-Key':KEY})
            first=asyncio.create_task(req('hairstyle','crew_cut'))
            while not entered.is_set():
                await asyncio.sleep(.01)
            second=await req('makeup','natural_makeup')
            assert second.status_code==429 and owner.active=='hairstyle:train001'
            released.set()
            assert (await first).status_code==200
            assert (await req('makeup','natural_makeup')).status_code==200
    asyncio.run(check())


def test_missing_enabled_hair_adapter_fails_at_preflight(monkeypatch):
    altered={**server.REGISTRY,'adapters':{**server.REGISTRY['adapters'],
        'train002':{'status':'enabled'}}}
    monkeypatch.setattr(server,'REGISTRY',altered)
    monkeypatch.delenv('AI_HAIR_ADAPTER_DIRS',raising=False)
    with pytest.raises(ValueError,match='do not match'):
        server.adapter_configuration()


def test_configuration_uses_one_url_and_explicit_rollback(monkeypatch):
    monkeypatch.setenv('AI_REMOTE_URL','https://one.example/')
    monkeypatch.setenv('AI_REMOTE_API_KEY',KEY)
    monkeypatch.setenv('FLUX_REMOTE_URL','https://old.example')
    assert destination('hairstyle','FLUX_REMOTE_URL','FLUX_REMOTE_API_KEY')==('https://one.example/hairstyle',KEY)
    assert destination('makeup','MAKEUP_REMOTE_URL','MAKEUP_REMOTE_API_KEY')==('https://one.example/makeup',KEY)
    assert destination('nails','NAILS_REMOTE_URL','NAILS_REMOTE_API_KEY')==('https://one.example/nails',KEY)
    monkeypatch.delenv('AI_REMOTE_API_KEY')
    with pytest.raises(RuntimeError,match='both'):
        destination('hairstyle','FLUX_REMOTE_URL','FLUX_REMOTE_API_KEY')
    monkeypatch.delenv('AI_REMOTE_URL')
    assert destination('hairstyle','FLUX_REMOTE_URL','FLUX_REMOTE_API_KEY')[0]=='https://old.example'


def test_base_initializes_once_and_health_reports_ready(tmp_path,monkeypatch):
    import app.nails.contract as nails_contract
    import json
    import types
    actual_root=ROOT
    review=json.loads((actual_root/'docs/experiments/unified-kaggle-gate1-review.json').read_text())
    folder=tmp_path/'docs/experiments'
    folder.mkdir(parents=True)
    (folder/'unified-kaggle-gate1-review.json').write_text(json.dumps(review))
    model=tmp_path/gate.REVISION
    model.mkdir()
    (model/'model_index.json').write_text('{}')
    monkeypatch.setenv('AI_MODEL_DIR',str(model))
    monkeypatch.setenv('AI_REMOTE_API_KEY',KEY)
    hair_dir=tmp_path/'gate1/adapters/hairstyle'
    makeup_dir=tmp_path/'gate1/adapters/makeup'
    nails_dir=tmp_path/'gate1/adapters/nails'
    for path in (hair_dir,makeup_dir,nails_dir):
        path.mkdir(parents=True)
    hair_file=hair_dir/'adapter.safetensors'
    hair_file.write_bytes(b'hair')
    (makeup_dir/'adapter.safetensors').write_bytes(b'makeup')
    (nails_dir/'nails001_local_v1.safetensors').write_bytes(b'nails')
    metadata={'checkpoint_sha256':gate.digest(hair_file),'training_steps':250,
              'experiment':'TRAIN-001','supported_style_ids':list(server.HAIR_STYLES),
              'base_model_id':gate.MODEL_ID,'base_model_revision':gate.REVISION}
    monkeypatch.setattr(server,'ROOT',tmp_path)
    monkeypatch.setattr(server,'adapter_configuration',lambda: {'train001':(hair_dir,metadata)})
    monkeypatch.setattr(server,'read_adapter_metadata',lambda *args: metadata)
    monkeypatch.setattr(server,'verify_makeup',lambda _:None)
    monkeypatch.setattr(nails_contract,'verify_adapter',lambda _:None)
    original_digest=gate.digest
    monkeypatch.setattr(gate,'digest',lambda path:review['base_model_index_sha256']
                         if Path(path).name=='model_index.json' else original_digest(path))
    monkeypatch.setattr(gate,'memory',lambda _: {})
    pipe=FakePipe()
    loads=[]
    def from_pretrained(path,**kwargs):
        loads.append(path)
        return pipe
    fake_cuda=SimpleNamespace(is_available=lambda:True,synchronize=lambda _:None)
    fake_torch=types.SimpleNamespace(float16='fp16',cuda=fake_cuda)
    fake_diffusers=types.SimpleNamespace(Flux2KleinPipeline=SimpleNamespace(from_pretrained=from_pretrained))
    monkeypatch.setitem(sys.modules,'torch',fake_torch)
    monkeypatch.setitem(sys.modules,'diffusers',fake_diffusers)
    monkeypatch.setattr(server,'inspect_adapter',lambda actual,path,name:{
        'library_adapter_name':'default_0','tensor_equality_verified':True,
        'converted_tensor_sha256':original_digest(path),'tensor_count':200,'verified_layer_count':100})
    runtime=server.UnifiedRuntime()
    runtime.load()
    assert len(loads)==1 and runtime.foundation_load_count==1
    assert runtime.health()['gpu_runtime_ready'] and runtime.health()['active_feature']=='hairstyle'
    assert runtime.health()['active_adapter']=='train001'


def test_unready_health_after_initialization_failure(monkeypatch):
    candidate=server.UnifiedRuntime()
    def failed_load():
        raise RuntimeError('private Base initialization detail')
    monkeypatch.setattr(candidate,'load',failed_load)
    monkeypatch.setattr(server,'runtime',candidate)
    async def check():
        async with server.lifespan(server.app):
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=server.app),base_url='http://test') as client:
                response=await client.get('/health')
                assert response.status_code==200
                assert response.json()['status']=='unready'
                assert response.json()['base_model_loaded'] is False
                assert 'private' not in response.text
    asyncio.run(check())


def test_http_handler_cancellation_drains_before_releasing_owner(fake_server):
    owner,_,views,_=fake_server
    entered,released=threading.Event(),threading.Event()
    views['hairstyle'].gate_event,views['hairstyle'].release=entered,released
    image=png(Image.new('RGB',(512,512),'white'))
    async def check():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=server.app),base_url='http://test') as client:
            def req(feature,style):
                return client.post(f'/{feature}/generate',data={'style_id':style},
                    files={'image':('input.png',image,'image/png')},headers={'X-API-Key':KEY})
            first=asyncio.create_task(req('hairstyle','crew_cut'))
            while not entered.is_set():
                await asyncio.sleep(.01)
            first.cancel()
            await asyncio.sleep(.01)
            first.cancel()
            assert (await req('makeup','natural_makeup')).status_code==429
            assert owner.owner.locked() and owner.active=='hairstyle:train001'
            released.set()
            result=await asyncio.gather(first,return_exceptions=True)
            assert isinstance(result[0],asyncio.CancelledError)
            assert not owner.owner.locked()
            assert (await req('makeup','natural_makeup')).status_code==200
    asyncio.run(check())


def test_central_application_uses_one_remote_root_and_renderer_stays_local(monkeypatch):
    scenario=CentralRemoteScenario()
    calls=[]
    real_async=httpx.AsyncClient
    def transport(request):
        feature=request.url.path.strip('/').split('/')[0]
        assert request.url.host=='unified.inference.invalid'
        assert request.url.path==f'/{feature}/generate'
        assert request.headers['X-API-Key']==KEY
        from email.parser import BytesParser
        from email.policy import default
        envelope=BytesParser(policy=default).parsebytes(b'Content-Type: '+request.headers['content-type'].encode()+b'\r\n\r\n'+request.content)
        fields={part.get_param('name',header='content-disposition'):part.get_payload(decode=True) for part in envelope.iter_parts()}
        style=fields['style_id'].decode()
        calls.append((feature,style))
        if feature=='makeup' and style=='soft_glam':
            return httpx.Response(503)
        return httpx.Response(200,json=scenario.response(feature,style))
    def client(*args,**kwargs):
        return real_async(*args,**kwargs,transport=httpx.MockTransport(transport))
    with scenario.installed():
        monkeypatch.setenv('AI_REMOTE_URL','https://unified.inference.invalid')
        monkeypatch.setenv('AI_REMOTE_API_KEY',KEY)
        monkeypatch.setattr(main,'engine',RemoteFluxEngine(*destination('hairstyle','FLUX_REMOTE_URL','FLUX_REMOTE_API_KEY')))
        monkeypatch.setattr(main,'makeup_engine',RemoteMakeupEngine(*destination('makeup','MAKEUP_REMOTE_URL','MAKEUP_REMOTE_API_KEY')))
        main._nails_pipeline.model=RemoteLocalizedNails(*destination('nails','NAILS_REMOTE_URL','NAILS_REMOTE_API_KEY'))
        with patch.object(httpx,'AsyncClient',client):
            test=TestClient(main.app)
            image=png(scenario.source)
            def app_request(feature,style):
                return test.post(f'/features/{feature}/generate',data={'style_id':style},
                    files={'image':('input.png',image,'image/png')})
            assert app_request('hairstyle','crew_cut').status_code==200
            assert app_request('makeup','natural_makeup').status_code==200
            assert app_request('nails','classic_red').status_code==200
            assert len([r for r in calls if r[0]=='nails'])==5
            before=len(calls)
            renderer=app_request('nails','nude_pink')
            assert renderer.status_code==200 and renderer.json()['metadata']['inference_path']=='renderer'
            assert len(calls)==before
            assert app_request('makeup','soft_glam').status_code==502
            assert calls[0][0]=='hairstyle' and calls[1][0]=='makeup'


def test_central_application_reaches_actual_unified_http_routes_with_fake_gpu(fake_server,monkeypatch):
    owner,_,_,_=fake_server
    scenario=CentralRemoteScenario()
    real_async=httpx.AsyncClient
    def local_unified_client(*args,**kwargs):
        return real_async(*args,**kwargs,transport=httpx.ASGITransport(app=server.app))
    with scenario.installed():
        monkeypatch.setenv('AI_REMOTE_URL','https://unified.inference.invalid')
        monkeypatch.setenv('AI_REMOTE_API_KEY',KEY)
        monkeypatch.setattr(main,'engine',RemoteFluxEngine(*destination('hairstyle','FLUX_REMOTE_URL','FLUX_REMOTE_API_KEY')))
        monkeypatch.setattr(main,'makeup_engine',RemoteMakeupEngine(*destination('makeup','MAKEUP_REMOTE_URL','MAKEUP_REMOTE_API_KEY')))
        main._nails_pipeline.model=RemoteLocalizedNails(*destination('nails','NAILS_REMOTE_URL','NAILS_REMOTE_API_KEY'))
        with patch.object(httpx,'AsyncClient',local_unified_client):
            client=TestClient(main.app)
            source=png(scenario.source)
            def request(feature,style):
                return client.post(f'/features/{feature}/generate',data={'style_id':style},
                    files={'image':('input.png',source,'image/png')})
            for feature,style in [('hairstyle','crew_cut'),('makeup','natural_makeup'),
                                  ('nails','classic_red'),('hairstyle','crew_cut')]:
                response=request(feature,style)
                assert response.status_code==200,(feature,style,response.text)
                assert response.json()['style']['id']==style
            count=len(owner.audit)
            assert count==8  # one Hair, one Makeup, five Nails crops, restored Hair
            renderer=request('nails','nude_pink')
            assert renderer.status_code==200 and renderer.json()['metadata']['inference_path']=='renderer'
            assert len(owner.audit)==count
            assert [row['feature'] for row in owner.audit]==[
                'hairstyle','makeup','nails','nails','nails','nails','nails','hairstyle']
