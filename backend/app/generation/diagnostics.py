"""Safe request identity and structured boundary logs, never request contents."""

from contextlib import contextmanager
from contextvars import ContextVar
from datetime import datetime, timezone
import json
import logging
import time
from uuid import UUID, uuid4

CONTEXT = ContextVar('ai_request_context', default=None)
LOGGER = logging.getLogger('ai_transport')


def identifier(value=None):
    try:
        return str(UUID(value)) if value else str(uuid4())
    except (ValueError, TypeError, AttributeError):
        return str(uuid4())


def current():
    return dict(CONTEXT.get() or {})


@contextmanager
def scope(**values):
    token = CONTEXT.set({**current(), **values})
    try:
        yield
    finally:
        CONTEXT.reset(token)


def emit(event, **values):
    # Callers provide only allowlisted fields. Never pass exception strings/URLs.
    LOGGER.warning(json.dumps({'event': event, 'time_utc': datetime.now(timezone.utc).isoformat(),
                               **current(), **values}, sort_keys=True))


class RequestDiagnostics:
    """Pure ASGI wrapper, preserves the owner's cancellation/drain behavior."""
    def __init__(self, app, layer='central', records=None):
        self.app, self.layer, self.records = app, layer, records

    async def __call__(self, asgi_scope, receive, send):
        if asgi_scope['type'] != 'http' or asgi_scope.get('method') != 'POST':
            return await self.app(asgi_scope, receive, send)
        headers = dict(asgi_scope.get('headers', []))
        correlation = identifier(headers.get(b'x-correlation-id', b'').decode('ascii', 'ignore'))
        request_id = identifier(headers.get(b'x-request-id', b'').decode('ascii', 'ignore'))
        pieces = asgi_scope.get('path', '').split('/')
        feature = next((p for p in pieces if p in ('hairstyle', 'makeup', 'nails')), 'unknown')
        if self.layer == 'central' and pieces == ['', 'generate']:
            feature = 'hairstyle'
        record = {'request_id': request_id, 'correlation_id': correlation,
                  'feature': feature, 'state': 'accepted', 'http_status': None,
                  'response_headers_sent': False, 'response_body_sent': False,
                  'disconnect_observed': False}
        if self.layer == 'worker':
            crop = headers.get(b'x-nails-crop-index', b'').decode('ascii', 'ignore')
            finger = headers.get(b'x-nails-finger', b'').decode('ascii', 'ignore')
            if crop in ('1', '2', '3', '4', '5'):
                record['crop_index'] = int(crop)
            if finger in ('thumb', 'index', 'middle', 'ring', 'little'):
                record['finger_id'] = finger
        if self.records is not None:
            self.records.append(record)
            del self.records[:-60]
        started = time.monotonic()

        async def observed_receive():
            message = await receive()
            if message['type'] == 'http.disconnect':
                record['disconnect_observed'] = True
            return message

        async def observed_send(message):
            if message['type'] == 'http.response.start':
                record['http_status'] = message['status']
                message = dict(message)
                message['headers'] = list(message.get('headers', [])) + [
                    (b'x-request-id', request_id.encode()), (b'x-correlation-id', correlation.encode())]
            await send(message)
            if message['type'] == 'http.response.start':
                record['response_headers_sent'] = True
            elif message['type'] == 'http.response.body' and not message.get('more_body', False):
                record['response_body_sent'] = True

        with scope(**{k: record[k] for k in ('request_id', 'correlation_id', 'feature', 'crop_index', 'finger_id') if k in record}):
            emit('request_start', layer=self.layer)
            try:
                await self.app(asgi_scope, observed_receive, observed_send)
                record['state'] = 'completed' if record['http_status'] and record['http_status'] < 400 else 'rejected'
            except BaseException as exc:
                record['state'] = 'cancelled' if type(exc).__name__ == 'CancelledError' else 'failed'
                record['exception_type'] = type(exc).__name__
                raise
            finally:
                record['elapsed_seconds'] = round(time.monotonic() - started, 3)
                emit('request_end', layer=self.layer, **{k: v for k, v in record.items()
                     if k not in ('request_id', 'correlation_id', 'feature')})
