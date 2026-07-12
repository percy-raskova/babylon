# Babylon Ansible Deployment Tree

This directory provisions and configures the Babylon Hetzner deployment. It is
the live topology as of 2026-07-11 — see `../HOW-TO-DEPLOY-HETZNER.md` for the
canonical, step-by-step deployment guide.

## Live topology

```text
site.yml
├── dbservers.yml   (hosts: dbservers)  -> roles: base, db
└── webservers.yml  (hosts: webservers) -> roles: base, firewall, web, nginx, backup
```

`site.yml` is the entrypoint (`ansible-playbook -i inventory.yml site.yml`); it
imports `dbservers.yml` then `webservers.yml` in sequence.

### Standalone playbooks

These are run independently of `site.yml`:

- `playbooks/bootstrap.yml` — one-time initial server hardening (deploy user,
  SSH key, UFW baseline). Run once, before `site.yml`, on a fresh box.
- `playbooks/hetzner.yml` — Hetzner-specific VPS setup (swap, Docker,
  fail2ban, unattended-upgrades). Optional, independent of `site.yml`.
- `playbooks/backup-smoke.yml` — verifies the daily Postgres backup landed in
  the R2 `daily/` prefix. Run after `backup` role changes or on a schedule.

### Roles (6 live)

| Role       | Used by                | Purpose                                    |
| ---------- | ----------------------- | ------------------------------------------ |
| `base`     | dbservers, webservers   | security updates, base packages, swap      |
| `db`       | dbservers               | PostgreSQL 17 + PostGIS + pgvector         |
| `firewall` | webservers               | nftables ruleset                           |
| `web`      | webservers               | virtualenv, Django app, Gunicorn, frontend |
| `nginx`    | webservers               | Nginx + Cloudflare origin-pull TLS         |
| `backup`   | webservers               | Postgres backups to Cloudflare R2 (rclone) |

Any role directory not listed above is dead and has been removed.

## Ansible Galaxy collections

Install with:

```bash
ansible-galaxy collection install -r ../requirements.yml
```

See `../requirements.yml` for the exact collections and the tasks that use
each one.

## Full deployment guide

For provisioning (Terraform), vault secrets, and the full run sequence, see
[`../HOW-TO-DEPLOY-HETZNER.md`](../HOW-TO-DEPLOY-HETZNER.md) — the canonical
guide.
