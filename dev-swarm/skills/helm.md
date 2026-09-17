# Helm Chart Engineer runbook

Agent: `devops-03` — Packages and releases applications as Helm charts.

## When to use
Use for chart authoring, templating bugs, releases and rollbacks.

## Key commands
- `helm template ./chart --values vals.yaml | less`
- `helm upgrade --install app ./chart -n prod --atomic --timeout 10m`
- `helm lint ./chart`
- `helm rollback app 2`
- `helm get values app -n prod`
- `helm unittest ./chart`

## Gotchas
- `--atomic` auto-rolls back failed upgrades; use it in CI.
- Quote template values that may parse as YAML types.
- Never store secrets in values.yaml; use external-secrets.
