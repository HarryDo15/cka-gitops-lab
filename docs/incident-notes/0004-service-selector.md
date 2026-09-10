# Service-selector exercise — 10 September 2026

## Recovery baseline

Resumed the existing VM with `bash scripts/up.sh`. Waited for all 16 pods to become Ready. Incident Desk retained test incidents #1 and #2 across the VM shutdown. Argo CD recovered with manual sync configured.

## Fault and diagnosis

Changed the Service selector using:

```bash
k -n incident-desk patch svc incident-desk --type merge \
  -p '{"spec":{"selector":{"app":"wrong-label"}}}'
k -n incident-desk get endpointslices -l kubernetes.io/service-name=incident-desk
k -n incident-desk get pods --show-labels
```

Observed zero ready Service endpoints and a failed HTTP request to `http://incident-desk/healthz` from inside the application pod. The application pod itself remained Ready. The selector no longer matched its `app=incident-desk` label.

An initial local exercise helper did not handle a null endpoints list. Its cleanup restored the Service through Argo CD before the corrected helper reran the full exercise successfully.

## Repair and verification

Ran `bash scripts/sync-app.sh`. Argo CD restored the selector from GitHub revision `f8161cd96be06d4f8459ccd2481de12dffb9a029`. Ready endpoints returned, Service DNS HTTP requests succeeded, and the Application returned to `Synced / Healthy`.

Created resolved incident #3 in Incident Desk with the symptom, diagnosis, cause, repair, and verification. No fault remains in the cluster or deployment manifests. Manual sync remains enabled.

## Lesson

A Ready pod does not prove the Service can route to it. Compare Service selectors with pod labels and inspect EndpointSlices before changing the application.
