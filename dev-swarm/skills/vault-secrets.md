# Vault Secrets Engineer runbook

Agent: `devops-22` — Manages secrets with HashiCorp Vault.

## When to use
Use for Vault policies, auth methods, dynamic creds, rotation.

## Key commands
- `vault kv put secret/app key=val`
- `vault policy write app policy.hcl`
- `vault auth enable approle`
- `vault operator unseal`
- `vault token create -policy=app -ttl=1h`

## Gotchas
- Root token is break-glass only; revoke it after init.
- Short TTLs + renewal beat long-lived tokens.
- Back up Raft snapshots; losing Vault = losing everything.
