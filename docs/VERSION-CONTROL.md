# Version-control checkpoints

Group related work into substantial, verified milestones before committing and pushing. Do not push every small edit or documentation change. This preference is recorded in `AGENTS.md` for future coding sessions.

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

1. Cluster bootstraps successfully, the node is Ready, and setup documentation matches the working system.
2. Incident Desk is deployed, API behavior and persistent storage are verified, and the first exercise is documented.
3. Argo CD is connected and GitLab CI builds an image that can be promoted and deployed.
4. A group of related CKA exercises is complete, with diagnosis and recovery notes.

Include related code, tests, scripts, and documentation in the same milestone commit. Keep the existing commit history; this preference applies to new work.

These are workflow reminders, not scheduled notifications.
