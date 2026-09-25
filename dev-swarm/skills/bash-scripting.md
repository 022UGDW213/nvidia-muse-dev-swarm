# Bash Scripting Specialist runbook

Agent: `devops-15` — Writes robust shell scripts and one-liners.

## When to use
Use for scripts, cron jobs, text processing, glue automation.

## Key commands
- `set -euo pipefail`
- `awk '{print $1}' file | sort | uniq -c | sort -nr`
- `find . -name '*.log' -mtime +7 -delete`
- `parallel -j8 cmd ::: args`

## Gotchas
- Always start scripts with `set -euo pipefail`.
- Quote every variable: "$var", never $var.
- Shellcheck your scripts before they run: it flags unquoted expansions, word-splitting and missing `-r` in `read` — the classes of bug that bite hardest in unattended cron jobs.
