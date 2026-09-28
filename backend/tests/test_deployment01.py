"""Deployment readiness and transport diagnostics, fake HTTP/GPU boundaries."""

import asyncio
import json
from types import SimpleNamespace
from uuid import UUID

import httpx
import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app import deployment, main
from app.generation.diagnostics import current, scope
from app.generation.remote_http import observed_request
from app.nails.geometry import ReviewedMaskSegmenter
from app.nails.hybrid import HybridNailsPipeline
from app.nails.remote import NailsGenerationError, RemoteLocalizedNails
from app.nails.styles import NAIL_STYLE_BY_ID
from test_nails_hybrid import hand_fixture
from test_unified_gate3 import fake_server, post, KEY, server

URL = 'https://demo.invalid'
CORRELATION = 'cbf85d0d-4fab-4927-8d64-9d4f71598032'


def logs(caplog):
    return [json.loads(row.message) for row in caplog.records if row.name == 'ai_transport']


@pytest.mark.parametrize('error,expected', [
    (httpx.ConnectError, 'connection_failure'), (httpx.ConnectTimeout, 'connect_timeout'),
    (httpx.ReadTimeout, 'read_timeout'), (httpx.WriteTimeout, 'write_timeout'),
    (httpx.PoolTimeout, 'pool_timeout'), (httpx.RemoteProtocolError, 'ambiguous_disconnect'),
    (httpx.ReadError, 'ambiguous_disconnect'), (httpx.WriteError, 'ambiguous_disconnect'),
])
def test_failure_classification_and_no_retry(error, expected, caplog):
    calls = []
    def handler(request):
        calls.append(request)
        raise error('PRIVATE_API_KEY private/path https://credential:secret@private.invalid')
    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            with scope(correlation_id=CORRELATION, crop_index=3, finger_id='middle'):
                with pytest.raises(error):
                    await observed_request(client, 'post', URL, feature='nails', style_id='classic_red',
                                           headers={'X-API-Key': 'PRIVATE_API_KEY'}, content=b'PRIVATE_IMAGE')
    asyncio.run(run())
    row = logs(caplog)[-1]
    assert len(calls) == 1 and row['category'] == expected and row['automatic_retry'] is False
    assert row['crop_index'] == 3 and row['finger_id'] == 'middle'
    assert row['remote_acceptance'] == 'unknown' and row['response_headers_received'] is False
    assert row['correlation_id'] == CORRELATION
    UUID(calls[0].headers['X-Request-ID'])
    assert calls[0].headers['X-Nails-Crop-Index'] == '3'
    assert calls[0].headers['X-Nails-Finger'] == 'middle'
    assert all(secret not in caplog.text for secret in ('PRIVATE_API_KEY', 'PRIVATE_IMAGE', 'private/path', URL))


@pytest.mark.parametrize('status,expected', [(400, 'validation_or_auth'), (401, 'validation_or_auth'),
    (422, 'validation_or_auth'), (429, 'busy'), (500, 'remote_http_error'), (503, 'remote_http_error')])
def test_http_status_never_retried(status, expected, caplog):
    calls = []
    def handler(request):
        calls.append(request)
        return httpx.Response(status, text='PRIVATE_RAW_BODY')
    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await observed_request(client, 'post', URL, feature='nails', style_id='classic_red')
    assert asyncio.run(run()).status_code == status
    row = logs(caplog)[-1]
    assert len(calls) == 1 and row['category'] == expected
    assert row['response_headers_received'] and row['response_body_received']
    assert row['automatic_retry'] is False and 'PRIVATE_RAW_BODY' not in caplog.text


def test_body_failure_after_headers_is_distinct(caplog):
    class BrokenBody(httpx.AsyncByteStream):
        async def __aiter__(self):
            yield b'partial'
            raise httpx.ReadError('PRIVATE_EXCEPTION')
    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(
                lambda _: httpx.Response(200, stream=BrokenBody()))) as client:
            with pytest.raises(httpx.ReadError):
                await observed_request(client, 'post', URL, feature='nails', style_id='classic_red')
    asyncio.run(run())
    row = logs(caplog)[-1]
    assert row['http_status'] == 200 and row['response_headers_received'] is True
    assert row['response_body_received'] is False and row['automatic_retry'] is False


def test_preflight_records_its_actual_timeout(caplog):
    def handler(request):
        assert request.extensions['timeout']['read'] == 10
        return httpx.Response(200, json={})
    async def run():
        async with httpx.AsyncClient(timeout=300, transport=httpx.MockTransport(handler)) as client:
            await observed_request(client, 'get', URL, feature='nails', style_id='health',
                                   boundary='step_preflight', timeout=10)
    asyncio.run(run())
    start = next(row for row in logs(caplog) if row['event'] == 'remote_start')
    assert start['boundary'] == 'step_preflight' and start['timeout_seconds'] == 10


def test_generated_notebook_and_sources_match_verified_bundle():
    from pathlib import Path
    from hashlib import sha256
    from scripts.package_deployment01 import notebook
    root = Path(__file__).resolve().parents[2]
    report = json.loads((root / 'docs/experiments/deployment01-bundle.json').read_text())
    saved = json.loads((root / 'notebooks/deployment01_kaggle.ipynb').read_text())
    assert saved == notebook(report)
    for index, cell in enumerate(saved['cells'], 1):
        compile(''.join(cell['source']), f'cell-{index}', 'exec')
        assert not cell['outputs']
    assert 'assert health.get("diagnostics_version") == "deployment-01"' in ''.join(saved['cells'][2]['source'])
    for name, digest in report['source_hashes'].items():
        # Bundle sources use LF; Windows Git may check them out as CRLF.
        assert sha256((root / name).read_bytes().replace(b'\r\n', b'\n')).hexdigest() == digest


def test_crop_diagnostics_and_renderer_bypass(caplog):
    source, mask, hand = hand_fixture()
    calls = []
    class Localizer:
        def locate(self, _): return hand
    class Model:
        async def generate(self, image, style):
            calls.append(current())
            if len(calls) == 3:
                raise NailsGenerationError('Controlled third crop failure')
            return Image.new('RGB', (512, 512), 'red')
    pipeline = HybridNailsPipeline(Localizer(), ReviewedMaskSegmenter(mask), Model())
    with scope(correlation_id=CORRELATION):
        with pytest.raises(NailsGenerationError):
            asyncio.run(pipeline.run(source, NAIL_STYLE_BY_ID['classic_red']))
        assert asyncio.run(pipeline.run(source, NAIL_STYLE_BY_ID['nude_pink'])).path == 'renderer'
    assert [row['crop_index'] for row in calls] == [1, 2, 3]
    assert all(row['correlation_id'] == CORRELATION and row['crop_count'] == 5 for row in calls)
    failure = next(row for row in logs(caplog) if row['event'] == 'nails_crop_failed')
    assert failure['crop_index'] == 3 and failure['finger_id'] in ('thumb', 'index', 'middle', 'ring', 'little')


def valid_env(monkeypatch):
    for name, value in {'AI_REMOTE_URL': URL, 'AI_REMOTE_API_KEY': KEY,
                        'GENERATION_ENGINE': 'remote_flux', 'MAKEUP_GENERATION_ENGINE': 'remote_makeup',
                        'NAILS_PREVIEW_MODE': 'hybrid', 'NAILS_INFERENCE_STEPS': '8'}.items():
        monkeypatch.setenv(name, value)


def ready_report():
    return {'status': 'ready', 'gpu_runtime_ready': True, 'base_model_loaded': True,
            'foundation_load_count': 1, 'base_model_revision': deployment.MODEL_REVISION,
            'supported_features': ['hairstyle', 'makeup', 'nails'], 'gpu_busy': False,
            'diagnostics_version': 'deployment-01', 'nails_inference_steps': [8, 12, 20]}


@pytest.mark.parametrize('change', [None, 'wrong_key', 'busy', 'wrong_base_count', 'missing_feature', 'old_worker'])
def test_readiness_checks_configuration_auth_and_runtime(monkeypatch, change):
    valid_env(monkeypatch)
    report = ready_report()
    if change == 'busy': report['gpu_busy'] = True
    if change == 'wrong_base_count': report['foundation_load_count'] = 2
    if change == 'missing_feature': report['supported_features'] = ['hairstyle', 'makeup']
    if change == 'old_worker': report.pop('diagnostics_version')
    calls = []
    def handler(request):
        calls.append(request.url.path)
        assert request.method == 'GET'
        return httpx.Response(401 if change == 'wrong_key' and request.url.path == '/status' else 200, json=report)
    real = httpx.AsyncClient
    monkeypatch.setattr(httpx, 'AsyncClient', lambda **kwargs: real(**kwargs, transport=httpx.MockTransport(handler)))
    hair = SimpleNamespace(url=URL + '/hairstyle', api_key=KEY)
    makeup = SimpleNamespace(url=URL + '/makeup', api_key=KEY)
    result = asyncio.run(deployment.check_readiness(hair, makeup))
    assert result['ready'] is (change is None)
    assert calls == ['/health', '/status']
    assert KEY not in json.dumps(result) and URL not in json.dumps(result)


@pytest.mark.parametrize('bad', ['missing', 'credentials_url', 'query_url', 'mock_mode', 'stale_client'])
def test_bad_readiness_configuration_no_remote_call(monkeypatch, bad):
    valid_env(monkeypatch)
    hair = SimpleNamespace(url=URL + '/hairstyle', api_key=KEY)
    makeup = SimpleNamespace(url=URL + '/makeup', api_key=KEY)
    if bad == 'missing': monkeypatch.delenv('AI_REMOTE_API_KEY')
    if bad == 'credentials_url': monkeypatch.setenv('AI_REMOTE_URL', 'https://secret:secret@demo.invalid')
    if bad == 'query_url': monkeypatch.setenv('AI_REMOTE_URL', URL + '?token=secret')
    if bad == 'mock_mode': monkeypatch.setenv('GENERATION_ENGINE', 'mock')
    if bad == 'stale_client': hair.url = 'https://old.invalid/hairstyle'
    monkeypatch.setattr(httpx, 'AsyncClient', lambda **kwargs: pytest.fail('Invalid config reached remote'))
    result = asyncio.run(deployment.check_readiness(hair, makeup))
    assert not result['ready'] and result['reason'] == 'configuration_incomplete_or_stale'


def test_central_and_worker_identity_propagation(fake_server, caplog):
    owner, _, _, _ = fake_server
    server.HTTP_RECORDS.clear()
    client = TestClient(server.app)
    image = Image.new('RGB', (512, 512), 'white')
    from central_remote_fixture import png
    response = client.post('/nails/generate', data={'style_id': 'classic_red'},
        files={'image': ('crop.png', png(image), 'image/png')},
        headers={'X-API-Key': KEY, 'X-Correlation-ID': CORRELATION,
                 'X-Request-ID': CORRELATION, 'X-Nails-Crop-Index': '4', 'X-Nails-Finger': 'ring'})
    assert response.status_code == 200
    assert response.headers['X-Correlation-ID'] == CORRELATION
    assert owner.audit[-1]['correlation_id'] == CORRELATION
    assert owner.audit[-1]['crop_index'] == 4 and owner.audit[-1]['finger_id'] == 'ring'
    assert server.HTTP_RECORDS[-1]['state'] == 'completed'
    assert server.HTTP_RECORDS[-1]['request_id'] == CORRELATION
    central = TestClient(main.app).post('/features/nails/generate', data={'style_id': 'invalid'},
                                      files={'image': ('hand.png', png(image), 'image/png')},
                                      headers={'X-Correlation-ID': 'unsafe/private/path'})
    assert central.status_code == 400
    UUID(central.headers['X-Correlation-ID'])
    assert 'unsafe/private/path' not in caplog.text


def test_missing_status_history_is_not_safe_retry(monkeypatch):
    valid_env(monkeypatch)
    real = httpx.AsyncClient
    report = {**ready_report(), 'requests': [], 'http_requests': []}
    monkeypatch.setattr(httpx, 'AsyncClient', lambda **kwargs: real(**kwargs,
        transport=httpx.MockTransport(lambda _: httpx.Response(200, json=report))))
    result = asyncio.run(deployment.diagnose(CORRELATION))
    assert result['records'] == [] and result['absence_does_not_prove_not_accepted'] is True
    assert result['automatic_retry'] is False


@pytest.mark.parametrize('error,reason', [(httpx.ConnectError, 'connection_failure'),
                                       (httpx.ReadTimeout, 'read_timeout')])
def test_readiness_transport_error_is_safe_and_clear(monkeypatch, error, reason):
    valid_env(monkeypatch)
    real = httpx.AsyncClient
    def fail(_): raise error('PRIVATE_KEY_AND_URL')
    monkeypatch.setattr(httpx, 'AsyncClient', lambda **kwargs: real(**kwargs, transport=httpx.MockTransport(fail)))
    result = asyncio.run(deployment.check_readiness(SimpleNamespace(url=URL+'/hairstyle', api_key=KEY),
                                                  SimpleNamespace(url=URL+'/makeup', api_key=KEY)))
    assert result == {'ready': False, 'reason': reason}


def test_demo_cli_reads_running_backend_and_preserves_existing_evidence(tmp_path, monkeypatch, capsys):
    from scripts import demo_readiness
    from io import BytesIO
    output = tmp_path / 'check.json'
    monkeypatch.setattr('sys.argv', ['demo_readiness.py', '--output', str(output)])
    seen = []
    def response(url, timeout):
        seen.append(url)
        return BytesIO(json.dumps({'ready': True, 'foundation_load_count': 1}).encode())
    monkeypatch.setattr(demo_readiness, 'urlopen', response)
    assert demo_readiness.main() == 0
    assert seen == ['http://127.0.0.1:8000/deployment/readiness']
    with pytest.raises(SystemExit): demo_readiness.main()
    assert json.loads(output.read_text())['ready'] is True


@pytest.mark.parametrize('failure', [False, True])
def test_rehearsal_is_bounded_and_stops_without_retry(tmp_path, monkeypatch, failure):
    from scripts import deployment01_smoke
    from central_remote_fixture import png
    image = tmp_path / 'input.png'
    image.write_bytes(png(Image.new('RGB', (512, 512), 'white')))
    output = tmp_path / 'out'
    monkeypatch.setattr('sys.argv', ['deployment01_smoke.py', '--hair', str(image), '--makeup', str(image),
                                    '--hand', str(image), '--output', str(output)])
    calls, gpu = [], [0]
    class FakeClient:
        def __init__(self, **kwargs): pass
        def __enter__(self): return self
        def __exit__(self, *_): pass
        def get(self, path):
            report = ({'ready': True} if path.endswith('readiness') else
                      {'available': True, 'successful_gpu_request_count': gpu[0], 'records': []})
            return httpx.Response(200, json=report, request=httpx.Request('GET', URL))
        def post(self, path, data, files):
            calls.append(data['style_id'])
            if failure and data['style_id'] == 'classic_red':
                return httpx.Response(502, headers={'X-Correlation-ID': CORRELATION})
            gpu[0] += 5 if data['style_id'] == 'classic_red' else 0 if data['style_id'] == 'nude_pink' else 1
            return httpx.Response(200, json={'status': 'completed', 'generator': 'fake',
                'style': {'id': data['style_id']}, 'metadata': {'nails_edited': 5, 'inference_path': 'renderer' if
                    data['style_id'] == 'nude_pink' else 'model', 'secret_field': 'PRIVATE_SECRET'},
                'image': {'data_url': 'PRIVATE_IMAGE'}}, headers={'X-Correlation-ID': CORRELATION})
    monkeypatch.setattr(deployment01_smoke.httpx, 'Client', FakeClient)
    assert deployment01_smoke.main() == (1 if failure else 0)
    report = json.loads((output / 'application.json').read_text())
    assert calls == (['crew_cut', 'natural_makeup', 'classic_red'] if failure else
                     ['crew_cut', 'natural_makeup', 'classic_red', 'nude_pink'])
    assert report['automatic_retries'] == 0
    assert 'PRIVATE_SECRET' not in json.dumps(report) and 'PRIVATE_IMAGE' not in json.dumps(report)
