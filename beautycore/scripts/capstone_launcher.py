"""Start the unified BeautyCore folder using its existing AI discovery stack.

This script owns only children it starts. Temporary URLs and credentials stay in
process memory; neither configuration file is modified.
"""

import argparse
import json
import os
from pathlib import Path
import secrets
import shutil
import socket
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from uuid import uuid4

from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[1]
HAIR_ROOT = ROOT.parent
if not (HAIR_ROOT / 'scripts' / 'capstone_discovery.py').is_file():
    raise SystemExit('BEAUTYCORE_STARTUP_FAILED stage=local_configuration Unified project root is missing the existing capstone startup scripts')
sys.path.insert(0, str(HAIR_ROOT))

from scripts.capstone_discovery import StartupError, discover, endpoint, verify_worker, request  # noqa: E402
from scripts.capstone_launch import WindowsJob, process_env, identity, occupied  # noqa: E402

BACKEND = 'http://127.0.0.1:8000'
BEAUTYCORE = 'http://127.0.0.1:3000'
WORK = ROOT / '.tmp' / 'capstone'
STATE = WORK / 'control.json'
REQUIRED_FEATURES = {'hairstyle', 'makeup', 'nails'}
WINDOWS_PROCESS_KEYS = {
    'PATH', 'SYSTEMROOT', 'WINDIR', 'COMSPEC', 'PATHEXT', 'TEMP', 'TMP',
    'USERPROFILE', 'APPDATA', 'LOCALAPPDATA', 'HOMEDRIVE', 'HOMEPATH',
    'PROGRAMDATA', 'PROGRAMFILES', 'PROGRAMFILES(X86)', 'PUBLIC',
    'NUMBER_OF_PROCESSORS', 'PROCESSOR_ARCHITECTURE', 'OS',
}


def beautycore_environment():
    source = ROOT / '.env.local'
    if not source.is_file():
        raise StartupError('BeautyCore .env.local is missing; complete one-time local setup')
    values = {key: value for key, value in dotenv_values(source).items() if value is not None}
    # Deliberately do not pass HAIR/Kaggle environment variables to Next.
    # BeautyCore's own ignored config supplies its application credentials.
    env = {key: value for key, value in os.environ.items() if key.upper() in WINDOWS_PROCESS_KEYS}
    env.update(values)
    for key in ('DATABASE_URL', 'GEMINI_API_KEY', 'SESSION_SECRET', 'AI_CONSULTATION_HANDLE_SECRET'):
        value = env.get(key, '').strip()
        if not value or value.startswith(('your_', 'replace-with-', 'postgresql://user:')):
            raise StartupError(f'BeautyCore {key} is missing or still a template value')
    if len(env['SESSION_SECRET']) < 32 or len(env['AI_CONSULTATION_HANDLE_SECRET']) < 32:
        raise StartupError('BeautyCore session and consultation secrets must each be at least 32 characters')
    configured_url = env.get('AI_FASTAPI_URL', '').rstrip('/')
    if configured_url and configured_url != BACKEND:
        raise StartupError('BeautyCore AI_FASTAPI_URL conflicts with the local private FastAPI address')
    env['AI_FASTAPI_URL'] = BACKEND + '/'
    env['NODE_ENV'] = 'development'
    return env


def backend_environment(url, key, bundle_sha):
    env = process_env(url, bundle_sha)
    if env.get('CONSULTATION_PROVIDER', '').strip().lower() != 'gemini':
        raise StartupError('Set CONSULTATION_PROVIDER=gemini in backend/.env')
    if not env.get('GEMINI_API_KEY', '').strip():
        raise StartupError('Set GEMINI_API_KEY in backend/.env')
    if env['AI_REMOTE_API_KEY'] != key:
        raise StartupError('Backend AI key changed during discovery')
    # Source checkouts are relocatable. These three private Nails assets are
    # installed under the unified root, never copied from an old drive path.
    local_assets = {
        'NAILS_HAND_LANDMARKER_PATH': HAIR_ROOT / 'data/nails/checkpoints/mediapipe/hand_landmarker.task',
        'NAILS_SEGMENT_PYTHON': HAIR_ROOT / 'data/nails/work/seg-venv/Scripts/python.exe',
        'NAILS_SEGMENT_CHECKPOINT': HAIR_ROOT / 'data/nails/checkpoints/mnemic/nails_seg_s_yolov8_v1.pt',
    }
    for name, path in local_assets.items():
        if not path.is_file():
            raise StartupError(f'Missing private Nails setup: {name}; see unified install guide')
        env[name] = str(path)
    return env


def local_dependencies():
    if not (HAIR_ROOT / 'backend' / 'app' / 'main.py').is_file():
        raise StartupError('Unified project root does not contain the expected FastAPI backend')
    next_script = ROOT / 'node_modules' / 'next' / 'dist' / 'bin' / 'next'
    tsx_script = ROOT / 'node_modules' / 'tsx' / 'dist' / 'cli.mjs'
    node = shutil.which('node')
    if not node or not next_script.is_file() or not tsx_script.is_file():
        raise StartupError('BeautyCore Node dependencies are missing; run npm ci once in BeautyCore')
    try:
        import uvicorn  # noqa: F401
    except ImportError:
        raise StartupError('FastAPI Python dependencies are missing; restore the HAIR backend environment') from None
    return node, next_script


def adapter_transport_ready(node, env):
    """Exercise the unchanged allowlisted GET transport with a synthetic client.

    Real HTTP auth is checked separately via the anonymous 401. This probe never
    creates a session, consults Gemini, sends a photo, or generates an image.
    """
    tsx = ROOT / 'node_modules' / 'tsx' / 'dist' / 'cli.mjs'
    try:
        result = subprocess.run([node, str(tsx), str(ROOT / 'scripts' / 'ai_adapter_probe.ts')],
                                cwd=ROOT, env=env, stdout=subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL, timeout=35, check=False)
    except (OSError, subprocess.TimeoutExpired):
        raise StartupError('BeautyCore AI adapter transport probe did not complete') from None
    if result.returncode != 0:
        raise StartupError('BeautyCore AI adapter cannot reach or validate FastAPI features')


def json_get(url, timeout=12):
    try:
        with urlopen(Request(url, headers={'Accept': 'application/json'}), timeout=timeout) as response:
            if response.status != 200:
                raise StartupError('Local readiness returned an unexpected status')
            raw = response.read(65537)
            if len(raw) > 65536:
                raise StartupError('Local readiness response is too large')
            return json.loads(raw)
    except (OSError, URLError, ValueError):
        raise StartupError('Local service is not reachable or returned invalid readiness') from None


def backend_ready():
    health = json_get(BACKEND + '/health')
    readiness = json_get(BACKEND + '/deployment/readiness')
    mode = json_get(BACKEND + '/consultations/mode')
    features = json_get(BACKEND + '/features')
    catalog = json_get(BACKEND + '/consultations/catalog')
    found = {item.get('id') for item in features if isinstance(item, dict)} if isinstance(features, list) else set()
    styles = catalog.get('styles', {}) if isinstance(catalog, dict) else {}
    if (health.get('status') != 'ok' or readiness.get('ready') is not True or
            readiness.get('foundation_load_count') != 1 or
            mode.get('provider') != 'gemini' or mode.get('model') != 'gemini-3.5-flash-lite' or
            not REQUIRED_FEATURES <= found or not isinstance(styles, dict) or
            any(not isinstance(styles.get(feature), list) or len(styles[feature]) < 3
                for feature in REQUIRED_FEATURES)):
        raise StartupError('FastAPI is reachable but unified AI, Gemini, or feature catalog is not ready')
    return readiness


def beautycore_ready():
    try:
        with urlopen(BEAUTYCORE + '/', timeout=15) as response:
            if response.status != 200:
                raise StartupError('BeautyCore returned an unexpected status')
        # The Phase 1 adapter requires a live client session. An anonymous 401
        # proves the protected route exists without weakening its boundary.
        try:
            urlopen(BEAUTYCORE + '/api/ai/features', timeout=15)
        except HTTPError as exc:
            if exc.code == 401:
                return
            raise StartupError('BeautyCore AI adapter guard returned an unexpected status') from None
        raise StartupError('BeautyCore AI adapter accepted an anonymous request')
    except (OSError, URLError):
        raise StartupError('BeautyCore is not reachable') from None


def wait_for(check, processes, stopped, seconds, stage):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if stopped.is_set():
            raise StartupError('Startup was stopped')
        if any(process.poll() is not None for process in processes):
            raise StartupError(f'Owned child exited during {stage}; inspect its log')
        try:
            return check()
        except StartupError:
            time.sleep(1)
    raise StartupError(f'{stage} timed out; inspect launcher logs')


def state_read():
    if not STATE.exists():
        return None
    try:
        state = json.loads(STATE.read_text(encoding='utf-8'))
        if (not isinstance(state, dict) or type(state.get('port')) is not int or
                not 1024 <= state['port'] <= 65535 or
                not isinstance(state.get('token'), str) or len(state['token']) != 64 or
                not isinstance(state.get('session_id'), str)):
            raise ValueError()
        return state
    except (OSError, ValueError):
        raise StartupError('Invalid launcher ownership record; no processes were stopped') from None


def control(state, action='status'):
    try:
        report = json.loads(request(f"http://127.0.0.1:{state['port']}/{action}",
                            body=b'' if action == 'stop' else None,
                            headers={'X-Launcher-Token': state['token']}))
    except (ValueError, TypeError):
        raise StartupError('Launcher controller did not return valid status') from None
    if report.get('session_id') != state['session_id']:
        raise StartupError('Launcher identity differs; no process was stopped')
    return report


def start_child(command, directory, env, log, job):
    process = subprocess.Popen(command, cwd=directory, env=env, stdout=log,
                               stderr=subprocess.STDOUT, creationflags=subprocess.CREATE_NO_WINDOW)
    job.add(process)
    return process


def supervise():
    session = os.environ['BEAUTYCORE_LAUNCH_SESSION']
    token = secrets.token_hex(32)
    status = {'session_id': session, 'identity': os.environ['BEAUTYCORE_LAUNCH_IDENTITY'],
              'stage': 'starting', 'ready': False}
    stopped = threading.Event()
    folder = WORK / session
    folder.mkdir(parents=True, exist_ok=False)

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def respond(self, stopping=False):
            expected = '/stop' if stopping else '/status'
            if self.path != expected or not secrets.compare_digest(self.headers.get('X-Launcher-Token', ''), token):
                self.send_error(403)
                return
            raw = json.dumps(status).encode()
            self.send_response(200)
            self.send_header('Content-Length', str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)
            if stopping:
                stopped.set()

        def do_GET(self):
            self.respond()

        def do_POST(self):
            self.respond(True)

    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    STATE.write_text(json.dumps({'session_id': session, 'port': server.server_port,
                                 'token': token}), encoding='utf-8')
    processes, logs = [], []
    job = None
    try:
        node, next_script = local_dependencies()
        job = WindowsJob()
        if occupied(8000):
            raise StartupError('Port 8000 has an unmanaged FastAPI process; its worker URL cannot be verified. Stop it manually, then rerun START.bat')
        status['stage'] = 'backend_start'
        log = (folder / 'backend.log').open('w', encoding='utf-8')
        logs.append(log)
        processes.append(start_child([sys.executable, '-m', 'uvicorn', 'app.main:app',
                                      '--host', '127.0.0.1', '--port', '8000'],
                                     HAIR_ROOT / 'backend', os.environ.copy(), log, job))
        status['stage'] = 'backend_readiness'
        wait_for(backend_ready, processes, stopped, 180, 'FastAPI readiness')
        if occupied(3000):
            raise StartupError('Port 3000 is occupied by an unmanaged process; close it manually, then rerun START.bat')
        status['stage'] = 'beautycore_start'
        log = (folder / 'beautycore.log').open('w', encoding='utf-8')
        logs.append(log)
        beauty_env = beautycore_environment()
        processes.append(start_child([node, str(next_script), 'dev', '--hostname', '127.0.0.1',
                                      '--port', '3000'], ROOT, beauty_env, log, job))
        status['stage'] = 'integrated_readiness'
        wait_for(beautycore_ready, processes, stopped, 180, 'BeautyCore readiness')
        backend_ready()  # Recheck after both services are up.
        adapter_transport_ready(node, beauty_env)
        status.update(stage='ready', ready=True)
        while not stopped.wait(1):
            if any(process.poll() is not None for process in processes):
                raise StartupError('An owned application process exited; inspect launcher logs')
    except Exception as exc:
        status.update(ready=False, failed=True,
                      detail=str(exc) if isinstance(exc, StartupError) else type(exc).__name__)
        (folder / 'failure.json').write_text(json.dumps(status, indent=2), encoding='utf-8')
        stopped.wait(2)
    finally:
        if job:
            job.close()
        for process in processes:
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                pass
        for log in logs:
            log.close()
        server.shutdown()
        server.server_close()
        current = state_read()
        if current and current['session_id'] == session:
            STATE.unlink()


def stop_owned():
    state = state_read()
    if state is None:
        print('BEAUTYCORE STOPPED: no launcher-owned session')
        return
    try:
        control(state, 'stop')
    except StartupError:
        if occupied(8000) or occupied(3000):
            raise StartupError('Controller unavailable; no process was killed. Inspect local ports manually') from None
        STATE.unlink()
        print('BEAUTYCORE STOPPED: stale record removed; no process was killed')
        return
    for _ in range(30):
        if not STATE.exists():
            print('BEAUTYCORE STOPPED: launcher-owned local services closed')
            return
        time.sleep(1)
    raise StartupError('Owned shutdown is still pending; inspect launcher logs')


def start(url_override=None):
    stage = 'local_configuration'
    session = None
    try:
        beautycore_environment()
        local_dependencies()
        base_env = process_env('')
        key = base_env['AI_REMOTE_API_KEY']
        stage = 'endpoint_discovery'
        if url_override:
            url, publication, bundle_sha = endpoint(url_override), 'manual_override', None
        else:
            url, record = discover(key)
            publication, bundle_sha = record['publication_id'], record['bundle_sha256']
        stage = 'remote_readiness'
        verify_worker(url, key)
        if bundle_sha is None:
            from scripts.capstone_discovery import TRAIN002_BUNDLE_SHA
            bundle_sha = TRAIN002_BUNDLE_SHA
        backend_env = backend_environment(url, key, bundle_sha)
        # Next receives its own .env.local when launched; only the local
        # adapter URL is process-injected. Never write a temporary tunnel URL.
        combined = backend_env.copy()
        combined['BEAUTYCORE_LAUNCH_IDENTITY'] = identity(backend_env)
        combined['BEAUTYCORE_LAUNCH_PUBLICATION'] = publication
        stage = 'local_ownership'
        WORK.mkdir(parents=True, exist_ok=True)
        import msvcrt
        with (WORK / 'launch.lock').open('a+b') as lock:
            lock.seek(0)
            try:
                msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
            except OSError:
                raise StartupError('Another launcher is starting; wait for it to finish') from None
            current = state_read()
            if current:
                try:
                    running = control(current)
                except StartupError:
                    running = None
                if running and running.get('identity') == identity(backend_env) and running.get('ready'):
                    backend_ready()
                    beautycore_ready()
                    print('BEAUTYCORE CAPSTONE READY (existing owned session)')
                    return 0
                if running:
                    stop_owned()  # Only our signed controller; never arbitrary PIDs.
                elif occupied(8000) or occupied(3000):
                    raise StartupError('Stale controller with occupied ports; no process was killed')
                else:
                    STATE.unlink()
            if occupied(3000):
                raise StartupError('Port 3000 is occupied by an unmanaged process; close it manually')
            session = str(uuid4())
            combined['BEAUTYCORE_LAUNCH_SESSION'] = session
            stage = 'supervisor_start'
            with (WORK / ('launcher-' + session + '.log')).open('w', encoding='utf-8') as log:
                supervisor = subprocess.Popen([sys.executable, str(Path(__file__).resolve()), '--supervise'],
                                              cwd=ROOT, env=combined, stdout=log,
                                              stderr=subprocess.STDOUT, creationflags=subprocess.CREATE_NO_WINDOW)
            deadline = time.monotonic() + 420
            last_stage = None
            while time.monotonic() < deadline:
                current = state_read()
                if current and current['session_id'] == session:
                    result = control(current)
                    if result['stage'] != last_stage:
                        print('BEAUTYCORE STARTING', 'stage=' + result['stage'], flush=True)
                        last_stage = result['stage']
                    if result.get('failed'):
                        raise StartupError(result['detail'])
                    if result.get('ready'):
                        print('\n====================================')
                        print('    BEAUTYCORE CAPSTONE READY')
                        print('====================================')
                        print('BeautyCore: READY | AI Backend: READY')
                        print('Gemini Consult: READY (configured, no live call)')
                        print('Hairstyle: READY | Makeup: READY | Nails: READY')
                        print('Kaggle Worker: READY')
                        print('Open: ' + BEAUTYCORE)
                        print('Logs: .tmp/capstone/' + session)
                        print('====================================')
                        import webbrowser
                        webbrowser.open(BEAUTYCORE)
                        return 0
                if supervisor.poll() is not None:
                    failure = WORK / session / 'failure.json'
                    if failure.is_file():
                        try:
                            report = json.loads(failure.read_text(encoding='utf-8'))
                            stage = report.get('stage', stage)
                            raise StartupError(report.get('detail', 'Local service startup failed'))
                        except (OSError, ValueError, TypeError):
                            pass
                    raise StartupError('Supervisor exited; inspect its log')
                time.sleep(1)
            raise StartupError('Local startup timed out; inspect launcher logs')
    except Exception as exc:
        if session:
            try:
                current = state_read()
                if current and current['session_id'] == session:
                    control(current, 'stop')
            except StartupError:
                pass
        print('BEAUTYCORE_STARTUP_FAILED', 'stage=' + stage,
              str(exc) if isinstance(exc, StartupError) else type(exc).__name__)
        print('Recovery: check configuration and local logs. Start Kaggle START CAPSTONE first; '
              'for discovery failure use START.bat --url <current HTTPS URL>.')
        return 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url', help='Emergency current Quick Tunnel URL; never persisted')
    parser.add_argument('--stop', action='store_true')
    parser.add_argument('--supervise', action='store_true', help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.supervise:
        supervise()
        return 0
    if args.stop:
        try:
            stop_owned()
            return 0
        except StartupError as exc:
            print('BEAUTYCORE_STOP_FAILED', str(exc))
            return 1
    return start(args.url)


if __name__ == '__main__':
    raise SystemExit(main())
