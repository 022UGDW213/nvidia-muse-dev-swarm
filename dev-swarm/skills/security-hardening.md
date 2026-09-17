# Security Hardening Engineer runbook

Agent: `devops-26` — Hardens systems, images and configs against attack.

## When to use
Use for CIS baselines, SSH/TLS config, image scanning, audits.

## Key commands
- `lynis audit system`
- `trivy image app:1.0`
- `sshd -T | grep -i permit`
- `ufw status verbose`

## Gotchas
- Disable password auth on SSH; keys only.
- Scan images in CI; fail builds on critical CVEs.
- Hardening without patching is theater; patch first.
