# Install Babylon

These instructions install Babylon, run two checks, and open the native Bevy
observer game.

Read [`NORTH_STAR.md`](NORTH_STAR.md) for the game purpose, client status,
validation standard, and gate order. [`CONSTITUTION.md`](CONSTITUTION.md)
v4.1.0 is the authority.

## 1. Prepare the host

Babylon development targets Debian Linux. On Windows, use Debian in
[WSL](https://learn.microsoft.com/en-us/windows/wsl/install).

<!-- Vale: this paragraph preserves literal Docker product and command names. -->
<!-- vale ste.UnapprovedWords = NO -->
Install [Git](https://git-scm.com/downloads),
[`mise`](https://mise.jdx.dev/getting-started.html),
[rustup](https://rustup.rs/), and Docker Engine with the Docker Compose
plug-in from their official guides. Docker Compose is a host prerequisite
because `mise run setup` starts Postgres.
Check them:
<!-- vale ste.UnapprovedWords = YES -->

```bash
git --version
mise --version
rustup --version
docker compose version
```

The repository pins its language tools. It does not install Docker on the host.

Install these Debian packages before `mise run setup`:

```bash
sudo apt-get update
sudo apt-get install -y build-essential pkg-config libssl-dev libpq-dev \
  libasound2-dev libudev-dev libwayland-dev libxkbcommon-dev libx11-dev \
  libxcursor-dev libxi-dev libxrandr-dev libvulkan-dev mesa-vulkan-drivers
```

## 2. Get Babylon

Clone the repository and select `dev`:

```bash
git clone https://github.com/percy-raskova/babylon.git
cd babylon
git checkout dev
```

Trust the local `mise` settings:

```bash
mise trust
```

Read a script before you grant trust when you did not get the clone from the
official repository.

## 3. Install the tools

Run the repository installation task:

```bash
mise run setup
```

The task installs the pinned tools, project dependencies, and local hooks. The
first run can be slow.

Daily development and reference data use the same Python 3.12.14 environment.
Python in `mise.lock` includes SQLite 3.53.1. `uv.lock` pins dependencies.
For reference-data checks, see the
[reference-data instructions](docs/how-to/reference-data-pipeline.rst).

## 4. Open the observer game

<!-- Vale: this paragraph preserves literal Bevy and host package names. -->
<!-- vale ste.UnapprovedWords = NO -->
<!-- vale ste.NounClusters = NO -->
A Bevy build needs Rust and Cargo plus the host window,
input, and audio development libraries. `rustup` selects the pinned
Rust and Cargo from `rust/rust-toolchain.toml`. The Debian package set
includes `libasound2-dev`, `libudev-dev`, `libwayland-dev`, and
`libxkbcommon-dev`.
<!-- vale ste.NounClusters = YES -->
<!-- vale ste.UnapprovedWords = YES -->

From the repository root, open or continue a campaign:

```bash
mise run play
```

The launcher builds `babylon-runtime` and `babylon-client` with native Cargo
from `rust/`. It reuses a reachable local database. If the default
database is
unavailable, it starts the repository database with `db:up` and checks again.
By default, the launcher connects to `babylon_test` on `127.0.0.1:5433`.

The runtime initializes a new database, installs the observer read roles,
and connects to Bevy through anonymous pipes. The window receives read
credentials. New campaigns start at period zero. One period advances four weeks
in one simulation tick. The runtime can reopen a supported save from the same
campaign content version. It reconciles the committed checkpoint before the
next period.

Choose **Continue** on the opening warning, then watch or skip the production
card. The Liberty start menu follows:

- **Continue** enters the campaign the launcher prepared or reopened, once ready.
- **New Game** starts the Wayne organizer campaign and preserves existing saves.
- **Load Game** lists saved campaigns, with **Open** and **Compare** controls.
- **Observer Campaigns** offers the regional, statewide, and Wayne maintenance presets.
- **Settings** controls audio, interface size, and reduced motion.
- **Quit** closes the game.

The start menu loops **The Purge**. The production card has its own fanfare.
Music volume cycles through mute, 25%, 50%, 75%, and 100%.
In **Settings**, **Next in-game track** selects the recording to play when you
enter the campaign. Soundtrack recordings play in sequence during a campaign.
Press **Escape** during a campaign to return to the start menu.

The supplied delayed-delivery parameters lengthen the `sheet-transfer` route.
The map shows 83 Michigan county baselines. The production display shows five
Designed county-industry cohorts, actual freight lots, and committed production.
The supplied horizon is 16 four-week periods (64 weeks). Comparing saved
campaigns shows their own committed values; their parameters can differ.

Observed QCEW jobs and wages are source records. Designed physical
quantities and labor-hours use declared scenario values. Observer campaigns
have no player interventions. **New Game** opens the Wayne organizer campaign.

For a new campaign that keeps saved worlds:

```bash
mise run play -- --new
mise run play -- --new --preset delayed
```

Use `--campaign UUID` to open a supported saved campaign. The runtime recovers
its stored scenario and parameters. `--preset` applies only to a new campaign.

Edit `content/scenarios/michigan/defines.toml` before starting a new campaign,
or pass `--defines /absolute/path/to/defines.toml` to choose another file.
Each New request validates and saves those values. Editing the file later does
not change an existing campaign; Open uses its saved values.

Older development saves with unsupported content versions cannot reopen.
Use `mise run play -- --new` to start a new campaign and keep those saves.

The launcher builds native binaries. The `--no-build` option uses the native
binaries on disk.
Use `mise run play` to connect the client to its runtime.

The continuation pointer is a plain UUID in
`$XDG_STATE_HOME/babylon/observer-campaign`, or
`~/.local/state/babylon/observer-campaign` by default.
The pointer is a personal preference. Campaign data stays in Postgres.
The client updates the pointer after the runtime successfully opens or creates
a campaign. A failed New or Open request leaves the previous pointer intact.

For a dedicated local database, set `BABYLON_RUNTIME_DSN` to an explicit
local host, port, database, user, and password before launch. Create that
database first. The launcher refuses an unavailable custom target. It does
not start a different database. It reuses a reachable target and leaves
the shared container unchanged.

To keep that choice for this checkout, put the connection in the `[env]`
section of `.mise.local.toml`, then run `mise trust .mise.local.toml`:

```toml
[env]
BABYLON_RUNTIME_DSN = "host=127.0.0.1 port=5433 dbname=babylon_play user=test password=test"
```

Replace the database and credentials with those of your dedicated database.
The local file stays outside Git.

### Query committed money movements

The local observer launcher starts a separate publisher for its selected database.
It fills missing committed periods at startup, including gaps below the latest
period, and listens for new commits while the session runs. Campaign switches
use the same database. Each publication uses the stored campaign identity.
The worker uses its own connections and the game can advance while it works.

To recover up to eight periods of one campaign, run the following command from
`rust/` with the writer and full-observer credentials described below.

```bash
cargo run -p babylon-persistence --bin babylon-economic-projections -- sweep \
  --campaign 28100000-0000-0000-0000-000000000001
```

The `babylon-money-journal` operator publishes derived facts for an existing
campaign in a database with the current schema. It does not create campaigns or
advance periods. Set `BABYLON_OBSERVER_DSN` to a confined login with the
installed `babylon_observer` role. Publication also needs `BABYLON_RUNTIME_DSN`
with the database owner's credentials. Both connections must use the same host,
port and database. The observer credential remains read only.

From `rust/`, publish a committed period, read its movements, or total its
payments over a published interval. Replace the UUID with the existing campaign
identity:

```bash
cargo run -p babylon-persistence --bin babylon-money-journal -- publish \
  --campaign 28100000-0000-0000-0000-000000000001 --first 1
cargo run -p babylon-persistence --bin babylon-money-journal -- details \
  --campaign 28100000-0000-0000-0000-000000000001 --first 1
cargo run -p babylon-persistence --bin babylon-money-journal -- totals \
  --campaign 28100000-0000-0000-0000-000000000001 --first 1 --last 13
```

Publish every period in an interval before querying its totals. The `publish`
command accepts `--last` for this purpose. Missing coverage produces a refusal,
including when adjacent published periods contain no transfers. Each period
publishes atomically. Repeating publication verifies the same source and facts.

Amounts are exact currency micro-units, returned as decimal strings. A
movement's debit is minus its positive amount and its credit is plus that
amount. Cash accounts, order reserves and payroll reserves have separate typed
identities. A reserve identity identifies stored money rather than its owner.
Only `delivery_settlement` records a sale payment. Reservations, refunds and
cancellations remain separate in SQL totals.

Detailed rows cover the latest 13 committed source periods as of publication.
Period identity, coverage and purpose totals remain stored for older periods.
The `details` command reconstructs older movements from authenticated source
receipts. Use `rebuild` with the same period flags as `publish` to replace
derived facts from those receipts. Retention still applies.

Warm detail and total queries use the SQL facts directly. The full observer can
also sum `public.v_observer_money_movement_total_v1` or inspect
`public.v_observer_money_movement_v1` with SQL.

### Read a campaign from the earlier schema

For a campaign from the Postgres schema at `2824cf38e`, copy the recorded
accounts to a second database. Prepare the destination with the new schema,
the same reference data and no campaigns. Set `BABYLON_PRE293_SOURCE_DSN`
to the source owner connection and `BABYLON_INSPECTION_TARGET_DSN` to the
destination owner connection.

From `rust/`, run the copy for one campaign.

```bash
cargo run -p babylon-persistence --bin babylon-inspection-copy -- \
  --campaign "$CAMPAIGN_ID"
```

The command reads the source in a read-only transaction. It checks the copied
foundation and committed periods before it saves the destination. The report
identifies the foundation and the latest committed tick. Use the destination
observer and runtime connections to publish the financial history there.

### Read site accounts and stock history

In **Circuit**, select a site and open **Accounts** to see its cash change, profit
and retained earnings for the selected period.

Use the site ID from the native `economy sites` command. With the full observer
login, read one published period or an inclusive range from `rust/`.

```bash
cargo run -p babylon-persistence --bin babylon-money-journal -- site-history \
  --campaign "$CAMPAIGN_ID" --site "$SITE_ID" --first 1 --last 13
```

Each period includes opening and closing balances, income, signed cash flows and
stock positions by good and unit. Amounts use decimal strings in currency micros.
Quantities use decimal strings in the recorded unit.

A physical campaign has a null statement and null stock costs. A null opening or
closing means that the books had no stock row at that boundary. An unpublished
period or an unknown site returns an error. Site history stays available after
the 13-period limit for individual money movements. Use native `economy site`
to read the source receipts and claims.

### Follow settled payments

Open a campaign in the full observer and select a county on the map. The
**Settled payments** panel shows who paid that county and whom it paid in the
selected period. Select a map arrow or its entry in the list to see both
endpoints and the amount. Choose `Open counterparty county` to
follow a payment to another mapped county. The list also includes payments
with no mapped endpoint.

Choose **Frame connections on map** to show the payer and recipient on the map.
Choose **County site accounts** to read the change in cash, profit and retained
earnings for all sites that operate in the county. Select a site to open its **Accounts**
for the same period.

From period two, choose **Compare with period** to see the county's net amount
and how it changed from the period before it. The ribbons show the selected period.
In Labor mode, the list includes transfers with unknown earlier hours.

From `rust/`, use the full observer login to rank payments in a published
campaign. The movement journal records each reserve posting. The flow report
counts the settlement from its economic payer to its credited recipient once.

```bash
cargo run -p babylon-persistence --bin babylon-money-journal -- flows \
  --campaign 28100000-0000-0000-0000-000000000001 --first 5 --last 8 \
  --compare-first 1 --compare-last 4 --group location
```

Choose `location`, `catchment`, `industry`, or `account` for `--group`.
With `--group location --focus county:26163`, each row identifies a location
that exchanged payments with Wayne County, Michigan. Its inflow is money Wayne
paid that location. Its outflow is money the location paid Wayne.

Each page returns twenty groups ranked by the sum of inflow, outflow, and internal
payments. Internal payments count once. If two distinct accounts both lack a
grouping key, the unknown group shows an inflow and an outflow for that payment.
Its net effect is zero.

Net equals inflow minus outflow. The comparison reports the change in that net amount.
The `remainder` field sums every group outside the page. Use `--offset 20` for the
next twenty. The report uses signed decimal strings in currency micros.

An optional `--bbox-4269 WEST,SOUTH,EAST,NORTH` filters visible endpoints with
NAD83 longitude and latitude. A county uses its captured TIGER internal point.
Other locations with no captured point stay outside the selected area. A site’s
operating county and the catchment it serves have distinct grouping keys.
Missing classifications appear as a null key when viewing all locations.

### Follow recorded labor

Select a county in the full observer. In the **Settled payments** panel, choose
**Labor hours**. The panel shows hours that entered or left the county and hours
that moved between local accounts. Choose **Map** or **Sankey** to follow the same connection.

The list includes movements with unknown earlier labor. The diagram sizes
each connection by its recorded hours. A movement with zero recorded hours
and unknown earlier labor stays in the list.

From `rust/`, rank movements for the same county and compare two periods.

```bash
cargo run -p babylon-persistence --bin babylon-money-journal -- flows \
  --campaign "$CAMPAIGN_ID" --measure labor --group location --focus county:26163 \
  --first 2 --compare-first 1
```

Each direction reports millionths of an hour, the number of movements, and the
number with unknown earlier labor. The same hours can appear in production, freight and
consumption. To see how many hours
people added and how much remained at each boundary, read the period ledger.

```bash
cargo run -p babylon-persistence --bin babylon-economic-projections -- labor-trace \
  --campaign "$CAMPAIGN_ID" --first 2 --last 4
```

The command writes one JSON object for each period and a `labor_trace_complete`
record. Each period identifies its foundation, committed tick and receipts.
Opening hours plus hours worked equal closing hours plus released hours.

### Read a site's financial statements

Set `BABYLON_OBSERVER_DSN` to the confined observer login described above.
The site commands need only this credential. From `rust/`, list the captured
campaign's sites. Set `SITE_ID` to a returned ID to read its first committed period.

```bash
cargo run -p babylon-client -- --headless \
  --campaign 28100000-0000-0000-0000-000000000001 economy sites
cargo run -p babylon-client -- --headless \
  --campaign 28100000-0000-0000-0000-000000000001 economy site "$SITE_ID" 1
```

The directory uses the fixed campaign foundation at period zero. At that period
the command returns the opening balance sheet. For each committed period it
returns opening and closing balances, income, and cash flows.

Amounts are exact decimal strings in currency micros. Spendable cash excludes
order and payroll reserves. The cash-flow statement shows reserve movements
that lack a documented operating, investing, or financing purpose on their own line.

To test the reports locally, run the disposable database check from the
project root. Set `BABYLON_SITE_STATEMENTS_CLIENT_EXE` to the absolute path of
a built `babylon-client` to include the native command checks.

```bash
BABYLON_POSTGRES_LIVE_FOCUS=money_journal mise run test:rust-postgres
```

## 5. Run the repository check

Run the standard local gate:

```bash
mise run check
```

The gate checks format, lint, types, and Python unit contracts. Rust changes
also use the Rust gate:

```bash
mise run rust:check-no-docs
```

Python tests cover retained data tools, operator workflows, and
language-neutral behavior contracts. Rust tests cover mechanics.

## Make a contribution

Read [`CONTRIBUTORS.md`](CONTRIBUTORS.md) before a change. Create a lane from
`dev`, add a failing test first, and open a PR against `dev`.

Use this command for a commit:

```bash
mise run commit -- "type(scope): description"
```

Do not commit directly to `dev` or `main`.

## Fault help

If `mise` is not available after installation, open a new terminal. Then run
`mise --version` again.

If `mise` does not load the repository settings, run `mise trust` from the
repository root.

If `mise run play` reports `CurrentCensusMismatch`, the database does not match
the current schema. Starting a new campaign with `--new` does not replace that
schema. Preserve the database and create a separate database from `template1`
with the current extension installation, then select it with
`BABYLON_RUNTIME_DSN` as described above. The launcher initializes its game tables.
Also check that you are running from the checkout containing the game changes
you want to play.

If dependency installation stops, run `mise run setup` again and keep the first error.
Open an [issue](https://github.com/percy-raskova/babylon/issues) with the command,
host system, and full error text.
