# Project ideas and CKA practice

## Project choices

| Project | What to build | Administration practice |
| --- | --- | --- |
| **Incident Desk — recommended starter** | Incident API with persistent records, then add a frontend and PostgreSQL | Deployments, Services, probes, ConfigMaps, PVCs, rollback, database backup |
| Background job platform | API, queue, worker, scheduled cleanup | Jobs, CronJobs, graceful shutdown, resource pressure, scheduling, DNS |
| Internal documentation portal | Static frontend and small backend with Git-driven releases | Services, ingress or Gateway API controller, TLS, RBAC, rollout troubleshooting |
| Backup and recovery service | Scheduled database backups, restore jobs, integrity reports | CronJobs, Secrets, volume mounts, retention, restore verification |

Incident Desk is deployed and verified, including storage persistence, Argo CD manual sync, and the Service-selector exercise. The other ideas are proposed extensions, not implemented features.

## Suggested progression

### Phase 1 — Understand the node

Bring the cluster up, then find `/etc/kubernetes/manifests`, `/etc/kubernetes/pki`, `/var/lib/kubelet`, the kubelet systemd unit, and containerd configuration. Explain why the control plane runs as static pods and how kubelet recreates them.

Practice `kubectl get`, `describe`, `logs`, `exec`, events, `journalctl`, and `crictl`. Confirm the node's runtime, architecture, cgroup driver, pod CIDR, and taints. Success means tracing a failing pod from Kubernetes events down to its node runtime.

### Phase 2 — Deploy and expose Incident Desk

Create the namespace, Deployment, Service, ConfigMap, and storage manifests described in [SETUP.md](SETUP.md). Use port-forwarding for the initial API access. Check DNS from a separate temporary pod and inspect EndpointSlices.

Break the Service selector and diagnose the missing endpoints. Break the readiness path and explain why the container runs but receives no Service traffic. Repair both in Git.

### Phase 3 — Persistence and recovery

Create an incident, replace its pod, and verify the record remains. Inspect PV/PVC binding, access modes, reclaim policy, and local PV node affinity. Intentionally mismatch a PVC request in an isolated exercise and explain why it remains Pending.

Create a consistent SQLite backup using its backup API, then restore and verify records. Copy backups outside the VM so deleting its disk does not destroy both the application and its backup. Later migrate to PostgreSQL and repeat with database-native backup tooling.

### Phase 4 — GitLab CI and Argo CD

Implement the build and promotion flow. Track a source commit through pipeline, registry image, deployment manifest, and running pod image ID. Introduce an invalid image reference, diagnose ImagePullBackOff, and recover with a Git revert.

Test manual sync first. Then enable self-heal and observe what happens after an imperative edit. Before deliberate break/fix practice, disable automated reconciliation so it does not silently repair the fault you are studying.

### Phase 5 — Access and resource management

Create a namespace-scoped read-only Role and RoleBinding. Verify allowed and denied operations with `kubectl auth can-i`. Add a LimitRange and ResourceQuota, and diagnose a rejected workload.

Add a Secret through a local command or approved secret workflow. Explain why a base64-encoded Secret committed to Git exposes its contents.

For NetworkPolicy exercises, first install a policy-capable network solution. Then prove allowed and blocked traffic using real connection tests; the presence of a NetworkPolicy object alone does not prove enforcement.

### Phase 6 — Node maintenance and control-plane recovery

Cordon the node and observe a newly created pod remain Pending, then uncordon it. Plan a drain and explain why a single node cannot reschedule workloads elsewhere. A PodDisruptionBudget can block voluntary eviction; it cannot create spare capacity.

Practice kubelet log inspection and recovery from a deliberately introduced configuration error after saving the original file. Keep a node shell open so you can recover when the API is unavailable.

Take and validate an etcd snapshot using tools appropriate to the installed etcd version. Document the snapshot location, certificates, and restore procedure. Perform an actual restore only after an independent backup and a clear recovery plan; a snapshot file alone is not proof of recoverability.

Plan a sequential minor-version kubeadm upgrade, checking supported version skew and CNI compatibility against current Kubernetes documentation before changing packages. Record the pre/post node and component versions.

## Limits of a one-node lab

- It supports real kubeadm, static-pod, etcd, kubelet, runtime, and application administration practice.
- It cannot demonstrate high availability, rescheduling onto another node, realistic topology spread, or cross-node networking.
- Draining or stopping the only node can interrupt all applications.
- Local persistent storage stays attached to that VM and is not replicated.
- GitLab CI and Argo CD add useful delivery practice; they supplement the core administration exercises.

For each drill, keep a short record: symptom, evidence, root cause, repair, and verification. Progress toward timed troubleshooting after completing the same task once with documentation.
