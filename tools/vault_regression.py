"""Golden-vault byte-gate (Program 24 WO-51 — Amendment W / Constitution III.13).

The vault is a deterministic materialization of the simulation: the same
scenario, seed, and tick count must bake byte-identical page content and
byte-identical dulwich commit history every time, on every machine. This
tool pins that as a regression gate over two non-authoritative reference scenarios:

* ``single_county`` — the in-process engine loop (no Postgres, no runner):
  ``create_single_county_scenario`` driven ``TICKS`` ticks with the
  per-kind :class:`~babylon.projection.vault.tick_baker.ArchiveTickBaker`
  baking every tick. Mirrors ``tools/record_projection_fixtures.py``'s
  loop mechanics exactly.
* ``org_probe`` — the in-process organization projection probe.

Modes:

* ``generate`` — one bake per scenario; writes
  ``tests/baselines/vault/<scenario>/manifest.json`` (final HEAD sha +
  per-page sha256 map). Committing that file IS a baseline ceremony
  (§6.5): the commit needs the ``Baselines: blessed(<slug>)`` trailer.
* ``compare`` — TWO independent bakes per scenario; asserts run1 HEAD ==
  run2 HEAD == committed manifest HEAD and the per-page sha map matches,
  printing a per-file drift table on any mismatch (exit 1).

Loud failure: a missing manifest or any drift is an error.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import tempfile
from pathlib import Path
from typing import Final

_REPO_ROOT: Final = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT / "src") not in sys.path:  # pragma: no cover - import shim
    sys.path.insert(0, str(_REPO_ROOT / "src"))

BASELINE_ROOT: Final = _REPO_ROOT / "tests" / "baselines" / "vault"

#: Scenario registry: name -> (bake callable name, tick count).
SCENARIOS: Final = ("single_county", "org_probe")

SINGLE_COUNTY_TICKS: Final = 5
ORG_PROBE_TICKS: Final = 5

#: Per-scenario tick counts (Task 13, spec §11) — generalizes what used to be
#: a hardcoded 2-way ternary in :func:`_build_manifest` so a 3rd (and any
#: future) scenario doesn't need that function edited again.
TICKS_BY_SCENARIO: Final[dict[str, int]] = {
    "single_county": SINGLE_COUNTY_TICKS,
    "org_probe": ORG_PROBE_TICKS,
}


def _bake_single_county(vault_root: Path) -> bytes:
    """In-process ``single_county`` bake: engine loop + per-kind tick baker.

    :param vault_root: Fresh directory the vault repository is created in.
    :returns: The vault repository's final HEAD commit sha (bytes, hex).
    """
    from dulwich.repo import Repo

    from babylon.engine.context import TickContext
    from babylon.engine.scenarios import create_single_county_scenario
    from babylon.engine.services import ServiceContainer
    from babylon.engine.simulation_engine import _DEFAULT_ENGINE
    from babylon.models.world_state import WorldState
    from babylon.projection.vault.materializer import VaultMaterializer
    from babylon.projection.vault.tick_baker import ArchiveTickBaker

    sys.path.insert(0, str(_REPO_ROOT / "tools"))
    from regression_test import build_single_county_overrides  # type: ignore[import-not-found]

    state, sim_config, defines = create_single_county_scenario()
    overrides = build_single_county_overrides(defines)
    graph = state.to_graph()
    baker = ArchiveTickBaker(VaultMaterializer(vault_root), ("26163",))

    for tick in range(SINGLE_COUNTY_TICKS):
        services = ServiceContainer.create(sim_config, defines, **overrides)
        context = TickContext(tick=tick, persistent_data={})
        _DEFAULT_ENGINE.run_tick(graph, services, context)
        world = WorldState.from_graph(graph, tick=tick)
        baker.on_tick_committed(tick=tick, world=world, graph=graph)

    repo = Repo(str(vault_root))
    try:
        return repo.head()
    finally:
        repo.close()


def _bake_org_probe(vault_root: Path) -> bytes:
    """In-process ``org_probe`` bake: engine loop + per-kind tick baker.

    Mirrors :func:`_bake_single_county` exactly except for the scenario
    factory and the absence of any county/calculator overrides (org_probe
    carries no ``county_fips`` territory, so there is no Wayne tensor
    registry to hydrate) — ``ArchiveTickBaker`` is constructed with an
    EMPTY ``county_fips`` tuple; it still bakes organization pages, since
    those are graph-enumerated (:func:`_node_ids`), not scope-enumerated
    (Task 13, spec §11).

    :param vault_root: Fresh directory the vault repository is created in.
    :returns: The vault repository's final HEAD commit sha (bytes, hex).
    """
    from dulwich.repo import Repo

    from babylon.engine.context import TickContext
    from babylon.engine.scenarios import create_org_probe_scenario
    from babylon.engine.services import ServiceContainer
    from babylon.engine.simulation_engine import _DEFAULT_ENGINE
    from babylon.models.world_state import WorldState
    from babylon.projection.vault.materializer import VaultMaterializer
    from babylon.projection.vault.tick_baker import ArchiveTickBaker

    state, sim_config, defines = create_org_probe_scenario()
    graph = state.to_graph()
    baker = ArchiveTickBaker(VaultMaterializer(vault_root), ())

    for tick in range(ORG_PROBE_TICKS):
        services = ServiceContainer.create(sim_config, defines)
        context = TickContext(tick=tick, persistent_data={})
        _DEFAULT_ENGINE.run_tick(graph, services, context)
        world = WorldState.from_graph(graph, tick=tick)
        baker.on_tick_committed(tick=tick, world=world, graph=graph)

    repo = Repo(str(vault_root))
    try:
        return repo.head()
    finally:
        repo.close()


def _bake(scenario: str, vault_root: Path) -> bytes:
    """Dispatch one bake.

    :param scenario: A member of :data:`SCENARIOS`.
    :param vault_root: Fresh directory for the vault repository.
    :returns: Final HEAD commit sha.
    """
    if scenario == "single_county":
        return _bake_single_county(vault_root)
    if scenario == "org_probe":
        return _bake_org_probe(vault_root)
    msg = f"unknown scenario: {scenario!r} (known: {', '.join(SCENARIOS)})"
    raise ValueError(msg)


def _file_manifest(vault_root: Path) -> dict[str, str]:
    """Per-page sha256 map of the vault worktree (``.git`` excluded).

    :param vault_root: The baked vault repository root.
    :returns: ``{relative_posix_path: sha256_hex}`` in sorted-key order.
    """
    entries: dict[str, str] = {}
    for path in sorted(vault_root.rglob("*")):
        if not path.is_file() or ".git" in path.relative_to(vault_root).parts:
            continue
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        entries[path.relative_to(vault_root).as_posix()] = digest
    return entries


def _manifest_path(scenario: str) -> Path:
    return BASELINE_ROOT / scenario / "manifest.json"


def _build_manifest(scenario: str, head_sha: bytes, files: dict[str, str]) -> dict[str, object]:
    ticks = TICKS_BY_SCENARIO[scenario]
    return {
        "scenario": scenario,
        "ticks": ticks,
        "head_sha": head_sha.decode("ascii"),
        "page_count": len(files),
        "files": files,
    }


def generate(scenarios: list[str]) -> int:
    """Bake each scenario once and write its golden manifest.

    :param scenarios: Scenario names to seed.
    :returns: Process exit code (0; failures raise, Loud Failure).
    """
    for scenario in scenarios:
        vault_root = Path(tempfile.mkdtemp(prefix=f"vault_golden_{scenario}_"))
        head = _bake(scenario, vault_root)
        files = _file_manifest(vault_root)
        manifest = _build_manifest(scenario, head, files)
        out = _manifest_path(scenario)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf8")
        print(f"[{scenario}] wrote {out} — HEAD {head.decode('ascii')}, {len(files)} pages")
    print("NOTE: committing tests/baselines/vault/** is a §6.5 ceremony — use")
    print("  python3 tools/generate_ceremony_message.py --slug <slug> --summary '...'")
    return 0


def _drift_table(golden: dict[str, str], live: dict[str, str]) -> list[str]:
    """Human-readable per-file drift rows between two sha maps."""
    rows: list[str] = []
    for path in sorted(set(golden) | set(live)):
        old, new = golden.get(path), live.get(path)
        if old == new:
            continue
        if old is None:
            rows.append(f"  ADDED   {path}")
        elif new is None:
            rows.append(f"  REMOVED {path}")
        else:
            rows.append(f"  CHANGED {path}")
    return rows


def compare(scenarios: list[str]) -> int:
    """Two independent bakes per scenario vs. the committed golden.

    :param scenarios: Scenario names to gate.
    :returns: 0 on byte-identity everywhere; 1 on any drift (with a
        per-file drift table printed).
    """
    failed = False
    for scenario in scenarios:
        manifest_file = _manifest_path(scenario)
        if not manifest_file.exists():
            print(f"[{scenario}] FAIL — no committed golden at {manifest_file}")
            failed = True
            continue
        golden = json.loads(manifest_file.read_text(encoding="utf8"))

        roots = [Path(tempfile.mkdtemp(prefix=f"vault_gate_{scenario}_{n}_")) for n in ("a", "b")]
        heads = [_bake(scenario, root) for root in roots]

        if heads[0] != heads[1]:
            print(
                f"[{scenario}] FAIL — two independent bakes DIVERGED: "
                f"{heads[0].decode('ascii')} != {heads[1].decode('ascii')} (determinism bug)"
            )
            failed = True
            continue

        live_files = _file_manifest(roots[0])
        head_hex = heads[0].decode("ascii")
        if head_hex != golden["head_sha"] or live_files != golden["files"]:
            print(f"[{scenario}] FAIL — drift vs. committed golden:")
            print(f"  HEAD golden {golden['head_sha']} vs live {head_hex}")
            for row in _drift_table(golden["files"], live_files):
                print(row)
            failed = True
            continue

        print(
            f"[{scenario}] PASS — two independent bakes byte-identical to golden "
            f"(HEAD {head_hex}, {len(live_files)} pages)"
        )
    return 1 if failed else 0


def main(argv: list[str] | None = None) -> int:
    """CLI entry point.

    :param argv: Argument vector (``None`` uses ``sys.argv``).
    :returns: Process exit code.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("generate", "compare"))
    parser.add_argument(
        "--scenario",
        action="append",
        choices=SCENARIOS,
        help="scenario to run (repeatable); default: all",
    )
    args = parser.parse_args(argv)

    scenarios = list(args.scenario) if args.scenario else list(SCENARIOS)
    if args.mode == "generate":
        return generate(scenarios)
    return compare(scenarios)


if __name__ == "__main__":
    raise SystemExit(main())
