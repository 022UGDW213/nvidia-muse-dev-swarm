# Ansible Automation Engineer runbook

Agent: `devops-05` — Automates config management with Ansible playbooks and roles.

## When to use
Use for playbooks, inventory, idempotent config enforcement.

## Key commands
- `ansible-playbook -i inv site.yml --check --diff`
- `ansible all -i inv -m ping`
- `ansible-vault encrypt secrets.yml`
- `ansible-galaxy install -r requirements.yml`
- `ansible-playbook site.yml --limit web --tags nginx`

## Gotchas
- Design tasks idempotent; reruns must be no-ops.
- `--check --diff` first on anything touching production.
- Vault-encrypt secret files; never commit plaintext.
