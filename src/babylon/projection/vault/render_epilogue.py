"""Sandboxed deterministic epilogue-page rendering (Constitution III.13).

Mirrors :mod:`babylon.projection.vault.render`'s environment-construction
discipline exactly (ADR099): a fresh
:class:`~jinja2.sandbox.ImmutableSandboxedEnvironment` per call, no custom
filters/globals/finalizers, templates loaded from this package's own
``templates/`` directory via a :class:`~jinja2.PackageLoader` (no
filesystem-escape surface), and :class:`~jinja2.StrictUndefined` so a
template referencing a genuinely nonexistent field raises loudly.

Unlike the county dossier, an :class:`~babylon.projection.vault.epilogues.
Epilogue` has no optional fields and no absence path: a recognized outcome
key always carries a complete headline/body/palette, so there is nothing
for the template to walk into statblock/absence rows. The loud-failure
surface here is instead the *lookup* — an unrecognized outcome key raises
before the template ever runs (Constitution III.11: a wrong value fails
loud; this function never fabricates a placeholder ending for an outcome it
does not recognize).

jinja2 is imported lazily (function-local) so importing this module —
and transitively ``babylon.projection.vault`` — never pulls jinja2 into
``sys.modules`` merely by being on the import path (package-``__init__``
contract; see ``tests/unit/projection/vault/test_package_isolation.py``).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from babylon.projection.vault.epilogues import EPILOGUES

if TYPE_CHECKING:
    from jinja2.sandbox import ImmutableSandboxedEnvironment

__all__ = ["render_epilogue"]


def _build_environment() -> ImmutableSandboxedEnvironment:
    """Construct the vault's Jinja2 environment for epilogue rendering.

    Construction is code, never data (ADR099): no custom finalize, filters,
    or globals are registered here, and this is the *only* place this
    module builds the environment.

    :returns: a sandboxed environment with StrictUndefined, autoescape off
        (the output is Markdown, not HTML), and templates resolved from this
        package's ``templates/`` directory only.
    """
    from jinja2 import PackageLoader, StrictUndefined
    from jinja2.sandbox import ImmutableSandboxedEnvironment

    return ImmutableSandboxedEnvironment(
        loader=PackageLoader("babylon.projection.vault", "templates"),
        undefined=StrictUndefined,
        autoescape=False,
        keep_trailing_newline=True,
    )


def render_epilogue(outcome: str) -> str:
    """Render one terminal outcome's epilogue page.

    Pure function of ``outcome`` — no wall-clock, no randomness, no
    filesystem reads inside the template — so two calls with the same
    argument yield byte-identical output (Constitution III.13's
    determinism contract).

    :param outcome: the lowercase ``GameOutcome`` value string (e.g.
        ``"unresolved"``) — one of
        :data:`~babylon.projection.vault.epilogues.EPILOGUES`'s keys.
    :returns: the rendered Markdown page text.
    :raises KeyError: if ``outcome`` is not a recognized epilogue key — a
        present-but-wrong outcome string fails loud (Constitution III.11);
        this function never fabricates a placeholder ending.
    """
    epilogue = EPILOGUES[outcome]
    environment = _build_environment()
    template = environment.get_template("epilogue.md.j2")
    return template.render(outcome=outcome, epilogue=epilogue)
