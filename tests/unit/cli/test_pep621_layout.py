"""PEP-621 dependency layout + server extra (ADR095 D3a/D2)."""

from __future__ import annotations

import tomllib
from pathlib import Path

DATA = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))


def _names(specs: list[str]) -> set[str]:
    out: set[str] = set()
    for spec in specs:
        head = spec.split(";")[0].strip()
        for sep in (">", "<", "=", "!", "~", "["):
            head = head.split(sep)[0]
        out.add(head.strip())
    return out


def test_project_dependencies_is_static_list() -> None:
    assert isinstance(DATA["project"]["dependencies"], list)
    assert "dependencies" not in DATA["project"].get("dynamic", [])
    # classifiers went static at the hatchling cutover (2026-07-22):
    # transcribed from the last poetry-core wheel's METADATA
    assert "classifiers" not in DATA["project"].get("dynamic", [])
    assert isinstance(DATA["project"]["classifiers"], list)
    assert "Programming Language :: Python :: 3.12" in DATA["project"]["classifiers"]


def test_no_legacy_poetry_table() -> None:
    assert "poetry" not in DATA.get("tool", {}), "legacy [tool.poetry] table remains"


def test_server_extra_absorbs_legacy_web_stack() -> None:
    server = _names(DATA["project"]["optional-dependencies"]["server"])
    expected = {
        "ansible-dev-tools",
        "rstcheck",
        "doc8",
        "boto3",
        "django",
        "djangorestframework",
        "django-cors-headers",
        "gunicorn",
    }
    assert expected <= server


def test_core_stays_in_default_deps() -> None:
    core = _names(DATA["project"]["dependencies"])
    for pkg in ("pydantic", "typer", "rich", "rustworkx", "openai"):
        assert pkg in core
    # server packages are NOT in the default set
    assert "django" not in core
    assert "gunicorn" not in core


def test_build_backend_is_hatchling() -> None:
    # hatchling replaced poetry-core 2026-07-22 (uv completion train); the
    # explicit src-layout mapping lives in [tool.hatch.build.targets.wheel]
    assert DATA["build-system"]["build-backend"] == "hatchling.build"
    assert DATA["tool"]["hatch"]["build"]["targets"]["wheel"]["packages"] == ["src/babylon"]
