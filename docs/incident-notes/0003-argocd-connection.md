# Argo CD integration checkpoint — 10 September 2026

Installed the pinned Argo CD v3.5.2 manifests. Initial container downloads were slow enough to exceed the installer readiness timeout. Transfers continued without pull errors; an extended readiness wait completed successfully without reinstalling or resetting the cluster.

Configured a read-only GitHub deploy key for `HarryDo15/cka-gitops-lab`. Its private half is stored only in the ignored local directory and the Kubernetes repository Secret. Created the restricted `cka-lab` AppProject and `incident-desk` Application.

After the repository server became Ready, refreshed the initial comparison error and completed the first manual sync. Observed:

- All seven Argo CD pods Ready and Running.
- Application `Synced / Healthy`.
- Sync operation `Succeeded` at GitHub revision `7ba7a3e7974706fd513c3577bf14622004b1db9e`.
- Manual sync retained; pruning disabled for this operation.
- Both existing persistence-test incidents readable through Service DNS after sync.

GitLab CI has not been configured or run. The Service-selector exercise is ready but has not been performed. The lab was stopped after verification to preserve its disk for the next session. These notes and the verifier fix are included in the session milestone commit. See [the handoff](../HANDOFF.md) for resume steps.
