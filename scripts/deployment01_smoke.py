"""Four central app requests for a fresh session rehearsal. No silent retries."""

import argparse
import hashlib
import json
from pathlib import Path
import time

import httpx


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for feature in ('hair', 'makeup', 'hand'):
        parser.add_argument('--' + feature, type=Path, required=True)
    parser.add_argument('--backend', default='http://127.0.0.1:8000')
    parser.add_argument('--output', type=Path, default=Path('.tmp/deployment01-rehearsal'))
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Choose a fresh output directory; preserve previous evidence.')
    inputs = {name: getattr(args, name).read_bytes() for name in ('hair', 'makeup', 'hand')}
    args.output.mkdir(parents=True)
    report = {'status': 'REHEARSAL_IN_PROGRESS', 'requests': [], 'automatic_retries': 0}
    def save():
        (args.output / 'application.json').write_text(json.dumps(report, indent=2) + '\n')
    def check(client, suffix):
        response = client.get(suffix)
        response.raise_for_status()
        return response.json()
    try:
        with httpx.Client(base_url=args.backend.rstrip('/'), timeout=900, follow_redirects=False) as client:
            report['readiness_before'] = check(client, '/deployment/readiness')
            report['worker_before'] = check(client, '/deployment/diagnostics')
            if not report['readiness_before'].get('ready') or not report['worker_before'].get('available'):
                raise RuntimeError('Readiness check failed')
            if report['worker_before']['successful_gpu_request_count'] != 0:
                raise RuntimeError('Rehearsal requires a fresh worker with no prior GPU requests')
            for feature, style, input_name in [('hairstyle', 'crew_cut', 'hair'),
                    ('makeup', 'natural_makeup', 'makeup'), ('nails', 'classic_red', 'hand'),
                    ('nails', 'nude_pink', 'hand')]:
                before = check(client, '/deployment/diagnostics')
                print('START', feature, style, flush=True)
                content = inputs[input_name]
                content_type = 'image/png' if content.startswith(b'\x89PNG') else 'image/jpeg'
                started = time.monotonic()
                response = client.post(f'/features/{feature}/generate', data={'style_id': style},
                    files={'image': ('input.png' if content_type == 'image/png' else 'input.jpg', content, content_type)})
                row = {'feature': feature, 'style_id': style, 'http_status': response.status_code,
                       'elapsed_seconds': round(time.monotonic() - started, 3),
                       'correlation_id': response.headers.get('X-Correlation-ID'), 'attempt': 1}
                report['requests'].append(row)
                if response.status_code != 200:
                    row['controlled_failure'] = True
                    report['worker_after_failure'] = check(client, '/deployment/diagnostics')
                    report['status'] = 'REHEARSAL_FAILED_REVIEW_DIAGNOSTICS'
                    save()
                    print('STOP: HTTP', response.status_code, 'correlation', row['correlation_id'], flush=True)
                    return 1
                payload = response.json()
                row['status'], row['generator'] = payload.get('status'), payload.get('generator')
                row['returned_style_id'] = payload.get('style', {}).get('id')
                if row['status'] != 'completed' or row['returned_style_id'] != style:
                    raise RuntimeError('Unexpected central result contract')
                # Keep only approved safe central metadata, never generated image bytes.
                metadata = payload.get('metadata', {})
                row['metadata'] = {k: metadata[k] for k in ('inference_path', 'nails_edited',
                    'timing_seconds', 'steps', 'seed', 'guidance', 'adapter_id', 'adapter_sha256') if k in metadata}
                row['input_sha256'] = hashlib.sha256(content).hexdigest()
                after = check(client, '/deployment/diagnostics')
                row['gpu_request_delta'] = after['successful_gpu_request_count'] - before['successful_gpu_request_count']
                expected_calls = (metadata.get('nails_edited') if style == 'classic_red' else
                                  0 if style == 'nude_pink' else 1)
                if not isinstance(expected_calls, int) or row['gpu_request_delta'] != expected_calls:
                    raise RuntimeError('GPU crop count does not match application result')
                if style == 'nude_pink' and (row['gpu_request_delta'] != 0 or metadata.get('inference_path') != 'renderer'):
                    raise RuntimeError('Renderer used GPU or wrong path')
                report['worker_after'] = after
                save()
                print('DONE', feature, style, 'HTTP', response.status_code, row['elapsed_seconds'], 'seconds', flush=True)
            report['readiness_after'] = check(client, '/deployment/readiness')
            if not report['readiness_after'].get('ready'):
                raise RuntimeError('Worker not ready after rehearsal')
            report['status'] = 'REHEARSAL_COMPLETED_REVIEW_REQUIRED'
            save()
            print(report['status'], 'Return application.json and notebook live-evidence.zip for review.')
            return 0
    except (httpx.RequestError, httpx.HTTPStatusError, ValueError, KeyError, RuntimeError) as exc:
        report['status'] = 'REHEARSAL_FAILED_REVIEW_DIAGNOSTICS'
        report['exception_type'] = type(exc).__name__
        save()
        print(report['status'], 'Preserve evidence. No automatic retry occurred.')
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
