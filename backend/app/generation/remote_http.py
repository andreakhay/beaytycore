"""One HTTP attempt with diagnostics. No retries or inferred acceptance state."""

import time

import httpx

from app.generation.diagnostics import current, emit, identifier, scope


def category(exc):
    if isinstance(exc, httpx.TimeoutException):
        return {'ConnectTimeout': 'connect_timeout', 'ReadTimeout': 'read_timeout',
                'WriteTimeout': 'write_timeout', 'PoolTimeout': 'pool_timeout'}.get(type(exc).__name__, 'timeout')
    if isinstance(exc, httpx.ConnectError):
        return 'connection_failure'
    if isinstance(exc, (httpx.RemoteProtocolError, httpx.ReadError, httpx.WriteError)):
        return 'ambiguous_disconnect'
    return 'transport_failure'


async def observed_request(client, method, url, *, feature, style_id, boundary='inference', **kwargs):
    request_id = identifier()
    correlation = current().get('correlation_id') or identifier()
    headers = dict(kwargs.pop('headers', {}))
    headers.update({'X-Request-ID': request_id, 'X-Correlation-ID': correlation})
    if current().get('crop_index'):
        headers['X-Nails-Crop-Index'] = str(current()['crop_index'])
        headers['X-Nails-Finger'] = current()['finger_id']
    started = time.monotonic()
    state = {'response_headers_received': False, 'response_body_received': False, 'http_status': None}

    async def on_response(response):
        state.update(response_headers_received=True, http_status=response.status_code)

    # HTTPX runs this hook before it buffers the body, so partial reads remain distinct.
    client.event_hooks['response'].append(on_response)
    effective_timeout = kwargs.get('timeout', client.timeout)
    timeout_seconds = (effective_timeout.read if isinstance(effective_timeout, httpx.Timeout)
                       else effective_timeout)
    with scope(request_id=request_id, correlation_id=correlation, feature=feature,
               style_id=style_id, attempt=1):
        emit('remote_start', boundary=boundary, destination='configured_remote', timeout_seconds=timeout_seconds)
        try:
            response = await getattr(client, method)(url, headers=headers, **kwargs)
            state.update(response_headers_received=True, response_body_received=True, http_status=response.status_code)
            status = response.status_code
            result = ('success' if status == 200 else 'busy' if status == 429 else
                      'validation_or_auth' if 400 <= status < 500 else 'remote_http_error')
            emit('remote_end', boundary=boundary, category=result,
                 elapsed_seconds=round(time.monotonic() - started, 3), **state,
                 server_record_exists='unknown', automatic_retry=False)
            return response
        except httpx.RequestError as exc:
            emit('remote_end', boundary=boundary, category=category(exc), exception_type=type(exc).__name__,
                 elapsed_seconds=round(time.monotonic() - started, 3), **state,
                 remote_acceptance='unknown', server_record_exists='unknown', automatic_retry=False)
            raise
        finally:
            client.event_hooks['response'].remove(on_response)
