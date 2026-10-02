"""Local startup checks with fake processes and HTTP boundaries, no GPU work."""

import importlib.util
import io
import json
import os
from pathlib import Path
import tempfile
import threading
import time
import unittest
from unittest.mock import patch
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import shutil
import subprocess
from urllib.error import HTTPError

MODULE = Path(__file__).resolve().parents[1] / 'scripts' / 'capstone_launcher.py'
spec = importlib.util.spec_from_file_location('beautycore_capstone_launcher', MODULE)
launcher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(launcher)


class LauncherTests(unittest.TestCase):
    def test_unified_root_is_derived_from_imported_launcher(self):
        self.assertEqual(launcher.HAIR_ROOT, launcher.ROOT.parent)
        self.assertEqual(launcher.HAIR_ROOT / 'backend' / 'app' / 'main.py',
                         Path(__file__).resolve().parents[2] / 'backend' / 'app' / 'main.py')

    def test_nails_private_assets_resolve_inside_unified_root(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            names = {
                'NAILS_HAND_LANDMARKER_PATH': root / 'data/nails/checkpoints/mediapipe/hand_landmarker.task',
                'NAILS_SEGMENT_PYTHON': root / 'data/nails/work/seg-venv/Scripts/python.exe',
                'NAILS_SEGMENT_CHECKPOINT': root / 'data/nails/checkpoints/mnemic/nails_seg_s_yolov8_v1.pt',
            }
            for path in names.values():
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(b'private test fixture')
            base = {'AI_REMOTE_API_KEY': 'shared-key-' + 'x' * 32,
                    'CONSULTATION_PROVIDER': 'gemini', 'GEMINI_API_KEY': 'configured'}
            with patch.object(launcher, 'HAIR_ROOT', root), \
                 patch.object(launcher, 'process_env', return_value=base.copy()):
                env = launcher.backend_environment('https://worker.example.invalid', base['AI_REMOTE_API_KEY'], 'approved')
                for name, path in names.items():
                    self.assertEqual(env[name], str(path))
                names['NAILS_SEGMENT_CHECKPOINT'].unlink()
                with self.assertRaisesRegex(launcher.StartupError, 'NAILS_SEGMENT_CHECKPOINT'):
                    launcher.backend_environment('https://worker.example.invalid', base['AI_REMOTE_API_KEY'], 'approved')

    def test_beautycore_config_and_process_override_without_rewriting_file(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / '.env.local'
            original = ('DATABASE_URL=postgresql://demo:pw@example.invalid/db\n'
                        'GEMINI_API_KEY=beauty-key\nSESSION_SECRET=' + 's' * 40 + '\n'
                        'AI_CONSULTATION_HANDLE_SECRET=' + 'h' * 40 + '\n')
            source.write_text(original)
            with patch.object(launcher, 'ROOT', root), patch.dict(os.environ,
                    {'AI_FASTAPI_URL': '', 'AI_REMOTE_API_KEY': 'private-worker-key'}):
                env = launcher.beautycore_environment()
            self.assertEqual(env['AI_FASTAPI_URL'], launcher.BACKEND + '/')
            self.assertEqual(env['GEMINI_API_KEY'], 'beauty-key')
            self.assertNotIn('AI_REMOTE_API_KEY', env)
            self.assertEqual(source.read_text(), original)

    def test_missing_config_and_conflicting_url_fail_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            with patch.object(launcher, 'ROOT', root):
                with self.assertRaisesRegex(launcher.StartupError, 'env.local is missing'):
                    launcher.beautycore_environment()
            (root / '.env.local').write_text('DATABASE_URL=postgresql://demo:pw@example.invalid/db\n'
                                             'GEMINI_API_KEY=key\nSESSION_SECRET=' + 's' * 40 + '\n'
                                             'AI_CONSULTATION_HANDLE_SECRET=' + 'h' * 40 + '\n'
                                             'AI_FASTAPI_URL=http://other.invalid:8000/\n')
            with patch.object(launcher, 'ROOT', root):
                with self.assertRaisesRegex(launcher.StartupError, 'conflicts'):
                    launcher.beautycore_environment()

    def test_private_readiness_checks_features_gemini_and_base_count(self):
        ok = {'/health': {'status': 'ok'},
              '/deployment/readiness': {'ready': True, 'foundation_load_count': 1},
              '/consultations/mode': {'provider': 'gemini', 'model': 'gemini-3.5-flash-lite'},
              '/features': [{'id': name} for name in sorted(launcher.REQUIRED_FEATURES)],
              '/consultations/catalog': {'services': [],
                                         'styles': {name: [{}, {}, {}] for name in launcher.REQUIRED_FEATURES}}}

        def get(url):
            return ok[url.removeprefix(launcher.BACKEND)]

        with patch.object(launcher, 'json_get', side_effect=get):
            self.assertTrue(launcher.backend_ready()['ready'])
            ok['/deployment/readiness']['foundation_load_count'] = 2
            with self.assertRaisesRegex(launcher.StartupError, 'not ready'):
                launcher.backend_ready()
            ok['/deployment/readiness']['foundation_load_count'] = 1
            ok['/features'].pop()
            with self.assertRaisesRegex(launcher.StartupError, 'not ready'):
                launcher.backend_ready()
            ok['/features'].append({'id': 'nails'})
            ok['/consultations/catalog']['styles']['nails'] = []
            with self.assertRaisesRegex(launcher.StartupError, 'not ready'):
                launcher.backend_ready()

    def test_anonymous_adapter_guard_is_required(self):
        class Page:
            status = 200
            def __enter__(self): return self
            def __exit__(self, *_): return False

        def get(url, timeout):
            if url.endswith('/api/ai/features'):
                raise HTTPError(url, 401, 'unauthorized', {}, None)
            return Page()

        with patch.object(launcher, 'urlopen', side_effect=get):
            launcher.beautycore_ready()
        with patch.object(launcher, 'urlopen', return_value=Page()):
            with self.assertRaisesRegex(launcher.StartupError, 'accepted an anonymous'):
                launcher.beautycore_ready()

    def test_adapter_transport_probe_is_read_only_and_fails_closed(self):
        with patch.object(launcher.subprocess, 'run', return_value=type('Result', (), {'returncode': 0})()) as run:
            launcher.adapter_transport_ready('node', {'AI_FASTAPI_URL': launcher.BACKEND + '/'})
            args = run.call_args.args[0]
            self.assertIn('ai_adapter_probe.ts', args[-1])
            self.assertEqual(run.call_args.kwargs['stdout'], launcher.subprocess.DEVNULL)
            self.assertEqual(run.call_args.kwargs['stderr'], launcher.subprocess.DEVNULL)
        with patch.object(launcher.subprocess, 'run', return_value=type('Result', (), {'returncode': 1})()):
            with self.assertRaisesRegex(launcher.StartupError, 'cannot reach'):
                launcher.adapter_transport_ready('node', {})

    def test_actual_adapter_core_gets_features_from_fake_private_backend(self):
        node = shutil.which('node')
        tsx = launcher.ROOT / 'node_modules' / 'tsx' / 'dist' / 'cli.mjs'
        if not node or not tsx.is_file():
            self.skipTest('BeautyCore Node dependencies are not installed')

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *_): pass
            def do_GET(self):
                if self.path != '/features':
                    self.send_error(404)
                    return
                raw = json.dumps([{'id': name} for name in sorted(launcher.REQUIRED_FEATURES)]).encode()
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)

        server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            env = {**os.environ, 'AI_FASTAPI_URL': f'http://127.0.0.1:{server.server_port}/',
                   'AI_CONSULTATION_HANDLE_SECRET': 's' * 40}
            result = subprocess.run([node, str(tsx), str(launcher.ROOT / 'scripts' / 'ai_adapter_probe.ts')],
                                    cwd=launcher.ROOT, env=env, capture_output=True, timeout=25)
            self.assertEqual(result.returncode, 0, 'Read-only adapter probe failed')
        finally:
            server.shutdown()
            server.server_close()
            thread.join(5)

    def test_unavailable_worker_does_not_start_processes_or_reveal_key(self):
        with patch.object(launcher, 'beautycore_environment', return_value={}), \
             patch.object(launcher, 'local_dependencies', return_value=('node', 'next')), \
             patch.object(launcher, 'process_env', return_value={'AI_REMOTE_API_KEY': 'private-key-' + 'x' * 32}), \
             patch.object(launcher, 'discover', side_effect=launcher.StartupError('No endpoint published')), \
             patch.object(launcher.subprocess, 'Popen') as popen, \
             patch('sys.stdout', new_callable=io.StringIO) as output:
            self.assertEqual(launcher.start(), 1)
            popen.assert_not_called()
            self.assertIn('stage=endpoint_discovery', output.getvalue())
            self.assertNotIn('private-key-', output.getvalue())

    def test_owned_healthy_session_is_reused_without_new_process(self):
        with tempfile.TemporaryDirectory() as temp:
            work = Path(temp)
            work.mkdir(exist_ok=True)
            current = {'session_id': 'existing', 'port': 12345, 'token': 'a' * 64}
            env = {'AI_REMOTE_API_KEY': 'private-' + 'x' * 32,
                   'CONSULTATION_PROVIDER': 'gemini', 'GEMINI_API_KEY': 'private-gemini'}
            with patch.object(launcher, 'WORK', work), patch.object(launcher, 'STATE', work / 'control.json'), \
                 patch.object(launcher, 'beautycore_environment', return_value={}), \
                 patch.object(launcher, 'local_dependencies', return_value=('node', 'next')), \
                 patch.object(launcher, 'process_env', return_value=env), \
                 patch.object(launcher, 'discover', return_value=('https://worker.example.invalid',
                     {'publication_id': 'new', 'bundle_sha256': 'approved'})), \
                 patch.object(launcher, 'verify_worker', return_value={'status': 'ready'}), \
                 patch.object(launcher, 'backend_environment', return_value=env), \
                 patch.object(launcher, 'identity', return_value='matching'), \
                 patch.object(launcher, 'state_read', return_value=current), \
                 patch.object(launcher, 'control', return_value={'identity': 'matching', 'ready': True}), \
                 patch.object(launcher, 'backend_ready', return_value={'ready': True}), \
                 patch.object(launcher, 'beautycore_ready'), \
                 patch.object(launcher.subprocess, 'Popen') as popen, \
                 patch('sys.stdout', new_callable=io.StringIO) as output:
                self.assertEqual(launcher.start(), 0)
                popen.assert_not_called()
                self.assertIn('existing owned session', output.getvalue())

    def test_supervisor_starts_only_backend_and_beautycore_and_stops_owned_job(self):
        class Process:
            def poll(self): return None
            def wait(self, timeout): return 0

        class Job:
            closed = False
            def close(self): self.closed = True

        with tempfile.TemporaryDirectory() as temp:
            work = Path(temp)
            session = 'demo-session'
            commands = []
            jobs = []

            def make_job():
                job = Job()
                jobs.append(job)
                return job

            def spawn(command, directory, env, log, job):
                commands.append((command, directory, env.copy()))
                return Process()

            with patch.object(launcher, 'WORK', work), patch.object(launcher, 'STATE', work / 'control.json'), \
                 patch.object(launcher, 'local_dependencies', return_value=('node', Path('next'))), \
                 patch.object(launcher, 'WindowsJob', side_effect=make_job), \
                 patch.object(launcher, 'occupied', return_value=False), \
                 patch.object(launcher, 'start_child', side_effect=spawn), \
                 patch.object(launcher, 'backend_ready', return_value={'ready': True}), \
                 patch.object(launcher, 'beautycore_ready'), \
                 patch.object(launcher, 'adapter_transport_ready') as probe, \
                 patch.object(launcher, 'beautycore_environment', return_value={'AI_FASTAPI_URL': launcher.BACKEND + '/'}), \
                 patch.dict(os.environ, {'BEAUTYCORE_LAUNCH_SESSION': session,
                                         'BEAUTYCORE_LAUNCH_IDENTITY': 'verified'}):
                thread = threading.Thread(target=launcher.supervise)
                thread.start()
                try:
                    deadline = time.monotonic() + 5
                    while time.monotonic() < deadline:
                        state = launcher.state_read()
                        if state and launcher.control(state).get('ready'):
                            break
                        time.sleep(.02)
                    else:
                        self.fail('Supervisor did not become ready')
                    self.assertEqual(len(commands), 2)
                    self.assertIn('uvicorn', commands[0][0])
                    self.assertIn('next', str(commands[1][0]))
                    self.assertEqual(commands[1][2]['AI_FASTAPI_URL'], launcher.BACKEND + '/')
                    probe.assert_called_once()
                    launcher.stop_owned()
                    thread.join(5)
                    self.assertFalse(thread.is_alive())
                    self.assertTrue(jobs[0].closed)
                finally:
                    if thread.is_alive():
                        state = launcher.state_read()
                        if state:
                            launcher.control(state, 'stop')
                        thread.join(5)

    def test_unmanaged_backend_port_is_not_adopted_or_killed(self):
        class Job:
            closed = False
            def close(self): self.closed = True

        with tempfile.TemporaryDirectory() as temp:
            work = Path(temp)
            job = Job()
            with patch.object(launcher, 'WORK', work), patch.object(launcher, 'STATE', work / 'control.json'), \
                 patch.object(launcher, 'local_dependencies', return_value=('node', Path('next'))), \
                 patch.object(launcher, 'WindowsJob', return_value=job), \
                 patch.object(launcher, 'occupied', return_value=True), \
                 patch.object(launcher, 'start_child') as spawn, \
                 patch.dict(os.environ, {'BEAUTYCORE_LAUNCH_SESSION': 'port-test',
                                         'BEAUTYCORE_LAUNCH_IDENTITY': 'verified'}):
                launcher.supervise()
                spawn.assert_not_called()
                self.assertTrue(job.closed)
                failure = json.loads((work / 'port-test' / 'failure.json').read_text())
                self.assertIn('unmanaged FastAPI', failure['detail'])


if __name__ == '__main__':
    unittest.main()
