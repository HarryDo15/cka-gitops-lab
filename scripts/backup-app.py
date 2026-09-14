"""Back up live Incident Desk to the Mac and verify an isolated restore via HTTP."""
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import time
import urllib.request
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
REMOTE = r'''
import os, sqlite3, sys, tempfile
from pathlib import Path
source = Path(os.environ.get('DB_PATH', '/data/incidents.db'))
with tempfile.TemporaryDirectory(prefix='.backup-', dir=str(source.parent)) as directory:
    snapshot = Path(directory) / 'snapshot.db'
    with sqlite3.connect(source.as_uri() + '?mode=ro', uri=True) as src:
        with sqlite3.connect(snapshot) as dst:
            src.backup(dst, pages=128, sleep=0.1)
            assert dst.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
    sys.stdout.buffer.write(snapshot.read_bytes())
'''


def verify_restore(backup):
    # Exercise restoration into a separate database; never overwrite live data.
    with tempfile.TemporaryDirectory(prefix='incident-desk-restore-') as directory:
        restored = Path(directory) / 'restored.db'
        with sqlite3.connect(backup.as_uri() + '?mode=ro', uri=True) as src:
            src.row_factory = sqlite3.Row
            expected = [dict(row) for row in src.execute('SELECT * FROM incidents ORDER BY id')]
            with sqlite3.connect(restored) as dst:
                src.backup(dst)
                assert dst.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
        # Bind port zero in the child to avoid port-selection races.
        code = """
import sys
from http.server import ThreadingHTTPServer
from server import Handler
server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
print(server.server_port, flush=True)
server.serve_forever()
"""
        env = dict(os.environ, DB_PATH=str(restored), PYTHONPATH=str(ROOT / 'app'))
        with tempfile.TemporaryFile(mode='w+') as log:
            child = subprocess.Popen([sys.executable, '-u', '-c', code], env=env,
                                     stdout=log, stderr=log, text=True)
            try:
                port = None
                deadline = time.monotonic() + 15
                while time.monotonic() < deadline:
                    if child.poll() is not None:
                        raise RuntimeError('Restored API failed to start')
                    log.seek(0)
                    line = log.readline().strip()
                    if line.isdigit():
                        port = int(line)
                        break
                    time.sleep(0.1)
                if port is None:
                    raise RuntimeError('Restored API startup timed out')
                opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
                def get(path):
                    with opener.open(f'http://127.0.0.1:{port}{path}', timeout=5) as response:
                        return json.load(response)
                assert get('/readyz')['status'] == 'ready'
                assert get('/incidents') == expected, 'Restored API records differ from snapshot'
                for record in expected:
                    assert get(f"/incidents/{record['id']}") == record
                return len(expected)
            finally:
                child.terminate()
                try:
                    child.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    child.kill()
                    child.wait()


def main():
    directory = ROOT / '.local' / 'backups'
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    backup = directory / f'incident-desk-{stamp}.db'
    partial = backup.with_suffix('.db.partial')
    fd = os.open(partial, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(fd, 'wb') as output:
            subprocess.run(['bash', str(ROOT / 'scripts/kubectl.sh'), '-n', 'incident-desk',
                            'exec', 'deploy/incident-desk', '--', 'python', '-c', REMOTE],
                           stdout=output, check=True, timeout=120)
        partial.rename(backup)
        count = verify_restore(backup)
    except Exception:
        failed_path = backup if backup.exists() else partial
        print(f'Backup or verification failed; inspect {failed_path}. No success record written.', file=sys.stderr)
        raise
    report = {'backup': backup.name, 'sha256': hashlib.sha256(backup.read_bytes()).hexdigest(),
              'verified_at': datetime.now(timezone.utc).isoformat(), 'incident_count': count,
              'integrity_check': 'ok', 'isolated_restore_api': 'passed',
              'scope': 'SQLite database; excludes cluster configuration and secrets'}
    report_path = backup.with_suffix('.json')
    with os.fdopen(os.open(report_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), 'w') as output:
        json.dump(report, output, indent=2)
        output.write('\n')
    print(f'PASS: backed up and restored {count} incidents; integrity and HTTP reads verified.')
    print(f'Backup: {backup}\nVerification: {report_path}')


if __name__ == '__main__':
    main()
