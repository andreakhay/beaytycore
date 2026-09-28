"""Signed, temporary endpoint mailbox. No keys or images are published."""

from hashlib import sha256
import hmac
import json
import re
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, HTTPRedirectHandler, build_opener
from uuid import UUID, uuid4

BUNDLE_NAME = 'deployment01_20260928_v2.bin'
BUNDLE_SHA = '68f6c9eb2bc0ce12b2c9c6d89e33f22898fb201b33a792887f6c5967ad16ec4e'
REVISION = 'a3b4f4849157f664bdbc776fd7453c2783562f4d'
VERSION = 'deployment-01'
FEATURES = {'hairstyle', 'makeup', 'nails'}
SCHEMA = 'capstone-discovery-v1'
TTL = 4 * 60 * 60
SERVICE = 'https://ntfy.sh'


class StartupError(RuntimeError):
    """Only safe, operator-facing messages belong here."""


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def request(url, *, body=None, headers=None):
    try:
        with build_opener(NoRedirect()).open(Request(url, data=body, headers=headers or {}), timeout=20) as response:
            raw = response.read(65537)
            if len(raw) > 65536:
                raise StartupError('Response exceeds discovery limit')
            return raw
    except HTTPError as exc:
        raise StartupError(f'HTTP {exc.code}; no automatic fallback') from None
    except (URLError, TimeoutError, OSError):
        raise StartupError('Connection failed; check Internet and current session') from None


def key_bytes(key):
    if not isinstance(key, str) or len(key) < 24:
        raise StartupError('Configure the same AI_REMOTE_API_KEY locally and in Kaggle Secrets')
    return key.encode()


def topic(key):
    return 'capstone-' + hmac.new(key_bytes(key), b'capstone-topic-v1', sha256).hexdigest()[:32]


def canonical(record):
    return json.dumps(record, sort_keys=True, separators=(',', ':')).encode()


def sign(record, key):
    signing_key = hmac.new(key_bytes(key), b'capstone-record-v1', sha256).digest()
    return hmac.new(signing_key, canonical(record), sha256).hexdigest()


def endpoint(url):
    if not isinstance(url, str):
        raise StartupError('Invalid endpoint')
    p = urlsplit(url)
    if (p.scheme != 'https' or p.username or p.password or p.query or p.fragment
            or p.path.rstrip('/') or p.netloc != p.hostname
            or not re.fullmatch(r'[a-z0-9-]+\.trycloudflare\.com', p.hostname or '')):
        raise StartupError('Expected an HTTPS Quick Tunnel server root, without credentials or paths')
    return url.rstrip('/')


def make_record(key, status, url=None, now=None):
    now = int(time.time() if now is None else now)
    record = {'schema': SCHEMA, 'publication_id': str(uuid4()), 'published_at': now,
              'expires_at': now + TTL, 'status': status, 'worker_version': VERSION,
              'bundle_sha256': BUNDLE_SHA}
    if status == 'ready':
        record['endpoint'] = endpoint(url)
    elif status not in ('starting', 'failed'):
        raise StartupError('Invalid publication state')
    return {**record, 'signature': sign(record, key)}


def validate_record(record, key, now=None):
    if not isinstance(record, dict):
        raise StartupError('Invalid discovery record')
    unsigned = {k: v for k, v in record.items() if k != 'signature'}
    signature = record.get('signature')
    if not isinstance(signature, str) or not hmac.compare_digest(signature, sign(unsigned, key)):
        raise StartupError('Discovery signature failed; no older-record fallback')
    allowed = {'schema', 'publication_id', 'published_at', 'expires_at', 'status',
               'worker_version', 'bundle_sha256', 'endpoint', 'signature'}
    if set(record) - allowed or record.get('schema') != SCHEMA or record.get('worker_version') != VERSION or record.get('bundle_sha256') != BUNDLE_SHA:
        raise StartupError('Wrong discovery schema/runtime/bundle')
    try:
        UUID(record['publication_id'])
        now = int(time.time() if now is None else now)
        start, expiry = record['published_at'], record['expires_at']
        if type(start) is not int or type(expiry) is not int or start > now + 90 or expiry - start != TTL or now >= expiry:
            raise ValueError()
    except (KeyError, TypeError, ValueError, AttributeError):
        raise StartupError('Discovery record is stale or has invalid publication identity') from None
    if record.get('status') != 'ready':
        raise StartupError('Latest Kaggle publication is not ready; run START CAPSTONE and wait')
    return endpoint(record.get('endpoint'))


def publish(record, key):
    response = json.loads(request(SERVICE + '/' + topic(key), body=canonical(record),
                        headers={'Content-Type': 'text/plain; charset=utf-8'}))
    if response.get('event') != 'message' or response.get('message') != canonical(record).decode():
        raise StartupError('Publication was not acknowledged')


def discover(key):
    try:
        raw = request(SERVICE + '/' + topic(key) + '/json?poll=1&since=latest')
        messages = [v for line in raw.splitlines() if (v := json.loads(line)).get('event') == 'message']
        if not messages:
            raise StartupError('No endpoint published; run START CAPSTONE in Kaggle')
        record = json.loads(messages[-1]['message'])
        return validate_record(record, key), record
    except (ValueError, KeyError, TypeError, AttributeError):
        raise StartupError('Discovery returned an invalid record; no older-record fallback') from None


def verify_health(value):
    if not isinstance(value, dict) or not (
            value.get('status') == 'ready' and value.get('gpu_runtime_ready') is True
            and value.get('base_model_loaded') is True and type(value.get('foundation_load_count')) is int
            and value['foundation_load_count'] == 1 and value.get('base_model_revision') == REVISION
            and value.get('diagnostics_version') == VERSION and value.get('gpu_busy') is False):
        raise StartupError('Wrong, busy or unready worker; expected verified Base count one')
    if not isinstance(value.get('supported_features'), list) or not FEATURES <= set(value['supported_features']):
        raise StartupError('Worker is missing Hair/Makeup/Nails support')
    return value


def verify_worker(url, key):
    url = endpoint(url)
    try:
        health = verify_health(json.loads(request(url + '/health')))
        verify_health(json.loads(request(url + '/status', headers={'X-API-Key': key})))
        return health
    except (ValueError, TypeError, AttributeError):
        raise StartupError('Worker returned malformed readiness') from None
