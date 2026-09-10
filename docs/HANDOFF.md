# Session handoff — 10 September 2026

## Saved state

The `cka-lab` Lima VM is stopped intentionally. Its disk retains Kubernetes, Argo CD, the locally built Incident Desk image, and the SQLite database. Do not delete or recreate the VM to resume.

Completed and verified before shutdown:

- VM restart recovery: node Ready and all eight system/network pods Running.
- Incident Desk deployment and seven passing API tests.
- Service DNS, create/read requests, and persistence across pod replacement.
- Bounded read retries in the verifier for Service routing convergence after rollout.
- Argo CD v3.5.2: seven Ready pods, read-only GitHub deploy key, restricted AppProject, and manual sync.
- First sync Succeeded with `Synced / Healthy` at revision `7ba7a3e7974706fd513c3577bf14622004b1db9e`; both test incidents remained readable.

The session commit updates documentation and the verifier; deployment manifests are unchanged. Argo CD may show the newer GitHub revision after resuming. No automatic sync is enabled.

## Resume

```bash
cd /Users/haido/Projects/cka-gitops-lab
bash scripts/up.sh
k get pods -A
k -n incident-desk get pods,svc,pvc
k -n argocd get application incident-desk
```

Allow application and Argo CD pods to become Ready. `k` is a local zsh alias selecting this project's `.local/kubeconfig`; use `bash scripts/kubectl.sh` if the alias is unavailable. `up.sh` refreshes the kubeconfig.

For the API, run in a separate terminal:

```bash
k -n incident-desk port-forward svc/incident-desk 8080:80
```

Then visit `http://localhost:8080/healthz` or `http://localhost:8080/incidents`.

For Argo CD:

```bash
k -n argocd port-forward svc/argocd-server 8081:443
```

Open `https://localhost:8081`; username is `admin`. Retrieve the initial password only in your terminal, if it has not been changed:

```bash
k -n argocd get secret argocd-initial-admin-secret \
  -o jsonpath='{.data.password}' | base64 --decode
```

Keep credentials, `.local/`, deploy keys, and database files out of Git.

## Next work

1. Complete [the Service-selector troubleshooting exercise](FIRST-EXERCISE.md). It has not yet been performed.
2. Keep Argo CD sync manual; `bash scripts/sync-app.sh` requests a sync without pruning. Verify `Synced / Healthy` afterward.
3. Configure GitLab CI and registry integration using [GITLAB.md](GITLAB.md). The pipeline is scaffolded but has never run.

Application persistence was tested across pod replacement. A full VM restart with the newly installed app and Argo CD is the next recovery check; only the base cluster restart was tested today.
