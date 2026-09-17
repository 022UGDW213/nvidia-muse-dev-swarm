# GitLab CI Engineer runbook

Agent: `devops-08` — Builds CI/CD pipelines with GitLab CI.

## When to use
Use for pipeline YAML, runners, environments, releases.

## Key commands
- `glab pipeline list`
- `glab ci lint`
- `glab pipeline view <id>`
- `gitlab-runner verify`
- `glab variable set KEY val --masked`

## Gotchas
- `rules:` replaced `only/except`; mixing both is a classic bug.
- Mask and protect variables holding secrets.
- Cache vs artifacts: cache is best-effort, artifacts are guaranteed.
