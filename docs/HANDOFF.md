# Session handoff — 10 September 2026

## Saved state

The `cka-lab` Lima VM is running after the latest verification session. Its disk retains Kubernetes, Argo CD, the promoted GitLab registry image and cached bootstrap image, and the SQLite database. Do not delete or recreate the VM to resume.

Completed and verified:

- VM restart recovery: node Ready and all eight system/network pods Running.
- Incident Desk deployment and seven passing API tests.
- Service DNS, create/read requests, and persistence across pod replacement.
- Bounded read retries in the verifier for Service routing convergence after rollout.
- Argo CD v3.5.2: seven Ready pods, read-only GitHub deploy key, restricted AppProject, and manual sync.
- First sync Succeeded with `Synced / Healthy` at revision `7ba7a3e7974706fd513c3577bf14622004b1db9e`; both test incidents remained readable.

GitHub promotion commit `761a0f3` selects the successful GitLab pipeline #2 image by digest and references the registry pull Secret. The running pod image ID was verified against that digest. No automatic sync is enabled. Later documentation-only commits do not change the deployment.

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

1. The [Service-selector troubleshooting exercise](FIRST-EXERCISE.md) passed and is recorded as resolved incident #3. See [the exercise evidence](incident-notes/0004-service-selector.md).
2. Keep Argo CD sync manual; `bash scripts/sync-app.sh` requests a sync without pruning. Verify `Synced / Healthy` afterward.
3. GitLab CI and registry promotion are complete. [Pipeline #2](https://gitlab.com/haithanh23.15/cka-gitops-lab/-/pipelines/2835617750) passed; source `f8161cd` produced image digest `sha256:aa93c22c55221d33eaf598cea063fd590a0463457e7a12c9eb82a6d296300eb0`, deployed by GitHub commit `761a0f3`. Follow [GITLAB.md](GITLAB.md) for subsequent source pushes and promotions.
4. Continue the optional exercises in [PRACTICE.md](PRACTICE.md): readiness failures, backup/restore, RBAC, resource quotas, and node maintenance. These future exercises are not claimed as completed.

Full VM restart with Incident Desk and Argo CD passed: all 16 pods became Ready, and test incidents #1 and #2 remained readable through Service DNS. Initial DNS requests during startup failed transiently; wait for pods to become Ready before verifying Service access.
