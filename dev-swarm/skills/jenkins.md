# Jenkins Pipeline Engineer runbook

Agent: `devops-09` — Maintains Jenkins controllers, agents and pipelines.

## When to use
Use for Jenkinsfiles, agent pools, plugin and credential issues.

## Key commands
- `java -jar jenkins-cli.jar -s $URL build job -s`
- `jenkins-cli list-jobs`
- `groovy console: println Jenkins.instance.pluginManager.plugins`

## Gotchas
- Keep Jenkins + plugins patched; unpatched Jenkins gets owned.
- Use credentials binding; never echo secrets in sh steps.
- Declarative pipelines beat scripted for maintainability.
