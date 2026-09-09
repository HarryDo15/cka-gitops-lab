# CKA GitOps Practice Lab

A hands-on Kubernetes administration project for an Apple Silicon MacBook: one Linux VM bootstrapped with **kubeadm**, with **GitLab CI** for image builds and **Argo CD** for GitOps delivery.

## Current status — 9 September 2026

This repository contains an initial scaffold and a documented implementation plan. **The cluster is not running yet.**

| Component | Status |
| --- | --- |
| Host inspection | Apple Silicon, macOS 26.6.2, 24 GiB RAM, 10 CPU cores |
| Lima | Installed through Homebrew, version 2.2.0 |
| Kubernetes VM | Bootstrap started; Linux image download in progress |
| Kubernetes | Configured for v1.34.11; not installed or validated |
| Argo CD | Installation script prepared for v3.5.2; not installed |
| Example application | Seven API tests pass; deployment pending VM startup |
| Kubernetes application manifests | Deployment, Service, ConfigMap, PVC and local PV prepared; Kustomize rendering passes |
| GitLab CI | Test, ARM64 BuildKit build and promotion artifact jobs prepared; GitLab access and first run pending |
| Argo CD application | Restricted AppProject and manual-sync Application prepared; connection pending |
| Remote repository | Private GitHub repository: https://github.com/HarryDo15/cka-gitops-lab; GitLab not yet configured |

The local Git repository is connected to the private GitHub repository [HarryDo15/cka-gitops-lab](https://github.com/HarryDo15/cka-gitops-lab). GitHub holds the project documentation and source; the requested CI service remains GitLab. If both hosts are used, choose one authoritative repository and define a mirror process before enabling deployments.

## Intended architecture

```mermaid
flowchart LR
    Developer[Local Git checkout] --> GitLab[GitLab repository]
    GitLab --> CI[GitLab CI runner]
    CI --> Registry[GitLab Container Registry]
    CI --> Update[Propose deployment image update]
    Update --> GitLab
    subgraph MacBook
        subgraph Lima Linux VM — 4 CPUs / 8 GiB RAM / 50 GiB disk
            Kubernetes[Single kubeadm control-plane and workload node]
            Argo[Argo CD]
            App[Incident Desk API and persistent volume]
            Argo --> App
            Kubernetes --- App
        end
    end
    GitLab -->|Argo CD pulls desired state| Argo
    Registry -->|Node pulls ARM64 image| App
```

macOS hosts the Linux VM. Inside it, kubeadm manages a real control plane with etcd and static pods, kubelet, and containerd. The control-plane scheduling taint is removed so the same node can run applications. Lima forwards the Kubernetes API to `127.0.0.1:16443` to avoid the common Docker Desktop port 6443.

The VM has no host filesystem mounts. Application data is intended to live inside its disk at `/var/lib/incident-desk`. Stopping the VM preserves that disk; deleting the VM destroys its local data.

The initial template uses Flannel. **Flannel alone does not enforce Kubernetes NetworkPolicy.** Add a policy-capable CNI or compatible policy engine before attempting network isolation exercises.

## Repository layout

```text
app/                       Python API and container image definition
infra/kubeadm.yaml          Adapted Lima v2.2.0 kubeadm template
scripts/up.sh              Create/start VM and copy isolated kubeconfig
scripts/kubectl.sh         kubectl wrapper using this project's kubeconfig
scripts/install-argocd.sh   Install pinned Argo CD manifests
scripts/connect-gitlab.sh  Scaffold; requires missing GitOps manifests
docs/SETUP.md              Installation and remaining integration work
docs/PRACTICE.md           Project ideas and CKA exercises
```

## Start here

Read [the setup guide](docs/SETUP.md) before running commands. The next infrastructure step is:

```bash
cd /Users/haido/Projects/cka-gitops-lab
bash scripts/up.sh
```

This downloads a Linux image and Kubernetes packages and creates the VM. The scripts are prepared but have not yet been validated against a running cluster.

For project options and exercises, see [the practice plan](docs/PRACTICE.md).

## References

- [Lima Kubernetes template, v2.2.0](https://github.com/lima-vm/lima/blob/v2.2.0/templates/k8s.yaml) — source of the adapted infrastructure template.
- [Lima virtual machine drivers](https://lima-vm.io/docs/config/vmtype/) — native macOS virtualization.
- [Installing kubeadm](https://kubernetes.io/docs/setup/production-environment/tools/kubeadm/install-kubeadm/).
- [Creating a kubeadm cluster](https://kubernetes.io/docs/setup/production-environment/tools/kubeadm/create-cluster-kubeadm/).
- [GitLab BuildKit integration](https://docs.gitlab.com/ci/docker/using_buildkit/).
- [Argo CD installation](https://argo-cd.readthedocs.io/en/stable/operator-manual/installation/).

Versions here record the choices made during setup, rather than a promise that they are the latest available releases.

## Version-control habit

Commit and push after each tested milestone or completed exercise. See [the checkpoint guide](docs/VERSION-CONTROL.md).

## First troubleshooting exercise

[Break and repair a Service selector](docs/FIRST-EXERCISE.md), then record its symptom, diagnosis, cause, fix, and verification in Incident Desk. Incidents are entered manually; this app is not a cluster monitoring agent.
