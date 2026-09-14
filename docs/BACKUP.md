# Incident Desk backup and isolated restore

Run from the project directory while the cluster and app are running:

```bash
python3 scripts/backup-app.py
```

The command uses SQLite's online backup API inside the app pod, streams the snapshot to `.local/backups/` on your Mac, restores it into a separate temporary database, and starts an isolated copy of the local Incident Desk API on a loopback port. It compares every restored incident with the snapshot and checks `/readyz`. The live database is never overwritten.

A successful run prints `PASS` and writes a JSON verification report next to the database, including its SHA-256 and incident count. Database and report files use mode 0600 and remain ignored by Git. Interrupted transfers remain `.db.partial`; a database without a passing report has not completed verification. Remote temporary snapshot files are removed on normal completion.

The script requires access to the Kubernetes API and permission to bind a local HTTP port. Run it from your terminal if an agent sandbox blocks either capability.

The host copy is outside the VM, so VM deletion will not remove it. It is still on the same Mac. This backs up application data only, not cluster configuration, registry credentials, or etcd. There is no automatic backup schedule or retention cleanup yet.

## Verification status — 14 September 2026

The cluster resumed and all 16 pods became Ready. An offline test verified snapshot integrity, record preservation and temporary-file cleanup against a fixture database.

The agent's live attempts were blocked by its network sandbox. The user then ran `python3 scripts/backup-app.py` in their terminal successfully at 06:36 UTC on 14 September 2026. All three incidents were restored and checked through the isolated API; integrity and HTTP reads passed. The saved backup hash, SQLite integrity, and incident count were independently checked against the report afterward.

Verified backup: `.local/backups/incident-desk-20260914T063604872644Z.db`; its matching `.json` file records the checks. Earlier failed attempts left unverified files with no success report; use the verified snapshot. This exercise proves an isolated application-data restore, not an in-place production recovery or a cluster/etcd restore.
