"""Image-free pre-demo checks against the actual running backend configuration."""

import os
from urllib.parse import urlsplit

import httpx

from app.nails.contract import MODEL_REVISION
from app.nails.inference_options import configured_steps

FEATURES = {'hairstyle', 'makeup', 'nails'}


def configuration(env):
    url, key = env.get('AI_REMOTE_URL', '').strip(), env.get('AI_REMOTE_API_KEY', '').strip()
    if not url or len(key) < 24:
        raise ValueError('Set both unified URL and API key (at least 24 characters), then restart FastAPI.')
    parts = urlsplit(url)
    if (parts.scheme != 'https' or not parts.hostname or parts.username or parts.password
            or parts.query or parts.fragment or parts.path.rstrip('/')):
        raise ValueError('Unified URL must be an HTTPS server root without credentials, query or feature path.')
    modes = {'GENERATION_ENGINE': 'remote_flux', 'MAKEUP_GENERATION_ENGINE': 'remote_makeup',
             'NAILS_PREVIEW_MODE': 'hybrid'}
    if any(env.get(name, '').strip().lower() != value for name, value in modes.items()):
        raise ValueError('Enable remote_flux, remote_makeup and hybrid modes, then restart FastAPI.')
    return url.rstrip('/'), key


async def check_readiness(engine, makeup_engine, nails_pipeline=None):
    try:
        url, key = configuration(os.environ)
        steps = configured_steps()
        for feature, client in [('hairstyle', engine), ('makeup', makeup_engine),
                                ('nails', nails_pipeline.model if nails_pipeline else None)]:
            if client is not None and (getattr(client, 'url', None) != f'{url}/{feature}'
                                       or getattr(client, 'api_key', None) != key):
                raise ValueError('Running backend clients differ from unified settings; restart FastAPI.')
        if nails_pipeline and (nails_pipeline.model is None or nails_pipeline.model.inference_steps != steps):
            raise ValueError('Running Nails configuration differs; restart FastAPI.')
    except (ValueError, RuntimeError):
        return {'ready': False, 'reason': 'configuration_incomplete_or_stale',
                'action': 'Check unified URL/key, feature modes and restart FastAPI.'}
    try:
        async with httpx.AsyncClient(timeout=12, follow_redirects=False) as client:
            health = await client.get(url + '/health')
            status = await client.get(url + '/status', headers={'X-API-Key': key})
        if health.status_code != 200 or status.status_code != 200:
            return {'ready': False, 'reason': 'remote_http_or_auth', 'health_http_status': health.status_code,
                    'status_http_status': status.status_code}
        h, s = health.json(), status.json()
        valid = all(isinstance(value, dict) and value.get('status') == 'ready'
                    and value.get('gpu_runtime_ready') is True and value.get('base_model_loaded') is True
                    and value.get('foundation_load_count') == 1
                    and value.get('base_model_revision') == MODEL_REVISION
                    and FEATURES <= set(value.get('supported_features', [])) for value in (h, s))
        valid = valid and h.get('diagnostics_version') == 'deployment-01' and not h.get('gpu_busy', True)
        valid = valid and steps in h.get('nails_inference_steps', [])
        return {'ready': bool(valid), 'reason': 'ready' if valid else 'remote_unready_busy_or_wrong_version',
                'foundation_load_count': h.get('foundation_load_count'),
                'supported_features': sorted(FEATURES & set(h.get('supported_features', []))),
                'nails_inference_steps': steps, 'diagnostics_version': h.get('diagnostics_version')}
    except httpx.RequestError as exc:
        from app.generation.remote_http import category
        return {'ready': False, 'reason': category(exc)}
    except (ValueError, TypeError, AttributeError):
        return {'ready': False, 'reason': 'invalid_remote_readiness_response'}


async def diagnose(identity):
    """Read history only. Missing history never establishes safe retry."""
    try:
        url, key = configuration(os.environ)
        async with httpx.AsyncClient(timeout=12, follow_redirects=False) as client:
            response = await client.get(url + '/status', headers={'X-API-Key': key})
        if response.status_code != 200:
            return {'available': False, 'reason': 'remote_status_unavailable'}
        report = response.json()
        fields = {'request_id', 'correlation_id', 'feature', 'style_id', 'crop_index', 'finger_id',
                  'state', 'http_status', 'response_headers_sent', 'response_body_sent',
                  'disconnect_observed', 'elapsed_seconds', 'inference_seconds', 'adapter_id',
                  'adapter_sha256', 'base_revision', 'inference_steps'}
        matches = [{k: v for k, v in row.items() if k in fields} for row in
                   report.get('http_requests', []) + report.get('requests', [])
                   if identity is None or identity in (row.get('request_id'), row.get('correlation_id'))]
        return {'available': True, 'worker_ready': report.get('gpu_runtime_ready'),
                'gpu_busy': report.get('gpu_busy'), 'records': matches,
                'foundation_load_count': report.get('foundation_load_count'),
                'successful_gpu_request_count': len(report.get('requests', [])),
                'history_is_bounded': True, 'absence_does_not_prove_not_accepted': True,
                'automatic_retry': False}
    except (ValueError, TypeError, AttributeError, httpx.RequestError):
        return {'available': False, 'reason': 'configuration_or_status_unavailable', 'automatic_retry': False}
