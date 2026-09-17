# Service Mesh Engineer runbook

Agent: `devops-30` — Runs Istio/Linkerd meshes: mTLS, routing, resilience.

## When to use
Use for sidecars, mTLS, canary routing, mesh upgrades.

## Key commands
- `istioctl analyze -A`
- `kubectl get vs -A`
- `linkerd check`
- `istioctl proxy-config cluster deploy/x`

## Gotchas
- mTLS STRICT mode breaks anything without a sidecar; migrate carefully.
- Mesh upgrades: control plane first, then data plane.
- Start with Linkerd if Istio's complexity isn't justified.
