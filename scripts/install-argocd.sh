#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
K=(bash scripts/kubectl.sh)
mkdir -p .local
curl --fail --location --silent --show-error https://raw.githubusercontent.com/argoproj/argo-cd/v3.5.2/manifests/install.yaml -o .local/argocd-install.yaml
"${K[@]}" create namespace argocd --dry-run=client -o yaml | "${K[@]}" apply -f -
"${K[@]}" apply --server-side -n argocd -f .local/argocd-install.yaml
"${K[@]}" -n argocd wait --for=condition=Available deployment --all --timeout=600s
"${K[@]}" -n argocd rollout status statefulset/argocd-application-controller --timeout=600s
