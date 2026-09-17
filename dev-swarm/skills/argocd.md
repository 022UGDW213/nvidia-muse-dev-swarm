# Argo CD GitOps Operator runbook

Agent: `devops-10` — Runs GitOps continuous delivery with Argo CD.

## When to use
Use for Application manifests, sync failures, drift, promotions.

## Key commands
- `argocd app list`
- `argocd app sync myapp --prune`
- `argocd app diff myapp`
- `argocd app get myapp --show-operation`
- `argocd admin settings rbac can megan get applications`

## Gotchas
- OutOfSync is normal; investigate only Unknown/Degraded.
- Use sync waves + hooks to order DB migrations before app rollout.
- Auto-sync + prune in prod needs branch protection discipline.
