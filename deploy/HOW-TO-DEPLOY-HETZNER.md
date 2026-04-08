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
  - An Origin CA certificate and private key for your domain
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
server_image    = "debian-13"  # Ships Python 3.12+ natively
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
terraform output -raw ansible_inventory_yaml > ../ansible/production_inventory.yml
```

Verify SSH access:

```bash
ssh root@$(terraform output -raw server_ips_v4 | head -1)
```

## Step 2: Install Ansible Galaxy Requirements

```bash
cd ../ansible/
ansible-galaxy collection install ansible.posix community.general community.postgresql
```

## Step 3: Create Encrypted Secrets with Ansible Vault

All production secrets (database password, Django secret key, SSL certificates,
R2 credentials) are stored in an AES-256 encrypted vault file. This keeps
secrets out of plaintext while allowing them to be versioned alongside the
playbooks.

### Create the vault password file

Choose a strong passphrase and store it in a file that is gitignored:

```bash
echo "your-strong-vault-passphrase" > .vault_pass
chmod 600 .vault_pass
```

### Generate secrets

Generate the Django secret key and database password:

```bash
python3 -c "import secrets; print('Django secret key:', secrets.token_urlsafe(64))"
python3 -c "import secrets; print('DB password:', secrets.token_urlsafe(32))"
```

### Create the Origin CA certificate

In the Cloudflare dashboard:

1. Go to SSL/TLS > Origin Server > Create Certificate
1. Choose "Generate private key and CSR with Cloudflare"
1. Add your hostname (e.g., `babylon.percypedia.biz`)
1. Set validity (15 years recommended)
1. Copy both the certificate PEM and private key PEM

### Create the vault

```bash
ansible-vault create group_vars/production/vault.yml --vault-password-file .vault_pass
```

This opens your `$EDITOR`. Paste the following, replacing placeholders with
your actual values:

```yaml
vault_django_secret_key: "your-generated-64-char-string"
vault_db_password: "your-generated-32-char-string"
vault_r2_access_key_id: "your-r2-access-key-id"
vault_r2_secret_access_key: "your-r2-secret-access-key"
vault_r2_account_id: "your-cloudflare-account-id"
vault_ssl_crt: |
  -----BEGIN CERTIFICATE-----
  <paste Cloudflare Origin CA certificate here>
  -----END CERTIFICATE-----
vault_ssl_key: |
  -----BEGIN PRIVATE KEY-----
  <paste Cloudflare Origin CA private key here>
  -----END PRIVATE KEY-----
```

Save and close. The file is now encrypted on disk. To verify:

```bash
# View contents (requires vault password)
ansible-vault view group_vars/production/vault.yml --vault-password-file .vault_pass

# Edit later
ansible-vault edit group_vars/production/vault.yml --vault-password-file .vault_pass
```

### How the vault integrates

`group_vars/production/vars.yml` (plaintext, committed) references vault
values via Jinja2:

```yaml
db_password: "{{ vault_db_password }}"
django_secret_key: "{{ vault_django_secret_key }}"
ssl_crt: "{{ vault_ssl_crt }}"
ssl_key: "{{ vault_ssl_key }}"
```

Ansible automatically merges both files from `group_vars/production/` and
resolves the references at playbook runtime.

### Security notes

- `.vault_pass` is gitignored and must never be committed
- The encrypted `vault.yml` file can optionally be committed (it is AES-256
  encrypted and useless without the password)
- `vault.yml.example` shows the required keys without real values
- Share the vault password with team members via a secure channel (password
  manager, not email/Slack)

## Step 4: Update Production Variables

Edit `group_vars/production/vars.yml` and replace the firewall placeholder:

```yaml
firewall_ssh_allowed_ipv4:
  - "YOUR.ACTUAL.IP/32"  # Replace with: curl ifconfig.me
```

All other variables are pre-configured for Babylon. The key settings:

| Variable                           | Value                    | Why                                       |
| ---------------------------------- | ------------------------ | ----------------------------------------- |
| `server_image`                     | `debian-13`              | Native Python 3.12+ (no deadsnakes PPA)   |
| `postgresql_version`               | `17`                     | With PostGIS 3 and pgvector extensions    |
| `use_poetry`                       | `true`                   | Exports requirements.txt from Poetry lock |
| `django_project_dir`               | `{{ project_path }}/web` | Django lives in `web/` subdirectory       |
| `nginx_use_cloudflare_origin_pull` | `true`                   | Rejects non-Cloudflare traffic            |

## Step 5: Run the Ansible Playbooks

Test connectivity:

```bash
ansible all -i production_inventory.yml -m ping --vault-password-file .vault_pass
```

Run the full stack:

```bash
ansible-playbook -i production_inventory.yml site.yml --vault-password-file .vault_pass
```

This runs `dbservers.yml` then `webservers.yml` in sequence:

- **dbservers.yml**: PostgreSQL 17, PostGIS, pgvector, tuning for 8GB RAM
- **webservers.yml**: base packages, nftables firewall, Django + Poetry,
  Node.js 22 LTS + React build, nginx, R2 backups

The frontend build runs automatically via `build_frontend.yml` (Node.js 22 LTS,
`npm ci`, `npm run build`). No manual SSH required.

## Step 6: Create the Django Superuser

This is the one step that requires interactive SSH access:

```bash
ssh root@<server-ip>
cd /webapps/babylon_web/
source bin/activate
cd babylon/web/
python manage.py createsuperuser
```

## Step 7: Verify the Deployment

### From your machine

```bash
# Health check (through Cloudflare)
curl https://babylon.percypedia.biz/health/

# CSRF check: login should succeed (POST through Cloudflare proxy)
# Visit https://babylon.percypedia.biz/accounts/login/ in a browser

# Frontend: React SPA should load
# Visit https://babylon.percypedia.biz/
```

### On the server

```bash
ssh root@<server-ip>

# Check gunicorn
sudo supervisorctl status

# Check nginx
sudo systemctl status nginx
sudo nginx -t

# Check PostgreSQL
sudo systemctl status postgresql
psql -U babylon -d babylon -c "SELECT 1;"

# Check PostGIS and pgvector extensions
psql -U babylon -d babylon -c "SELECT PostGIS_Version();"
psql -U babylon -d babylon -c "SELECT extversion FROM pg_extension WHERE extname = 'vector';"

# Check logs
tail -f /webapps/babylon_web/logs/gunicorn_supervisor.log
sudo tail -f /var/log/nginx/access.log
```

## Network Architecture

```text
User Browser
    |
    v
Cloudflare CDN/WAF (babylon.percypedia.biz)
    |  SSL termination + re-encryption
    |  Authenticated Origin Pull (mutual TLS)
    |  Rate limit: 60 req/min on /api/
    v
Hetzner VPS (nftables: HTTPS only from Cloudflare CIDRs)
    |
    v
nginx (TLS 1.2+, Origin CA cert, DH-2048)
    |
    |-- /api/, /accounts/, /admin/, /health/  -->  Gunicorn (Unix socket)
    |                                                  |
    |                                                  v
    |                                             Django (DRF)
    |                                                  |
    |                                                  v
    |                                             PostgreSQL 17
    |                                             + PostGIS + pgvector
    |
    |-- /static/   -->  Django collectstatic files
    |
    |-- /assets/   -->  Vite-built React assets (1yr cache, immutable)
    |
    '-- /          -->  React SPA fallback (try_files -> index.html)
```

## Troubleshooting

**CSRF errors on login (403 Forbidden)**: Django is not recognizing the HTTPS
connection through Cloudflare. Verify that `production.py` has
`SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")` and that the
nginx template passes `X-Forwarded-Proto https` in proxy headers.

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
cat /webapps/babylon_web/logs/gunicorn_supervisor.log
```

**ModuleNotFoundError for babylon engine code**: The PYTHONPATH is not set.
Verify `gunicorn_start.j2` includes the line:

```bash
export PYTHONPATH="{{ project_path }}:{{ project_path }}/src:$PYTHONPATH"
```

**PostGIS extension missing**: The Ansible db role installs it automatically,
but if you need to add it manually:

```bash
sudo apt-get install postgresql-17-postgis-3
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
ls /webapps/babylon_web/babylon/web/frontend/dist/index.html
sudo nginx -t
```

**Vault password error**: Ensure `.vault_pass` exists and contains the correct
passphrase:

```bash
ansible-vault view group_vars/production/vault.yml --vault-password-file .vault_pass
```
