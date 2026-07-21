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
    # classifiers stay poetry-derived
    assert "classifiers" in DATA["project"].get("dynamic", [])


def test_no_legacy_poetry_dependencies_table() -> None:
    assert "dependencies" not in DATA["tool"]["poetry"], "legacy [tool.poetry.dependencies] remains"


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


def test_build_backend_stays_poetry_core() -> None:
    assert DATA["build-system"]["build-backend"] == "poetry.core.masonry.api"
