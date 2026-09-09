# Working on this lab

- Use `bash scripts/kubectl.sh` for cluster operations to select the lab kubeconfig.
- Keep `.local/`, kubeconfigs, private keys, access tokens, and database files out of Git.
- Group related changes into large, tested milestones before committing and pushing: a working cluster, a verified application deployment, and a working CI/GitOps flow. The user explicitly corrected the earlier frequent-push preference; do not commit or push each small change.
- Remind the user to commit and push after completing a substantial milestone or a group of related practice exercises.
- Update documentation with observed status. Distinguish a prepared pipeline from one that has actually run.
- Use manual Argo CD sync during break/fix exercises; explain any change to reconciliation behavior.
- Preserve application data and avoid resetting or deleting the VM without explicit authorization.
