#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
mkdir -p .local
if limactl list --format '{{.Name}}' | grep -qx cka-lab; then
  limactl start cka-lab
else
  limactl start --name cka-lab --tty=false infra/kubeadm.yaml
fi
SOURCE="$(limactl list cka-lab --format '{{.Dir}}')/copied-from-guest/kubeconfig.yaml"
cp "$SOURCE" .local/kubeconfig
chmod 600 .local/kubeconfig
bash scripts/kubectl.sh wait --for=condition=Ready node --all --timeout=300s
bash scripts/kubectl.sh get nodes -o wide
