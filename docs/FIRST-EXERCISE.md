# Exercise 1: the Service has no endpoints

Goal: diagnose an unreachable application without deleting the cluster or its data. Run this only after the application is healthy. Argo CD should remain in manual-sync mode.

## Establish the baseline

```bash
bash scripts/kubectl.sh -n incident-desk get pods,svc,pvc
bash scripts/kubectl.sh -n incident-desk get endpointslices \
  -l kubernetes.io/service-name=incident-desk
bash scripts/kubectl.sh -n incident-desk exec deploy/incident-desk -- \
  python -c "import urllib.request; print(urllib.request.urlopen('http://incident-desk/healthz', timeout=5).read().decode())"
```

Expected: Ready pod, Bound PVC, an EndpointSlice containing the pod address, and an HTTP response with status `ok`.

## Introduce one fault

```bash
bash scripts/kubectl.sh -n incident-desk patch service incident-desk \
  --type merge -p '{"spec":{"selector":{"app":"wrong-label"}}}'
```

Repeat the HTTP request through the Service. It should fail even though the pod remains Ready. Inspect the Service selector, pod labels, and EndpointSlices until you can explain why.

A port-forward directly to a Deployment or pod can still work because it bypasses Service routing. Do not use that alone as proof that the Service is repaired.

## Repair and verify

Restore the configuration already stored in Git:

```bash
bash scripts/sync-app.sh
# Wait for the Argo CD operation to complete, then inspect:
bash scripts/kubectl.sh -n argocd get application incident-desk
bash scripts/kubectl.sh -n incident-desk get endpointslices \
  -l kubernetes.io/service-name=incident-desk
```

Repeat the HTTP request from the baseline. It should succeed again. If Argo CD has not been connected yet, use `bash scripts/kubectl.sh apply -k deploy` instead.

## Record the incident

After recovery, port-forward the Service in a separate terminal:

```bash
bash scripts/kubectl.sh -n incident-desk port-forward svc/incident-desk 8080:80
```

Create a record:

```bash
curl -H 'Content-Type: application/json' \
  -d '{"title":"Service unavailable","symptom":"HTTP requests through the Service failed","status":"investigating"}' \
  http://127.0.0.1:8080/incidents
```

Use the returned ID in place of `1`:

```bash
curl -X PATCH -H 'Content-Type: application/json' \
  -d '{"status":"resolved","cause":"Service selector did not match pod labels","diagnosis":"Pod remained Ready; EndpointSlice had no usable endpoints","fix":"Synced the correct selector from Git","verification":"HTTP request through Service DNS succeeded"}' \
  http://127.0.0.1:8080/incidents/1
```

The app tracks manually entered incidents about this cluster. It does not automatically monitor Kubernetes. When it is unavailable, take local notes and enter them after recovery.

## Version-control checkpoint

Write a short lesson in `docs/incident-notes/` containing your actual observations and commands. Keep credentials and database exports out of it. Review the note, commit it, and push to GitHub. No configuration commit is needed if the repair simply restored the existing desired state.
