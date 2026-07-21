"""WO-44 e2e: a real ``--vault-root`` run bakes a deterministic vault.

Drives the actual headless ``run()`` (Postgres + reference SQLite, same
environment guards as the shock e2e) twice with identical config and a
vault root, and asserts the P4 precondition: the two independently-baked
vault repositories end at the SAME commit sha — content, history shape,
and sim-time commit metadata all byte-identical. Leans on the keel's
``test_two_independent_bakes_at_the_same_tick_are_byte_identical_commits``
for the single-commit primitive; this test proves the whole runner path
(tick 0 included) composes to the same guarantee.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest

_SQLITE = Path("data/sqlite/marxist-data-3NF.sqlite")
_DSN = os.environ.get(
    "BABYLON_TEST_PG_DSN",
    "dbname=babylon_test host=localhost port=5433 user=test password=test",
)

pytestmark = [pytest.mark.integration, pytest.mark.ledger, pytest.mark.slow]

if not _SQLITE.exists():  # pragma: no cover - environment guard
    pytest.skip("live reference DB absent", allow_module_level=True)


def _pg_reachable() -> bool:
    try:
        import psycopg

        psycopg.connect(_DSN, connect_timeout=3).close()
    except Exception:
        return False
    return True


if not _pg_reachable():  # pragma: no cover - environment guard
    pytest.skip("local Postgres test DB unavailable", allow_module_level=True)

_TICKS = 3


def _bake_run(vault_root: Path) -> bytes:
    """One real headless run with the vault observer wired; returns HEAD sha."""
    from dulwich.repo import Repo

    from babylon.engine.headless_runner.models import ExitReason, SimulationRunConfig
    from babylon.engine.headless_runner.runner import run as runner_run
    from babylon.engine.headless_runner.scopes import resolve_scope

    os.environ.setdefault("BABYLON_TEST_PG_DSN", _DSN)
    scope = resolve_scope("detroit-tri-county")
    config = SimulationRunConfig(
        ticks=_TICKS,
        start_year=2010,
        random_seed=2010,
        scope_name="detroit-tri-county",
        scope_fips=scope.scope_fips,
        external_node_ids=scope.external_node_ids,
        sqlite_reference_path=_SQLITE,
        output_dir=Path(tempfile.mkdtemp(prefix="sim_vault_e2e_out_")),
        vault_root=vault_root,
    )
    result = runner_run(config)
    assert result.exit_reason == ExitReason.COMPLETED, result.exit_reason

    repo = Repo(str(vault_root))
    try:
        return repo.head()
    finally:
        repo.close()


@pytest.fixture(scope="module")
def two_baked_vaults() -> tuple[Path, Path, bytes, bytes]:
    root_a = Path(tempfile.mkdtemp(prefix="sim_vault_e2e_a_")) / "vault"
    root_b = Path(tempfile.mkdtemp(prefix="sim_vault_e2e_b_")) / "vault"
    return root_a, root_b, _bake_run(root_a), _bake_run(root_b)


class TestVaultRunEndToEnd:
    def test_every_scope_county_page_is_baked(
        self, two_baked_vaults: tuple[Path, Path, bytes, bytes]
    ) -> None:
        root_a, _, _, _ = two_baked_vaults
        from babylon.engine.headless_runner.scopes import resolve_scope

        for fips in sorted(resolve_scope("detroit-tri-county").scope_fips):
            assert (root_a / "county" / f"{fips}.md").exists(), f"county/{fips}.md not baked"

    def test_tick_zero_is_baked(self, two_baked_vaults: tuple[Path, Path, bytes, bytes]) -> None:
        """The WO-44 gap fix observable end-to-end: the vault's FIRST commit
        is the tick-0 bake, so the repo's root commit message names tick 0."""
        from dulwich.repo import Repo

        root_a, _, _, _ = two_baked_vaults
        repo = Repo(str(root_a))
        try:
            entries = list(repo.get_walker())
        finally:
            repo.close()
        root_message = entries[-1].commit.message.decode("utf8")
        assert "tick 0" in root_message

    def test_two_independent_runs_bake_byte_identical_vaults(
        self, two_baked_vaults: tuple[Path, Path, bytes, bytes]
    ) -> None:
        _, _, head_a, head_b = two_baked_vaults
        assert head_a == head_b
