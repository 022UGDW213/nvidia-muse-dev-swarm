# ELK Logging Engineer runbook

Agent: `devops-13` — Centralizes and queries logs with the Elastic stack.

## When to use
Use for index design, pipeline parsing, Kibana queries, retention.

## Key commands
- `GET /logs-*/_search`
- `PUT /_ilm/policy/logs-30d`
- `filebeat test config`
- `logstash -t -f pipeline.conf`

## Gotchas
- Set explicit mappings; dynamic mapping explosions kill clusters.
- ILM rollover keeps shard counts sane; don't hand-roll retention.
- Parse at the edge (Filebeat) to keep Logstash simple.
