"""Run from repository root. Calls local FastAPI only, never reads/prints secrets."""

import argparse
import json
from pathlib import Path
from urllib.request import urlopen
from urllib.error import HTTPError, URLError
from uuid import UUID


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--backend', default='http://127.0.0.1:8000')
    parser.add_argument('--request-id', type=UUID, help='A remote request ID or hand correlation ID from logs')
    parser.add_argument('--snapshot', action='store_true', help='Read safe bounded worker history without inference')
    parser.add_argument('--output', type=Path, help='Save this safe check, refusing to overwrite existing evidence')
    args = parser.parse_args()
    if args.output and args.output.exists():
        parser.error('Output already exists; preserve it and choose a new name.')
    suffix = (f'/deployment/diagnostics/{args.request_id}' if args.request_id else
              '/deployment/diagnostics' if args.snapshot else '/deployment/readiness')
    try:
        try:
            response = urlopen(args.backend.rstrip('/') + suffix, timeout=35)
        except HTTPError as exc:
            response = exc
        with response:
            report = json.load(response)
        print(json.dumps(report, indent=2))
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
        return 0 if report.get('available' if args.request_id or args.snapshot else 'ready') is True else 1
    except (URLError, ValueError, TimeoutError, OSError):
        print('PRE_DEMO_NOT_READY: central backend is unreachable or returned an invalid check response.')
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
