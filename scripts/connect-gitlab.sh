#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
REPO_URL="${1:?Usage: bash scripts/connect-gitlab.sh https://gitlab.com/group/project.git}"
case "$REPO_URL" in https://*.git|git@github.com:*.git) ;; *) echo 'Use an HTTPS Git URL or a GitHub SSH URL ending in .git' >&2; exit 1;; esac
export REPO_URL
mkdir -p .local
python3 - <<'PY'
import json, os
from pathlib import Path
for name in ('project', 'application'):
    p = Path(f'gitops/{name}.yaml').read_text()
    Path(f'.local/{name}.yaml').write_text(p.replace('REPLACE_REPO_URL', json.dumps(os.environ['REPO_URL'])))
PY
bash scripts/kubectl.sh apply -f .local/project.yaml
bash scripts/kubectl.sh apply -f .local/application.yaml
