# Install Babylon

These instructions install Babylon and run two checks. They then show the optional Bevy
administrative viewer.

Read [`NORTH_STAR.md`](NORTH_STAR.md) for the game purpose, client status,
validation standard, and gate order. [`CONSTITUTION.md`](CONSTITUTION.md)
v4.0.0 is the authority.

The first simulation below is a frozen Python smoke test, not the Bevy play
surface.

## 1. Prepare the host

Babylon uses a Linux toolchain. On Windows, use
[WSL](https://learn.microsoft.com/en-us/windows/wsl/install). On macOS or Linux,
use a terminal with Git.

<!-- Vale: this paragraph preserves literal Docker product and command names. -->
<!-- vale ste.UnapprovedWords = NO -->
Install [Git](https://git-scm.com/downloads),
[`mise`](https://mise.jdx.dev/getting-started.html),
[Nix](https://nixos.org/download/), and Docker Engine with the Docker Compose
plug-in from their official guides. Docker Compose is a host prerequisite
because `mise run setup` starts Postgres.
`mise run setup` requires [Nix](https://nixos.org/download/) because canonical
schema bootstrap uses the repository Nix shell to run the pinned Rust migrator.
Check them:
<!-- vale ste.UnapprovedWords = YES -->

```bash
git --version
mise --version
nix --version
docker compose version
```

The repository pins its language tools. It does not install Docker on the host.

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

## 4. Run the smoke test

Run the frozen Python reference for one small tick:

```bash
mise run reference:python-smoke
```

The command must show an initial tick, one simulation step, and a completed
tick. The command does not prove that the Bevy client has player actions.

## 5. Run the repository check

Run the standard local gate:

```bash
mise run check
```

The gate checks format, lint, types, and Python unit contracts. Rust changes
also use the Rust gate:

```bash
mise run rust:check
```

Python tests have value during the Rust port. They test the frozen reference,
data tools, and language-neutral behavior contracts.

## 6. Open the Bevy viewer

<!-- Vale: this paragraph preserves literal Bevy and host package names. -->
<!-- vale ste.UnapprovedWords = NO -->
<!-- vale ste.NounClusters = NO -->
This step is optional. A Bevy build needs Rust and Cargo plus the host window,
input, and audio development libraries. The pinned Nix shell installed in step
1 supplies Rust and Cargo. On Debian-family Linux hosts, the native package set
includes `libasound2-dev`, `libudev-dev`, `libwayland-dev`, and
`libxkbcommon-dev`.
<!-- vale ste.NounClusters = YES -->
<!-- vale ste.UnapprovedWords = YES -->

Run the fast developer lane:

```bash
mise run nix -- mise run rust:client-dev-dylib
```

The Bevy client shows the county atlas and moves ticks forward. The client is
an administrative viewer with no player action.

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

If dependency installation stops, run `mise run setup` again and keep the first error.
Open an [issue](https://github.com/percy-raskova/babylon/issues) with the command,
host system, and full error text.
