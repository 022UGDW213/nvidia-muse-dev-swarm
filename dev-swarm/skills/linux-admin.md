# Linux Systems Administrator runbook

Agent: `devops-14` — Administers Linux servers: services, users, storage, tuning.

## When to use
Use for systemd units, permissions, disk, package and boot issues.

## Key commands
- `systemctl status x --no-pager`
- `journalctl -u x -f`
- `df -h; du -sh /* 2>/dev/null | sort -h | tail`
- `ss -tlnp`
- `sysctl -w vm.swappiness=10`

## Gotchas
- Check `journalctl`, not just the service status.
- Full disks cause the weirdest failures; monitor inodes too.
- Use `systemctl edit` drop-ins instead of editing unit files.
