{
  description = "Babylon — MLM-TW geopolitical simulation engine (Nix Player Channel, ADR094)";

  inputs = {
    # Match infra's channel (babylon-infra flake pins nixos-25.11).
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-25.11";
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
    { nixpkgs, flake-utils, pyproject-nix, uv2nix, pyproject-build-systems, ... }:
    flake-utils.lib.eachDefaultSystem (
      system:
      let
        pkgs = nixpkgs.legacyPackages.${system};
        lib = pkgs.lib;
        python = pkgs.python312;

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
