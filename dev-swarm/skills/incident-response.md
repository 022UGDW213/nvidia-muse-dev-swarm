# Incident Response Engineer runbook

Agent: `devops-27` — Leads incident triage, mitigation and postmortems.

## When to use
Use for outages, Sev triage, comms, postmortem writeups.

## Key commands
- `kubectl get events -A --sort-by=.lastTimestamp | tail -20`
- `journalctl --since '30 min ago' -p err`
- `git log --oneline -20  # what changed recently?`

## Gotchas
- Mitigate first, root-cause later; MTTR beats perfect diagnosis.
- What changed? Deploys/config changes cause most incidents.
- Write the postmortem within 48h or the lessons evaporate.
