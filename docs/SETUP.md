# Setup and implementation checklist

## 1. Host prerequisites

Lima 2.2.0 is installed. Existing tools include Docker, Git, and kubectl v1.34.1. The planned Kubernetes v1.34.11 matches the installed kubectl minor version. The Mac has enough capacity for the initial 4-vCPU, 8-GiB VM; reduce other heavy workloads if memory pressure becomes noticeable.

The template is adapted from Lima's v2.2.0 `k8s.yaml` and pins Kubernetes packages and control-plane images to 1.34.11. Flannel is pinned to v0.28.5. The Ubuntu base image is resolved through Lima's bundled `ubuntu-lts` template; this is not a fully immutable VM build.

## 2. Bootstrap the VM

From the repository root:

```bash
bash scripts/up.sh
bash scripts/kubectl.sh get nodes -o wide
bash scripts/kubectl.sh get pods -A
limactl shell cka-lab sudo kubeadm version
limactl shell cka-lab sudo systemctl status kubelet --no-pager
```

Expected outcome: exactly one Ready node, running control-plane components, CoreDNS, and Flannel. The script writes `.local/kubeconfig`, which is excluded from Git and contains administrative credentials. It does not modify your default kubectl context.

The template configures containerd's systemd cgroup driver, disables swap during provisioning, enables forwarding, and removes the control-plane taint for single-node scheduling. Validate swap remains disabled after a reboot as part of the bootstrap checks.

If startup fails:

```bash
limactl list
limactl shell cka-lab sudo tail -n 100 /var/log/cloud-init-output.log
limactl shell cka-lab sudo journalctl -u kubelet -n 100 --no-pager
```

Do not delete the VM as the first troubleshooting step. Inspect the failed provisioning phase and repair it; this is useful CKA practice.

## 3. Install Argo CD

After the node is healthy:

```bash
bash scripts/install-argocd.sh
bash scripts/kubectl.sh -n argocd get pods
bash scripts/kubectl.sh -n argocd port-forward svc/argocd-server 8081:443
```

Open `https://localhost:8081`. The initial installation uses a self-signed certificate. In another terminal, retrieve the initial admin password locally:

```bash
bash scripts/kubectl.sh -n argocd get secret argocd-initial-admin-secret \
  -o jsonpath='{.data.password}' | base64 --decode
```

Use username `admin`, change the password after login, and keep credentials out of commits. Argo CD is not yet connected to any repository.

## 4. Finish the application deployment

The starter API uses Python's standard library and SQLite:

| Endpoint | Behavior |
| --- | --- |
| `GET /` | Application information and configurable welcome message |
| `GET /healthz` | Process liveness |
| `GET /readyz` | Database accessibility |
| `GET /incidents` | List stored incidents |
| `POST /incidents` | Create an incident from `{"title":"Investigate failed rollout"}` |

Still to implement in `deploy/`:

- A namespace and Kustomize configuration.
- One-replica Deployment with `Recreate` strategy for the initial SQLite workload.
- Service, ConfigMap for `WELCOME_MESSAGE`, readiness and liveness probes on port 8080.
- CPU and memory requests/limits, non-root security context, and disabled automatic service-account token mounting.
- Static local PersistentVolume and matching PVC, with node affinity and `Retain` reclaim policy. Mount `/var/lib/incident-desk` at `/data` for UID/GID 10001.

The local directory is created by the VM provisioning script. A local PV has node affinity and does not provide failover or a hard filesystem quota merely because its requested capacity is set. Keep one API replica initially; separate the database before exploring horizontal scaling.

## 5. Connect GitLab CI and GitOps

Required user-specific information: GitLab instance and project URL, repository visibility, available runner, and registry access method. Do not paste access tokens into this document.

Recommended initial arrangement: GitLab-hosted source and registry, a hosted CI runner, and Argo CD in the local cluster. This avoids running a full GitLab server on the Mac.

Implement `.gitlab-ci.yml` with these stages:

1. Test API behavior and validate Kubernetes manifests.
2. Build an image supporting `linux/arm64`, or a multi-platform image supporting both `linux/arm64` and `linux/amd64`.
3. Push to `$CI_REGISTRY_IMAGE` using an immutable commit tag, preferably recording the image digest for deployment.
4. Propose a change to the image reference under `deploy/` through a merge request. Keep promotion explicit and avoid pipelines recursively committing to themselves.
5. After merge, let Argo CD detect and sync the change.

A runner's architecture and privilege policy determine whether to use native ARM builds, BuildKit, or Docker Buildx with emulation. Decide this before writing the build job. Hosted CI does not need inbound access to the Mac's Kubernetes API; Argo CD pulls from GitLab.

For a private repository, configure an Argo CD repository credential with read-only repository access. For a private image registry, create an image pull secret using a deploy token with `read_registry`, then reference it from the workload. CI's short-lived job token is not a suitable persistent image-pull credential. Store credentials in GitLab variables and Kubernetes Secrets, not committed YAML; base64 is not encryption.

Still to implement in `gitops/`:

- `project.yaml`: an AppProject limited to the selected repository and application namespace.
- `application.yaml`: an Application pointing to `deploy/`, with `REPLACE_REPO_URL` as the connection-script placeholder.

Only after these files exist, run:

```bash
bash scripts/connect-gitlab.sh https://gitlab.com/YOUR_GROUP/YOUR_PROJECT.git
```

Begin with manual sync so troubleshooting edits remain visible. When enabling automated sync and self-heal, suspend them before break/fix drills and restore them afterward.

## 6. Acceptance checks

- [ ] One kubeadm node is Ready and system pods are healthy.
- [ ] Argo CD components are healthy and its local UI is reachable.
- [ ] GitLab pipeline tests and builds an ARM64-compatible image successfully.
- [ ] Argo CD reports the application Synced and Healthy at the intended commit.
- [ ] A POST creates an incident and a subsequent GET returns it.
- [ ] Deleting the application pod preserves the incident after recreation.
- [ ] A merged image update reaches the cluster and a Git revert restores the previous release.
- [ ] VM stop/start recovers the node and application with data intact.

These checks are pending; no end-to-end deployment has been verified.

## Daily operations

```bash
# Stop the lab to release CPU and RAM; disk is preserved.
limactl stop cka-lab

# Resume and refresh the project kubeconfig.
bash scripts/up.sh

# Enter the node for administration exercises.
limactl shell cka-lab
```

Deletion is intentionally not part of the normal workflow. Back up application data and etcd before any VM deletion or destructive recovery exercise.

## Optional GitHub publication

The local Git repository can be pushed after creating an empty GitHub repository and choosing its visibility:

```bash
git remote add origin git@github.com:YOUR_ACCOUNT/cka-gitops-lab.git
git push -u origin main
```

No GitHub repository has been created or published by this setup. If GitHub becomes the source of truth, explicitly configure mirroring to GitLab so CI and Argo CD observe the same commits.
