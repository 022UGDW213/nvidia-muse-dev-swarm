# Terraform IaC Engineer runbook

Agent: `devops-04` — Provisions cloud infrastructure with Terraform/OpenTofu.

## When to use
Use for HCL modules, plan review, state surgery, drift.

## Key commands
- `terraform init -upgrade`
- `terraform plan -out=tfplan`
- `terraform apply tfplan`
- `terraform state list | head`
- `terraform import aws_instance.web i-123`
- `tofu fmt -recursive`

## Gotchas
- Remote state + locking (S3+DynamoDB / GCS) is mandatory for teams.
- Review the plan, not just the code; `apply` on red plans is how outages happen.
- Tainted resources get replaced next apply; untaint if it was a fluke.
