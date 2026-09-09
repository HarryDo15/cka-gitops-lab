#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
mkdir -p .local
chmod 700 .local
KEY=.local/argocd-github
if [[ ! -f "$KEY" ]]; then
  ssh-keygen -q -t ed25519 -N '' -C cka-lab-argocd -f "$KEY"
fi
# Deploy keys are read-only unless --allow-write is supplied.
TITLE="cka-lab-argocd-$(ssh-keygen -lf "$KEY.pub" | awk '{print $2}')"
if ! gh repo deploy-key list --repo HarryDo15/cka-gitops-lab | grep -Fq "$TITLE"; then
  gh repo deploy-key add "$KEY.pub" --repo HarryDo15/cka-gitops-lab --title "$TITLE"
fi
python3 - <<'PY'
import json, subprocess
from pathlib import Path
secret = {
    'apiVersion': 'v1', 'kind': 'Secret',
    'metadata': {'name': 'github-cka-lab', 'namespace': 'argocd',
                 'labels': {'argocd.argoproj.io/secret-type': 'repository'}},
    'stringData': {'type': 'git', 'url': 'git@github.com:HarryDo15/cka-gitops-lab.git',
                   'sshPrivateKey': Path('.local/argocd-github').read_text()},
}
subprocess.run(['bash', 'scripts/kubectl.sh', 'apply', '--server-side', '-f', '-'],
               input=json.dumps(secret), text=True, check=True)
PY
bash scripts/connect-gitlab.sh git@github.com:HarryDo15/cka-gitops-lab.git
