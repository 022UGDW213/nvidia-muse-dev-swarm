# Kubernetes Operator runbook

Agent: `devops-02` — Deploys and debugs workloads on Kubernetes clusters.

## When to use
Use for manifests, kubectl triage, scheduling, RBAC, upgrades.

## Key commands
- `kubectl get pods -A -o wide`
- `kubectl describe pod <p>`
- `kubectl logs -f deploy/<d> --previous`
- `kubectl rollout status deploy/<d>`
- `kubectl apply -f manifests/`
- `kubectl top pods -A`
- `kubectl auth can-i --list --as=system:serviceaccount:ns:sa`

## Gotchas
- Always set requests/limits; no limits = noisy-neighbor evictions.
- CrashLoopBackOff: check `logs --previous` before redeploying.
- Apply is declarative; avoid imperative edits on live objects.
