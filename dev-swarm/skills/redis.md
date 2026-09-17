# Redis Operator runbook

Agent: `devops-20` — Operates Redis caches, queues and stores.

## When to use
Use for memory, persistence, replication, latency issues.

## Key commands
- `redis-cli INFO memory`
- `redis-cli --latency-history`
- `redis-cli --rdb dump.rdb`
- `CONFIG GET maxmemory*`
- `redis-cli --bigkeys`

## Gotchas
- Set maxmemory + eviction policy; OOM kills the process.
- KEYS * blocks; use SCAN in production.
- AOF everysec is the sane durability default.
