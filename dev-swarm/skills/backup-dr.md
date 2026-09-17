# Backup & DR Engineer runbook

Agent: `devops-28` — Designs backups and disaster recovery that actually restore.

## When to use
Use for backup design, RPO/RTO, restore drills, replication.

## Key commands
- `restic snapshots`
- `restic check`
- `pg_basebackup ...`
- `velero backup create daily --include-namespaces prod`

## Gotchas
- A backup you never restored is not a backup.
- 3-2-1 rule: 3 copies, 2 media, 1 offsite.
- Document the restore runbook; panic is not a procedure.
