"""Check metrics and end-to-end pod log ingestion through a Grafana port-forward."""
import argparse
import base64
from contextlib import contextmanager
import json
from pathlib import Path
import subprocess
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
import uuid

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--restart-check', action='store_true', help='Restart Prometheus and Loki and verify pre-restart telemetry survives')
args = parser.parse_args()

ROOT = Path(__file__).resolve().parents[1]
K = ['bash', str(ROOT / 'scripts/kubectl.sh')]

def run(*args):
    return subprocess.check_output(K + list(args), text=True)

def retry(check, seconds=180):
    end = time.monotonic() + seconds
    last = None
    while time.monotonic() < end:
        try:
            return check()
        except (AssertionError, URLError, ConnectionError, TimeoutError, KeyError) as error:
            last = error
            time.sleep(3)
    raise RuntimeError(f'Verification timed out: {last}')

@contextmanager
def grafana_forward():
    proc = subprocess.Popen(K + ['-n', 'monitoring', 'port-forward', 'svc/monitoring-grafana', '13000:80'],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        yield proc
    finally:
        if proc.poll() is None:
            proc.terminate()
            proc.wait(timeout=10)

secret = json.loads(run('-n', 'monitoring', 'get', 'secret', 'grafana-admin', '-o', 'json'))['data']
user = base64.b64decode(secret['admin-user']).decode()
password = base64.b64decode(secret['admin-password']).decode()
auth = base64.b64encode(f'{user}:{password}'.encode()).decode()

def get(path):
    try:
        with urlopen(Request('http://127.0.0.1:13000' + path, headers={'Authorization': 'Basic ' + auth}), timeout=10) as response:
            return json.load(response)
    except HTTPError as error:
        raise URLError(f'{error.code}: {error.read().decode()[:500]}') from error

with grafana_forward() as proc:
    def ready():
        assert proc.poll() is None, 'Grafana port-forward exited; ensure port 13000 is free'
        data = get('/api/health')
        assert data.get('database') == 'ok', data
    retry(ready)
    sources = get('/api/datasources')
    prometheus = next(s['uid'] for s in sources if s['type'] == 'prometheus')
    def query_metric(expression):
        result = get('/api/datasources/proxy/uid/' + prometheus + '/api/v1/query?' + urlencode({'query': expression}))
        assert result['status'] == 'success' and result['data']['result'], expression
        assert any(float(row['value'][1]) >= 1 for row in result['data']['result']), expression
    for expression in ['kube_node_info', 'node_uname_info', 'up{job="apiserver"}',
                       'up{service="loki"}', 'up{service="alloy"}',
                       'kube_deployment_status_replicas_available{namespace="incident-desk",deployment="incident-desk"}']:
        retry(lambda: query_metric(expression))
        print('PASS metric:', expression)
    # Generate a real app HTTP log. The marker is not sent directly to Loki.
    marker = 'observability-check-' + uuid.uuid4().hex
    code = ("import urllib.request,urllib.error; "
            f"url='http://incident-desk.incident-desk.svc.cluster.local/{marker}'; "
            "\ntry: urllib.request.urlopen(url,timeout=10)\nexcept urllib.error.HTTPError as e: assert e.code == 404\n")
    run('-n', 'incident-desk', 'exec', 'deploy/incident-desk', '--', 'python', '-c', code)
    def log_seen():
        query = '{namespace="incident-desk"} |= "' + marker + '"'
        data = get('/api/datasources/proxy/uid/loki/loki/api/v1/query_range?' + urlencode({
            'query': query, 'since': '10m', 'limit': '20'}))
        assert data['status'] == 'success' and data['data']['result'], 'Waiting for app log in Loki'
    retry(log_seen)
    print('PASS log pipeline: Incident Desk stdout -> Alloy -> Loki -> Grafana')
    if args.restart_check:
        historical_time = str(time.time())
        expression = 'node_uname_info'
        path = '/api/datasources/proxy/uid/' + prometheus + '/api/v1/query?' + urlencode({
            'query': expression, 'time': historical_time})
        before = get(path)['data']['result']
        assert before, 'Expected a pre-restart sample'
        for workload in ['statefulset/prometheus-monitoring-prometheus', 'deployment/loki']:
            run('-n', 'monitoring', 'rollout', 'restart', workload)
            print(run('-n', 'monitoring', 'rollout', 'status', workload, '--timeout=600s'))
        def historical_metric():
            assert get(path)['data']['result'] == before, 'Pre-restart metric sample changed or disappeared'
        retry(historical_metric)
        retry(log_seen)
        print('PASS persistence: pre-restart metric and app log survived Prometheus and Loki pod replacement')
claims = json.loads(run('-n', 'monitoring', 'get', 'pvc', '-o', 'json'))['items']
assert len(claims) >= 4 and all(p['status']['phase'] == 'Bound' for p in claims), 'Expected four Bound monitoring PVCs'
print(run('-n', 'monitoring', 'get', 'pods,pvc'))
print('PASS observability checks. Incident records were not modified.')
