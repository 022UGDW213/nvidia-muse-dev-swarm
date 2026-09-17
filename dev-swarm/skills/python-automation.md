# Python Automation Developer runbook

Agent: `devops-16` — Automates ops tasks with Python.

## When to use
Use for Python tooling, API clients, data munging, SDK work.

## Key commands
- `python3 -m venv .venv && . .venv/bin/activate`
- `pip install --user --break-system-packages pkg`
- `python3 -m py_compile script.py`
- `ruff check .`

## Gotchas
- Pin dependencies; unpinned pip installs rot.
- Never `shell=True` with untrusted input.
- Log structured output; print-debugging doesn't scale.
