# GitLab CI with GitHub version control

GitHub `HarryDo15/cka-gitops-lab` is the source of truth. Argo CD can read this private repository using a dedicated read-only deploy key. GitLab hosts a second copy for CI and the image registry.

## First-time connection

1. Create an empty private GitLab project called `cka-gitops-lab` under your account or group.
2. Authenticate Git to that GitLab instance locally.
3. Add the second remote and push:

```bash
git remote add gitlab https://gitlab.com/YOUR_NAMESPACE/cka-gitops-lab.git
git push gitlab main
```

The checked-in `.gitlab-ci.yml` starts a pipeline. It uses a Docker-compatible runner with rootless BuildKit support. GitLab-hosted Linux runners are the intended starting point. Runner availability, account verification and compute allowance must be checked on your account.

The image targets ARM64, matching the Mac's VM. Because the current Dockerfile only copies source and has no `RUN` instruction, the build can assemble the ARM64 image from an AMD64 runner without executing ARM binaries. If you add `RUN` steps, use a native ARM64 runner or configure emulation.

## Pipeline stages

- `test`: runs HTTP API tests, including invalid input and database failure behavior.
- `build`: rootless BuildKit pushes an image tagged with the commit SHA and exports its registry digest.
- `promotion`: creates `promoted-image.txt` and a digest-pinned `deploy/kustomization.yaml` as downloadable artifacts. It does not automatically commit to either repository.

Pipeline execution has not been verified until GitLab access is connected. For a self-managed runner, check its user namespace/AppArmor settings against [GitLab's BuildKit guidance](https://docs.gitlab.com/ci/docker/using_buildkit/).

## Private registry access

Create a GitLab deploy token with `read_registry`. Enter it locally when creating the Kubernetes image pull secret; never paste it into Git or chat. Attach the resulting secret to the workload's `imagePullSecrets`. A persistent deployment needs a deploy token rather than an expiring CI job token.

See [GitLab deploy token documentation](https://docs.gitlab.com/user/project/deploy_tokens/). Repository read access is not needed for the registry token while Argo CD uses GitHub.

## Promote a successful build

Download `promoted-image.txt` from a successful pipeline. Use its image reference:

```bash
python3 scripts/promote-image.py 'registry.gitlab.com/YOUR_NAMESPACE/cka-gitops-lab@sha256:ACTUAL_64_CHARACTER_DIGEST'
git diff -- deploy/kustomization.yaml
bash scripts/kubectl.sh apply --dry-run=server -k deploy
git add deploy/kustomization.yaml
git commit -m "Promote tested Incident Desk image"
git push origin main
bash scripts/sync-app.sh
bash scripts/kubectl.sh -n incident-desk rollout status deploy/incident-desk
```

The placeholder digest above is intentionally invalid. Replace the whole image reference with the artifact value.

Push source changes to `gitlab main` whenever you want a new CI build. Promotion-only commits need not be sent to GitLab immediately. Keep GitHub authoritative; do not independently edit both copies of `main`. Automatic mirroring can be configured later if your GitLab account supports the chosen mirroring feature.

**Checkpoint reminder:** group related work into a substantial, verified milestone before committing and pushing to GitHub.
