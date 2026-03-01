# Article X: Deployment Infrastructure

> Annex to [Babylon Constitution](../constitution.md). This file contains the full rationale, rejected alternatives, and implementation details for each infrastructure principle.

### 1. Bare Metal, Ansible-Managed

No Docker, no Nix, no containerization. Everything installs on the host
OS via apt packages and is configured declaratively by Ansible playbooks.
The entire server state is described in version-controlled roles. Nothing
is installed by hand on the VPS.

**Rationale**: Containers add an abstraction layer that must be maintained,
debugged, and secured independently of the application. For a solo-developer
project (X.6), the operational cost of container orchestration exceeds its
benefits. Ansible playbooks provide declarative configuration without the
runtime overhead of container images, registries, and networking overlays.

**Rejected Alternatives**:

| Alternative | Why Rejected |
| ----------- | ------------ |
| Docker Compose | Additional abstraction layer; debugging requires container-specific tools; solo-developer overhead |
| Nix/NixOS | Steep learning curve; non-standard package ecosystem; repair requires Nix expertise |
| Kubernetes | Explicitly rejected per X.6 (requires second full-time job to maintain) |

**Implementation Requirements**:

1. All server configuration MUST exist as Ansible roles in version control
2. `apt` is the sole package manager for system packages
3. Manual SSH changes are prohibited — if it is not in a playbook, it does not exist
4. Ansible inventory MUST support at minimum: production, staging

### 2. Terraform Provisions, cloud-init Bridges, Ansible Configures

Terraform creates and destroys cloud resources (servers, firewalls, DNS
records, object storage). cloud-init creates the deploy user on first
boot — the only thing it does. Ansible configures everything after. These
three tools have non-overlapping responsibilities.

**Responsibility Matrix**:

| Tool | Creates | Configures | Manages State |
| ---------- | ------------------------------ | ---------- | ------------- |
| Terraform | Servers, firewalls, DNS, R2 | Nothing | HCL state file |
| cloud-init | Deploy user + SSH key | Nothing | None (runs once) |
| Ansible | Nothing | Everything | Playbook idempotency |

**Rationale**: Overlapping responsibilities between provisioning and
configuration tools is a primary source of infrastructure bugs. When
Terraform and Ansible both manage firewall rules, drift is inevitable.
Strict separation means each tool owns its domain completely.

**The cloud-init Bridge**: cloud-init exists solely to solve the bootstrap
problem — Ansible needs SSH access to configure a server, but the server
needs a user and SSH key before Ansible can connect. cloud-init creates
the deploy user with the Ansible SSH key on first boot. It does nothing
else. This is the narrowest possible bridge between provisioning and
configuration.

### 3. Postgres Bare Metal from PGDG

PostgreSQL installs from the upstream PGDG apt repository directly on
the host. Extensions (PostGIS, pgvector) install as apt packages.
Ansible's `community.postgresql` collection manages database creation,
roles, extensions, and pg_hba declaratively. Postgres listens on Unix
socket only — never exposed to the network.

**Security Model**: Unix socket only. Postgres never listens on a TCP
port. Django connects via the socket file. This eliminates an entire
class of network-based attacks. The `pg_hba.conf` is managed by Ansible
and uses `peer` authentication for the deploy user.

**Extension Management**: PostGIS and pgvector install as system packages
from the PGDG repository. This ensures binary compatibility with the
installed PostgreSQL version. Extensions are enabled per-database via
Ansible's `community.postgresql.postgresql_ext` module.

**Relationship to II.6**: The Hydration Pattern (II.6) originally specified
SQLite as the cold storage layer. Feature 037 extends this to PostgreSQL
for runtime state persistence. The constitutional commitment is to the
pattern (cold → warm → hot → back), not to a specific database engine.
Postgres replaces SQLite for runtime writes; SQLite remains for read-only
reference data (`marxist-data-3NF.sqlite`).

**Rejected Alternatives**:

| Alternative | Why Rejected |
| ----------- | ------------ |
| Managed database (RDS, etc.) | Cost; vendor lock-in; solo-developer can manage single Postgres instance |
| Postgres in Docker | Additional failure mode; volume management complexity; see X.1 |
| CockroachDB/distributed | Solo-developer constraint (X.6); single-node sufficient |

### 4. systemd as Sole Supervisor

All processes (Postgres, Gunicorn, Nginx, Woodpecker) run as systemd
units. No additional supervisors. Service dependencies, restart policies,
and cgroup resource limits are declared in unit files deployed by Ansible.

**Managed Services**:

| Unit | Type | Restart Policy | Resource Limits |
| -------- | ------- | -------------- | --------------- |
| postgres | service | always | Memory via cgroup |
| gunicorn | service | on-failure | Memory + CPU |
| nginx | service | always | Default |
| woodpecker-server | service | on-failure | Memory |
| woodpecker-agent | service | on-failure | Memory + CPU |

**Rationale**: systemd is already present on every Debian/Ubuntu server.
Adding Supervisor, PM2, or similar tools creates a second process
management layer that must be configured, monitored, and debugged
independently. systemd provides dependency ordering (`After=`, `Requires=`),
resource limits (cgroups), and restart policies natively.

**Implementation Requirements**:

1. Every long-running process MUST have a systemd unit file
2. Unit files MUST be deployed by Ansible (not created manually)
3. Service dependencies MUST be explicit (`After=`, `Requires=`)
4. Resource limits MUST be declared for all application processes

### 5. Cloudflare Edge, Hetzner Compute

Nothing computes on Cloudflare; nothing reaches users without Cloudflare
first. Cloudflare handles DNS, SSL, DDoS, WAF, CDN, R2 storage, and
Workers AI. Hetzner handles Django, Postgres, NetworkX, and CI/CD.
Division of labor is strict — no function is shared between the two.

**Request Path**:

```
Player → Cloudflare (DNS + SSL + WAF + CDN)
       → Hetzner VPS (Nginx → Gunicorn → Django)
       → Engine (NetworkX, Systems, Formulas)
       → Postgres (state persistence)
       → back up the chain
```

**Responsibility Matrix**:

| Function | Cloudflare | Hetzner |
| ------------- | ---------- | ------- |
| DNS | Yes | No |
| SSL termination | Yes | No |
| DDoS/WAF | Yes | No |
| CDN (static) | Yes | No |
| R2 (object storage) | Yes | No |
| Workers AI | Yes | No |
| Django | No | Yes |
| Postgres | No | Yes |
| NetworkX engine | No | Yes |
| CI/CD (Woodpecker) | No | Yes |

**Relationship to II.5**: Workers AI on the Cloudflare edge handles the
AI narrative layer. This aligns with II.5 (AI Observes, Never Controls) —
the AI layer is physically separated from the compute layer, reinforcing
the architectural boundary between mechanics and narrative.

**Rationale**: Cloudflare provides enterprise-grade edge security at a
price point accessible to solo developers (free tier covers most needs).
Hetzner provides bare-metal-equivalent compute at commodity pricing.
Neither provider's functions overlap, eliminating configuration drift
between edge and origin.

### 6. Solo-Developer Constraint

Every infrastructure component is filtered through: does this require a
second full-time job to maintain? If yes, reject it. Kubernetes,
Prometheus+Grafana, HashiCorp Vault, service meshes, and container
orchestration are explicitly rejected until scale demands them.

**The Filter Question**: "If I am sick for a week, will this component
drift into an unrecoverable state?" If yes, it is too complex.

**Explicitly Rejected (with conditions for reconsideration)**:

| Component | Why Rejected | Reconsider When |
| --------- | ------------ | --------------- |
| Kubernetes | Operational complexity exceeds single-developer capacity | >3 services requiring independent scaling |
| Prometheus + Grafana | Maintenance overhead for monitoring stack | >1000 DAU requiring SLA monitoring |
| HashiCorp Vault | Secrets management overhead | Regulatory compliance requirement |
| Service mesh (Istio, etc.) | Requires K8s; see above | Never (unless K8s adopted) |
| Container orchestration | See X.1 | Parallel team deployment requirement |
| Multi-region | Coordination complexity | Legal requirement or >50ms latency SLA |

**Rationale**: Infrastructure complexity has a maintenance tax that
compounds. Each component requires monitoring, upgrading, debugging, and
securing. A solo developer's time is the scarcest resource. Every hour
spent maintaining infrastructure is an hour not spent on the simulation
engine. The constitution acknowledges this as a constraint, not a
preference — these tools are rejected because of current scale, not
because they lack merit.

**Relationship to IX**: Adding infrastructure components that violate
this constraint requires a constitutional amendment, not just a spec
approval. This ensures the filter is applied deliberately, not bypassed
by feature creep.
