# How to Deploy Babylon to Hetzner with Ansible

This guide walks you through provisioning a Hetzner VPS with Terraform and
configuring it with Ansible to serve the Babylon web application (Django +
React) behind nginx with Cloudflare as the CDN/WAF layer.

## Before You Begin

Ensure you have:

- Terraform >= 1.0 installed locally
- Ansible >= 9.0 installed locally (with `ansible-galaxy`)
- An SSH key pair (Ed25519 recommended: `~/.ssh/id_ed25519`)
- A [Hetzner Cloud](https://console.hetzner.cloud/) account with an API token
- A [Cloudflare](https://dash.cloudflare.com/) account with:
  - A zone for your domain (e.g., `percypedia.biz`)
  - An API token with DNS edit, SSL/TLS edit, and R2 admin permissions
  - R2 access keys (Access Key ID + Secret Access Key)
- The Babylon repository cloned locally

## Step 1: Provision the VPS with Terraform

```bash
cd deploy/terraform/
cp terraform.tfvars.example terraform.tfvars
```

Edit `terraform.tfvars` with your credentials:

```hcl
hcloud_token            = "your-hetzner-api-token"
cloudflare_api_token    = "your-cloudflare-api-token"
cloudflare_account_id   = "your-cloudflare-account-id"
cloudflare_zone_id      = "your-cloudflare-zone-id"
cloudflare_zone_name    = "percypedia.biz"
cloudflare_record_name  = "babylon"

project_name  = "babylon"
environment   = "production"

ssh_key_name        = "babylon-ssh-key"
ssh_public_key_path = "~/.ssh/id_ed25519.pub"

server_count    = 1
server_type     = "cx32"       # 4 vCPU, 8GB RAM
server_image    = "debian-12"
server_location = "ash"        # Ashburn, Virginia

# IMPORTANT: Replace with your actual public IP
ssh_allowed_ips = ["YOUR.PUBLIC.IP/32"]
```

Provision the server:

```bash
terraform init
terraform plan
terraform apply
```

After apply completes, generate the Ansible inventory:

```bash
terraform output -raw ansible_inventory_yaml > ../ansible/inventory.yml
```

Verify SSH access:

```bash
ssh root@$(terraform output -raw server_ips_v4 | head -1)
```

## Step 2: Install Ansible Galaxy Requirements

```bash
cd ../ansible/
ansible-galaxy install -r requirements.yml
```

If `requirements.yml` is empty, install the required collections manually:

```bash
ansible-galaxy collection install ansible.posix community.general community.postgresql
```

## Step 3: Customize Ansible Variables for Babylon

The Ansible roles are forked from `jcalazan/ansible-django-stack` and contain
placeholder values that need updating. Edit
`group_vars/development/vars.yml` (or create a `group_vars/production/vars.yml`
for production).

These are the values you **must** change:

```yaml
# ---- Repository ----
git_repo: https://github.com/percy-raskova/babylon.git  # Your actual repo
git_branch: main                                          # Or your deploy branch

# ---- Project naming ----
project_name: babylon
application_name: babylon_web

# ---- Python ----
enable_deadsnakes_ppa: true
virtualenv_python_version: python3.12

# ---- Django ----
django_settings_file: "babylon_web.settings.production"
django_secret_key: "<generate-a-64-char-random-string>"

# ---- Database ----
db_user: babylon
db_name: babylon
db_password: "<strong-random-password>"

# ---- Requirements path ----
# Poetry exports to requirements.txt, or use pyproject.toml directly
requirements_file: "{{ project_path }}/requirements.txt"

# ---- Firewall: SSH whitelist ----
firewall_ssh_allowed_ipv4:
  - YOUR.PUBLIC.IP/32

firewall_ssh_allowed_ipv6:
  - YOUR:IPV6:ADDRESS/128

# ---- R2 backup credentials (read from env) ----
r2_access_key_id: "{{ lookup('ansible.builtin.env', 'R2_ACCESS_KEY_ID') }}"
r2_secret_access_key: "{{ lookup('ansible.builtin.env', 'R2_SECRET_ACCESS_KEY') }}"
r2_account_id: "{{ lookup('ansible.builtin.env', 'R2_ACCOUNT_ID') }}"
```

Generate a Django secret key:

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(64))"
```

## Step 4: Update Ansible Templates for Babylon

### nginx Template

The nginx template at `roles/nginx/templates/django_default_project.j2`
references `{{ application_name }}` throughout, so renaming the variable in Step
3 is sufficient. However, the template needs a new `location` block to serve the
built React frontend.

Add a block for the frontend static assets before the Django `location /`
block:

```nginx
# React frontend (production build)
location /assets/ {
    alias {{ project_path }}/web/frontend/dist/assets/;
    expires 1y;
    add_header Cache-Control "public, immutable";
}

location /index.html {
    alias {{ project_path }}/web/frontend/dist/index.html;
    add_header Cache-Control "no-cache";
}
```

And update the root `location /` to serve `index.html` as the SPA fallback
**after** the Django proxy:

```nginx
location / {
    # Try static files first, then SPA fallback, then Django
    try_files $uri $uri/ @django;
}

location @django {
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto https;
    proxy_set_header Host $host;
    proxy_redirect off;
    proxy_pass http://{{ application_name }}_wsgi_server;
}
```

Alternatively, you can keep `/api/`, `/accounts/`, `/admin/`, `/health/`, and
`/static/` routed to Django, and let everything else fall through to
`index.html`:

```nginx
location /api/ {
    proxy_pass http://{{ application_name }}_wsgi_server;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto https;
    proxy_set_header Host $host;
}

location /accounts/ {
    proxy_pass http://{{ application_name }}_wsgi_server;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto https;
    proxy_set_header Host $host;
}

location /admin/ {
    proxy_pass http://{{ application_name }}_wsgi_server;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto https;
    proxy_set_header Host $host;
}

location /health/ {
    proxy_pass http://{{ application_name }}_wsgi_server;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto https;
    proxy_set_header Host $host;
}

location /static/ {
    alias {{ nginx_static_dir }};
}

# SPA fallback: serve React frontend
location / {
    root {{ project_path }}/web/frontend/dist;
    try_files $uri $uri/ /index.html;
}
```

### Gunicorn Start Script

The `roles/web/templates/gunicorn_start.j2` script sets `DJANGO_SETTINGS_MODULE`
from `{{ django_settings_file }}`. With the variable set to
`babylon_web.settings.production` in Step 3, this works without further changes.

### virtualenv_postactivate

The `roles/web/templates/virtualenv_postactivate.j2` exports Django environment
variables into the virtualenv. Verify it includes:

```bash
export DJANGO_SETTINGS_MODULE="{{ django_settings_file }}"
export DJANGO_SECRET_KEY="{{ django_secret_key }}"
export POSTGRES_DB="{{ db_name }}"
export POSTGRES_USER="{{ db_user }}"
export POSTGRES_PASSWORD="{{ db_password }}"
export ALLOWED_HOSTS="{{ nginx_server_name }}"
```

If these are not present, add them to the `django_environment` dict in your
`vars.yml`:

```yaml
django_environment:
  DJANGO_SETTINGS_MODULE: "{{ django_settings_file }}"
  DJANGO_SECRET_KEY: "{{ django_secret_key }}"
  POSTGRES_DB: "{{ db_name }}"
  POSTGRES_USER: "{{ db_user }}"
  POSTGRES_PASSWORD: "{{ db_password }}"
  ALLOWED_HOSTS: "{{ nginx_server_name }}"
```

## Step 5: Run the Ansible Playbooks

Set R2 credentials in your shell before running Ansible:

```bash
export R2_ACCESS_KEY_ID="your-r2-access-key"
export R2_SECRET_ACCESS_KEY="your-r2-secret-key"
export R2_ACCOUNT_ID="your-cloudflare-account-id"
```

Test connectivity:

```bash
ansible all -i inventory.yml -m ping
```

Run the full stack:

```bash
# Database server setup (PostgreSQL + PostGIS)
ansible-playbook -i inventory.yml dbservers.yml

# Web server setup (nginx, gunicorn, Django, firewall, backup)
ansible-playbook -i inventory.yml webservers.yml
```

Or run the combined playbook:

```bash
ansible-playbook -i inventory.yml site.yml
```

## Step 6: Build and Deploy the Frontend

SSH into the server and build the React frontend:

```bash
ssh deploy@<server-ip>

cd /webapps/babylon/babylon/web/frontend/
npm install
npm run build
```

If Node.js is not installed on the server, build locally and copy:

```bash
# On your local machine
cd web/frontend/
npm run build

# Copy to server
scp -r dist/ deploy@<server-ip>:/webapps/babylon/babylon/web/frontend/dist/
```

Restart nginx to pick up the new static files:

```bash
ssh deploy@<server-ip> "sudo systemctl reload nginx"
```

## Step 7: Initialize the Database Schema

The `game_session`, `game_turn`, and `action_result` tables are created by the
engine's DDL, not Django migrations. On the server:

```bash
ssh deploy@<server-ip>
cd /webapps/babylon/

# Activate the virtualenv
source bin/activate

# Run Django migrations (creates auth tables, PlayerProfile, GameEventLog)
cd babylon/web/
python manage.py migrate

# Create a superuser
python manage.py createsuperuser

# Initialize engine tables (if not already done by the engine bridge)
# The engine_bridge.create_game() call handles this automatically on first use
```

## Step 8: Verify the Deployment

### From Your Machine

```bash
# Health check (through Cloudflare)
curl https://babylon.percypedia.biz/health/

# Direct to origin (if your IP is whitelisted in the firewall)
curl -k https://<server-ip>/health/
```

### On the Server

```bash
ssh deploy@<server-ip>

# Check gunicorn
sudo supervisorctl status

# Check nginx
sudo systemctl status nginx
sudo nginx -t

# Check PostgreSQL
sudo systemctl status postgresql
psql -U babylon -d babylon -c "SELECT 1;"

# Check logs
tail -f /webapps/babylon/babylon/web/logs/web.jsonl
sudo tail -f /var/log/nginx/access.log
```

### Verify Backup

```bash
# Run backup manually
ansible-playbook -i inventory.yml playbooks/backup-smoke.yml
```

## Network Architecture

```text
User Browser
    │
    ▼
Cloudflare CDN/WAF (babylon.percypedia.biz)
    │  SSL termination + re-encryption
    │  Static cache: /static/* (1 year)
    │  API bypass: /api/*, /admin/*
    │  Rate limit: 60 req/min on /api/
    ▼
Hetzner VPS (nftables: HTTPS only from Cloudflare CIDRs)
    │
    ▼
nginx (TLS 1.2, Cloudflare Authenticated Origin Pull)
    │
    ├── /api/, /accounts/, /admin/, /health/ → Gunicorn (Unix socket)
    │                                              │
    │                                              ▼
    │                                         Django (DRF)
    │                                              │
    │                                              ▼
    │                                         PostgreSQL + PostGIS
    │
    ├── /static/ → Django collectstatic files
    │
    └── / → React SPA (web/frontend/dist/)
```

## Troubleshooting

**Ansible fails at "Install PostgreSQL"**: The PostgreSQL APT repo key may have
changed. SSH into the server and add it manually:

```bash
sudo apt-get install -y postgresql-common
sudo /usr/share/postgresql-common/pgdg/apt.postgresql.org.sh
```

**502 Bad Gateway from nginx**: Gunicorn is not running. Check supervisor:

```bash
sudo supervisorctl status babylon_web
sudo supervisorctl restart babylon_web
cat /webapps/babylon/logs/gunicorn_supervisor.log
```

**PostGIS extension missing**: Install it on the server:

```bash
sudo apt-get install postgresql-16-postgis-3
psql -U postgres -d babylon -c "CREATE EXTENSION IF NOT EXISTS postgis;"
```

**Cloudflare 522 (Connection timed out)**: The origin server firewall is
blocking Cloudflare. Verify that nftables allows HTTPS from Cloudflare CIDRs:

```bash
sudo nft list ruleset | grep 'tcp dport 443'
```

**Frontend shows blank page**: The React `dist/` directory is missing or nginx
is not configured to serve it. Verify:

```bash
ls /webapps/babylon/babylon/web/frontend/dist/index.html
sudo nginx -t
```
