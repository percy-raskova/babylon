{
  description = "Babylon — MLM-TW geopolitical simulation engine (Nix Player Channel, ADR094)";

  inputs = {
    # Match infra's channel (babylon-infra flake pins nixos-25.11).
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-25.11";
    # python/sqlite only: the reference-DB builder pins sqlite 3.53.1
    # (tools/build_reference_db.py::PINNED_SQLITE_VERSION — the byte-identical
    # build contract, ADR098). This exact rev's python312 links sqlite 3.53.1
    # (verified 2026-07-20). Pinned by REV in the URL so `nix flake update`
    # cannot drift it; bumping this input IS a declared sqlite-pin change, and
    # both halves of the lockstep now live in THIS repo (environment-
    # sovereignty ruling 2026-07-21; previously the babylon-infra flake).
    nixpkgs-data.url = "github:NixOS/nixpkgs/a16c3fde2ffeab7f6326f50f460aaffde7ae066d";
    flake-utils.url = "github:numtide/flake-utils";

    pyproject-nix = {
      url = "github:pyproject-nix/pyproject.nix";
      inputs.nixpkgs.follows = "nixpkgs";
    };
    uv2nix = {
      url = "github:pyproject-nix/uv2nix";
      inputs.pyproject-nix.follows = "pyproject-nix";
      inputs.nixpkgs.follows = "nixpkgs";
    };
    pyproject-build-systems = {
      url = "github:pyproject-nix/build-system-pkgs";
      inputs.pyproject-nix.follows = "pyproject-nix";
      inputs.uv2nix.follows = "uv2nix";
      inputs.nixpkgs.follows = "nixpkgs";
    };
  };

  outputs =
    { nixpkgs, nixpkgs-data, flake-utils, pyproject-nix, uv2nix, pyproject-build-systems, ... }:
    flake-utils.lib.eachDefaultSystem (
      system:
      let
        pkgs = nixpkgs.legacyPackages.${system};
        lib = pkgs.lib;
        python = pkgs.python312;
        # sqlite-3.53.1 interpreter for the babylon data layer (see nixpkgs-data)
        pythonData = nixpkgs-data.legacyPackages.${system}.python312;

        # Source filter. The committed src/babylon_data symlink points outside
        # the sandbox and is DEAD in any Nix build; a fileset difference drops it
        # (plus heavy non-package trees) so uv2nix builds babylon from a clean copy.
        projectSrc = lib.fileset.toSource {
          root = ./.;
          fileset = lib.fileset.difference ./. (
            lib.fileset.unions [
              (lib.fileset.maybeMissing ./src/babylon_data)
              (lib.fileset.maybeMissing ./web)
              (lib.fileset.maybeMissing ./node_modules)
              (lib.fileset.maybeMissing ./ai)
              (lib.fileset.maybeMissing ./hypergraph-rs)
            ]
          );
        };

        workspace = uv2nix.lib.workspace.loadWorkspace { workspaceRoot = ./.; };

        # Overlay generated from uv.lock; wheels preferred for hermetic, fast builds.
        lockOverlay = workspace.mkPyprojectOverlay { sourcePreference = "wheel"; };

        # Point the local `babylon` package at the filtered tree so the dead
        # symlink never enters its build. `babylon` is the normalized project
        # name (pyproject `[project] name = "babylon"`, verified).
        srcOverlay = _final: prev: {
          babylon = prev.babylon.overrideAttrs (_old: { src = projectSrc; });
        };

        # FIX-FORWARD (recorded deviation from the brief's verbatim flake.nix):
        # `ratelimit` (a base dependency) ships only a legacy-setup.py sdist and
        # does not declare `setuptools` in its build-system.requires, so uv2nix's
        # inherited build environment lacks it — a well-documented uv2nix gotcha
        # for underdeclared build deps. This overlay only touches flake.nix (not
        # pyproject.toml/uv.lock, which are ADR095-owned).
        buildFixupOverlay = final: prev: {
          ratelimit = prev.ratelimit.overrideAttrs (old: {
            nativeBuildInputs = (old.nativeBuildInputs or [ ]) ++ final.resolveBuildSystem {
              setuptools = [ ];
            };
          });
        };

        pythonSet =
          (pkgs.callPackage pyproject-nix.build.packages { inherit python; }).overrideScope
            (lib.composeManyExtensions [
              pyproject-build-systems.overlays.wheel
              lockOverlay
              srcOverlay
              buildFixupOverlay
            ]);

        babylonEnv = pythonSet.mkVirtualEnv "babylon-env" workspace.deps.default;
      in
      {
        packages = {
          babylon = babylonEnv;
          default = babylonEnv;

          # Game-managed Postgres cluster runtime closure (ADR104 ruling 2:
          # Postgres — initdb into ~/.local/share/babylon/pg, unix socket,
          # child process of the game, superuser-in-own-cluster so
          # `CREATE EXTENSION postgis`/`pgvector` needs no host-admin step).
          # This output makes the server binaries + both extensions
          # REACHABLE from the flake (eval-verified: `nix eval
          # .#packages.<system>.pg-runtime.drvPath`); it does NOT build the
          # cluster-lifecycle code (initdb/pg_ctl/unix-socket wiring,
          # first-run idempotent DDL applier + stamp table) — that is a
          # LATER T7 unit, gated on the keel DSN-unification seam (T1.2),
          # and lives in src/, out of this lane's scope fence.
          # `withPackages` bundles the extensions into $out/lib so
          # `CREATE EXTENSION postgis;` / `CREATE EXTENSION vector;` resolve
          # without any separate install step.
          pg-runtime = pkgs.postgresql_17.withPackages (ps: [
            ps.postgis
            ps.pgvector
          ]);
        };

        # ── Reference-data fixed-output derivation — PLANNED, NOT YET WIRED ──
        # ADR104 (Postgres/data ruling) + PROGRAM_v1_0_0 ruling 1: the 4.49GB
        # reference DB ships through the SAME signed R2 cache install.sh
        # already trusts (ADR094 D1) — no second trust mechanism — as a Nix
        # fixed-output derivation (content-addressed by sha256, so Nix
        # verifies the download itself; no separate signature check needed
        # beyond the narinfo signature already covering the closure).
        #
        # Pin source (data-artifacts.yaml `product:`, current build,
        # ADR098 byte-identity contract):
        #   name          = marxist-data-3NF.sqlite
        #   sha256        = f760bab5c63ce879decd72cfe3bf51c569a5a4ba2a4a57e0ccbb5d90f5e6fa42
        #   sqlite_version= 3.53.1  (nixpkgs-data pin, tools/build_reference_db.py::PINNED_SQLITE_VERSION)
        #
        # Blocked on Runbook C3's PRE-STEP (ai/_inbox/PROGRAM_v1_0_0_ceremony_runbook.md):
        # babylon-data has no public serving domain yet — R2 dashboard must
        # attach a Custom Domain (e.g. data.babylon.percypedia.biz) before any
        # URL exists to pin. Per this lane's brief: do NOT write a FOD with a
        # dead URL. The exact shape to drop in, once that domain is live and
        # the sha is re-confirmed against the release build, is (documented,
        # not evaluated — this is a comment, not live Nix):
        #
        #   packages.reference-data = pkgs.fetchurl {
        #     url    = "https://<DATA_DOMAIN_FROM_C3>/marxist-data-3NF.sqlite";
        #     sha256 = "f760bab5c63ce879decd72cfe3bf51c569a5a4ba2a4a57e0ccbb5d90f5e6fa42";
        #   };
        #
        # Nix's own hash verification IS the integrity check (fetchurl fails
        # loudly on mismatch) — same discipline as the GGUF manifest's
        # in-band sha256 (Runbook C3). See docs/how-to/reference-data-fod.rst
        # for the full landing checklist.

        # Canonical dev/build environment (vendored from the babylon-infra
        # devshell, environment-sovereignty ruling 2026-07-21 — the infra
        # submodule is unmounted; babylon-infra's flake governs ops tooling
        # only). Same nixpkgs rev the submodule's lock carried, so every tool
        # store path is unchanged.
        devShells.default = pkgs.mkShell {
          packages = (with pkgs; [
            uv                  # package/venv manager (pure uv/PEP-621 since PR #236)
            nodejs_22
            git-lfs
            postgresql_16.lib   # libpq for pure-python psycopg
            gdal                # GeoDjango runtime + geospatial CLI/headers (ogr2ogr, gdal-config)
            geos
            proj
            openblas
            rustc
            cargo
            fluidsynth
            playwright-driver.browsers
            mise                # task runner pinned here, not assumed on the host
            jq                  # post-tool-lint.sh dispatcher
          ]) ++ [
            pythonData          # the only python312 on PATH: venvs build on it unchanged
          ];
          # sentinel for task guards — IN_NIX_SHELL is too generic (the
          # workstation shell is itself a nix-shell)
          BABYLON_DEVSHELL = "default";

          shellHook = ''
            # Determinism + 2026-07-12 freeze fix (mirrors .mise.toml [env])
            export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
            export NUMEXPR_NUM_THREADS=1 RAYON_NUM_THREADS=1
            # libpq for pure-python psycopg, PLUS the nix libstdc++ for
            # manylinux wheels (greenlet, pyarrow): the nix python's dynamic
            # linker cannot see host system libs, so every C++-linked wheel
            # needs the store's libstdc++ on the loader path.
            export LD_LIBRARY_PATH=${pkgs.stdenv.cc.cc.lib}/lib:${pkgs.postgresql_16.lib}/lib''${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}
            # GeoDjango cannot ctypes-find_library() under the nix linker —
            # hand it exact store paths (web settings consume these when set;
            # host installs keep using ldconfig lookup).
            export GDAL_LIBRARY_PATH=${pkgs.gdal}/lib/libgdal.so
            export GEOS_LIBRARY_PATH=${pkgs.geos}/lib/libgeos_c.so
            # Pinned Playwright browsers (no npx playwright install)
            export PLAYWRIGHT_BROWSERS_PATH=${pkgs.playwright-driver.browsers}
            export PLAYWRIGHT_SKIP_VALIDATE_HOST_REQUIREMENTS=true
            # Environment contract: this shell provides TOOLS, not python
            # imports. nixpkgs' python setup hooks export python-built
            # packages' site-packages onto PYTHONPATH (gdal here), which
            # shadows the repo venv built on a different interpreter (bit
            # babylon's git hooks 2026-07-20: nix pathspec 0.12.1 shadowed
            # venv pathspec 1.0.4 → mypy hook crash → silent commit aborts).
            # Nothing needs the export. Guard: mise run check:env-contract.
            unset PYTHONPATH
            echo "babylon devshell: python=$(python3 --version) sqlite=$(python3 -c 'import sqlite3; print(sqlite3.sqlite_version)') node=$(node --version)"
          '';
        };

        # Reference-DB builder env (ADR098): exactly the toolchain of
        # tools/build_reference_db.py — the pinned sqlite-3.53.1 interpreter
        # plus pyarrow (parquet sources) and pyyaml (manifest product-sha
        # compare). Its own small closure so the nightly rebuild-verify leg
        # needs no venv bootstrap.
        devShells.dataBuild = pkgs.mkShell {
          packages = [
            (pythonData.withPackages (ps: [ ps.pyarrow ps.pyyaml ]))
          ];
          BABYLON_DEVSHELL = "dataBuild";
          shellHook = ''
            # Determinism pins (mirrors the default shell / .mise.toml [env])
            export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
            export NUMEXPR_NUM_THREADS=1 RAYON_NUM_THREADS=1
            # Environment contract — see devShells.default. withPackages
            # embeds pyarrow/pyyaml in the interpreter env; PYTHONPATH is
            # pure setup-hook leakage here too.
            unset PYTHONPATH
            echo "dataBuild shell: python=$(python3 --version) sqlite=$(python3 -c 'import sqlite3; print(sqlite3.sqlite_version)')"
          '';
        };

        # `nix flake check` runs this. It is a SMOKE gate only — importable
        # package + working console script. The determinism/regression gate needs
        # tools/ + committed baselines and runs as a CI step (Task 3), NOT here.
        checks.smoke = pkgs.runCommand "babylon-smoke" { } ''
          ${babylonEnv}/bin/python -c 'import babylon; print("babylon import OK")'
          ${babylonEnv}/bin/babylon --help > /dev/null
          echo "babylon --help OK"
          touch $out
        '';

        apps.default = {
          type = "app";
          program = "${babylonEnv}/bin/babylon";
        };
      }
    );
}
