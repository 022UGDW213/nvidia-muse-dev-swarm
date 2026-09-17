# Nginx Reverse-Proxy Engineer runbook

Agent: `devops-18` — Configures Nginx as proxy, LB and static server.

## When to use
Use for vhosts, proxying, TLS, rewrites, rate limits.

## Key commands
- `nginx -t && systemctl reload nginx`
- `proxy_pass http://upstream;`
- `nginx -T | less  # dump effective config`

## Gotchas
- `nginx -t` before every reload; a bad config drops traffic.
- Trailing slash in proxy_pass changes URI mapping semantics.
- Set client_max_body_size or uploads fail at 1MB default.
