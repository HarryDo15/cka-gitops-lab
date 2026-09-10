# Application deployment checkpoint — 10 September 2026

Resumed the existing VM with `bash scripts/up.sh`. The node returned to Ready and all eight system/network pods returned to Running after the overnight shutdown.

Built the ARM64 bootstrap image inside the VM with `bash scripts/bootstrap-app.sh`. The namespace, local PV, StorageClass, PVC, ConfigMap, Service, and Deployment were applied successfully; the application became available.

All seven host API tests passed. `python3 scripts/verify-app.py` created an incident through Service DNS, replaced the pod, and confirmed the saved incident remained available.

The first verification exposed a brief connection refusal immediately after rollout readiness. A subsequent Service request returned the original record. The verifier now retries reads for up to 30 seconds to allow Service routing to converge; it does not retry writes. The revised verification passed, including recovery from the transient refusal.

The test incidents remain in the application for inspection. Argo CD and GitLab CI are still pending. The Service-selector exercise is prepared but has not been performed.
