"""Contract tests for WO-44: the runner actually wires the vault observer.

The keel shipped the ``TickCommitObserver`` seam but ``run()`` never
passed one (a zero-line no-op) and the bare tick-0 ``persist_tick``
bypassed it entirely — so P4's golden vault could never have been baked.
These tests pin the wiring: observer construction from config, the tick-0
bake, the content-hash skip, and one-commit-per-tick batching
(vault-at-scale: national scope must cost commits proportional to CHANGE,
never ~1.64M commits of scope size).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from uuid import UUID

import pytest

from babylon.config.defines._assembler import GameDefines
from babylon.engine.factories import create_bourgeoisie, create_proletariat
from babylon.engine.headless_runner.models import SimulationRunConfig
from babylon.engine.headless_runner.runner import _build_tick_commit_observer, _tick_loop
from babylon.models import WorldState
from babylon.projection.vault.materializer import VaultMaterializer
from babylon.projection.vault.tick_baker import CountyTickBaker

pytestmark = [pytest.mark.unit]

_SESSION_ID = UUID("00000000-0000-0000-0000-000000000044")


class _FakeBridge:
    """Stand-in for WorldStateBridge — captures per-tick persist calls."""

    def __init__(self) -> None:
        self.persist_calls: list[tuple[int, str]] = []
        self.event_capture: Any = None

    def persist_tick(
        self,
        world: Any,  # noqa: ARG002 — bridge shape
        tick: int,
        determinism_hash: str,
        opposition_states: Any = None,  # noqa: ARG002 — bridge shape
    ) -> None:
        self.persist_calls.append((tick, determinism_hash))

    def poll_endgame(self, world: Any, tick: int) -> Any:  # noqa: ARG002 — bridge shape
        return None

    @property
    def auditor(self) -> None:
        return None


class _RecordingObserver:
    """TickCommitObserver double — records every observed tick."""

    def __init__(self) -> None:
        self.ticks: list[int] = []

    def on_tick_committed(self, *, tick: int, world: Any, graph: Any) -> None:  # noqa: ARG002
        self.ticks.append(tick)


def _make_config(**overrides: Any) -> SimulationRunConfig:
    defaults: dict[str, Any] = {
        "ticks": 5,
        "start_year": 2010,
        "random_seed": 2010,
        "scope_name": "wayne-solo",
        "scope_fips": frozenset({"26163", "26099"}),
        "external_node_ids": frozenset(),
        "sqlite_reference_path": Path("data/sqlite/marxist-data-3NF.sqlite"),
        "output_dir": Path("/tmp/test_vault_wiring"),
    }
    defaults.update(overrides)
    return SimulationRunConfig(**defaults)


def _make_minimal_world_and_graph() -> tuple[WorldState, Any]:
    prol = create_proletariat(id="C001", county_fips="26163")
    bourg = create_bourgeoisie(id="C002", county_fips="26163")
    world = WorldState(tick=0, entities={"C001": prol, "C002": bourg}, config=GameDefines())
    return world, world.to_graph()


def _commit_count(root: Path) -> int:
    from dulwich.repo import Repo

    repo = Repo(str(root))
    try:
        return sum(1 for _ in repo.get_walker())
    finally:
        repo.close()


class TestObserverConstruction:
    def test_no_vault_root_wires_no_observer(self) -> None:
        """The None default IS the qa:regression byte-identity contract."""
        assert _build_tick_commit_observer(_make_config()) is None

    def test_vault_root_wires_a_county_tick_baker_over_the_scope(self, tmp_path: Path) -> None:
        observer = _build_tick_commit_observer(_make_config(vault_root=tmp_path / "vault"))
        assert isinstance(observer, CountyTickBaker)
        assert observer._county_fips == ("26099", "26163")


class TestTickZeroBakeGap:
    def test_observer_sees_tick_zero_and_every_subsequent_tick(self) -> None:
        """The bare tick-0 persist_tick no longer bypasses the observer."""
        world, graph = _make_minimal_world_and_graph()
        observer = _RecordingObserver()

        ticks_completed, endgame = _tick_loop(
            bridge=_FakeBridge(),  # type: ignore[arg-type]
            world=world,
            runtime=None,
            session_id=_SESSION_ID,
            config=_make_config(ticks=5),
            per_tick_durations=[],
            graph=graph,
            tick_commit_observer=observer,
        )

        assert ticks_completed == 5
        assert endgame is None
        assert observer.ticks == [0, 1, 2, 3, 4]

    def test_no_observer_still_runs_the_loop_unchanged(self) -> None:
        world, graph = _make_minimal_world_and_graph()
        bridge = _FakeBridge()
        ticks_completed, _ = _tick_loop(
            bridge=bridge,  # type: ignore[arg-type]
            world=world,
            runtime=None,
            session_id=_SESSION_ID,
            config=_make_config(ticks=3),
            per_tick_durations=[],
            graph=graph,
        )
        assert ticks_completed == 3
        assert [t for t, _ in bridge.persist_calls] == [0, 1, 2]


class TestVaultAtScale:
    def test_one_commit_covers_the_whole_tick(self, tmp_path: Path) -> None:
        materializer = VaultMaterializer(tmp_path / "vault")
        sha = materializer.bake_tick(
            {"county/26163.md": "# Wayne\n", "county/26099.md": "# Macomb\n"}, tick=1
        )
        assert sha is not None
        assert _commit_count(tmp_path / "vault") == 1
        assert (tmp_path / "vault" / "county" / "26163.md").read_text(
            encoding="utf8"
        ) == "# Wayne\n"

    def test_unchanged_pages_are_skipped_by_content_hash(self, tmp_path: Path) -> None:
        """A quiet tick costs NO commit; a partial change commits once."""
        root = tmp_path / "vault"
        materializer = VaultMaterializer(root)
        pages = {"county/26163.md": "# Wayne\n", "county/26099.md": "# Macomb\n"}
        materializer.bake_tick(pages, tick=1)

        assert materializer.bake_tick(pages, tick=2) is None
        assert _commit_count(root) == 1

        changed = dict(pages)
        changed["county/26163.md"] = "# Wayne — changed\n"
        assert materializer.bake_tick(changed, tick=3) is not None
        assert _commit_count(root) == 2

    def test_two_independent_tick_bakes_are_byte_identical_commits(self, tmp_path: Path) -> None:
        """The keel's two-bake determinism contract survives batching."""
        shas: list[bytes] = []
        for name in ("a", "b"):
            materializer = VaultMaterializer(tmp_path / name)
            sha = materializer.bake_tick(
                {"county/26163.md": "# Wayne\n", "county/26099.md": "# Macomb\n"}, tick=7
            )
            assert sha is not None
            shas.append(sha)
        assert shas[0] == shas[1]
