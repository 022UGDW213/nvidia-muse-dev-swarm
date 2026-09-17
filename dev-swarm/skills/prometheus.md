# Prometheus Monitoring Engineer runbook

Agent: `devops-11` — Instruments and alerts with Prometheus + Alertmanager.

## When to use
Use for PromQL queries, alert rules, exporter gaps, cardinality.

## Key commands
- `rate(http_requests_total[5m])`
- `histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket[5m])) by (le))`
- `promtool check rules rules.yml`
- `amtool config routes test --config.file=am.yml`

## Gotchas
- High cardinality labels (user IDs) will OOM your Prometheus.
- `rate()` needs range >= 4x scrape interval to be stable.
- Alert on symptoms (latency/errors), not causes (CPU).
