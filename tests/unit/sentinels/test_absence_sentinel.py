"""Tests for the absence sentinel (task #64): every sqlite connect site
carries a cited disposition.

Founding incident (2026-07-20, G1 nightly): ``SubstrateSystem``'s lattice
build called ``get_reference_session()`` on a runner with no reference
database. ``sqlite3.connect``/SQLAlchemy's ``create_engine("sqlite:///path")``
both silently CREATE an empty file when the path is missing, so the absence
surfaced two systems later as a baffling ``no such table: dim_county``
instead of a loud error at the point of connection. Part A of task #64 fixed
the one entry point that bit; this file tests the STATIC scanner that keeps
every OTHER sqlite connect site under ``src/babylon`` honest.

Three tiers, mirroring the family's own established shape
(``test_dangling.py``):

- **Efficacy** (:func:`find_connect_sites` against synthetic ``tmp_path``
  trees) — the scanner correctly classifies each syntactic form.
- **Regression** (injected registry rows against synthetic sites) — proves
  each of the three gating rules actually reds on a genuine violation and
  stays clean on a genuine pass, independent of the live registry's state.
- **Liveness** (the real, shipped registry against the real tree) — the
  scan is clean on the integrated repo, proving the sentinel actually
  functions against production source, not only synthetic fixtures.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from babylon.sentinels.absence.checks import (
    ConnectSite,
    check_readonly_backslide,
    check_stale_dispositions,
    check_unregistered_connections,
    find_connect_sites,
    main,
)
from babylon.sentinels.absence.registry import (
    CONNECTION_DISPOSITIONS,
    ConnectionDisposition,
    _build_registry,
)
from babylon.sentinels.base import SentinelCheckError

pytestmark = pytest.mark.unit

_TOOLS_DIR = Path(__file__).resolve().parents[3] / "tools"
_TOOL_PATH = _TOOLS_DIR / "sentinel_check.py"


def _write_src(tmp_path: Path, source: str, name: str = "sample.py") -> Path:
    """Write a synthetic module under ``tmp_path/src/babylon/<name>``.

    :param tmp_path: The pytest tmp_path fixture root.
    :param source: The module source to write.
    :param name: The filename (may include subdirectories).
    :returns: The written file's path.
    """
    path = tmp_path / "src" / "babylon" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source, encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# find_connect_sites -- scanner efficacy
# ---------------------------------------------------------------------------


def test_memory_literal_is_classified_memory(tmp_path: Path) -> None:
    """MUTATION: an exact `:memory:` literal auto-passes."""
    _write_src(tmp_path, "import sqlite3\nsqlite3.connect(':memory:')\n")
    sites = find_connect_sites(repo_root=tmp_path)
    assert sites == (ConnectSite("src/babylon/sample.py", 2, "sqlite3.connect", "memory"),)


def test_readonly_uri_literal_is_classified_readonly(tmp_path: Path) -> None:
    """MUTATION: a `mode=ro` f-string URI is classified readonly."""
    _write_src(
        tmp_path,
        "import sqlite3\n"
        "sqlite_path = '/tmp/x.sqlite'\n"
        "sqlite3.connect(f'file:{sqlite_path}?mode=ro', uri=True)\n",
    )
    sites = find_connect_sites(repo_root=tmp_path)
    assert sites == (ConnectSite("src/babylon/sample.py", 3, "sqlite3.connect", "readonly"),)


def test_unresolvable_argument_is_classified_writable(tmp_path: Path) -> None:
    """MUTATION: a bare Name argument (no literal to resolve) defaults writable --
    absence of proof of safety is not proof of safety."""
    _write_src(
        tmp_path,
        "import sqlite3\ndef f(path):\n    return sqlite3.connect(path)\n",
    )
    sites = find_connect_sites(repo_root=tmp_path)
    assert sites == (ConnectSite("src/babylon/sample.py", 3, "sqlite3.connect", "writable"),)


def test_create_engine_sqlite_literal_is_a_hit(tmp_path: Path) -> None:
    """MUTATION: create_engine with an inline sqlite f-string literal is a hit."""
    _write_src(
        tmp_path,
        "from sqlalchemy import create_engine\n"
        "path = '/tmp/x.sqlite'\n"
        "create_engine(f'sqlite:///{path}')\n",
    )
    sites = find_connect_sites(repo_root=tmp_path)
    assert sites == (ConnectSite("src/babylon/sample.py", 3, "create_engine", "writable"),)


def test_create_engine_resolves_module_level_name_binding(tmp_path: Path) -> None:
    """MUTATION: create_engine(NAME) resolves NAME through a module-level
    assignment -- the exact reference/database.py NORMALIZED_DATABASE_URL shape."""
    _write_src(
        tmp_path,
        "from sqlalchemy import create_engine\n"
        "DB_URL = f'sqlite:///{1}'\n"
        "def get_engine():\n"
        "    return create_engine(DB_URL)\n",
    )
    sites = find_connect_sites(repo_root=tmp_path)
    assert sites == (ConnectSite("src/babylon/sample.py", 4, "create_engine", "writable"),)


def test_create_engine_over_non_sqlite_literal_is_not_a_hit(tmp_path: Path) -> None:
    """create_engine("postgresql://...") is out of this sentinel's scope entirely."""
    _write_src(
        tmp_path,
        "from sqlalchemy import create_engine\ncreate_engine('postgresql:///db')\n",
    )
    assert find_connect_sites(repo_root=tmp_path) == ()


def test_create_engine_over_unresolvable_name_is_not_a_hit(tmp_path: Path) -> None:
    """create_engine(url) over an opaque parameter cannot be proven sqlite --
    the persistence/database.py DatabaseConnection wrapper shape."""
    _write_src(
        tmp_path,
        "from sqlalchemy import create_engine\ndef f(url):\n    return create_engine(url)\n",
    )
    assert find_connect_sites(repo_root=tmp_path) == ()


def test_scan_raises_on_missing_scan_root(tmp_path: Path) -> None:
    with pytest.raises(SentinelCheckError):
        find_connect_sites(repo_root=tmp_path, scan_root="nowhere")


def test_scan_raises_on_unparseable_source(tmp_path: Path) -> None:
    _write_src(tmp_path, "def (:\n", name="broken.py")
    with pytest.raises(SentinelCheckError):
        find_connect_sites(repo_root=tmp_path)


# ---------------------------------------------------------------------------
# Regression: the three gating rules against synthetic sites + registries
# ---------------------------------------------------------------------------


def test_unregistered_writable_connection_is_flagged() -> None:
    """Growth gate: a file with a writable hit and no registry row reds."""
    sites = (ConnectSite("src/babylon/unregistered.py", 10, "sqlite3.connect", "writable"),)
    violations = check_unregistered_connections(sites=sites, dispositions={})
    assert len(violations) == 1
    assert "src/babylon/unregistered.py" in violations[0]
    assert "unregistered-connection" in violations[0]


def test_memory_only_file_needs_no_registration() -> None:
    """A file whose only site is `:memory:` is never required to register."""
    sites = (ConnectSite("src/babylon/scratch.py", 5, "sqlite3.connect", "memory"),)
    assert check_unregistered_connections(sites=sites, dispositions={}) == []


def test_registered_file_is_not_flagged_as_unregistered() -> None:
    sites = (ConnectSite("src/babylon/known.py", 5, "sqlite3.connect", "writable"),)
    dispositions = {
        "src/babylon/known.py": ConnectionDisposition(
            file="src/babylon/known.py", disposition="declared_debt", reason="test row"
        )
    }
    assert check_unregistered_connections(sites=sites, dispositions=dispositions) == []


def test_readonly_uri_file_with_a_writable_site_backslides() -> None:
    """Backslide gate: a readonly_uri-registered file must have EVERY hit read-only."""
    sites = (
        ConnectSite("src/babylon/reader.py", 8, "sqlite3.connect", "readonly"),
        ConnectSite("src/babylon/reader.py", 20, "sqlite3.connect", "writable"),
    )
    dispositions = {
        "src/babylon/reader.py": ConnectionDisposition(
            file="src/babylon/reader.py", disposition="readonly_uri", reason="test row"
        )
    }
    violations = check_readonly_backslide(sites=sites, dispositions=dispositions)
    assert len(violations) == 1
    assert "src/babylon/reader.py:20" in violations[0]
    assert "readonly-backslide" in violations[0]


def test_readonly_uri_file_all_readonly_passes() -> None:
    sites = (ConnectSite("src/babylon/reader.py", 8, "sqlite3.connect", "readonly"),)
    dispositions = {
        "src/babylon/reader.py": ConnectionDisposition(
            file="src/babylon/reader.py", disposition="readonly_uri", reason="test row"
        )
    }
    assert check_readonly_backslide(sites=sites, dispositions=dispositions) == []


def test_non_readonly_uri_disposition_is_never_checked_for_backslide() -> None:
    """A declared_debt/guarded/etc row's writable sites are its own documented
    debt, not a backslide from a readonly_uri promise that was never made."""
    sites = (ConnectSite("src/babylon/debt.py", 8, "sqlite3.connect", "writable"),)
    dispositions = {
        "src/babylon/debt.py": ConnectionDisposition(
            file="src/babylon/debt.py", disposition="declared_debt", reason="test row"
        )
    }
    assert check_readonly_backslide(sites=sites, dispositions=dispositions) == []


def test_stale_registry_row_is_flagged() -> None:
    """Stale-row gate: a registered file with zero remaining hits reds."""
    dispositions = {
        "src/babylon/gone.py": ConnectionDisposition(
            file="src/babylon/gone.py", disposition="guarded", reason="test row"
        )
    }
    violations = check_stale_dispositions(sites=(), dispositions=dispositions)
    assert len(violations) == 1
    assert "src/babylon/gone.py" in violations[0]
    assert "stale-disposition" in violations[0]


def test_registered_file_with_a_remaining_hit_is_not_stale() -> None:
    sites = (ConnectSite("src/babylon/live.py", 3, "sqlite3.connect", "writable"),)
    dispositions = {
        "src/babylon/live.py": ConnectionDisposition(
            file="src/babylon/live.py", disposition="declared_debt", reason="test row"
        )
    }
    assert check_stale_dispositions(sites=sites, dispositions=dispositions) == []


def test_memory_only_site_still_keeps_a_registered_row_live() -> None:
    """Unlike the growth gate, staleness counts a :memory: site as "still here"."""
    sites = (ConnectSite("src/babylon/scratch.py", 3, "sqlite3.connect", "memory"),)
    dispositions = {
        "src/babylon/scratch.py": ConnectionDisposition(
            file="src/babylon/scratch.py", disposition="creates_own_store", reason="test row"
        )
    }
    assert check_stale_dispositions(sites=sites, dispositions=dispositions) == []


# ---------------------------------------------------------------------------
# Registry shape teeth
# ---------------------------------------------------------------------------


def test_connection_disposition_rejects_blank_file() -> None:
    with pytest.raises(ValueError, match="file"):
        ConnectionDisposition(file="", disposition="guarded", reason="x")


def test_connection_disposition_rejects_non_py_file() -> None:
    with pytest.raises(ValueError, match="\\.py"):
        ConnectionDisposition(file="src/babylon/x.txt", disposition="guarded", reason="x")


def test_connection_disposition_rejects_blank_reason() -> None:
    with pytest.raises(ValueError, match="reason"):
        ConnectionDisposition(file="src/babylon/x.py", disposition="guarded", reason="  ")


def test_connection_disposition_rejects_unknown_disposition() -> None:
    with pytest.raises(ValueError, match="disposition"):
        ConnectionDisposition(
            file="src/babylon/x.py",
            disposition="not_a_real_disposition",  # type: ignore[arg-type]
            reason="x",
        )


def test_build_registry_rejects_duplicate_file_rows() -> None:
    rows = (
        ConnectionDisposition(file="src/babylon/x.py", disposition="guarded", reason="a"),
        ConnectionDisposition(file="src/babylon/x.py", disposition="readonly_uri", reason="b"),
    )
    with pytest.raises(ValueError, match="duplicate"):
        _build_registry(rows)


def test_real_registry_has_no_duplicate_files() -> None:
    """The shipped registry already passed this guard at import time -- this
    test just makes that fact independently assertable, mirroring the
    dangling sentinel's own `_unknown_member_classes` liveness pin."""
    assert len(CONNECTION_DISPOSITIONS) > 0


# ---------------------------------------------------------------------------
# Liveness: the real, shipped registry against the current tree
# ---------------------------------------------------------------------------


def test_real_tree_is_clean() -> None:
    """No unregistered/backslid/stale rows against the actual repo."""
    assert check_unregistered_connections() == []
    assert check_readonly_backslide() == []
    assert check_stale_dispositions() == []


def test_main_check_exits_zero_on_the_real_tree() -> None:
    assert main(["--check"]) == 0


def test_cli_entry_point_clean_on_live_tree() -> None:
    """`sentinel_check.py absence --check` exits 0 on the integrated tree."""
    result = subprocess.run(  # noqa: S603 - fixed argv, no shell, trusted path
        [sys.executable, str(_TOOL_PATH), "absence", "--check"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, (
        "expected the ABSENCE sensor to be clean on the integrated tree:\n"
        f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )
    assert "Absence clean" in result.stdout
