#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
bash scripts/kubectl.sh -n argocd patch application incident-desk --type merge \
  -p '{"operation":{"sync":{"prune":false},"initiatedBy":{"username":"lab-operator"}}}'
bash scripts/kubectl.sh -n argocd get application incident-desk
