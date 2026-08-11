"""Player-role ``synchronous_commit=off`` DECLARED in the config template
(ADR176 ruling 32 / P-F completion — issue #382).

Ruling 32 read in full: "synchronous_commit=off on the player, DECLARED in
the config template (worst case one in-flight tick, re-simulated
bit-identically)". The 2026-08-11 bundle-closure audit found P-F only
half-landed: ``ALTER ROLE test SET synchronous_commit = off``
(``docker/postgres/initdb/01-babylon-init.sql``, spec-087 FR-005) covers the
``test`` role but is *invisible* to a config audit (Director's own framing,
postgres-brief-2026-07-29.md D-list item 6) — no separate "player" role
exists yet (the game-managed player cluster is rust-port future work, ADR176
ruling 33 change-table item #27), so today's player-equivalent surface is
the dev config template docker-compose.yml selects
(``docker/postgres/postgresql.conf``). "Declared" means: a cluster-wide GUC
any auditor can grep, not a value hidden in ``pg_db_role_setting``.

Pure text assertions against the tracked config file — no Postgres needed,
mirrors ``tests/unit/cli/test_uv_migration.py``'s config-parsing pattern.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PLAYER_CONF = (ROOT / "docker/postgres/postgresql.conf").read_text(encoding="utf-8")
CI_CONF = (ROOT / "docker/postgres/postgresql.ci.conf").read_text(encoding="utf-8")
INITDB_SQL = (ROOT / "docker/postgres/initdb/01-babylon-init.sql").read_text(encoding="utf-8")


def _guc_lines(conf_text: str) -> list[str]:
    return [
        stripped for line in conf_text.splitlines() if (stripped := line.split("#", 1)[0].strip())
    ]


def test_player_config_declares_synchronous_commit_off() -> None:
    """The dev/player config template sets ``synchronous_commit = off`` as
    a cluster-wide GUC — grep-able, not hidden behind a role name."""
    guc_lines = _guc_lines(PLAYER_CONF)
    assert "synchronous_commit = off" in guc_lines, (
        "docker/postgres/postgresql.conf must DECLARE synchronous_commit = off "
        "(ADR176 ruling 32) instead of relying solely on the invisible "
        "ALTER ROLE test mechanism"
    )


def test_player_config_no_longer_claims_cluster_wide_on() -> None:
    """The stale comment claiming synchronous_commit 'stays ON cluster-wide'
    must not survive next to a cluster-wide OFF declaration — an accurate
    comment matters as much as the GUC itself for an audit trail."""
    assert "synchronous_commit stays ON cluster-wide" not in PLAYER_CONF


def test_test_role_alter_still_present_for_ci_parity() -> None:
    """The original spec-087 FR-005 mechanism (ALTER ROLE test) stays —
    surgical addition, not a replacement; CI's fork explicitly promises
    identical behavioral settings to dev (docker/postgres/postgresql.ci.conf
    docstring), and CI shares this initdb script via the base compose file."""
    assert "ALTER ROLE test SET synchronous_commit = off;" in INITDB_SQL


def test_ci_config_behaviorally_consistent_with_player() -> None:
    """postgresql.ci.conf's own docstring promises every BEHAVIORAL setting
    stays identical to the dev/player config, memory sizing the only
    divergence. The resulting synchronous_commit value for role `test` must
    therefore still be `off` on both — CI keeps relying on the initdb ALTER
    (untouched), the player config now also declares it at the cluster
    level. Neither file may declare the opposite value."""
    assert "synchronous_commit = on" not in _guc_lines(PLAYER_CONF)
    assert "synchronous_commit = on" not in _guc_lines(CI_CONF)
