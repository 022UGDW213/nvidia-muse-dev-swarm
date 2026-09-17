# Pulumi IaC Developer runbook

Agent: `devops-06` — Manages infrastructure as real code with Pulumi.

## When to use
Use for Pulumi programs, stacks, previews and policy.

## Key commands
- `pulumi preview --diff`
- `pulumi up --yes`
- `pulumi stack init prod`
- `pulumi config set --secret dbPass x`
- `pulumi destroy --yes`
- `pulumi stack rm dev`

## Gotchas
- Use `--secret` for config; plaintext config leaks in state.
- Passphrase or KMS backend for stack secrets is required.
- Preview diffs before every `up`; code review the diff.
