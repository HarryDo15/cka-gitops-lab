"""Verify Service DNS, API writes, and persistence across a Deployment restart."""
import json
from pathlib import Path
import subprocess
import uuid

ROOT = Path(__file__).resolve().parents[1]
K = ["bash", str(ROOT / "scripts/kubectl.sh")]


def run(*args):
    return subprocess.check_output(K + list(args), text=True)


def api(payload=None):
    code = (
        "import json,urllib.request; "
        "url='http://incident-desk.incident-desk.svc.cluster.local/incidents'; "
        f"data={None if payload is None else json.dumps(payload).encode()!r}; "
        "req=urllib.request.Request(url,data=data,headers={'Content-Type':'application/json'}); "
        "print(urllib.request.urlopen(req,timeout=10).read().decode())"
    )
    return json.loads(run("-n", "incident-desk", "exec", "deploy/incident-desk", "--", "python", "-c", code))


def pod_uid():
    pods = json.loads(run("-n", "incident-desk", "get", "pods", "-l", "app=incident-desk", "-o", "json"))
    return {p["metadata"]["uid"] for p in pods["items"] if not p["metadata"].get("deletionTimestamp")}


marker = "persistence-check-" + uuid.uuid4().hex[:12]
incident = api({"title": marker})
assert incident["title"] == marker, incident
before = pod_uid()
print(f"Created incident {incident['id']} through Service DNS; restarting the application.")
print(run("-n", "incident-desk", "rollout", "restart", "deployment/incident-desk"))
print(run("-n", "incident-desk", "rollout", "status", "deployment/incident-desk", "--timeout=180s"))
assert before.isdisjoint(pod_uid()), "Expected a replacement pod"
assert incident in api(), "Record was lost after pod recreation"
print("PASS: Service DNS, API create/read, replacement pod, and persistent data.")
