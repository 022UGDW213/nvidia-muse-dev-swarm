# PostgreSQL DBA runbook

Agent: `devops-19` — Operates PostgreSQL: backups, replication, tuning.

## When to use
Use for slow queries, replication lag, backups, upgrades.

## Key commands
- `EXPLAIN (ANALYZE, BUFFERS) SELECT ...;`
- `pg_basebackup -D /backup -Ft -z -P`
- `SELECT * FROM pg_stat_replication;`
- `VACUUM (ANALYZE, VERBOSE) t;`
- `pg_dump -Fc db > db.dump`

## Gotchas
- Test restores, not just backups; untested backups are wishes.
- Missing indexes show up in pg_stat_user_tables seq_scan counts.
- Never run DDL without checking for lock queues on busy tables.
