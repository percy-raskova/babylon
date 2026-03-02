# Specification: Django Web Application & Infrastructure

**Feature Branch**: `038-django-web-application`
**Created**: 2026-03-01
**Revised**: 2026-03-01 (v3 — combined application + infrastructure)
**Status**: Implementation-ready
**Depends On**: Feature 037 (Postgres Runtime DB), Constitution, Features 011-036
**Supersedes**: PyQt6 desktop application as primary interface, Feature 038 v1/v2
**Incorporates**: Babylon Infrastructure Specification v2

---

## 1. Purpose & Scope

This spec defines everything needed to stand up Babylon as a single-player web application: a Django backend serving a React frontend, running bare metal on a single VPS managed by Ansible, fronted by Cloudflare. The player builds revolutionary organizations against a CPU-controlled state apparatus. Game state lives in Postgres. JSON is the interchange format at every boundary.

This is a combined specification covering both the application layer (Django project, engine bridge, JSON API, React frontend, game models) and the infrastructure layer (Terraform provisioning, Ansible configuration, systemd supervision, Cloudflare edge services, backups, CI/CD). Previous versions of this spec covered only the application layer and assumed Docker Compose for deployment. That assumption is now replaced: everything runs bare metal, managed by Ansible.

**This spec covers:**

- Django project scaffolding and settings
- Engine bridge: how Django calls the simulation engine
- JSON API surface for the React frontend
- Authentication (single-player, but login-gated for beta access control)
- React frontend architecture (point-and-click MVP)
- NPC decision system (rules-based heuristic)
- Narrative AI integration (optional for MVP)
- VPS provisioning (Terraform + cloud-init)
- Server configuration (Ansible roles)
- Process supervision (systemd)
- Edge security and CDN (Cloudflare)
- Database installation and tuning (PostgreSQL 18 bare metal)
- Backup strategy (pg_dump → R2)
- CI/CD pipeline (Woodpecker)
- Infrastructure interface contract (where the two layers meet)

**This spec does NOT cover:**

- The Postgres schema (Feature 037)
- Simulation engine internals (Features 011-036)
- Multiplayer or concurrent play (Babylon is single-player; the CPU is the enemy)
- Federated multi-instance play (defer)
- Steam/PyInstaller distribution (separate concern)
- Sophisticated NPC AI (MVP uses rules-based heuristic per Feature 025)

---

## Part I: Architectural Decisions

These decisions govern both the application and infrastructure layers. They are the highest-level constraints that everything else must satisfy.

### 2.1 Single-Player, Immediate Resolution

Babylon is a single-player turn-based strategy game. The player controls revolutionary organizations. The state apparatus, businesses, and rival factions are CPU-controlled NPCs using rules-based heuristics. There is no multiplayer, no waiting for other players, no turn deadlines, no concurrency concerns.

The gameplay loop is immediate and synchronous. The player views the current game state, selects actions for their organizations, and submits. The tick resolves instantly — Django calls the engine in-process, the engine computes the new state, the result renders. No task queues, no Celery, no WebSockets, no polling. Plain HTTP request/response. The player clicks "End Turn," the page refreshes with the new world.

This means the entire concurrency model collapses to "one user, one request at a time." Gunicorn workers exist for reliability and static file handling, not for parallel request processing. The tick resolver is the only process touching game state, and it runs synchronously within the Django request cycle.

### 2.2 Django Calls the Engine Directly

When the player submits actions and triggers tick resolution, the Django view calls the existing engine code in-process. The engine runs `step()` on the NetworkX graph, computes all 12+ system passes, and returns. The view then persists the new state to Postgres and serves the updated game state as JSON.

No separation between "web server" and "game server." They are the same process. This is the simplest possible architecture for a single-player turn-based game and there is no reason to complicate it until tick resolution takes longer than a few seconds (which would indicate a performance bug in the engine, not an architecture problem).

### 2.3 CPU Opponents via Rules Heuristic

NPC organizations (state apparatus, businesses, civil society orgs, rival factions) make decisions via deterministic rules-based heuristics, not LLMs. This is Feature 025's NPC AI stub. The heuristic runs during tick resolution as part of the engine's OODA system. It is fast (microseconds per org), deterministic (same RNG seed produces same decisions), and requires zero external API calls.

The decision architecture uses a strategy pattern so the heuristic can be replaced with a trained neural network or LLM-backed agent later without changing any other code. But for MVP, it is pure Python conditional logic running inside the engine.

### 2.4 JSON as Universal Interchange

JSON is the glue at every boundary in the system.

Between React and Django: the API serves and consumes JSON exclusively. No server-rendered HTML templates in the final architecture. React fetches game state as JSON, renders it, and posts player actions as JSON.

Between Django and the engine: the `EngineBridge` translates between Django's request/response world and the engine's Pydantic models. Pydantic models serialize to JSON natively via `.model_dump()`. The bridge hydrates engine state from Postgres, runs the tick, and serializes the result back to JSON for the API response.

Between the engine and Postgres: Feature 037 specifies JSONB columns for flexible attribute storage (node attributes, edge attributes, config snapshots). The engine writes structured JSON to Postgres and reads it back during hydration.

This means every layer speaks JSON. A developer can inspect any boundary with `curl` and `jq`. The React frontend can be replaced with any JSON-consuming client without touching the backend. The engine's Pydantic models guarantee JSON schema consistency.

### 2.5 Everything Runs Bare Metal, Managed by Ansible

There is no Docker, no Nix, no containerization layer. Terraform provisions the VPS and seeds the deploy user via cloud-init. Ansible configures and maintains everything on the server. systemd supervises all processes.

The governing design constraint is: will this require a second full-time job to maintain? If yes, reject it. Complexity is the enemy. A solo developer needs to be able to rebuild the entire server from scratch in twenty minutes by running `terraform apply` followed by `ansible-playbook playbook.yml`.

PostgreSQL 18 installs from the PGDG apt repository directly on the host. PostGIS, pgvector, and pgrouting install as apt packages alongside it. Python and Poetry install via system packages. Nginx installs from Debian repos. Every package, configuration file, systemd unit, firewall rule, and cron job is described in Ansible playbooks. Nothing is installed or configured by hand.

Local development runs Django directly via `manage.py runserver` against a local Postgres instance. The developer can install Postgres however they prefer — Docker, Homebrew, system package. The spec does not constrain the local development database, only the production one.

### 2.6 Cloudflare as Shield, Hetzner as Brain

Cloudflare operates as the shield and content delivery layer. Nothing computes on Cloudflare; nothing reaches users without passing through Cloudflare first. The domain `babylon.percypedia.biz` is DNS-proxied through Cloudflare, meaning the public internet never sees the Hetzner IP directly.

Cloudflare provides: DNS with automatic HTTPS certificate provisioning at the edge, L7 DDoS protection and WAF (SQL injection blocking, rate limiting), CDN caching for static assets (React build, CSS, images), uptime monitoring for the proxied domain, and R2 object storage (zero egress fees) for Postgres backup archives.

Hetzner provides: the VPS running Django, Postgres, Nginx, and the simulation engine. The L3/L4 Cloud Firewall filters traffic at the hypervisor before it reaches the VPS. The host firewall (nftables) provides defense-in-depth behind Hetzner's Cloud Firewall.

This division means SSL termination happens at the Cloudflare edge, not on the VPS. There is no Certbot, no Let's Encrypt certificate renewal, no SSL configuration in Nginx. Nginx accepts traffic from Cloudflare's IP ranges over HTTP (or Cloudflare's origin certificate for full-strict mode) and sets the real IP header from Cloudflare's `CF-Connecting-IP`.

### 2.7 MVP Frontend: Point-and-Click React

The MVP frontend is a React single-page application that provides a point-and-click interface for the complete game loop. The player must be able to view the hex map, inspect territories and organizations, select actions from the nine-verb vocabulary, submit actions, and view tick results — all without touching a terminal, writing JSON by hand, or reading raw database output.

This is not a polished game UI. It is a functional interface that lets someone who is not the developer play the game and provide feedback. Visual design is secondary to interaction completeness. Every player verb must be accessible via clickable UI elements.

---

## Part II: Application Layer

### 3. Django Project Structure

```
babylon/
├── src/babylon/                    # Engine code (untouched by Django)
├── web/                            # Django project root
│   ├── manage.py
│   ├── babylon_web/                # Django project package
│   │   ├── __init__.py
│   │   ├── settings/
│   │   │   ├── __init__.py
│   │   │   ├── base.py             # Shared settings
│   │   │   ├── development.py      # DEBUG=True, local Postgres
│   │   │   └── production.py       # DEBUG=False, Cloudflare, Unix socket
│   │   ├── urls.py                 # Root URL conf
│   │   └── wsgi.py                 # Gunicorn entry point
│   ├── game/                       # Main game Django app
│   │   ├── models.py               # Django ORM: sessions, actions, results
│   │   ├── views.py                # Minimal: serve React SPA shell
│   │   ├── urls.py                 # URL patterns
│   │   ├── serializers.py          # DRF serializers for JSON API
│   │   ├── api.py                  # DRF viewsets
│   │   ├── admin.py                # Admin panel registration
│   │   ├── engine_bridge.py        # Adapter: Django ↔ simulation engine
│   │   └── tick_resolver.py        # Tick resolution orchestration
│   ├── accounts/                   # Auth app
│   │   ├── models.py               # Player profile extending User
│   │   ├── views.py                # Login/logout
│   │   └── urls.py
│   └── frontend/                   # React app (Vite)
│       ├── package.json
│       ├── vite.config.js
│       └── src/
│           ├── App.jsx
│           ├── components/
│           │   ├── HexMap.jsx      # Leaflet + H3 hex rendering
│           │   ├── ActionPanel.jsx # 9-verb selection interface
│           │   ├── OrgDashboard.jsx# Organization state display
│           │   ├── TickResults.jsx # Post-resolution narrative + events
│           │   ├── InspectorPanel.jsx  # Node/edge detail on click
│           │   └── TimeSeriesPanel.jsx # Economic charts over ticks
│           ├── api/
│           │   └── client.js       # JSON API client (fetch wrapper)
│           └── hooks/
│               └── useGameState.js # State management
├── infra/                          # Infrastructure as code
│   ├── terraform/
│   │   ├── main.tf                 # Hetzner server + cloud-init
│   │   ├── cloudflare.tf           # DNS, R2 buckets, page rules
│   │   ├── variables.tf
│   │   ├── outputs.tf              # Server IP, bucket URLs
│   │   ├── cloud-init.yml          # Deploy user bootstrap
│   │   └── terraform.tfvars        # (gitignored)
│   ├── ansible/
│   │   ├── ansible.cfg
│   │   ├── inventory.yml           # Populated from terraform output
│   │   ├── playbook.yml            # Master playbook
│   │   ├── roles/
│   │   │   ├── common/             # SSH, fail2ban, firewall, swap
│   │   │   ├── postgres/           # PGDG install, extensions, config
│   │   │   ├── python/             # Python 3.12, Poetry
│   │   │   ├── babylon/            # App deploy, systemd unit, .env
│   │   │   ├── nginx/              # Reverse proxy config
│   │   │   ├── woodpecker/         # CI/CD binaries + systemd
│   │   │   └── backup/             # pg_dump cron, rclone to R2
│   │   └── vault/secrets.yml       # ansible-vault encrypted
│   └── scripts/
│       └── upload-reference-sqlite.sh
├── data/                           # Reference SQLite database (read-only)
├── pyproject.toml                  # Poetry: engine + Django deps
└── .woodpecker.yml                 # CI/CD pipeline definition
```

The Django project lives in `web/` alongside the engine in `src/babylon/`. They share the same Poetry environment. The `infra/` directory contains all infrastructure-as-code. The engine is imported by the Django project as a Python package — no separate build step, no subprocess calls, no REST API between them.

### 4. Django Settings

#### 4.1 Shared Settings (base.py)

The database engine is `django.contrib.gis.db.backends.postgis` (GeoDjango) to enable spatial queries natively. The SQLite reference database is mounted as a second database connection in read-only mode — it is the empirical ground truth and is never written to by Django or the engine.

Django REST Framework handles all JSON serialization with session-based authentication. CORS headers are enabled for local development where the React dev server runs on a different port. All sensitive values (database password, secret key, domain) come from environment variables, never hardcoded.

#### 4.2 Production Settings (production.py)

These settings reflect the bare-metal Ansible deployment with Cloudflare proxying.

`DEBUG = False`. `ALLOWED_HOSTS` set to the deployment domain (`babylon.percypedia.biz`). `SECURE_SSL_REDIRECT = True` to force HTTPS. `SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')` because Cloudflare terminates TLS at the edge and Nginx forwards over HTTP internally — without this header, Django's CSRF middleware rejects all POST requests as insecure. `SESSION_COOKIE_SECURE = True`, `CSRF_COOKIE_SECURE = True`. `CSRF_TRUSTED_ORIGINS` includes the production domain with HTTPS scheme. `SECURE_HSTS_SECONDS = 300` initially, increased to `31536000` after confirming everything works (HSTS is cached by browsers and effectively irreversible once set to a long timeout).

The database connection uses a Unix socket, not TCP. The `HOST` field in `DATABASES` is empty string (Django's convention for Unix socket via the default `/var/run/postgresql/` socket directory). There is no TCP port, no hostname, no Docker service name. See the Infrastructure Interface section for the exact connection parameters.

Static files are collected to `/opt/babylon/staticfiles/` via `collectstatic`, and Nginx serves this directory directly.

#### 4.3 Development Settings (development.py)

`DEBUG = True`. CORS allows `localhost:5173` (Vite dev server). Database points to `localhost:5432` via TCP (the developer's local Postgres, however installed). No `SECURE_PROXY_SSL_HEADER` because there is no reverse proxy in development.

### 5. Engine Bridge

#### 5.1 Purpose

The `engine_bridge.py` module is the sole translation layer between Django's HTTP/JSON world and the simulation engine's Pydantic/NetworkX world. It is the only file in the Django project that imports engine code. If any other Django module imports from `babylon.engine` or `babylon.models`, that is a boundary violation — stop and refactor.

This boundary preserves the option of running the engine headless, in unit tests, behind a CLI, or behind a completely different frontend. The engine must never know Django exists.

#### 5.2 Responsibilities

**Hydration**: Read the latest tick state from Postgres (via Feature 037's persistence layer) and reconstruct the in-memory simulation state: NetworkX graph, XGI hypergraph, WorldState Pydantic model, and all system registrations. This happens once per tick resolution request.

**Action injection**: Translate the player's submitted actions (JSON from the API) into the engine's action format and insert them into the action queue. Also inject NPC actions generated by the rules heuristic.

**Tick execution**: Call `engine.run_tick()`. During this call, zero database I/O occurs. The engine operates purely on in-memory state. This is a constitutional requirement (Article II.6: State is Data, Engine is Transformation).

**Persistence**: After tick execution, write the new in-memory state back to Postgres via Feature 037's bulk insert path. Full snapshot, not diffs.

**Snapshot serialization**: Serialize the current game state to a JSON-compatible dict for the API to serve. This includes the hex grid, node attributes, edge relationships, organization states, community consciousness, economic indicators, and event log for the current tick.

#### 5.3 JSON Output Contract

The bridge exposes a `get_snapshot()` method that returns a Python dict (JSON-serializable) structured for frontend consumption. The exact schema evolves with the engine, but the top-level keys are stable:

- `tick`: current tick number
- `economy`: national and county-level economic indicators
- `nodes`: list of graph nodes with type, attributes, and position
- `edges`: list of graph edges with type, mode, and attributes
- `communities`: hyperedge community states with consciousness
- `hexes`: hex grid states with economic and control data
- `organizations`: player and NPC org summaries (OODA state, resources, membership)
- `events`: events that occurred during the last tick resolution
- `available_actions`: for each player org, the 9 verbs with valid targets and costs
- `narrative`: AI-generated text describing the tick (empty string if narrative AI disabled)

This dict is what the React frontend receives from `GET /api/games/{id}/state/`. It is the complete view of the game world.

### 6. Django Models

Django ORM manages game management tables only. Simulation state persists via Feature 037's raw SQL layer. These Django models handle sessions, player actions, and action outcomes.

#### 6.1 GameSession

Represents a single playthrough. Captures the scenario name, a frozen copy of the full GameDefines configuration (JSONB), the RNG seed for deterministic replay, lifecycle status (active/paused/completed/abandoned), current tick number, and the user who created it.

A player can have multiple saved games. Each game is fully independent with its own state history. Because Babylon is single-player, the GameSession has a single `created_by` user who is the player. There is no PlayerSession join table, no multi-user game linking.

#### 6.2 PlayerAction

One submitted action for a specific tick and organization. Contains the organization node ID, the verb (one of the nine player verbs), the target node or edge ID, and a JSON parameters field for verb-specific data.

The uniqueness constraint is `(game, tick, organization_id)` — one action per organization per tick. Since this is single-player, all actions for a tick come from the same user. The player may control multiple organizations and submits one action per org.

#### 6.3 ActionResult

Resolution outcome of a player action, written during tick resolution. Contains the initiative score, resource costs deducted, success/failure flag, and a JSON state deltas field describing what changed. The state deltas are what the frontend displays as "here's what happened when you did that."

### 7. JSON API

All communication between the React frontend and Django is JSON over REST. The API is the contract that decouples the frontend from the backend. If the API is correct, the frontend can be rebuilt from scratch without touching Django, and vice versa.

#### 7.1 Endpoints

**Game lifecycle:**

- `GET /api/games/` — list the player's saved games (id, scenario, tick, status, timestamps)
- `POST /api/games/` — create a new game (scenario name, optional RNG seed)
- `GET /api/games/{id}/` — game metadata (scenario, config, status, current tick)
- `POST /api/games/{id}/pause/` — pause a game
- `POST /api/games/{id}/resume/` — resume a paused game

**Game state (read-only, no mutations):**

- `GET /api/games/{id}/state/` — full game state snapshot as JSON (the `get_snapshot()` output)
- `GET /api/games/{id}/map/` — hex grid data optimized for Leaflet rendering (GeoJSON features with H3 boundaries and economic attributes)
- `GET /api/games/{id}/timeseries/` — tick summary history for charts (arrays of per-tick economic ratios, edge counts, org counts)
- `GET /api/games/{id}/node/{node_id}/` — detailed node state (social class, territory, or organization)
- `GET /api/games/{id}/org/{org_id}/` — organization detail (OODA profile, membership, resources, edges)

**Player actions (mutations):**

- `GET /api/games/{id}/actions/available/` — for each player org, the 9 verbs with valid targets and resource costs for the current tick
- `POST /api/games/{id}/actions/` — submit an action (org_id, verb, target_id, parameters)
- `GET /api/games/{id}/actions/pending/` — actions submitted for current tick but not yet resolved
- `POST /api/games/{id}/resolve/` — trigger tick resolution (submit all pending actions, run engine, return results)

**Tick results:**

- `GET /api/games/{id}/results/{tick}/` — results of a specific tick (action outcomes, events, narrative text, state deltas)

#### 7.2 JSON Response Conventions

All responses follow a consistent envelope:

```json
{
  "status": "ok",
  "data": { ... },
  "tick": 42,
  "session_id": "uuid"
}
```

Error responses:

```json
{
  "status": "error",
  "error": "description of what went wrong",
  "code": "ACTION_INVALID_TARGET"
}
```

#### 7.3 Authentication

Every API endpoint requires session authentication. The React app includes the Django session cookie and CSRF token with every request. Unauthenticated requests receive a 401 response. There is no token-based auth, no JWT, no OAuth — just Django's built-in session middleware.

### 8. Authentication

#### 8.1 Beta Access Control

No self-registration. Percy creates accounts manually via the Django admin panel. Beta testers receive a username and password. They log in at `/accounts/login/`, receive a session cookie, and access the game. Nobody can access any game functionality without credentials Percy has explicitly created.

#### 8.2 Login Flow

The React app checks auth status on load. If not authenticated, it redirects to a login page (can be a simple Django template or a React login component posting to Django's auth endpoint). After successful login, the session cookie is set and the React app loads the game list.

#### 8.3 Player Profile

A minimal `PlayerProfile` model extends Django's User with a display name and game statistics. This is mostly for the admin panel and future use. The game itself identifies the player by `request.user`.

### 9. React Frontend (MVP)

#### 9.1 Design Philosophy

The MVP frontend must be functional, not beautiful. Every game interaction must be accessible via point-and-click. The player should never need to type JSON, read logs, or use a terminal. The minimum viable experience is: look at the map, look at your orgs, pick an action, click submit, see what happened.

Visual polish comes after the simulation validates. The trigger for investing in frontend quality is when a beta tester says "this is interesting but hard to use" — meaning the game mechanics are engaging enough that the interface is the bottleneck.

#### 9.2 Component Architecture

**HexMap** — The primary game viewport. A Leaflet map centered on Detroit (42.33°N, 83.05°W) with H3 hexagons rendered as GeoJSON polygons. Color encodes a selectable metric: profit rate, heat, consciousness, organizational presence, or edge density. Clicking a hex opens the inspector panel with detail. This component fetches data from `/api/games/{id}/map/` and re-fetches after each tick resolution. Color palette follows Constitution Article VII: BLOOD_VOID, BLACK, CRIMSON (power), GOLD (action/solidarity), SILVER (mass), ASH (muted). Luminosity encodes magnitude.

**ActionPanel** — The player's primary interaction surface. Displays the player's organizations with their current OODA state and available action points. For each org, shows all 9 verbs organized in the constitutional 3×3 grid: Build Org (Educate, Reproduce, Investigate), Project Power (Attack, Mobilize, Campaign), Manage Resources (Aid, Move, Negotiate). All verbs are always visible — none are hidden or disabled. Selecting a verb shows valid targets and resource costs. The player queues one action per org, then clicks "End Turn" to trigger resolution. Feedforward previews show projected effects before submission.

**OrgDashboard** — Detailed view of an organization. OODA profile (cycle time, action points, capacity), membership count and composition (cadre vs sympathizer base), resource state (Cadre Labor, Sympathizer Labor, material resources), edge relationships to other orgs with mode indicators (EXTRACTIVE, TRANSACTIONAL, SOLIDARISTIC, ANTAGONISTIC, CO-OPTIVE as categorical badges, not scalar bars), and consciousness distribution across members.

**InspectorPanel** — Context-sensitive detail panel. Clicking a hex, node, edge, or organization populates this panel with relevant data. For a territory node: economic composition, social class distribution, organizational presence, heat level. For an edge: mode, flow values, transition history. For a community hyperedge: consciousness tendency (assimilationist-liberal, assimilationist-fascist, revolutionary), collective identity, ideological contestation, material basis.

**TickResults** — Displayed after tick resolution. Shows what happened: player action outcomes (success/failure, costs, effects), NPC actions taken (state apparatus verb selections with factional dominance indicator), events fired (uprisings, repressions, edge mode transitions, heat spikes), economic changes, and narrative text if available. This is the "newspaper" of the game — what the player reads to understand the consequences of their choices and plan their next move.

**TimeSeriesPanel** — Line charts showing economic indicators over ticks. Profit rate, exploitation rate, OCC, imperial rent Φ, consciousness levels by community, organizational strength metrics. Uses Recharts. Data comes from `/api/games/{id}/timeseries/` which reads from Feature 037's tick summary table. Helps the player see trends and validate whether their strategy is working.

#### 9.3 Game Loop in the Frontend

1. Player loads game → React fetches `/api/games/{id}/state/` → renders map, orgs, available actions
2. Player clicks through orgs, selects verbs and targets → actions stored in React component state
3. Player clicks "End Turn" → React POSTs each action to `/api/games/{id}/actions/` → then POSTs to `/api/games/{id}/resolve/`
4. Django resolves the tick (engine runs in-process, returns immediately) → React fetches the new state and tick results → renders updated map and TickResults panel
5. Repeat

The entire loop is synchronous from the player's perspective. Click, wait briefly, see results. No polling, no WebSockets, no loading spinners (unless tick resolution takes unexpectedly long, in which case there is a bug in the engine).

#### 9.4 Build and Serving

The React app is built with Vite. Production build outputs to `web/frontend/dist/`. Django's `STATICFILES_DIRS` includes this directory. `collectstatic` copies everything to `/opt/babylon/staticfiles/`. Nginx serves static files directly from that directory. Cloudflare caches them at the edge. In development, Vite's dev server runs on port 5173 with hot module replacement, proxying API calls to Django on port 8000.

### 10. NPC Decision System (Rules Heuristic)

#### 10.1 Architecture

NPC organizations make decisions during tick resolution as part of the engine's OODA system. The heuristic is pure Python conditional logic — no external API calls, no LLM, no neural network. It runs inside the engine, not in Django.

The decision architecture uses a strategy pattern: each organization subtype (StateApparatus, Business, PoliticalFaction, CivilSocietyOrg) has a corresponding decision strategy that implements a common protocol. The strategy receives the current WorldState and returns a list of actions. The engine resolves NPC actions alongside player actions in initiative order during the Action Phase.

#### 10.2 State Apparatus Heuristic

The state apparatus (FBI, local police, etc.) operates via the attention thread system (Feature 032). The heuristic allocates threads to highest-heat organizations, selects from the six state verbs (ADMINISTER, DEVELOP, RESEARCH, CO-OPT, REPRESS, WITHDRAW) weighted by the currently dominant faction's objective function. Finance-capital faction favors CO-OPT and DEVELOP. Security-state faction favors REPRESS and ADMINISTER. Settler-populist faction favors DEVELOP (as displacement) and CO-OPT (bribe labor aristocracy). The scarce resource is attention (threads), not violence capacity.

#### 10.3 Business Heuristic

Businesses employ from the cheapest available labor pool, attempt to break strikes when active, and otherwise maintain operations. Surplus extraction happens automatically in Layer 0 — the business heuristic only handles strategic decisions about labor relations and capital allocation.

#### 10.4 Rival Faction Heuristic

Rival political factions recruit in territories where the player is weak, organize existing members, and consider alliances based on ideological overlap thresholds. Liberal factions default to CAMPAIGN and MOBILIZE. Fascist factions default to MOBILIZE and ATTACK when settler collective identity is rising.

#### 10.5 Replacement Path

The strategy pattern means the heuristic can be replaced per-org-type without changing any other code. The replacement path is: trained small neural network (learns from gameplay data collected during beta), then optionally LLM-backed strategic decisions at a slower cadence. But the heuristic ships first and is the baseline.

### 11. Narrative AI (Optional for MVP)

#### 11.1 Scope

If included in MVP, the narrative AI generates a short text description of each tick's events — a "news broadcast" or "intelligence briefing" style summary. It reads from game state (what happened this tick) and optionally from a pgvector RAG corpus (historical analogies). It runs after tick resolution, before serving results to the player.

#### 11.2 Provider: Cloudflare Workers AI

The narrative generation runs on Cloudflare Workers AI using LoRA-adapted 8B models. The cost is approximately $0.00014 per narration call, roughly $0.028 per full game session (200 ticks). Django makes a single HTTPS call to the Workers AI endpoint after the engine finishes, passing a structured summary of the tick's events and relevant RAG chunks. The generated text is stored in Postgres alongside the tick results and served as the `narrative` field in the tick results JSON.

The Workers AI token is stored in the Ansible-deployed `.env` file, sourced from ansible-vault encrypted secrets.

#### 11.3 RAG Integration

The pgvector corpus (Feature 037, FR-021/FR-022) stores embedded chunks from the Marxist theory corpus and historical case studies. The narrative prompt includes semantically similar chunks retrieved from the corpus based on the current game state — high unemployment plus rising fascism retrieves Weimar Germany analogies.

#### 11.4 Non-Fatal Failure

Failure is non-fatal. If the API call times out, fails, or is disabled, the `narrative` field is an empty string and the game continues. The player still sees structured event data — the narrative is supplemental flavor, not required information. Constitutional requirement: AI Observes, Never Controls (Article II.5).

#### 11.5 MVP Decision

This is genuinely optional for MVP. If it delays shipping, cut it. The game is playable and testable without narrative text. Add it in the first post-launch iteration once the core gameplay loop validates.

---

## Part III: Infrastructure Layer

### 12. Compute Provider: Hetzner Cloud

A Hetzner CX32 VPS: 4 shared vCPUs (x86), 8 GB RAM, 80 GB NVMe, 20 TB monthly traffic. Located in Ashburn, Virginia (datacenter code `ash`) for low latency to the Detroit test geography. Runs Debian 12 (Bookworm), supported through June 2028.

Hetzner was selected over DigitalOcean (4–5× price premium for equivalent specs), Contabo (documented CPU oversubscription, no Terraform provider), and OVH (weak Terraform support). Monthly cost is approximately €8 ($8.50 USD).

Hetzner Cloud services used: Cloud Firewall (L3/L4 stateful packet filtering at the hypervisor, inbound locked to Cloudflare IP ranges plus SSH from known IPs), automated server snapshots for disaster recovery (approximately 20% of server cost), and private networks (RFC 1918 space for future multi-server expansion). Hetzner Object Storage is NOT used because it is EU-only; Cloudflare R2 replaces it.

### 13. Edge Services: Cloudflare

Cloudflare free tier provides: authoritative DNS with automatic HTTPS certificate provisioning at the edge, L7 DDoS protection and WAF, CDN caching for static assets, and uptime monitoring.

Cloudflare paid services: R2 Object Storage (zero egress fees, S3-compatible, used for Postgres backup archives; free tier provides 10 GB storage, 1M writes, 10M reads per month), Workers AI for narrative generation (see Section 11).

### 14. Bootstrapping: Terraform + cloud-init

Terraform manages cloud infrastructure as declarative code using two providers: `hetznercloud/hcloud` (servers, firewalls, SSH keys, networks) and `cloudflare/cloudflare` (DNS records, R2 buckets, WAF rules).

Terraform's only job is creating and destroying cloud resources. It does not configure what runs on them — that is Ansible's domain. The `user_data` (cloud-init) argument on `hcloud_server` is the single bridge between the two tools. On first boot, cloud-init creates a non-root `deploy` user, installs the SSH public key for passwordless access, grants passwordless sudo, disables root SSH login and password authentication, and optionally installs Python (required for Ansible). After `terraform apply` completes and the server is online, Ansible connects as the deploy user and takes over entirely.

Terraform state is stored locally for solo operation. `terraform.tfvars` is gitignored.

### 15. Configuration Management: Ansible

Ansible is the single source of truth for the entire server state. Every task is idempotent — running the playbook against an already-configured server changes nothing. Weekly playbook runs detect and correct configuration drift.

#### 15.1 Role: common

OS-level hardening and baseline configuration. Hardens SSH (key-only auth, disables password login, disables root login — reinforces cloud-init). Installs and configures fail2ban. Enables unattended-upgrades for Debian security patches. Configures nftables host firewall (defense-in-depth behind Hetzner Cloud Firewall). Creates 2 GB swap file to prevent the OOM killer from terminating Postgres under memory spikes.

#### 15.2 Role: postgres

Installs PostgreSQL 18 from the PGDG apt repository using the `community.postgresql` Ansible collection. Adds PGDG apt repository and signing key. Installs `postgresql-18`, `postgresql-18-postgis-3`, `postgresql-18-pgvector`, and `postgresql-18-pgrouting`. Creates the `babylon` database role with scram-sha-256 authentication. Creates the `babylon` database. Enables extensions: `postgis`, `vector`, `gen_random_uuid`, `pgrouting`. Configures `pg_hba.conf` for local password auth only (localhost). Tunes `postgresql.conf` for 8 GB RAM (`shared_buffers`, `work_mem`, `effective_cache_size`). Postgres listens only on localhost — never exposed to the internet. Django connects via Unix socket at `/var/run/postgresql/` for zero TCP overhead.

#### 15.3 Role: python

Installs Python 3.12+ from Debian repos. Installs pipx and uses it to install Poetry globally. Clones the Babylon repository to `/opt/babylon`. Runs `poetry install --no-dev` in the project directory.

#### 15.4 Role: babylon

Deploys `babylon.service` systemd unit (Jinja2 template, see Section 16). Deploys Django `.env` with production settings: `DEBUG=False`, database credentials, secret key, allowed hosts, CSRF trusted origins, Workers AI token. Runs `python manage.py collectstatic`. Runs `python manage.py migrate`. Enables and starts the service.

#### 15.5 Role: nginx

Installs Nginx from Debian repos. Deploys site configuration: reverse proxy to Gunicorn on `127.0.0.1:8000`. Serves static files from Django's `STATIC_ROOT` (`/opt/babylon/staticfiles/`) directly. Configures `real_ip_header CF-Connecting-IP` and `set_real_ip_from` directives for Cloudflare's IP ranges so that Django sees the player's real IP, not Cloudflare's. Accepts traffic from Cloudflare IP ranges only.

#### 15.6 Role: woodpecker

Downloads Woodpecker server and agent binaries. Deploys systemd units for both. Configures Codeberg OAuth integration.

#### 15.7 Role: backup

Deploys `backup-postgres.sh` script. Installs rclone for R2 uploads. Creates cron job: daily `pg_dump` compressed with zstd, uploaded to Cloudflare R2. Retention: 7 daily plus 4 weekly backups via R2 lifecycle rules. Monthly restore verification runs as a Woodpecker pipeline: pull the latest backup from R2, create a temporary Postgres database, restore the dump, run row-count and schema-integrity checks, drop the temporary database, report pass/fail. A backup never restored is a hypothesis, not a backup.

### 16. Process Supervision: systemd

systemd is PID 1 on Debian and handles all process lifecycle management. No additional supervisor is needed.

#### 16.1 Supervision Tree

```
systemd (PID 1)
├── postgresql@18-main.service     (PGDG-managed)
├── babylon.service
│   └── gunicorn (3 workers) → Django + NetworkX
├── nginx.service
├── woodpecker-server.service
├── woodpecker-agent.service
├── sshd.service
├── fail2ban.service
└── unattended-upgrades.timer
```

#### 16.2 Babylon Service Unit

The `babylon.service` unit file is deployed by Ansible as a Jinja2 template. Key properties:

**Restart policy**: `Restart=always` with `RestartSec=5` keeps Gunicorn alive through crashes.

**Dependency ordering**: `After=postgresql@18-main.service` ensures Postgres is ready before Babylon starts.

**Resource controls**: cgroup limits `MemoryMax=6G` and `CPUWeight=80` prevent the simulation engine from starving Postgres during heavy graph operations. This is important because NetworkX graph traversals during tick resolution can spike memory, and Postgres needs headroom for its own operations.

**Logging**: stdout/stderr captured by the journal. Query with `journalctl -u babylon`. No separate log rotation configuration required.

**Gunicorn command**: `gunicorn babylon_web.wsgi:application --workers 3 --bind 127.0.0.1:8000`. Three workers for reliability and static file handling. For a single-player game with 5–15 beta testers playing turn-based, this is more than sufficient.

### 17. Production Request Path

```
Player browser
  → Cloudflare (SSL termination, WAF, CDN, DDoS protection)
    → Hetzner Cloud Firewall (L3/L4 stateful filtering)
      → nftables host firewall (defense-in-depth)
        → Nginx (reverse proxy, static file serving)
          → Gunicorn (3 workers, 127.0.0.1:8000)
            → Django (auth, routing, engine bridge)
              → PostgreSQL 18 (Unix socket, /var/run/postgresql/)
```

Static file requests (React build, CSS, images) are served by Cloudflare's CDN on cache hit, or by Nginx directly from `/opt/babylon/staticfiles/` on cache miss. API requests (`/api/*`) and admin requests (`/admin/*`) pass through the full chain to Django.

### 18. CI/CD: Woodpecker

Woodpecker server and agent run as systemd services on the VPS (standalone binaries, no Docker). Woodpecker monitors the Codeberg repository and triggers pipelines on push to `main`.

#### 18.1 Deploy Pipeline

1. Woodpecker detects push to `main`
2. Run test suite (`pytest`)
3. `git pull origin main` (Woodpecker runs on the same host)
4. `poetry install --no-dev`
5. `python manage.py migrate`
6. `python manage.py collectstatic --noinput`
7. `sudo systemctl restart babylon`

#### 18.2 Additional Pipelines

Backup verification: monthly scheduled pipeline (Section 15.7). Lint and type-check: `ruff`, `mypy`, formatting checks.

### 19. Security Posture

#### 19.1 Network Security (Defense in Depth)

Five layers, from outermost to innermost:

1. **Cloudflare WAF** — L7 inspection, DDoS protection, SQL injection blocking, rate limiting
2. **Hetzner Cloud Firewall** — L3/L4 stateful rules at the hypervisor, before traffic reaches the VPS. Inbound locked to Cloudflare IP ranges (HTTP/HTTPS) plus SSH from known IPs
3. **nftables host firewall** — Defense-in-depth on the VPS itself
4. **fail2ban** — Bans IPs after repeated SSH failures
5. **Nginx** — `real_ip_header CF-Connecting-IP`, only accepts connections from Cloudflare ranges

#### 19.2 Access Control

SSH key-only authentication. Password login disabled. Root login disabled. Dedicated `deploy` user with scoped sudo. Django admin for player account creation — no self-registration for beta.

#### 19.3 Application Security

`DEBUG=False` in production. SSL redirect, secure session cookies, secure CSRF cookies, HSTS, and `SECURE_PROXY_SSL_HEADER` all enabled. Postgres listens only on Unix socket — no port to firewall, no network exposure. `ALLOWED_HOSTS` restricted to the production domain. PBKDF2 password hashing (Django default).

#### 19.4 Patching

`unattended-upgrades` handles Debian security patches automatically. Application dependencies updated deliberately via `poetry update` and tested in CI before deploy.

### 20. Backup Strategy

#### 20.1 Postgres Backups

Daily `pg_dump` → zstd compression → rclone upload to Cloudflare R2. Retention: 7 daily plus 4 weekly backups via R2 lifecycle rules.

#### 20.2 Archival Pipeline

Completed games export to Parquet (zstd compression, approximately 10:1 ratio) via Feature 037's archival system, uploaded to R2, then purged from active Postgres storage. DuckDB reads Parquet from R2 natively for cross-game analytics. This is complementary to the pg_dump backups — pg_dump is disaster recovery, Parquet export is analytical archival.

#### 20.3 Server-Level Backups

Hetzner automated snapshots (approximately 20% of server cost) provide full-disk recovery. These supplement but do not replace pg_dump — snapshots capture a potentially inconsistent database state.

#### 20.4 Restore Verification

Monthly restore verification runs as a Woodpecker pipeline. Pull the latest backup from R2, create a temporary Postgres database on the same server, restore the dump, run row-count and schema-integrity checks, drop the temporary database, report pass/fail. Failure is treated as a production incident.

### 21. Monitoring

Cloudflare uptime checks for the proxied domain (free, zero configuration). Disk usage alert via cron job checking `df -h`, alerting when any filesystem exceeds 80%. `journalctl -u babylon` for application errors, Nginx logs for proxy issues.

Prometheus, Grafana, Loki, Datadog, and New Relic are all explicitly rejected. For one server serving one single-player game, `journalctl` combined with Cloudflare analytics provides sufficient observability. Victoria Metrics (single-binary Prometheus alternative) is the upgrade path if monitoring needs grow.

### 22. Secrets Management

ansible-vault encrypts variable files containing sensitive values. Decryption key stored on the operator's machine, never committed. `.env` files (mode 0600) deployed by Ansible to the VPS for Django settings. A `.env.template` is committed with placeholders; the actual `.env` is gitignored.

Secrets inventory: Cloudflare API token (consumed by Terraform and backup script), R2 credentials (backup script and Django storage), Workers AI token (Django narrative layer), Postgres password (Ansible and Django settings), Django `SECRET_KEY` (Django settings), Woodpecker OAuth credentials (Woodpecker server).

Upgrade path: SOPS + age when the secrets inventory grows beyond six values. HashiCorp Vault is explicitly rejected as over-engineered for solo operation.

### 23. Cost Analysis

| Service | Monthly Cost | Notes |
|---|---|---|
| Hetzner CX32 | ~$8.50 | 4 vCPU, 8GB RAM, 80GB NVMe |
| Hetzner backups | ~$1.70 | 20% of server cost |
| Cloudflare free tier | $0 | DNS, CDN, WAF, DDoS |
| Cloudflare R2 | $0 | Free tier for beta volumes |
| Cloudflare Workers AI | ~$3–5 | Usage-dependent, only if narrative AI enabled |
| Codeberg | $0 | Free for FOSS |
| **Total (beta)** | **~$13–15/mo** | |

---

## Part IV: Interface Contract

This section pins every deployment-dependent setting that both the application and infrastructure layers must agree on. If either layer changes one of these values, the other must update to match. This is the contract that prevents drift.

### 24.1 Database Connection

| Parameter | Production Value | Development Value |
|---|---|---|
| Engine | `django.contrib.gis.db.backends.postgis` | Same |
| Name | `babylon` | `babylon` (or developer's preference) |
| User | `babylon` | Developer's preference |
| Password | From `.env` (Ansible-deployed) | Developer's preference |
| Host | `''` (empty = Unix socket) | `localhost` |
| Port | `''` (empty = default socket) | `5432` |
| Socket path | `/var/run/postgresql/` (Debian/PGDG default) | N/A (TCP in dev) |

The empty `HOST` and `PORT` in production tell Django to connect via the Unix socket at the default path. The `pg_hba.conf` entry is `local babylon babylon scram-sha-256`.

### 24.2 Static Files

| Setting | Value |
|---|---|
| `STATIC_URL` | `/static/` |
| `STATIC_ROOT` | `/opt/babylon/staticfiles/` |
| `STATICFILES_DIRS` | Includes `web/frontend/dist/` (React build output) |
| Nginx location | `location /static/ { alias /opt/babylon/staticfiles/; }` |
| Cloudflare caching | Automatic for `/static/*` paths |

### 24.3 Application Paths

| Path | Purpose | Owner |
|---|---|---|
| `/opt/babylon/` | Application code (cloned repo) | Ansible `python` role |
| `/opt/babylon/staticfiles/` | Collected static files | Ansible `babylon` role (`collectstatic`) |
| `/opt/babylon/data/` | SQLite reference database (read-only) | Upload script |
| `/opt/babylon/web/` | Django project root | Repository |
| `/opt/babylon/src/babylon/` | Engine code | Repository |

### 24.4 Process Identity

| Setting | Value |
|---|---|
| Gunicorn bind | `127.0.0.1:8000` |
| Gunicorn workers | `3` |
| WSGI module | `babylon_web.wsgi:application` |
| Working directory | `/opt/babylon/web/` |
| systemd unit | `babylon.service` |
| cgroup MemoryMax | `6G` |
| cgroup CPUWeight | `80` |

### 24.5 Django Environment Variables

These are the variables the Ansible `babylon` role writes to `/opt/babylon/web/.env` and that Django's production settings read via `os.environ`:

| Variable | Description |
|---|---|
| `DJANGO_SECRET_KEY` | Django secret key |
| `DJANGO_ALLOWED_HOSTS` | Comma-separated allowed hosts |
| `DJANGO_DEBUG` | `False` in production |
| `DATABASE_PASSWORD` | Postgres `babylon` role password |
| `CSRF_TRUSTED_ORIGINS` | `https://babylon.percypedia.biz` |
| `WORKERS_AI_TOKEN` | Cloudflare Workers AI API token |
| `R2_ACCESS_KEY_ID` | Cloudflare R2 credentials (for archival) |
| `R2_SECRET_ACCESS_KEY` | Cloudflare R2 credentials (for archival) |

### 24.6 Nginx ↔ Django Contract

Nginx sets `X-Forwarded-Proto: https` on all proxied requests. Django reads this via `SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')`. Without this header, Django's CSRF middleware rejects all POST requests because it sees HTTP internally even though the player connected over HTTPS via Cloudflare. This is the single most common misconfiguration when running Django behind a reverse proxy — if CSRF errors appear in production, check this first.

---

## Part V: Deployment and Migration

### 25. Initial Provisioning (Day 1)

1. `terraform apply` creates the Hetzner server (with cloud-init deploy user), cloud firewall, SSH key, private network, and Cloudflare DNS records and R2 buckets
2. Terraform outputs the server IP address
3. Wait for cloud-init to complete (approximately 30 seconds)
4. `ansible-playbook playbook.yml` connects as the deploy user and configures everything: OS hardening, Postgres 18 with extensions, Python/Poetry, Nginx, Gunicorn, Woodpecker, backup cron, systemd units
5. Upload the reference SQLite database
6. Create the Django superuser via `manage.py createsuperuser`
7. Create beta tester accounts via the admin panel at `/admin/`
8. Verify: `curl https://babylon.percypedia.biz/health/` returns 200

### 26. Subsequent Deploys

Woodpecker handles routine deploys on push to `main`: pull, install, migrate, collectstatic, restart. Manual deploys via SSH are also possible: `ansible-playbook playbook.yml --tags app` re-deploys just the application role.

### 27. Drift Correction

Running `ansible-playbook playbook.yml` periodically ensures configuration has not drifted. Ansible is idempotent — unchanged resources are skipped.

### 28. Migration Path from PyQt6

The PyQt6 God Mode dashboard code is not deleted. It becomes a local development and analysis tool that can connect to the same Postgres database as the Django web app. The two interfaces coexist — the web app is for players, the PyQt6 dashboard is for the developer.

Implementation order:

1. Stand up Django project scaffolding (Part II of this spec)
2. Implement Feature 037 Postgres runtime database
3. Wire EngineBridge to existing engine code
4. Build MVP React frontend (point-and-click, all 9 verbs accessible)
5. Stand up infrastructure (Part III of this spec — Terraform + Ansible)
6. Deploy to Hetzner VPS, onboard beta testers
7. Iterate based on gameplay feedback
8. Add narrative AI via Workers AI when core loop validates
9. Invest in frontend polish when testers say the game is interesting but ugly

### 29. Django Admin as God Mode

The Django admin panel at `/admin/` is the developer analytics dashboard for free. All game management models are registered with display fields, filters, and read-only protections on configuration snapshots. Percy can inspect any game session, view submitted actions, check action outcomes, and monitor game state.

For analytical queries beyond what the admin panel provides, SSH into the VPS and run `psql` against the local Postgres instance directly. The tick summary tables (Feature 037) are designed for exactly this kind of ad hoc querying.

---

## Part VI: Testing and Validation

### 30. Testing Strategy

**Unit tests**: Django model constraints (action uniqueness per org per tick), serializer validation, API endpoint auth requirements, EngineBridge JSON output schema validation.

**Integration tests**: Full single-turn lifecycle — create session, submit actions, resolve tick, verify state persisted and retrievable. Engine bridge round-trip — hydrate from Postgres, run tick, persist, hydrate again, compare. This validates the no-DB-I/O-during-tick constitutional requirement by verifying that the hydrated state after persist matches the in-memory state after tick execution.

**Validation tests**: Detroit test case — run 52 ticks (1 simulated year), verify TRPF trajectory direction, verify Wayne County capital share decreases over time while Oakland increases, verify gentrification directional predictions match QCEW/Census trends. This is the falsification test that proves the engine works.

**Frontend tests**: Minimal for MVP. Verify React components render without crashing given mock JSON data. Verify action submission hits the correct API endpoint with correct JSON schema. Full E2E tests with Playwright or Cypress are a post-MVP concern.

**Infrastructure tests**: Ansible playbook runs idempotently (second run changes nothing). Restore verification pipeline passes (Section 20.4). Health endpoint returns 200 after deploy.

---

## Part VII: Rejected Alternatives

These technologies solve real problems at scale. None of them solve problems Babylon has today.

| Technology | Reason for Rejection |
|---|---|
| Docker / Docker Compose | Unnecessary indirection for one server. Ansible manages bare metal directly |
| Nix / NixOS | Complexity tax without proportional benefit for a solo developer |
| Kubernetes | Cluster orchestration for one server |
| Celery / task queues | Single-player game with synchronous tick resolution. No async work |
| WebSockets | No real-time updates needed. Turn-based, request/response |
| JWT / OAuth | Django session auth is sufficient for 15 beta testers |
| Consul / service mesh | Service discovery for one service |
| HashiCorp Vault | Key management for six secrets |
| Prometheus + Grafana + Loki | Full observability stack for one VPS |
| Ubuntu | Snap daemon overhead, Canonical telemetry |
| Contabo | CPU oversubscription, no Terraform provider |
| GitHub | Codeberg for AGPL-3.0 FOSS hosting |
| Apache AGE | Deferred — recursive CTEs handle graph queries for beta. SQL:PGQ is the long-term direction |

---

## Part VIII: What Claude Code Needs to Know

**The engine is the product. The frontend is a viewport.** Do not over-invest in frontend polish before the simulation validates against the Detroit test case.

**Single-player only.** There is no multiplayer, no concurrency, no waiting for other players. One user, one game at a time, immediate tick resolution.

**JSON everywhere.** The API serves JSON. The engine bridge produces JSON. Postgres stores JSONB. If something is not JSON-serializable, fix the serialization, do not work around it.

**Import boundary is sacred.** Engine code must NEVER import Django. `engine_bridge.py` is the sole translation layer. If you find yourself importing `babylon.engine` in a Django view, route it through the bridge.

**Feature 037 owns the simulation schema.** Django ORM manages GameSession, PlayerAction, ActionResult. Everything else (simulation state, graph persistence, hex data, community consciousness) goes through Feature 037's raw SQL persistence layer. Do not duplicate table definitions.

**No magic constants.** All game parameters come from GameDefines. Nothing hardcoded in views, serializers, or frontend components.

**Constitution is authoritative.** If something in this spec conflicts with the Babylon constitution, the constitution wins. Flag it immediately.

**Existing codebase lives in `src/babylon/`.** The Django project in `web/` wraps the engine. It does not replace it, restructure it, or copy code out of it.

**The SQLite reference database is read-only.** Never write to it. It is calibrated federal statistical data.

**NPC decisions are rules-based heuristics.** No LLM calls during tick resolution. The heuristic runs inside the engine as pure Python. It is fast and deterministic.

**No Docker.** Everything runs bare metal, managed by Ansible. systemd supervises processes. Postgres connects via Unix socket at `/var/run/postgresql/`. Nginx proxies to `127.0.0.1:8000`.

**Cloudflare terminates SSL.** Django never sees HTTPS directly. The `SECURE_PROXY_SSL_HEADER` setting is required or CSRF breaks. See the Infrastructure Interface section (Part IV).

**Test with Detroit.** Wayne County (26163), Oakland County (26125), Macomb County (26099). If it does not work for tri-county Detroit, it does not work.
