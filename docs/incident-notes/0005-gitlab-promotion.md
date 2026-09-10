# GitLab CI and registry promotion — 10 September 2026

## Verified delivery chain

| Step | Evidence |
| --- | --- |
| Private GitLab project | `haithanh23.15/cka-gitops-lab`, ID `86290156` |
| Source revision | `f8161cd96be06d4f8459ccd2481de12dffb9a029` |
| Successful pipeline | [#2 / 2835617750](https://gitlab.com/haithanh23.15/cka-gitops-lab/-/pipelines/2835617750) |
| Test job | `16410864977`, success |
| ARM64 BuildKit build and push | `16410864978`, success |
| Promotion artifact job | `16410864979`, success |
| Image | `registry.gitlab.com/haithanh23.15/cka-gitops-lab@sha256:aa93c22c55221d33eaf598cea063fd590a0463457e7a12c9eb82a6d296300eb0` |
| GitHub promotion commit | `761a0f3cfcd9f804e85d0a406e3ab1d4bc8121fb` |
| Argo CD | Manual sync Succeeded; `Synced / Healthy` |
| Running pod | `incident-desk-7c47ff6fcd-zxlzr`, Ready; image ID matches published digest |
| Data | Incidents #1, #2 and resolved Service exercise #3 remained readable through Service DNS |

## Setup issues resolved

The initial SSH push failed host-key verification. Used HTTPS with the existing GitLab credential helper instead. No credentials are stored in remote URLs.

Pipeline #1 failed before jobs were created because GitLab required account identity verification. The user completed verification; pipeline #2 then ran successfully. GitLab CI lint independently returned valid with no errors or warnings.

Created a project deploy token scoped only to `read_registry` and passed its value directly into the Kubernetes `gitlab-registry` Secret. The token is not committed. The deployment references that Secret and the immutable image digest.

Validated the manifests with a server-side dry run, pushed the promotion to GitHub, manually synced Argo CD, waited for rollout readiness, compared the actual pod image ID to the artifact digest, and read existing incidents through the Service.

## Current state

The lab is running. GitHub remains authoritative; GitLab holds source revision `f8161cd` used by the verified pipeline. Promotion and later documentation commits live on GitHub. Push subsequent source changes to GitLab when a new CI build is wanted. Manual Argo CD sync remains enabled for break/fix practice.
