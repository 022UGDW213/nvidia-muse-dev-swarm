# Docker Specialist runbook

Agent: `devops-01` — Builds, optimizes and operates Docker images and Compose stacks.

## When to use
Use for anything container-image related: Dockerfiles, Compose files, registries, image size/perf.

## Key commands
- `docker build -t app:1.0 .`
- `docker compose up -d --build`
- `docker images --format '{{.Repository}}:{{.Tag}} {{.Size}}'`
- `docker system prune -af --volumes`
- `docker inspect <c> | jq .`
- `docker logs -f --tail 100 <c>`
- `docker exec -it <c> sh`

## Gotchas
- Never bake secrets into layers; use --secret or runtime env.
- Pin base image digests in production Dockerfiles.
- `latest` tag + cached layers = stale deploys; use immutable tags.
