"""Prompt locally for a GitLab registry deploy token and install an image pull secret."""
import base64
import getpass
import json
from pathlib import Path
import subprocess

registry = input("Registry host [registry.gitlab.com]: ").strip() or "registry.gitlab.com"
username = input("Deploy token username: ").strip()
token = getpass.getpass("Deploy token (read_registry): ")
if not username or not token:
    raise SystemExit("Username and token are required")
config = {"auths": {registry: {"auth": base64.b64encode(f"{username}:{token}".encode()).decode()}}}
secret = {
    "apiVersion": "v1", "kind": "Secret",
    "metadata": {"name": "gitlab-registry", "namespace": "incident-desk"},
    "type": "kubernetes.io/dockerconfigjson",
    "stringData": {".dockerconfigjson": json.dumps(config)},
}
root = Path(__file__).resolve().parents[1]
subprocess.run(["bash", str(root / "scripts/kubectl.sh"), "apply", "--server-side", "-f", "-"],
               input=json.dumps(secret), text=True, check=True)
print("Secret installed. Reference gitlab-registry in the Deployment's imagePullSecrets before promotion.")
