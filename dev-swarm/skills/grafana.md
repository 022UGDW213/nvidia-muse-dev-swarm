# Grafana Dashboard Engineer runbook

Agent: `devops-12` — Builds dashboards and visualization in Grafana.

## When to use
Use for dashboards, variables, alert rules, datasource config.

## Key commands
- `grafana-cli admin reset-admin-password x`
- `provisioning: dashboards/datasources YAML under /etc/grafana/provisioning`

## Gotchas
- Template dashboards with variables; one dashboard per service, not per host.
- Provision dashboards as code so they survive upgrades.
- Alerting: prefer Grafana managed alerts over panel alerts.
