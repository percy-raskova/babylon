# Feature Specification: Cloudflare Edge Services

**Spec ID**: `039-cloudflare-edge-services`
**Feature Branch**: `039-cloudflare-edge-services`
**Created**: 2026-03-01
**Status**: Implementation-ready
**Depends On**: 038-django-web-application (infrastructure layer), Constitution Article III (Methodology)
**Governed By**: Infrastructure Specification v2

---

## Executive Summary

This specification defines every Cloudflare service consumed by Babylon, the Terraform resources that provision them, the interface contracts between Cloudflare and the Hetzner VPS, and the implementation tasks to stand them up. Cloudflare is the shield and content delivery layer. Nothing computes on Cloudflare; nothing reaches users without passing through Cloudflare first.

The governing principle is a strict division of labor: Cloudflare handles edge concerns (DNS, SSL, WAF, CDN, object storage, AI inference). Hetzner handles compute concerns (Django, Postgres, NetworkX, CI/CD). The two layers meet at three interface boundaries: HTTP traffic (Nginx ↔ Cloudflare proxy), object storage (backup scripts and Django ↔ R2), and AI inference (Django narrative layer ↔ Workers AI). Each boundary is defined by an explicit contract in this document.

---

## 1. DNS and Proxy Configuration

### 1.1 Domain Structure

The production domain is `babylon.percypedia.biz`. Cloudflare is the authoritative DNS provider for `percypedia.biz`. A single proxied A record points to the Hetzner VPS IP address.

| Record Type | Name | Value | Proxy Status | TTL |
|---|---|---|---|---|
| A | babylon | Hetzner VPS IPv4 | Proxied (orange cloud) | Auto |

Proxied status means all HTTP/HTTPS traffic routes through Cloudflare's edge network before reaching the origin server. The VPS IP address is never exposed to the public internet. DNS resolution returns Cloudflare's anycast IPs, not the origin.

### 1.2 Why Proxied, Not DNS-Only

DNS-only (grey cloud) would expose the Hetzner IP directly. Proxied mode provides: DDoS absorption at the edge before traffic reaches the VPS, WAF inspection of HTTP payloads, CDN caching of static assets, automatic SSL certificate provisioning at the edge, and real IP masking (the origin's IP never appears in DNS responses). The tradeoff is that all traffic must pass through Cloudflare — if Cloudflare goes down, the site is unreachable even though the VPS is healthy. For a beta game server, this tradeoff is acceptable.

### 1.3 Terraform Resource

```hcl
resource "cloudflare_record" "babylon" {
  zone_id = var.cloudflare_zone_id
  name    = "babylon"
  content = hcloud_server.babylon.ipv4_address
  type    = "A"
  proxied = true
  ttl     = 1  # Auto (managed by Cloudflare when proxied)
}
```

The `content` field reads the VPS IP from the Hetzner Terraform resource output. No manual IP entry.

---

## 2. SSL/TLS Termination

### 2.1 Mode: Full (Strict)

Cloudflare's SSL/TLS encryption mode is set to Full (Strict). This means:

- **Browser → Cloudflare**: TLS terminated at the edge. Cloudflare provisions and renews certificates automatically. No Certbot, no Let's Encrypt, no certificate management on the VPS.
- **Cloudflare → Origin**: Cloudflare re-encrypts the connection to the origin server. "Strict" requires a valid certificate on the origin — either a Cloudflare Origin CA certificate (free, 15-year validity) or a publicly trusted certificate. We use Origin CA.

### 2.2 Origin CA Certificate

A Cloudflare Origin CA certificate is installed on Nginx. This certificate is trusted only by Cloudflare's edge network — browsers connecting directly to the VPS IP would see a certificate warning. This is a feature, not a bug: it ensures all legitimate traffic passes through Cloudflare.

Generation: Cloudflare Dashboard → SSL/TLS → Origin Server → Create Certificate. RSA or ECDSA, 15-year validity, covering `babylon.percypedia.biz` and `*.percypedia.biz`.

Deployment: Ansible's `nginx` role deploys the certificate and private key to `/etc/nginx/ssl/` with mode `0600`. The certificate is stored in the Ansible vault as an encrypted variable.

### 2.3 Nginx SSL Configuration

```nginx
server {
    listen 443 ssl;
    server_name babylon.percypedia.biz;

    ssl_certificate     /etc/nginx/ssl/cloudflare-origin.pem;
    ssl_certificate_key /etc/nginx/ssl/cloudflare-origin-key.pem;

    # Only accept connections from Cloudflare
    # (see Section 5.2 for full IP allowlisting)
}
```

### 2.4 No Let's Encrypt

The VPS guide v1 used Let's Encrypt with DNS-01 challenges via the Cloudflare API. This is replaced. With Full (Strict) mode and Origin CA, there is no ACME challenge, no certbot timer, no renewal failure risk, no DNS-01 API token scope to manage. The Origin CA certificate lasts 15 years.

### 2.5 Terraform Resource

```hcl
resource "cloudflare_zone_settings_override" "babylon" {
  zone_id = var.cloudflare_zone_id

  settings {
    ssl                      = "strict"
    always_use_https         = "on"
    min_tls_version          = "1.2"
    tls_1_3                  = "on"
    automatic_https_rewrites = "on"
  }
}
```

---

## 3. WAF and DDoS Protection

### 3.1 Free Tier Coverage

Cloudflare's free tier includes: L7 DDoS mitigation (automatic, no configuration), managed WAF ruleset (OWASP core rules, SQL injection detection, XSS filtering), and rate limiting (basic, 1 rule on free tier).

### 3.2 Rate Limiting Rule

A single rate limit rule protects the game API from abuse or runaway client bugs. The game is turn-based — no legitimate client makes more than a handful of requests per minute.

| Parameter | Value | Rationale |
|---|---|---|
| Expression | `http.request.uri.path matches "^/api/"` | Scope to API endpoints only |
| Period | 60 seconds | Per-minute window |
| Requests | 60 | 1 req/sec sustained. Turn submission + polling |
| Action | Block (429) | Client retries with backoff |

Static assets (`/static/*`) are excluded from rate limiting — they are cached at the edge and don't hit the origin.

### 3.3 Terraform Resource

```hcl
resource "cloudflare_ruleset" "rate_limit" {
  zone_id     = var.cloudflare_zone_id
  name        = "Babylon API rate limiting"
  description = "Prevent API abuse"
  kind        = "zone"
  phase       = "http_ratelimit"

  rules {
    action = "block"
    ratelimit {
      characteristics     = ["cf.colo.id", "ip.src"]
      period              = 60
      requests_per_period = 60
      mitigation_timeout  = 60
    }
    expression  = "(http.request.uri.path matches \"^/api/\")"
    description = "API rate limit: 60 req/min per IP"
    enabled     = true
  }
}
```

### 3.4 Security Headers

Cloudflare Transform Rules add security headers to all responses without configuring them in Nginx or Django:

| Header | Value |
|---|---|
| `X-Content-Type-Options` | `nosniff` |
| `X-Frame-Options` | `DENY` |
| `Referrer-Policy` | `strict-origin-when-cross-origin` |

### 3.5 Authenticated Origin Pulls

Cloudflare's Authenticated Origin Pulls feature adds a client certificate to requests from Cloudflare to the origin. Nginx validates this certificate, ensuring that even if someone discovers the origin IP, they cannot reach Nginx without presenting Cloudflare's client certificate. This is defense-in-depth beyond IP allowlisting.

Configuration in Nginx:

```nginx
ssl_client_certificate /etc/nginx/ssl/cloudflare-authenticated-origin-pull.pem;
ssl_verify_client on;
```

The Cloudflare client CA certificate is a public, well-known certificate downloaded from Cloudflare's documentation. It does not contain secrets.

---

## 4. CDN Caching

### 4.1 What Gets Cached

| Path Pattern | Content | Cache Behavior | TTL |
|---|---|---|---|
| `/static/*` | React build, CSS, JS, images | Cache Everything | 1 year (immutable, hashed filenames) |
| `/api/*` | Game state, actions, tick results | Bypass Cache | N/A |
| `/admin/*` | Django admin panel | Bypass Cache | N/A |
| `/health/` | Health check endpoint | Bypass Cache | N/A |
| `/` | SPA entry point (index.html) | Cache with short TTL | 5 minutes |

### 4.2 Cache Rules

React's build process produces hashed filenames (`main.a1b2c3d4.js`). These are immutable — the hash changes when content changes. Long TTLs are safe because the filename itself is the cache key. The SPA's `index.html` gets a short TTL because it references the hashed asset filenames and must update when a new build deploys.

### 4.3 Terraform Resource

```hcl
resource "cloudflare_ruleset" "cache" {
  zone_id     = var.cloudflare_zone_id
  name        = "Babylon cache rules"
  description = "Cache static assets, bypass API"
  kind        = "zone"
  phase       = "http_request_cache_settings"

  rules {
    action = "set_cache_settings"
    action_parameters {
      cache = true
      edge_ttl {
        mode    = "override_origin"
        default = 31536000  # 1 year
      }
      browser_ttl {
        mode    = "override_origin"
        default = 31536000
      }
    }
    expression  = "(http.request.uri.path matches \"^/static/\")"
    description = "Cache static assets for 1 year"
    enabled     = true
  }

  rules {
    action = "set_cache_settings"
    action_parameters {
      cache = false
    }
    expression  = "(http.request.uri.path matches \"^/api/\" or http.request.uri.path matches \"^/admin/\")"
    description = "Bypass cache for API and admin"
    enabled     = true
  }
}
```

### 4.4 Cache Purge on Deploy

The Woodpecker CI deploy pipeline purges Cloudflare's cache after `collectstatic` runs, ensuring players receive the latest React build. A targeted purge of `/static/*` avoids clearing the entire zone cache.

```bash
curl -X POST "https://api.cloudflare.com/client/v4/zones/${ZONE_ID}/purge_cache" \
  -H "Authorization: Bearer ${CF_API_TOKEN}" \
  -H "Content-Type: application/json" \
  --data '{"prefixes":["babylon.percypedia.biz/static/"]}'
```

This runs as a step in the Woodpecker pipeline after `collectstatic` and before the service restart.

---

## 5. Network Security: Origin Lockdown

### 5.1 Defense in Depth Model

Traffic passes through three filtering layers before reaching Django:

1. **Cloudflare edge** — L7 WAF, DDoS mitigation, rate limiting, bot detection
2. **Hetzner Cloud Firewall** — L3/L4 stateful packet filtering at the hypervisor. Applied before the packet enters the VPS kernel. Rules: allow TCP 443 from Cloudflare IPv4 and IPv6 ranges; allow TCP 22 from operator's known IPs; deny all else
3. **Host firewall (nftables)** — Same rules, defense-in-depth inside the VPS. If the Hetzner firewall is misconfigured or bypassed (e.g., private network traffic), the host firewall catches it
4. **Nginx** — `ssl_verify_client on` (authenticated origin pulls) plus `set_real_ip_from` directives restricted to Cloudflare IP ranges
5. **fail2ban** — Bans IPs after repeated SSH failures

### 5.2 Cloudflare IP Ranges

Cloudflare publishes their IP ranges at `https://www.cloudflare.com/ips/`. These must be kept current in three places: Hetzner Cloud Firewall rules (Terraform), nftables rules (Ansible), and Nginx `set_real_ip_from` directives (Ansible).

The Ansible `nginx` role includes a task that fetches the current Cloudflare IP list and templates the Nginx config. A scheduled Woodpecker pipeline re-runs this task weekly to catch range updates.

### 5.3 Real IP Restoration

Cloudflare proxies all traffic, so Nginx sees Cloudflare's IP as the connecting client. The `CF-Connecting-IP` header contains the real player IP. Nginx configuration:

```nginx
# Cloudflare IPv4 ranges (templated by Ansible)
set_real_ip_from 173.245.48.0/20;
set_real_ip_from 103.21.244.0/22;
# ... (full list from Cloudflare)
real_ip_header CF-Connecting-IP;
real_ip_recursive on;
```

Django then reads the correct client IP from `request.META['REMOTE_ADDR']` without any additional middleware. This is essential for: Django admin login audit logs, rate limiting accuracy (without this, all players appear as one IP), and fail2ban integration for application-level bans.

---

## 6. R2 Object Storage

### 6.1 Purpose

Cloudflare R2 provides S3-compatible object storage with zero egress fees. Hetzner's own object storage is EU-only, creating unacceptable transatlantic latency from the Ashburn VPS. R2 replaces it for all object storage needs.

### 6.2 Buckets

| Bucket | Contents | Access Pattern | Lifecycle |
|---|---|---|---|
| `babylon-backups` | pg_dump archives (zstd-compressed) | Write daily, read on restore | 7 daily + 4 weekly retention |
| `babylon-reference` | Reference SQLite database, NAICS mappings | Write on data refresh, read on VPS init | Versioned, no expiry |
| `babylon-archives` | Completed game Parquet exports | Write on game completion, read for analytics | No expiry |
| `babylon-static` | Future: large static media if CDN-from-R2 needed | Write on deploy | No expiry |

### 6.3 Backup Lifecycle

The `babylon-backups` bucket uses R2 lifecycle rules to automatically expire old backups:

| Rule | Prefix | Action | After |
|---|---|---|---|
| Daily cleanup | `daily/` | Delete | 7 days |
| Weekly cleanup | `weekly/` | Delete | 28 days |

The backup script (Ansible `backup` role) writes to `daily/babylon-YYYY-MM-DD.sql.zst`. A weekly cron job copies the Sunday backup to `weekly/`. Lifecycle rules handle garbage collection.

### 6.4 Parquet Archival Pipeline

Completed games export to Parquet (zstd compression, approximately 10:1 ratio) via Feature 037's archival system. The export workflow:

1. Game reaches terminal state (final tick or player exits)
2. Django management command `archive_game --game-id <id>` exports all tick data to Parquet
3. `rclone copy` uploads the Parquet file to `babylon-archives/<game_id>/`
4. Django marks the game as archived and purges tick-level data from active Postgres storage
5. DuckDB reads Parquet from R2 natively for cross-game analytics (future)

### 6.5 Reference Database Distribution

The reference SQLite database (ingested federal data: QCEW, BEA, Census, FRED, HIFLD, BTS, FCC, ATUS) is uploaded to `babylon-reference/marxist-data-3NF.sqlite`. The Ansible `babylon` role downloads this file during provisioning rather than shipping it in the Git repository. This keeps the repo lightweight and allows the reference database to update independently of code deploys.

Upload script (run from the developer's machine after a data refresh):

```bash
rclone copy ./data/marxist-data-3NF.sqlite r2:babylon-reference/ \
  --s3-provider=Cloudflare \
  --s3-access-key-id=$R2_ACCESS_KEY_ID \
  --s3-secret-access-key=$R2_SECRET_ACCESS_KEY \
  --s3-endpoint=https://${CF_ACCOUNT_ID}.r2.cloudflarestorage.com
```

### 6.6 Access Credentials

R2 access uses S3-compatible API tokens scoped per use case:

| Token | Scope | Consumers |
|---|---|---|
| `R2_BACKUP_TOKEN` | Read/write `babylon-backups` | Backup cron, restore script |
| `R2_REFERENCE_TOKEN` | Read `babylon-reference` | Ansible provisioning, init script |
| `R2_ARCHIVE_TOKEN` | Read/write `babylon-archives` | Django archival command |

All tokens are stored in the Ansible vault and deployed to the VPS as environment variables in restricted `.env` files.

### 6.7 Terraform Resources

```hcl
resource "cloudflare_r2_bucket" "backups" {
  account_id = var.cloudflare_account_id
  name       = "babylon-backups"
  location   = "ENAM"  # Eastern North America
}

resource "cloudflare_r2_bucket" "reference" {
  account_id = var.cloudflare_account_id
  name       = "babylon-reference"
  location   = "ENAM"
}

resource "cloudflare_r2_bucket" "archives" {
  account_id = var.cloudflare_account_id
  name       = "babylon-archives"
  location   = "ENAM"
}
```

### 6.8 Cost

R2 free tier: 10 GB storage, 1M Class A (write) operations, 10M Class B (read) operations per month. For beta, daily pg_dump archives (~50-100 MB compressed), the reference SQLite (~500 MB), and occasional Parquet exports will stay well within free tier. No egress charges regardless of volume.

---

## 7. Workers AI: Narrative Generation

### 7.1 Constitutional Compliance

The Constitution states: "AI Observes, Never Controls." The narrative layer reads from simulation state after tick resolution. It never determines mechanical outcomes. If the Workers AI call fails, the `narrative` field returns empty and the game continues. Failure is non-fatal.

### 7.2 Architecture

Django makes a single HTTPS POST to the Cloudflare Workers AI REST API after each tick resolves. The call is synchronous but timeout-bounded. The response (generated narrative text) is stored in Postgres alongside the tick results and served as the `narrative` field in the tick results JSON.

```
Django (tick resolved) → HTTPS POST → Workers AI → narrative text → Postgres
```

There is no Worker function deployed. Django calls the REST API directly. No Wrangler, no Worker script, no deployment pipeline for the AI layer. This is a deliberate simplification — the REST API is sufficient and avoids a second deployment target.

### 7.3 Model Selection

The target model class is an 8B-parameter model with LoRA adaptation capability. The specific model depends on Workers AI's catalog at deployment time. Candidates as of March 2026:

| Model | Context Window | Cost (input) | Cost (output) | Notes |
|---|---|---|---|---|
| @cf/meta/llama-3.1-8b-instruct-fast | 128K | ~$0.10/M tokens | ~$0.16/M tokens | Default candidate |
| @cf/deepseek/deepseek-r1-distill-qwen-32b | 128K | Varies | Varies | Heavier, better reasoning |

Model selection is a configuration value in Django settings, not hardcoded. The `WORKERS_AI_MODEL` environment variable allows switching without code changes.

### 7.4 The Gramscian Wire

The narrative system produces three channels, generated in a single structured API call via tool use or structured JSON output:

| Channel | Voice | Purpose |
|---|---|---|
| Corporate Feed | Hegemonic, passive voice, status-quo-affirming | "Authorities restored order after minor disturbances" |
| Liberated Signal | Counter-hegemonic, active voice, systemic analysis | ">>> Workers occupied the plant after wage theft reached $2.3M" |
| Intel Stream | Raw data, clinical, surveillance aesthetic | "SUBJECT ORG increased recruitment 340% in H3 cell 872f" |

The three channels are not three API calls. A single prompt instructs the model to generate all three perspectives on the tick's events, returning structured JSON. Django parses the response and stores each channel separately.

### 7.5 Prompt Architecture

The system prompt is constructed per-tick from three components:

1. **Identity and constraints** (~500 tokens, static): The Gramscian Wire voice definitions, output format specification, constitutional constraint reminders
2. **Reference documentation** (~2,000-4,000 tokens, semi-static): Theoretical concepts relevant to current game state, loaded from the docs/ folder and packed into the prompt. Since this is a one-shot call (not conversational), the full prompt can be large without the typical 10-15% system prompt budget concern
3. **Tick state** (~500-1,500 tokens, per-tick): Current world state summary, events this tick, network topology deltas, relevant metrics

Total prompt size: ~3,000-6,000 tokens input, ~400-800 tokens output per tick.

### 7.6 RAG Integration

The pgvector corpus (Feature 037) stores embedded chunks from the Marxist theory corpus and historical case studies. Before calling Workers AI, Django retrieves semantically similar chunks based on the tick's events. High unemployment plus rising fascism retrieves Weimar Germany analogies. The retrieved chunks are injected into the prompt's reference documentation section.

### 7.7 Django Integration

```python
# settings.py
WORKERS_AI_ENABLED = env.bool("WORKERS_AI_ENABLED", default=False)
WORKERS_AI_TOKEN = env("WORKERS_AI_TOKEN", default="")
WORKERS_AI_ACCOUNT_ID = env("WORKERS_AI_ACCOUNT_ID", default="")
WORKERS_AI_MODEL = env(
    "WORKERS_AI_MODEL",
    default="@cf/meta/llama-3.1-8b-instruct-fast"
)
WORKERS_AI_TIMEOUT = 15  # seconds
```

The `WORKERS_AI_ENABLED` flag allows disabling narrative generation entirely for MVP. When disabled, the `narrative` field is always empty. The game is playable and testable without narrative text.

### 7.8 Error Handling

| Failure Mode | Response | Player Impact |
|---|---|---|
| HTTP timeout (>15s) | Empty narrative, log warning | None — structured data still shown |
| 4xx error (auth, rate limit) | Empty narrative, log error, alert | None — but operator investigates |
| 5xx error (model overloaded) | Retry once with exponential backoff, then empty | Slight delay, then none |
| Malformed JSON response | Empty narrative, log the raw response | None |

### 7.9 Cost Model

Per-tick cost at ~4,000 input tokens and ~600 output tokens:

| Metric | Value |
|---|---|
| Input cost per tick | ~$0.0004 |
| Output cost per tick | ~$0.0001 |
| Total per tick | ~$0.0005 |
| Per game (520 ticks) | ~$0.26 |
| Per month (10 games) | ~$2.60 |
| Workers AI free tier | 10,000 neurons/day |

For beta with 5-15 testers playing sporadically, monthly Workers AI cost is approximately $3-5. This stays well under the $15/month total infrastructure budget.

### 7.10 LoRA Fine-Tuning (Deferred)

Workers AI supports LoRA adapters on compatible models. The plan is to fine-tune on: Mao Zedong's "Oppose Stereotyped Party Writing" for prose style, collected game narratives from beta playtesting for domain knowledge, and historical case study descriptions for analogical reasoning. This is post-MVP. The base model with heavy system prompting ships first.

---

## 8. Uptime Monitoring

Cloudflare provides built-in health checks for proxied domains at no cost. Configuration:

| Parameter | Value |
|---|---|
| Check URL | `https://babylon.percypedia.biz/health/` |
| Interval | 5 minutes |
| Expected status | 200 |
| Notification | Email to operator |

The `/health/` endpoint is a lightweight Django view that confirms the application is running and Postgres is reachable. It does not exercise the full simulation engine.

---

## 9. Interface Contracts

These are the agreements between the Cloudflare layer and the Hetzner layer. If either side changes, the other must update to match.

### 9.1 Cloudflare → Nginx (HTTP Traffic)

| Parameter | Value | Owner |
|---|---|---|
| Protocol to origin | HTTPS (Full Strict) | Cloudflare zone settings |
| Origin certificate | Cloudflare Origin CA, 15-year, on Nginx | Ansible `nginx` role |
| Client certificate verification | Authenticated Origin Pulls enabled | Both |
| Real IP header | `CF-Connecting-IP` | Cloudflare (sends), Nginx (reads) |
| `X-Forwarded-Proto` | `https` | Cloudflare (sends), Django (reads via `SECURE_PROXY_SSL_HEADER`) |
| Allowed source IPs on origin | Cloudflare IPv4 + IPv6 ranges | Hetzner Firewall + nftables + Nginx |

### 9.2 Backup Script → R2 (Object Storage)

| Parameter | Value | Owner |
|---|---|---|
| Tool | rclone | Ansible `backup` role |
| Endpoint | `https://<account_id>.r2.cloudflarestorage.com` | Cloudflare |
| Auth | S3-compatible access key + secret | Ansible vault → `.env` |
| Bucket | `babylon-backups` | Terraform |
| Path convention | `daily/babylon-YYYY-MM-DD.sql.zst` | Backup script |
| Lifecycle | 7 daily, 4 weekly | R2 bucket rules |

### 9.3 Django → Workers AI (Narrative)

| Parameter | Value | Owner |
|---|---|---|
| Endpoint | `https://api.cloudflare.com/client/v4/accounts/<id>/ai/run/<model>` | Cloudflare |
| Auth | Bearer token in `Authorization` header | Ansible vault → `.env` |
| Model | `@cf/meta/llama-3.1-8b-instruct-fast` (configurable) | Django settings |
| Timeout | 15 seconds | Django settings |
| Failure mode | Non-fatal; empty narrative | Django code |
| Response format | JSON with `corporate`, `liberated`, `intel` fields | System prompt contract |

### 9.4 Secrets That Cross the Boundary

| Secret | Created In | Consumed By | Stored In |
|---|---|---|---|
| Cloudflare API token | Cloudflare Dashboard | Terraform, cache purge script | `terraform.tfvars` (gitignored), Ansible vault |
| R2 access key ID | Cloudflare R2 settings | Backup script, Django archival | Ansible vault → `.env` |
| R2 secret access key | Cloudflare R2 settings | Backup script, Django archival | Ansible vault → `.env` |
| Workers AI token | Cloudflare Dashboard | Django narrative layer | Ansible vault → `.env` |
| Origin CA private key | Cloudflare Dashboard | Nginx | Ansible vault → Nginx SSL dir |

---

## 10. Terraform Resource Inventory

Complete list of Cloudflare resources managed by Terraform:

| Resource | Type | Purpose |
|---|---|---|
| `cloudflare_record.babylon` | DNS A record | Proxied domain pointing to VPS |
| `cloudflare_zone_settings_override.babylon` | Zone settings | SSL mode, TLS version, HTTPS redirect |
| `cloudflare_ruleset.rate_limit` | Rate limiting | API endpoint protection |
| `cloudflare_ruleset.cache` | Cache rules | Static asset caching, API bypass |
| `cloudflare_r2_bucket.backups` | R2 bucket | Postgres backup archives |
| `cloudflare_r2_bucket.reference` | R2 bucket | Reference SQLite database |
| `cloudflare_r2_bucket.archives` | R2 bucket | Completed game Parquet exports |

All resources live in `infra/terraform/cloudflare.tf`. The Cloudflare provider is configured with an API token scoped to the `percypedia.biz` zone and R2 bucket management.

---

## 11. Cost Analysis

| Service | Monthly Cost | Tier |
|---|---|---|
| DNS + proxy | $0 | Free |
| SSL termination | $0 | Free (Origin CA) |
| WAF + DDoS | $0 | Free tier managed rules |
| CDN caching | $0 | Free |
| Uptime monitoring | $0 | Free |
| R2 storage (beta) | $0 | Free tier (10GB, 1M writes, 10M reads) |
| Workers AI (beta) | ~$3-5 | Usage-dependent |
| **Total Cloudflare** | **~$3-5/mo** | |

R2 costs become non-zero when storage exceeds 10 GB (~$0.015/GB-month) or operations exceed free tier limits. At beta scale this is unlikely.

---

## 12. Rejected Alternatives

| Alternative | Why Rejected |
|---|---|
| Let's Encrypt + Certbot | Origin CA eliminates certificate renewal entirely |
| Cloudflare Tunnel (cloudflared) | Additional daemon complexity for no benefit over direct proxy |
| Cloudflare Workers (compute) | Django handles all compute; Workers would be a second deployment target |
| Cloudflare Pages | React build served by Nginx; split deploy adds complexity |
| Cloudflare D1 | SQLite reference data served from R2; D1 adds vendor lock-in |
| Cloudflare KV | No key-value cache needs; Postgres handles all state |
| Cloudflare Queues | No async job queue needed at beta scale |
| Hetzner Object Storage | EU-only; transatlantic latency from Ashburn VPS |

---

## 13. Future Considerations

**Federated instances.** Each federation node is an independent VPS behind its own Cloudflare proxy. R2 becomes the shared reference data distribution point — all instances pull the same reference SQLite. Workers AI could serve as a shared narrator endpoint, or each instance could run its own.

**Cloudflare Pages for docs.** Project documentation (Sphinx-generated) could deploy to Cloudflare Pages at `docs.percypedia.biz`, separate from the game server. No shared infrastructure with the VPS.

**R2 as CDN origin.** If static assets grow large (map tiles, audio, video), R2 can serve as a CDN origin directly, bypassing the VPS for media delivery. Cloudflare's free tier includes R2 → CDN serving with no egress fees.

**Workers as API gateway.** If the game needs geographic routing (players in different regions routed to different VPS instances), a Cloudflare Worker can serve as an edge router. This is Epoch 3 infrastructure.

**SQL/PGQ over Hyperdrive.** Cloudflare Hyperdrive provides connection pooling for Postgres. Irrelevant for a single VPS, but useful if Workers ever need direct database access for edge-computed features.

---

## 14. Implementation Tasks

### Phase 1: Terraform Foundation

- T001: Write `infra/terraform/cloudflare.tf` with provider configuration and zone data source
- T002: Create `cloudflare_record.babylon` A record resource
- T003: Create `cloudflare_zone_settings_override` for SSL, TLS, HTTPS settings
- T004: Create three `cloudflare_r2_bucket` resources (backups, reference, archives)
- T005: Create `cloudflare_ruleset.rate_limit` for API rate limiting
- T006: Create `cloudflare_ruleset.cache` for static asset caching and API bypass
- T007: Validate: `terraform plan` shows expected resources, `terraform apply` provisions cleanly

### Phase 2: Origin Security (Ansible)

- T008: Generate Origin CA certificate from Cloudflare Dashboard, add to Ansible vault
- T009: Update Ansible `nginx` role to deploy Origin CA cert and enable SSL
- T010: Add `ssl_verify_client on` with Cloudflare authenticated origin pull CA
- T011: Template `set_real_ip_from` directives from Cloudflare IP list
- T012: Create Hetzner Cloud Firewall rules in Terraform (Cloudflare IPs + SSH only)
- T013: Update nftables rules in Ansible `common` role to match Cloud Firewall
- T014: Validate: direct connection to VPS IP returns SSL error; connection via `babylon.percypedia.biz` succeeds

### Phase 3: R2 Integration (Ansible + Scripts)

- T015: Install rclone in Ansible `backup` role
- T016: Deploy rclone config with R2 credentials from vault
- T017: Update `backup-postgres.sh` to write to `babylon-backups` with daily/weekly prefix convention
- T018: Create R2 lifecycle rules for 7-daily + 4-weekly retention
- T019: Write `upload-reference-sqlite.sh` script for `babylon-reference` bucket
- T020: Create Woodpecker pipeline for monthly restore verification from R2
- T021: Validate: backup uploads, lifecycle expires old files, restore succeeds

### Phase 4: Workers AI (Django)

- T022: Add `WORKERS_AI_*` settings to Django settings module
- T023: Write `narrative/client.py` — HTTP client for Workers AI REST API with timeout and retry
- T024: Write `narrative/gramscian_wire.py` — prompt construction for three-channel output
- T025: Integrate with tick resolution: call after engine step, store result in Postgres
- T026: Add `WORKERS_AI_ENABLED` feature flag; verify game works with flag off
- T027: Validate: narrative generates for a test tick, empty narrative on timeout, game continues on failure

### Phase 5: CI/CD Integration

- T028: Add cache purge step to Woodpecker deploy pipeline (after `collectstatic`)
- T029: Add weekly Cloudflare IP refresh pipeline (re-template Nginx config, reload)
- T030: Validate: deploy triggers cache purge, IP refresh updates Nginx without downtime

---

## 15. Falsifiable Predictions

Per Constitution Article III.2, every spec defines falsifiable predictions:

**FP-039-1**: With Cloudflare proxy enabled and Hetzner Cloud Firewall restricting to Cloudflare IPs, a direct HTTP request to the VPS IP address on port 443 returns a connection refused or SSL handshake failure. If this succeeds, the origin lockdown is broken.

**FP-039-2**: With CDN caching enabled, repeated requests to `/static/main.<hash>.js` within the TTL window produce `CF-Cache-Status: HIT` headers. If all requests show `MISS`, caching is misconfigured and every static asset request hits the origin.

**FP-039-3**: Workers AI narrative generation adds less than 3 seconds to tick resolution latency (p95). If narrative generation consistently exceeds 3 seconds, the timeout value must decrease or the call must move to async/background.

**FP-039-4**: A pg_dump backup uploaded to R2 can be restored to a fresh Postgres instance and pass schema integrity checks. If the monthly restore verification fails, the backup pipeline is producing corrupt or incomplete dumps.

**FP-039-5**: Disabling the `WORKERS_AI_ENABLED` flag produces identical game state outcomes (same tick data, same graph mutations) as enabled mode. If outcomes differ, the narrative layer is influencing mechanical state, violating "AI Observes, Never Controls."
