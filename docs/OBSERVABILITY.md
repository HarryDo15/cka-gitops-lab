# Monitoring and logging for the CKA lab

## Status — 14 September 2026

**Deployed and verified on the local kubeadm cluster; VM subsequently stopped at the user’s request.** Start it with `bash scripts/up.sh` before accessing Grafana. The following health results were recorded before shutdown. All eight observability pods are Ready and all four monitoring PVCs are Bound. Helm 4.3.0 is installed; release `monitoring` is deployed at revision 4. Helm lint/render and the live checks passed for node metadata, Linux metrics, API-server scraping, Loki/Alloy scraping, Incident Desk replica availability, and a real app log queried through Grafana.

The controlled restart check also passed: the identical historical metric sample and unique pre-restart app log survived Prometheus and Loki pod replacement. This verifies telemetry persistence across pod replacement; a full VM restart and Alertmanager silence persistence were not tested in this milestone.

The configuration, scripts and verification notes are grouped into one observability milestone.

## Components

| Component | Purpose | Configuration |
| --- | --- | --- |
| Prometheus | Collect Kubernetes, node and container metrics | kube-prometheus-stack chart 89.2.0; 30-second scrape interval |
| Grafana | Kubernetes dashboards and log exploration | Chart-bundled version; generated admin credential in a Kubernetes Secret |
| Alertmanager | Group and display alerts | Local-only receiver; no email, Slack or other notification configured |
| kube-state-metrics | Report workload and resource state | Chart dependency |
| node-exporter | Report Linux node metrics | Chart dependency |
| Loki | Store and query pod logs | Image 3.7.7; one process with filesystem storage |
| Alloy | Discover pods and send their logs to Loki | Image v1.19.2; read-only access to pods and pod logs |

Prometheus handles metrics, not log storage. Alloy reads pod stdout/stderr through the Kubernetes API without privileged filesystem mounts. It does not collect host journald or Kubernetes Event objects. Use `limactl shell cka-lab sudo journalctl -u kubelet` and `kubectl get events` for those sources.

The app has no `/metrics` endpoint yet. Its availability is observed through deployment state, and its HTTP activity through logs. The `IncidentDeskUnavailable` alert fires after two minutes with no available replica; it does not detect a broken Service selector when the pod itself is healthy.

## Install

```bash
cd /Users/haido/Projects/cka-gitops-lab
brew install helm
bash scripts/install-observability.sh
```

If the VM is stopped, first run `bash scripts/up.sh`. Do not recreate it.

The installer:

1. Checks the API, downloads the pinned monitoring chart, runs Helm lint and renders it under ignored `.local/observability/`.
2. Verifies the expected single Ready node, at least 7 GiB allocatable RAM, 2 GiB available guest memory for the initial installation, and 12 GiB free guest disk.
3. Creates a `monitoring` namespace, a separate `cka-observability` StorageClass, four local PVs, and a Grafana credential if none exists.
4. Installs the monitoring chart, then applies Loki, Alloy and their ServiceMonitors.
5. Checks real Prometheus metrics and traces a unique HTTP request log from Incident Desk through Alloy and Loki into Grafana.

It never edits Incident Desk or its database and never changes Argo CD's sync policy. The log check makes a harmless request to a nonexistent API route; this intentionally creates a 404 log line.

The stack is initially managed by Helm plus the checked-in logging manifests. It is **not yet an Argo CD application**. The existing namespace-restricted application project must not be widened merely to install cluster-wide monitoring CRDs and RBAC. A dedicated infrastructure AppProject can be added after this stack works.

## Deployment findings

- Slow first image downloads exceeded Grafana's initial rollout deadline. The pods subsequently became Ready; rerunning the installer recovered without deleting data. Logging deployments allow 20 minutes for startup.
- Helm merged the chart's default Alertmanager child route with our local receiver. Explicit `routes: []` removes the stale reference to `null`.
- Grafana's automatic plugin updater attempted to replace the bundled Loki plugin on its read-only filesystem. The update failed and made the datasource unavailable. `grafana.ini.plugins.preinstall_disabled: true` keeps the image's bundled plugins; restarting Grafana restored Loki queries. Grafana uses `Recreate` to avoid concurrent SQLite users during upgrades.

## Access Grafana

```bash
bash scripts/kubectl.sh -n monitoring port-forward svc/monitoring-grafana 3000:80
```

Open **http://localhost:3000**, username `admin`. In a separate terminal retrieve the password:

```bash
bash scripts/kubectl.sh -n monitoring get secret grafana-admin \
  -o jsonpath='{.data.admin-password}' | base64 --decode
```

Keep the password out of chat and Git. If you change it in Grafana, update the Secret through a local credential workflow too: the verifier authenticates using that Secret.

Browse the provisioned **Kubernetes / Compute Resources** dashboards. In **Explore**, choose Prometheus or Loki.

Useful PromQL:

```promql
kube_deployment_status_replicas_available{namespace="incident-desk"}
sum by (namespace) (rate(container_cpu_usage_seconds_total{container!="",container!="POD"}[5m]))
sum by (namespace) (container_memory_working_set_bytes{container!="",container!="POD"})
node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes
```

Useful LogQL:

```logql
{namespace="incident-desk"}
{namespace="incident-desk"} |= "404"
{namespace="argocd"} |~ "(?i)error|warn"
{namespace="kube-system"}
```

For direct metrics/alert views:

```bash
bash scripts/kubectl.sh -n monitoring port-forward svc/monitoring-prometheus 9090:9090
# In another terminal, if needed:
bash scripts/kubectl.sh -n monitoring port-forward svc/monitoring-alertmanager 9093:9093
```

## Sizing and coverage limits

The resource requests total roughly 1.2 GiB RAM plus chart helper containers. Limits permit higher usage. Before installation, the running VM had 6.3 GiB available memory and 41 GiB free disk; the installer also checks capacity before modifying the cluster.

| Store | PV capacity | Retention |
| --- | --- | --- |
| Prometheus | 3 GiB | 2 days or approximately 2 GB of TSDB blocks, whichever is reached first |
| Loki | 3 GiB | 48 hours, deleted asynchronously by the compactor |
| Grafana | 1 GiB | Persistent dashboard/user state |
| Alertmanager | 1 GiB | 48 hours of alert data; persistent silences/state |

The PVs use distinct directories under `/var/lib/cka-observability/` and `Retain`. **Local PV capacity does not enforce a disk quota.** Loki's time retention is not a strict size limit; a noisy workload can fill the shared VM disk before records expire. Watch `node_filesystem_avail_bytes`, reduce verbosity/retention if necessary, and leave free space for etcd, images and the app. Prometheus WAL/head data also consume space beyond its block-retention target.

Alloy uses temporary local state; collector restarts can replay logs or lose data during prolonged outages. This is a learning setup, not a durable audit pipeline. Stopping the VM also stops monitoring, and losing the VM disk loses its telemetry. There is no external uptime check or alert delivery.

Scraping of kubeadm's loopback-bound scheduler, controller-manager and kube-proxy endpoints, and certificate-protected etcd metrics, is disabled. API-server, kubelet/cAdvisor, node and workload metrics remain configured. Some bundled control-plane dashboards consequently have empty panels. Do not expose those endpoints broadly simply to remove a gap.

Services are ClusterIP and user access is through loopback port-forwarding. Loki has no authentication inside this lab. Flannel does not enforce NetworkPolicy, so pod-to-pod isolation is not provided by this configuration. Monitoring improves visibility; it does not make the single node highly available or harden cluster access by itself.

## Verify and practice

```bash
python3 scripts/verify-observability.py
bash scripts/kubectl.sh -n monitoring get pods,pvc
```

The verifier temporarily uses local port 13000 and stops its own port-forward afterward. Keep that port free. It checks node metadata, Linux metrics, app replica availability, log ingestion through Grafana's datasource proxy, and Bound PVCs.

For a controlled Prometheus and Loki pod replacement, run `python3 scripts/verify-observability.py --restart-check`. It saves a metric query at a fixed pre-restart time, generates a unique app log, replaces both pods, and checks that the same historical sample and log remain queryable. Then use the existing Service-selector exercise and compare pod readiness, Service endpoints and app logs. For the replica alert, use a readiness-failure exercise and wait for its two-minute `for` duration.

If deployment fails, inspect the first error instead of uninstalling the stack:

```bash
bash scripts/kubectl.sh -n monitoring get events --sort-by=.metadata.creationTimestamp
bash scripts/kubectl.sh -n monitoring describe pods
bash scripts/kubectl.sh -n monitoring logs deploy/alloy --tail=100
bash scripts/kubectl.sh -n monitoring logs deploy/loki --tail=100
```

Do not delete PVCs to resolve a Pending pod. Inspect selectors, node affinity, requests, ownership and existing PV claim bindings. Helm upgrades across future chart versions may require separate CRD upgrade steps; the installer deliberately pins 89.2.0.

For subsequent changes, verify the combined result and commit/push **one complete milestone**.

## References

- [Pinned monitoring chart](https://github.com/prometheus-community/helm-charts/tree/kube-prometheus-stack-89.2.0/charts/kube-prometheus-stack)
- [Alloy Kubernetes pod log source](https://grafana.com/docs/alloy/latest/reference/components/loki/loki.source.kubernetes/)
- [Alloy health endpoints](https://grafana.com/docs/alloy/latest/reference/http/)
- [Grafana plugin configuration](https://grafana.com/docs/grafana/latest/setup-grafana/configure-grafana/#plugins)
- [Loki retention and compaction](https://grafana.com/docs/loki/latest/operations/storage/retention/)
