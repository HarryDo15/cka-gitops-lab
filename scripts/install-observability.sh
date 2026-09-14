#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
export KUBECONFIG="$ROOT/.local/kubeconfig"
command -v helm >/dev/null || { echo 'Install Helm first: brew install helm' >&2; exit 1; }
[[ -f "$KUBECONFIG" ]] || { echo 'Start the lab first: bash scripts/up.sh' >&2; exit 1; }
umask 077
export HELM_CACHE_HOME="$ROOT/.local/helm/cache"
export HELM_CONFIG_HOME="$ROOT/.local/helm/config"
export HELM_DATA_HOME="$ROOT/.local/helm/data"
mkdir -p .local/observability/charts
K=(bash scripts/kubectl.sh)
"${K[@]}" get --raw=/readyz
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts --force-update
helm repo update prometheus-community
CHART=.local/observability/charts/kube-prometheus-stack-89.2.0.tgz
helm pull prometheus-community/kube-prometheus-stack --version 89.2.0 --destination .local/observability/charts
helm lint "$CHART" -f observability/prometheus-values.yaml
helm template monitoring "$CHART" --namespace monitoring --include-crds \
  -f observability/prometheus-values.yaml > .local/observability/monitoring-rendered.yaml
"${K[@]}" kustomize observability > .local/observability/logging-rendered.yaml
python3 scripts/prepare-observability.py
helm upgrade --install monitoring "$CHART" --namespace monitoring \
  -f observability/prometheus-values.yaml --wait --timeout 15m
"${K[@]}" apply -k observability
"${K[@]}" apply -f observability/service-monitors.yaml
"${K[@]}" -n monitoring rollout status deployment/loki --timeout=1200s
"${K[@]}" -n monitoring rollout status deployment/alloy --timeout=1200s
"${K[@]}" -n monitoring rollout status statefulset/prometheus-monitoring-prometheus --timeout=600s
"${K[@]}" -n monitoring rollout status statefulset/alertmanager-monitoring-alertmanager --timeout=600s
python3 -u scripts/verify-observability.py
