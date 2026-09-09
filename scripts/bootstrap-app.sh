#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
mkdir -p .local
COPYFILE_DISABLE=1 tar -czf .local/app.tar.gz -C app Dockerfile server.py
limactl copy .local/app.tar.gz cka-lab:/tmp/incident-desk-app.tar.gz
limactl shell cka-lab bash -c 'mkdir -p /tmp/incident-desk-build && tar -xzf /tmp/incident-desk-app.tar.gz -C /tmp/incident-desk-build && sudo nerdctl --namespace k8s.io build -t docker.io/library/incident-desk:bootstrap /tmp/incident-desk-build'
bash scripts/kubectl.sh apply -f infra/storage.yaml
bash scripts/kubectl.sh apply -k deploy
bash scripts/kubectl.sh -n incident-desk rollout status deployment/incident-desk --timeout=180s
