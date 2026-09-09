# Incident: initial VM provisioning stopped before kubeadm installation

Date: 9 September 2026

## Symptom

The Linux VM and containerd were running, but Lima kept waiting for kubeadm. `cloud-final.service` had exited with status 1. There was no Kubernetes admin kubeconfig.

## Diagnosis

Inspected the cloud-init journal and generated provisioning scripts under `/mnt/lima-cidata/provision.system/`. Rerunning the prerequisite script exposed:

```text
install: invalid user: '10001'
```

The directory creation command attempted to set ownership to an application UID that was not registered as a Linux user. This image's `install` implementation rejected it.

After correcting ownership setup, package selection exited with status 141. The `apt-cache madison ... | awk ... exit` pipeline ran under `pipefail`; the early `awk` exit could give the producer SIGPIPE even after it printed the correct package version.

A subsequent provisioning stage had also written an empty containerd sandbox image because kubeadm was unavailable when it evaluated the image lookup.

## Repair

- Created the application data directory first, then set numeric ownership with `chown 10001:10001`.
- Changed package selection to consume the full input stream while selecting only the first match.
- Made GPG key import noninteractive and repeatable.
- Required a valid kubeadm sandbox image before generating runtime configuration.
- Installed the pinned Kubernetes packages and resumed the remaining bootstrap stages in the existing VM.

## Verification

Verified on 9 September 2026: Kubernetes v1.34.11 reports `lima-cka-lab` Ready; all eight control-plane, CoreDNS, kube-proxy, and Flannel pods are Running with zero restarts. The host API `/readyz` returns `ok`, `scripts/up.sh` refreshes the isolated kubeconfig successfully, and swap is disabled. The VM runs Ubuntu 26.04 LTS and containerd 2.3.3. Full VM stop/start recovery remains untested.

## Lesson

A running VM does not imply a running Kubernetes cluster. Inspect the failed provisioning phase and repair its partial state before attempting a cluster reset.
