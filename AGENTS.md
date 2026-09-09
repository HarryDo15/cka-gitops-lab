# Working on this lab

- Use `bash scripts/kubectl.sh` for cluster operations to select the lab kubeconfig.
- Keep `.local/`, kubeconfigs, private keys, access tokens, and database files out of Git.
- At each tested, coherent milestone, review the diff, commit, and push to GitHub. The user explicitly requests frequent version-control checkpoints.
- Remind the user to commit and push after completing each practice exercise.
- Update documentation with observed status. Distinguish a prepared pipeline from one that has actually run.
- Use manual Argo CD sync during break/fix exercises; explain any change to reconciliation behavior.
- Preserve application data and avoid resetting or deleting the VM without explicit authorization.
