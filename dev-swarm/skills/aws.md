# AWS Cloud Engineer runbook

Agent: `devops-23` — Builds and operates workloads on AWS.

## When to use
Use for EC2/VPC/IAM/S3/RDS, CLI work, cost triage.

## Key commands
- `aws ec2 describe-instances --query ...`
- `aws s3 sync ./dist s3://bucket --delete`
- `aws iam get-account-authorization-details | less`

## Gotchas
- Least-privilege IAM; no `*` actions in production policies.
- S3 buckets: block public access by default, always.
- Tag everything; untagged spend is unmanageable spend.
