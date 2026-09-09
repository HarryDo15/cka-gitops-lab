# Version-control checkpoints

Commit and push after each small, working milestone: a repaired exercise, passing application change, verified deployment, or documentation update. This preference is also recorded in `AGENTS.md` for future coding sessions.

```bash
git status --short
git diff
# Run the checks appropriate to your change.
git add <specific-files>
git diff --cached --check
git diff --cached
git commit -m "Describe the working change"
git push origin main
git status --short --branch
```

Use a branch and pull request for experiments you do not want deployed from `main`. Git is for source and configuration; never add `.local/`, kubeconfigs, database files, private keys, or tokens.

Suggested checkpoints:

1. Cluster bootstraps and node is Ready.
2. API tests pass and the workload survives pod recreation.
3. Argo CD reads the repository and syncs successfully.
4. GitLab produces a tested ARM64 image.
5. A digest-pinned promotion is deployed and verified.
6. Each completed CKA break/fix exercise, with a short incident note.

These are workflow reminders, not scheduled notifications.
