# Azure Cloud Engineer runbook

Agent: `devops-25` — Builds and operates workloads on Azure.

## When to use
Use for VMs/VNet/AKS/Entra, az CLI, Bicep templates.

## Key commands
- `az vm list -o table`
- `az storage blob upload-batch ...`
- `az aks get-credentials -g rg -n cluster`

## Gotchas
- Resource groups are blast-radius boundaries; plan them.
- Managed identities beat stored credentials every time.
- Bicep over raw ARM JSON for sanity.
