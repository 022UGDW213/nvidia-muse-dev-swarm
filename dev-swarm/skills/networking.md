# Network Engineer runbook

Agent: `devops-17` — Diagnoses network paths, DNS, TLS and connectivity.

## When to use
Use for connectivity, DNS, cert, latency and firewall issues.

## Key commands
- `dig +short example.com`
- `mtr -rwc 20 host`
- `openssl s_client -connect host:443 -servername host | openssl x509 -noout -dates`
- `tcpdump -i any port 443 -c 50 -w cap.pcap`
- `ss -tlnp | head`

## Gotchas
- It's always DNS. Check DNS first, seriously.
- MTU/fragmentation causes 'works locally, fails remotely'.
- Capture with tcpdump before guessing; guessers lose hours.
