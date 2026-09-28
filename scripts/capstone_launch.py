"""Windows START/STOP entry point, only manages processes it owns."""

import argparse
import ctypes
from ctypes import wintypes
from hashlib import sha256
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
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
from uuid import uuid4

from dotenv import dotenv_values

try:
    from scripts.capstone_discovery import StartupError, discover, endpoint, verify_worker, request, BUNDLE_SHA, BUNDLE_REGISTRIES, TRAIN002_BUNDLE_SHA
except ModuleNotFoundError:
    from capstone_discovery import StartupError, discover, endpoint, verify_worker, request, BUNDLE_SHA, BUNDLE_REGISTRIES, TRAIN002_BUNDLE_SHA

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / '.tmp/capstone'
STATE = WORK / 'control.json'
BACKEND = 'http://127.0.0.1:8000'
FRONTEND = 'http://localhost:3000'


class WindowsJob:
    """Kill-on-close job contains only new project children, never existing PIDs."""
    def __init__(self):
        if os.name != 'nt':
            raise StartupError('This launcher requires Windows')
        class Basic(ctypes.Structure):
            _fields_ = [('process_time', ctypes.c_longlong), ('job_time', ctypes.c_longlong),
                        ('flags', wintypes.DWORD), ('min_ws', ctypes.c_size_t), ('max_ws', ctypes.c_size_t),
                        ('active', wintypes.DWORD), ('affinity', ctypes.c_size_t),
                        ('priority', wintypes.DWORD), ('scheduling', wintypes.DWORD)]
        class IO(ctypes.Structure):
            _fields_ = [(name, ctypes.c_ulonglong) for name in ('read_ops', 'write_ops', 'other_ops',
                        'read_bytes', 'write_bytes', 'other_bytes')]
        class Extended(ctypes.Structure):
            _fields_ = [('basic', Basic), ('io', IO), ('process_memory', ctypes.c_size_t),
                        ('job_memory', ctypes.c_size_t), ('peak_process', ctypes.c_size_t), ('peak_job', ctypes.c_size_t)]
        self.api = ctypes.WinDLL('kernel32', use_last_error=True)
        self.api.CreateJobObjectW.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR]
        self.api.CreateJobObjectW.restype = wintypes.HANDLE
        self.api.SetInformationJobObject.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD]
        self.api.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
        self.api.CloseHandle.argtypes = [wintypes.HANDLE]
        self.handle = self.api.CreateJobObjectW(None, None)
        info = Extended()
        info.basic.flags = 0x2000
        if not self.handle or not self.api.SetInformationJobObject(self.handle, 9, ctypes.byref(info), ctypes.sizeof(info)):
            self.close()
            raise StartupError('Cannot create owned Windows process group')

    def add(self, process):
        if not self.api.AssignProcessToJobObject(self.handle, wintypes.HANDLE(int(process._handle))):
            process.terminate()
            process.wait(timeout=10)
            raise StartupError('Cannot safely own this process; stopped only the new child')

    def close(self):
        if getattr(self, 'handle', None):
            self.api.CloseHandle(self.handle)
            self.handle = None


def occupied(port):
    with socket.socket() as connection:
        connection.settimeout(0.3)
        return connection.connect_ex(('127.0.0.1', port)) == 0


def require_free_ports():
    ports = [str(port) for port in (8000, 3000) if occupied(port)]
    if ports:
        raise StartupError('Local port(s) ' + ', '.join(ports) + ' occupied by a process not managed by this launcher. '
                           'It may be running in the background. Close the process using that port, then retry the launcher.')


def process_env(url, bundle_sha=BUNDLE_SHA):
    # Conventional precedence: process environment, then .env defaults.
    values = {k: v for k, v in dotenv_values(ROOT / 'backend/.env').items() if v is not None}
    env = {**values, **os.environ}
    key = env.get('AI_REMOTE_API_KEY', '')
    if len(key) < 24:
        raise StartupError('Set the shared API key once in backend/.env; never put it in the launcher')
    env.update(AI_REMOTE_URL=url, GENERATION_ENGINE='remote_flux', MAKEUP_GENERATION_ENGINE='remote_makeup',
               NAILS_PREVIEW_MODE='hybrid', PYTHONUNBUFFERED='1', NEXT_PUBLIC_API_BASE_URL=BACKEND,
               # Match the signed approved bundle, not a stale legacy override.
               # A local legacy TRAIN-002 override must not advertise unavailable GPU styles.
               HAIRCAPSTONE_STYLE_REGISTRY_PATH=str(ROOT / 'backend/app' / BUNDLE_REGISTRIES[bundle_sha]))
    return env


def identity(env):
    return sha256((env['AI_REMOTE_URL'] + '\0' + env['AI_REMOTE_API_KEY'] + '\0'
                   + env.get('HAIRCAPSTONE_STYLE_REGISTRY_PATH', '')).encode()).hexdigest()


def control(state, action='status'):
    if type(state.get('port')) is not int or not 1024 <= state['port'] <= 65535:
        raise StartupError('Invalid local launcher ownership record')
    token = state.get('token')
    if not isinstance(token, str) or len(token) != 64:
        raise StartupError('Invalid local launcher ownership token')
    response = json.loads(request(f"http://127.0.0.1:{state['port']}/{action}",
                    body=b'' if action == 'stop' else None, headers={'X-Launcher-Token': token}))
    if response.get('session_id') != state.get('session_id'):
        raise StartupError('Local controller identity differs; no process was killed')
    return response


def saved_state():
    if not STATE.exists():
        return None
    try:
        value = json.loads(STATE.read_text(encoding='utf-8'))
        if not isinstance(value, dict):
            raise ValueError()
        return value
    except (ValueError, OSError):
        raise StartupError('Invalid local launcher state; inspect .tmp/capstone without killing other processes') from None


def frontend_ready():
    from urllib.request import urlopen
    from urllib.error import URLError
    try:
        with urlopen(FRONTEND, timeout=10) as response:
            return response.status == 200
    except (OSError, URLError):
        return False


def wait_application(processes, stopped, status, *, timeout=180):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if stopped.is_set():
            raise StartupError('Startup was stopped')
        if any(p.poll() is not None for p in processes):
            raise StartupError('Owned child exited; inspect its log')
        try:
            report = json.loads(request(BACKEND + '/deployment/readiness'))
            if report.get('ready') is True:
                if status == 'backend_readiness' or frontend_ready():
                    return
        except StartupError:
            pass
        time.sleep(1)
    raise StartupError('Readiness deadline exceeded; inspect local logs')


def start_child(command, directory, env, log, job):
    process = subprocess.Popen(command, cwd=directory, env=env, stdout=log, stderr=subprocess.STDOUT,
                               creationflags=subprocess.CREATE_NO_WINDOW)
    job.add(process)
    return process


def supervise():
    env = dict(os.environ)
    session = env['CAPSTONE_LAUNCH_SESSION']
    token = secrets.token_hex(32)
    status = {'session_id': session, 'identity': identity(env), 'ready': False, 'stage': 'backend_start'}
    stopped, processes = threading.Event(), []
    directory = WORK / session
    directory.mkdir(parents=True, exist_ok=False)
    began = time.monotonic()
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_): pass
        def respond(self, stop=False):
            if not secrets.compare_digest(self.headers.get('X-Launcher-Token', ''), token) or self.path != ('/stop' if stop else '/status'):
                self.send_error(403)
                return
            raw = json.dumps(status).encode()
            self.send_response(200)
            self.send_header('Content-Length', str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)
            if stop:
                stopped.set()
        def do_GET(self): self.respond()
        def do_POST(self): self.respond(True)
    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    state = {'session_id': session, 'port': server.server_port, 'token': token}
    STATE.write_text(json.dumps(state), encoding='utf-8')
    job, logs = None, []
    try:
        status['stage'] = 'local_port_check'
        require_free_ports()
        status['stage'] = 'backend_start'
        job = WindowsJob()
        backend_log = (directory / 'backend.log').open('w', encoding='utf-8')
        logs.append(backend_log)
        processes.append(start_child([sys.executable, '-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1',
                                     '--port', '8000'], ROOT / 'backend', env, backend_log, job))
        status['stage'] = 'backend_readiness'
        wait_application(processes, stopped, status['stage'])
        status['stage'] = 'frontend_start'
        node = shutil.which('node')
        next_script = ROOT / 'frontend/node_modules/next/dist/bin/next'
        if not node or not next_script.is_file():
            raise StartupError('Existing Node/Next dependencies missing; restore the one-time local setup')
        frontend_log = (directory / 'frontend.log').open('w', encoding='utf-8')
        logs.append(frontend_log)
        # This is exactly the current npm dev script, without an intermediate shell.
        processes.append(start_child([node, str(next_script), 'dev', '--port', '3000'],
                                     ROOT / 'frontend', env, frontend_log, job))
        status['stage'] = 'final_readiness'
        wait_application(processes, stopped, status['stage'])
        status.update(ready=True, stage='ready')
        (directory / 'startup.json').write_text(json.dumps({
            'status': 'CAPSTONE_READY', 'session_id': session,
            'publication_id': env.get('CAPSTONE_PUBLICATION_ID', 'manual_override'),
            'endpoint_and_key_fingerprint': identity(env),
            'startup_seconds': round(time.monotonic() - began, 3),
            'backend_readiness': True, 'frontend_http_ready': True,
            'automatic_generation_retries': 0}, indent=2), encoding='utf-8')
        while not stopped.wait(1):
            if any(p.poll() is not None for p in processes):
                raise StartupError('Owned application process exited')
    except Exception as exc:
        status.update(ready=False, stage=status['stage'], failed=True,
                      detail=str(exc) if isinstance(exc, StartupError) else type(exc).__name__)
        (directory / 'failure.json').write_text(json.dumps(status, indent=2), encoding='utf-8')
        stopped.wait(3)
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
        if STATE.exists() and saved_state().get('session_id') == session:
            STATE.unlink()


def stop_owned():
    state = saved_state()
    if not state:
        print('CAPSTONE STOPPED: no launcher-owned session')
        return
    try:
        control(state, 'stop')
    except StartupError:
        if occupied(8000) or occupied(3000):
            raise StartupError('Controller unavailable; no processes were killed. Close existing terminals manually') from None
        STATE.unlink()
        print('CAPSTONE STOPPED: stale control record removed, no processes killed')
        return
    for _ in range(30):
        if not STATE.exists():
            print('CAPSTONE STOPPED')
            return
        time.sleep(1)
    raise StartupError('Owned shutdown still pending; inspect .tmp/capstone logs')


def start(url_override=None, train002=False):
    WORK.mkdir(parents=True, exist_ok=True)
    stage = 'local_configuration'
    created_session = None
    try:
        env = process_env('')
        key = env['AI_REMOTE_API_KEY']
        stage = 'endpoint_discovery'
        if url_override:
            url, publication, bundle_sha = endpoint(url_override), 'manual_override', TRAIN002_BUNDLE_SHA if train002 else BUNDLE_SHA
        else:
            url, record = discover(key)
            publication = record['publication_id']
            bundle_sha = record.get('bundle_sha256', BUNDLE_SHA)
        stage = 'remote_readiness'
        verify_worker(url, key)
        env = process_env(url, bundle_sha)
        env['CAPSTONE_PUBLICATION_ID'] = publication
        # Exclusive for one startup only. Kernel automatically releases after launcher death.
        import msvcrt
        with (WORK / 'launch.lock').open('a+b') as lock:
            lock.seek(0)
            try:
                msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
            except OSError:
                raise StartupError('Another launcher is starting; wait for its result') from None
            state = saved_state()
            if state:
                try:
                    status = control(state)
                except StartupError:
                    status = None
                if status and status.get('identity') == identity(env) and status.get('ready'):
                    wait_application([], threading.Event(), 'final_readiness', timeout=20)
                    print('CAPSTONE READY (existing owned session)', FRONTEND)
                    return 0
                stage = 'owned_session_shutdown'
                stop_owned()
            stage = 'local_port_check'
            require_free_ports()
            session = str(uuid4())
            created_session = session
            env['CAPSTONE_LAUNCH_SESSION'] = session
            stage = 'supervisor_start'
            log_path = WORK / ('launcher-' + session + '.log')
            with log_path.open('w', encoding='utf-8') as log:
                supervisor = subprocess.Popen([sys.executable, str(Path(__file__).resolve()), '--supervise'],
                    cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT,
                    creationflags=subprocess.CREATE_NO_WINDOW)
            last_stage = None
            deadline = time.monotonic() + 420
            while time.monotonic() < deadline:
                state = saved_state()
                if state and state['session_id'] == session:
                    status = control(state)
                    stage = status['stage']
                    if stage != last_stage:
                        print('CAPSTONE STARTING', 'stage=' + stage, flush=True)
                        last_stage = stage
                    if status.get('failed'):
                        raise StartupError(status['detail'])
                    if status.get('ready'):
                        print('CAPSTONE READY', FRONTEND)
                        print('Logs: .tmp/capstone/' + session)
                        return 0
                if supervisor.poll() is not None:
                    raise StartupError('Supervisor exited; inspect launcher log')
                time.sleep(1)
            raise StartupError('Local startup deadline exceeded')
    except Exception as exc:
        # Only ask this launcher's newly created controller to stop on startup failure.
        if created_session:
            try:
                state = saved_state()
                if state and state.get('session_id') == created_session:
                    control(state, 'stop')
            except StartupError:
                pass
        print('CAPSTONE_STARTUP_FAILED', 'stage=' + stage,
              str(exc) if isinstance(exc, StartupError) else type(exc).__name__)
        if stage in ('local_port_check', 'owned_session_shutdown'):
            print('Recovery: resolve the local process conflict, then run START_CAPSTONE.bat again. Keep Kaggle running.')
        else:
            print('Recovery: inspect the reported stage and local logs. For discovery/remote readiness, check START CAPSTONE in Kaggle. '
                  'Emergency: START_CAPSTONE.bat --url <current HTTPS URL>')
        return 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url', help='Explicit emergency Quick Tunnel URL, never written to .env')
    parser.add_argument('--train002', action='store_true', help='Expanded Hair bundle for emergency --url only')
    parser.add_argument('--stop', action='store_true')
    parser.add_argument('--supervise', action='store_true', help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.train002 and not args.url:
        parser.error('--train002 is only for emergency --url; normal startup discovers the bundle automatically')
    if args.supervise:
        supervise()
        return 0
    if args.stop:
        try:
            stop_owned()
            return 0
        except StartupError as exc:
            print('CAPSTONE_STOP_FAILED', str(exc))
            return 1
    return start(args.url, train002=args.train002)


if __name__ == '__main__':
    raise SystemExit(main())
