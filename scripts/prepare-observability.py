"""Validate the lab and create dedicated local monitoring storage and a Grafana secret."""
import json
from pathlib import Path
import secrets
import subprocess

ROOT = Path(__file__).resolve().parents[1]
K = ['bash', str(ROOT / 'scripts/kubectl.sh')]

def output(*args):
    return subprocess.check_output(K + list(args), text=True)

def apply(items):
    subprocess.run(K + ['apply', '--server-side', '-f', '-'],
                   input=json.dumps({'apiVersion': 'v1', 'kind': 'List', 'items': items}), text=True, check=True)

def quantity(value):
    for unit, multiplier in [('Ki', 1024), ('Mi', 1024**2), ('Gi', 1024**3)]:
        if value.endswith(unit):
            return float(value[:-len(unit)]) * multiplier
    return float(value)

nodes = json.loads(output('get', 'nodes', '-o', 'json'))['items']
if len(nodes) != 1 or nodes[0]['metadata']['name'] != 'lima-cka-lab':
    raise SystemExit('Expected exactly one lima-cka-lab node. Refusing to modify another cluster.')
node = nodes[0]
if not any(c['type'] == 'Ready' and c['status'] == 'True' for c in node['status']['conditions']):
    raise SystemExit('The lab node must be Ready before installing monitoring.')
if quantity(node['status']['allocatable']['memory']) < 7 * 1024**3:
    raise SystemExit('Expected an 8 GiB VM. Check VM memory before deploying this profile.')

# Check actual guest headroom before creating anything. Reruns can bypass only the
# extra RAM check when the existing monitoring workloads are already present.
existing = output('-n', 'monitoring', 'get', 'deployment', 'monitoring-grafana', '--ignore-not-found', '-o', 'name').strip()
free_kib = int(subprocess.check_output(['limactl', 'shell', 'cka-lab', 'awk',
                                      '/MemAvailable:/ {print $2}', '/proc/meminfo'], text=True).strip())
free_bytes = int(subprocess.check_output(['limactl', 'shell', 'cka-lab', 'sh', '-c',
                                        "df -B1 --output=avail /var/lib | tail -n 1"], text=True).strip())
if not existing and free_kib < 2 * 1024**2:
    raise SystemExit('Less than 2 GiB memory available in the guest; free resources before installing.')
if free_bytes < 12 * 1024**3:
    raise SystemExit('Less than 12 GiB free in the VM. Resolve disk pressure before installing.')

stores = [('prometheus', '3Gi', '1000:2000'), ('alertmanager', '1Gi', '1000:2000'),
          ('grafana', '1Gi', '472:472'), ('loki', '3Gi', '10001:10001')]
items = [
    {'apiVersion': 'v1', 'kind': 'Namespace', 'metadata': {'name': 'monitoring'}},
    {'apiVersion': 'storage.k8s.io/v1', 'kind': 'StorageClass',
     'metadata': {'name': 'cka-observability'}, 'provisioner': 'kubernetes.io/no-provisioner',
     'volumeBindingMode': 'WaitForFirstConsumer', 'reclaimPolicy': 'Retain'},
]
for name, size, owner in stores:
    path = '/var/lib/cka-observability/' + name
    subprocess.run(['limactl', 'shell', 'cka-lab', 'sudo', 'mkdir', '-p', path], check=True)
    subprocess.run(['limactl', 'shell', 'cka-lab', 'sudo', 'chown', owner, path], check=True)
    subprocess.run(['limactl', 'shell', 'cka-lab', 'sudo', 'chmod', '0770', path], check=True)
    items.append({'apiVersion': 'v1', 'kind': 'PersistentVolume',
                  'metadata': {'name': 'cka-observability-' + name,
                               'labels': {'observability-store': name}},
                  'spec': {'capacity': {'storage': size}, 'volumeMode': 'Filesystem',
                           'accessModes': ['ReadWriteOnce'], 'persistentVolumeReclaimPolicy': 'Retain',
                           'storageClassName': 'cka-observability', 'local': {'path': path},
                           'nodeAffinity': {'required': {'nodeSelectorTerms': [{'matchExpressions': [
                               {'key': 'kubernetes.io/hostname', 'operator': 'In',
                                'values': [node['metadata']['labels']['kubernetes.io/hostname']]}]}]}}}})
items.append({'apiVersion': 'v1', 'kind': 'PersistentVolumeClaim',
              'metadata': {'name': 'grafana-data', 'namespace': 'monitoring'},
              'spec': {'storageClassName': 'cka-observability', 'accessModes': ['ReadWriteOnce'],
                       'selector': {'matchLabels': {'observability-store': 'grafana'}},
                       'resources': {'requests': {'storage': '1Gi'}}}})
apply(items)
if not output('-n', 'monitoring', 'get', 'secret', 'grafana-admin', '--ignore-not-found', '-o', 'name').strip():
    apply([{'apiVersion': 'v1', 'kind': 'Secret',
            'metadata': {'name': 'grafana-admin', 'namespace': 'monitoring'},
            'stringData': {'admin-user': 'admin', 'admin-password': secrets.token_urlsafe(32)}}])
print('Dedicated monitoring storage and Grafana credentials are ready.')
