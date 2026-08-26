"""Executable contract for the PER-258 Django estate removal."""

from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Final

import pytest

pytestmark = pytest.mark.unit

_ROOT: Final[Path] = Path(__file__).resolve().parents[3]
_PYPROJECT: Final[Path] = _ROOT / "pyproject.toml"
_ACTIVE_AUTOMATION: Final[tuple[Path, ...]] = (
    _ROOT / ".mise.toml",
    _ROOT / ".github" / "actions" / "bootstrap-python" / "action.yml",
    _ROOT / ".github" / "workflows" / "ci.yml",
    _ROOT / ".github" / "workflows" / "main.yml",
    _ROOT / ".github" / "workflows" / "weekly-pg-integration.yml",
    _ROOT / ".github" / "workflows" / "weekly-py313.yml",
)
_RETIRED_PATHS: Final[tuple[Path, ...]] = (
    _ROOT / "web",
    _ROOT / "tests" / "unit" / "web",
    _ROOT / "tests" / "integration" / "web",
    _ROOT / "tests" / "unit" / "observatory",
    _ROOT / "tests" / "unit" / "test_contract_parity.py",
    _ROOT / "tests" / "scripts" / "quickstart_walkthrough.sh",
)
_RETIRED_DISTRIBUTIONS: Final[frozenset[str]] = frozenset(
    {
        "django",
        "django-cors-headers",
        "django-stubs",
        "djangorestframework",
        "djangorestframework-stubs",
        "gunicorn",
        "pytest-django",
    }
)
_RETIRED_AUTOMATION_TERMS: Final[tuple[str, ...]] = (
    "DJANGO_SETTINGS_MODULE",
    "babylon_web",
    "pytest-django",
    "mypy_django_plugin",
    "--extra server",
    "GeoDjango",
)


def _distribution_name(requirement: str) -> str:
    """Return the normalized distribution name before extras or a version pin."""
    return requirement.split("[", 1)[0].split(">", 1)[0].split("=", 1)[0].lower()


def test_retired_django_paths_are_absent() -> None:
    present = [str(path.relative_to(_ROOT)) for path in _RETIRED_PATHS if path.exists()]
    assert present == [], f"retired Django/web paths remain: {present}"


def test_python_dependencies_exclude_the_django_stack() -> None:
    config = tomllib.loads(_PYPROJECT.read_text(encoding="utf-8"))
    requirements = list(config["project"]["dependencies"])
    for group in config["project"].get("optional-dependencies", {}).values():
        requirements.extend(group)
    for group in config.get("dependency-groups", {}).values():
        requirements.extend(group)
    names = {_distribution_name(requirement) for requirement in requirements}
    assert names.isdisjoint(_RETIRED_DISTRIBUTIONS), names & _RETIRED_DISTRIBUTIONS


def test_python_tooling_has_no_django_bootstrap() -> None:
    config = tomllib.loads(_PYPROJECT.read_text(encoding="utf-8"))
    pytest_config = config["tool"]["pytest"]["ini_options"]
    assert "DJANGO_SETTINGS_MODULE" not in pytest_config
    assert "web" not in pytest_config["pythonpath"]
    mypy_config = config["tool"]["mypy"]
    assert "web" not in mypy_config["mypy_path"].split(":")
    assert "mypy_django_plugin.main" not in mypy_config["plugins"]
    assert "django-stubs" not in config["tool"]


@pytest.mark.parametrize("path", _ACTIVE_AUTOMATION)
def test_active_automation_does_not_bootstrap_django(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    present = [term for term in _RETIRED_AUTOMATION_TERMS if term in text]
    assert present == [], f"{path.relative_to(_ROOT)} retains Django automation: {present}"
