# Setup and daily use

Run commands from `/Users/haido/Projects/cka-gitops-lab`. The README records what has actually been verified; this guide describes the complete workflow.

## 1. Start the single-node cluster

```bash
bash scripts/up.sh
bash scripts/kubectl.sh get nodes -o wide
bash scripts/kubectl.sh get pods -A
```

Lima creates a native ARM64 Linux VM with 4 CPUs, 8 GiB RAM, and a 50 GiB disk. The template pins Kubernetes to 1.34.11 and Flannel to v0.28.5. Its base image comes from Lima 2.2.0's Ubuntu LTS template. Initial downloads can be slow.

The VM uses containerd, systemd cgroups, and kubeadm. Its only node schedules both control-plane and application pods. The host API endpoint is `https://127.0.0.1:16443`.

Always use `bash scripts/kubectl.sh` or explicitly export this project's `.local/kubeconfig`. The wrapper does not change your default Kubernetes context. The kubeconfig contains administrative credentials and must remain outside Git.

Troubleshooting:

```bash
limactl list
limactl shell cka-lab sudo tail -n 100 /var/log/cloud-init-output.log
limactl shell cka-lab sudo journalctl -u kubelet -n 100 --no-pager
limactl shell cka-lab sudo kubeadm version
limactl shell cka-lab sudo swapon --show
```

Expected: one Ready node, healthy CoreDNS and Flannel, and no active swap. Inspect errors before restarting or rebuilding the VM.

## 2. Bootstrap Incident Desk

```bash
bash scripts/bootstrap-app.sh
python3 scripts/verify-app.py
bash scripts/kubectl.sh -n incident-desk port-forward svc/incident-desk 8080:80
```

The bootstrap script builds `docker.io/library/incident-desk:bootstrap` directly into the VM's Kubernetes containerd image store. This initial image does not require a registry. The manifest's `IfNotPresent` policy lets kubelet use it. Use this script for the initial bootstrap; after registry promotion, the GitOps image reference becomes authoritative.

The local build tag is deliberately a bootstrap convenience. Application source changes require another build and a pod restart until the GitLab image workflow is connected. CI promotions use immutable digests instead.

The API runs as UID/GID 10001 with a read-only root filesystem and a writable `/data` mount. Its SQLite database resides on a static local PV at `/var/lib/incident-desk` in the VM. A single replica and `Recreate` deployment strategy avoid concurrent rollout replicas sharing the database. Local storage is not replicated; declared PV capacity is not a filesystem quota.

In another terminal:

```bash
curl http://127.0.0.1:8080/healthz
curl http://127.0.0.1:8080/readyz
curl -H 'Content-Type: application/json' \
  -d '{"title":"Investigate failed rollout"}' http://127.0.0.1:8080/incidents
curl http://127.0.0.1:8080/incidents
```

`verify-app.py` creates a small test incident through Service DNS, restarts the Deployment, checks that the pod was replaced, and verifies that the record remains. It intentionally leaves the test record for inspection.

The PV uses `Retain` and the PVC has Argo CD `Prune=false`. These reduce accidental cleanup risk, but neither replaces a backup. Deleting the VM destroys its disk and local application data.

## 3. Install and connect Argo CD

```bash
bash scripts/install-argocd.sh
bash scripts/connect-github.sh
bash scripts/sync-app.sh
bash scripts/kubectl.sh -n argocd get applications
```

Argo CD is pinned to v3.5.2. `connect-github.sh` generates an ignored local SSH key and adds its public half as a read-only deploy key to `HarryDo15/cka-gitops-lab`. The private half is installed as a Kubernetes repository Secret. The account-wide GitHub CLI credential is not given to Argo CD.

The AppProject permits only the configured repository, `incident-desk` namespace, and the required application resource types. The namespace, StorageClass, and PV are bootstrapped outside Argo CD. There is no automatic application deletion finalizer.

Sync is manual for predictable break/fix practice. After a GitHub push, Argo CD detects the desired revision; run `sync-app.sh` or use the UI to apply it. Wait for Synced and Healthy before calling the deployment verified:

```bash
bash scripts/kubectl.sh -n argocd get application incident-desk \
  -o jsonpath='{.status.sync.status}{" / "}{.status.health.status}{"\n"}'
```

UI access:

```bash
bash scripts/kubectl.sh -n argocd port-forward svc/argocd-server 8081:443
```

Open `https://localhost:8081` and use username `admin`. The initial installation has a self-signed certificate. Retrieve the initial password only in your local terminal:

```bash
bash scripts/kubectl.sh -n argocd get secret argocd-initial-admin-secret \
  -o jsonpath='{.data.password}' | base64 --decode
```

Change the password after login and keep it out of commits.

## 4. Connect GitLab CI

See [GITLAB.md](GITLAB.md) for the second Git remote, runner requirements, registry credentials, and digest promotion workflow. GitHub remains the source of truth. GitLab CI builds the image; Argo CD pulls the deployment configuration from GitHub.

Before promoting a private registry image:

```bash
python3 scripts/registry-secret.py
```

This prompts locally for a deploy token with `read_registry` and sends it directly to Kubernetes. Add the following under the Deployment's `spec.template.spec`, then commit and push:

```yaml
imagePullSecrets:
  - name: gitlab-registry
```

No GitLab credentials should be committed. A successful local test is not evidence that the remote pipeline has run; verify its first execution in GitLab.

## 5. Daily operations and checkpoints

```bash
# Pause the VM; preserve its disk.
limactl stop cka-lab

# Resume and refresh kubeconfig.
bash scripts/up.sh

# Work inside the node.
limactl shell cka-lab

# Run API tests on the host.
python3 -m unittest discover -s app -p 'test_*.py' -v
```

After each working change or completed exercise, review, commit, and push. See [VERSION-CONTROL.md](VERSION-CONTROL.md). The private GitHub repository is [HarryDo15/cka-gitops-lab](https://github.com/HarryDo15/cka-gitops-lab), with `main` tracking `origin/main`.

Flannel alone does not enforce NetworkPolicy. Add a policy-capable network solution before claiming that isolation exercises work. A one-node cluster also cannot demonstrate failover onto another node.
