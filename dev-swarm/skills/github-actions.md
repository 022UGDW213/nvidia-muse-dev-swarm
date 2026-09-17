# GitHub Actions Engineer runbook

Agent: `devops-07` — Builds CI/CD pipelines with GitHub Actions.

## When to use
Use for workflow authoring, caching, releases, runner issues.

## Key commands
- `gh workflow run ci.yml -f ref=main`
- `gh run list --limit 5`
- `gh run view <id> --log-failed`
- `act -j build  # local test`
- `gh secret set TOKEN --body x`

## Gotchas
- Pin third-party actions to SHAs, not moving tags.
- Use OIDC instead of long-lived PATs wherever possible.
- `pull_request_target` runs in base context; never checkout untrusted code with it.
