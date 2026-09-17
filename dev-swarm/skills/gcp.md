# GCP Cloud Engineer runbook

Agent: `devops-24` — Builds and operates workloads on Google Cloud.

## When to use
Use for GCE/GKE/IAM/Storage, gcloud work, budget guardrails.

## Key commands
- `gcloud compute instances list`
- `gsutil rsync -r ./dist gs://bucket`
- `gcloud iam service-accounts list`

## Gotchas
- Budgets are alerts, not hard caps; pair with quotas.
- Service accounts: one per workload, minimal roles.
- Enable audit logs before you need them.
