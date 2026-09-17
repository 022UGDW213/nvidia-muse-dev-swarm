# Load Testing Engineer runbook

Agent: `devops-29` — Proves systems hold up under load with k6/Locust/JMeter.

## When to use
Use for load scripts, capacity questions, perf regressions.

## Key commands
- `k6 run --vus 100 --duration 5m script.js`
- `locust -f locustfile.py --headless -u 200 -r 20`
- `ab -n 10000 -c 100 https://app/health`

## Gotchas
- Test from outside your VPC; localhost lies.
- Ramp gradually; instant 10k VUs tests your LB, not your app.
- Watch p95/p99, not averages; averages hide pain.
