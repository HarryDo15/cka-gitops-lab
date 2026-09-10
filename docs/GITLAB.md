# GitLab CI with GitHub version control

GitHub `HarryDo15/cka-gitops-lab` is the source of truth. Argo CD can read this private repository using a dedicated read-only deploy key. GitLab hosts a second copy for CI and the image registry.

## Current connection — 10 September 2026

Private project: [haithanh23.15/cka-gitops-lab](https://gitlab.com/haithanh23.15/cka-gitops-lab), project ID `86290156`. Local remote `gitlab` uses HTTPS. GitHub remains authoritative.

Source revision `f8161cd96be06d4f8459ccd2481de12dffb9a029` was pushed successfully. [Pipeline #1](https://gitlab.com/haithanh23.15/cka-gitops-lab/-/pipelines/2835609825) failed before creating any jobs. A direct pipeline request returned: `Identity verification is required in order to run CI jobs`.

Account verification was completed. [Pipeline #2](https://gitlab.com/haithanh23.15/cka-gitops-lab/-/pipelines/2835617750) passed all three jobs against source revision `f8161cd`. The published ARM64 image digest is `sha256:aa93c22c55221d33eaf598cea063fd590a0463457e7a12c9eb82a6d296300eb0`.

A project deploy token scoped only to `read_registry` is installed as Kubernetes Secret `incident-desk/gitlab-registry`. The Deployment references it through `imagePullSecrets`. The token value was not written to Git or local files. GitHub promotion commit `761a0f3` was manually synced through Argo CD; the running pod image ID matches the published digest, the application is `Synced / Healthy`, and incidents #1–#3 survived.

The initial SSH push failed host-key verification. The successful HTTPS push used the existing `glab auth docker-helper` credential through an ignored local Git credential adapter; no token was stored in the remote URL or committed. On this Mac, repeat with:

```bash
git -c credential.helper= \
  -c 'credential.helper=!python3 /Users/haido/Projects/cka-gitops-lab/.local/gitlab-credential-helper.py' \
  push gitlab main
```

The adapter is local-only. On another checkout, configure GitLab HTTPS authentication locally or verified SSH access before pushing.

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

Pipeline #2 verified this configuration on GitLab-hosted runners. For a self-managed runner, check its user namespace/AppArmor settings against [GitLab's BuildKit guidance](https://docs.gitlab.com/ci/docker/using_buildkit/).

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
