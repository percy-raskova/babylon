"""Necropolis Codex - Revolutionary Hope Styling Extension.

Custom RST roles for :hope: and :hopedim: text that renders in
PhosphorGreen/ForestDim in PDF output.

Usage in RST::

    :hope:`Organization is the difference.`
    :hopedim:`The Critical Window:`

Only use for:
    - Revolutionary organization content
    - P(S|R) > P(S|A) / Warsaw Ghetto Dynamic
    - Solidarity transmission, critical window, enforcer radicalization
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from docutils import nodes
from docutils.parsers.rst import roles

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from docutils.parsers.rst.states import Inliner
    from sphinx.application import Sphinx
    from sphinx.writers.html5 import HTML5Translator
    from sphinx.writers.latex import LaTeXTranslator


# Custom node classes for hope text (must be at module level for pickling)
class hope_node(nodes.inline):  # noqa: N801 - docutils naming convention
    """Node for revolutionary hope text (PhosphorGreen in PDF)."""


class hopedim_node(nodes.inline):  # noqa: N801 - docutils naming convention
    """Node for dimmer hope text (ForestDim in PDF)."""


# Role functions - docutils API signature
# B006 ignored: mutable defaults required by docutils API, never modified
def hope_role(
    _name: str,
    rawtext: str,
    text: str,
    _lineno: int,
    _inliner: Inliner,
    options: Mapping[str, Any] = {},  # noqa: B006
    content: Sequence[str] = (),
) -> tuple[Sequence[nodes.Node], Sequence[nodes.system_message]]:
    """Role for revolutionary hope text (PhosphorGreen in PDF)."""
    _ = options, content  # Required by API but unused
    node = hope_node(rawtext, text, classes=["hope"])
    return [node], []


def hopedim_role(
    _name: str,
    rawtext: str,
    text: str,
    _lineno: int,
    _inliner: Inliner,
    options: Mapping[str, Any] = {},  # noqa: B006
    content: Sequence[str] = (),
) -> tuple[Sequence[nodes.Node], Sequence[nodes.system_message]]:
    """Role for dimmer hope text (ForestDim in PDF)."""
    _ = options, content  # Required by API but unused
    node = hopedim_node(rawtext, text, classes=["hopedim"])
    return [node], []


# Visitor functions for LaTeX output
def visit_hope_latex(self: LaTeXTranslator, _node: hope_node) -> None:
    """Visit hope node in LaTeX output."""
    self.body.append(r"\hope{")


def depart_hope_latex(self: LaTeXTranslator, _node: hope_node) -> None:
    """Depart hope node in LaTeX output."""
    self.body.append("}")


def visit_hopedim_latex(self: LaTeXTranslator, _node: hopedim_node) -> None:
    """Visit hopedim node in LaTeX output."""
    self.body.append(r"\hopedim{")


def depart_hopedim_latex(self: LaTeXTranslator, _node: hopedim_node) -> None:
    """Depart hopedim node in LaTeX output."""
    self.body.append("}")


# Visitor functions for HTML output
def visit_hope_html(self: HTML5Translator, _node: hope_node) -> None:
    """Visit hope node in HTML output."""
    self.body.append('<span class="hope">')


def depart_hope_html(self: HTML5Translator, _node: hope_node) -> None:
    """Depart hope node in HTML output."""
    self.body.append("</span>")


def visit_hopedim_html(self: HTML5Translator, _node: hopedim_node) -> None:
    """Visit hopedim node in HTML output."""
    self.body.append('<span class="hopedim">')


def depart_hopedim_html(self: HTML5Translator, _node: hopedim_node) -> None:
    """Depart hopedim node in HTML output."""
    self.body.append("</span>")


def setup(app: Sphinx) -> dict[str, Any]:
    """Register custom roles and nodes with Sphinx."""
    # Register the roles
    # Stubs incorrectly require Sequence[reference] return type,
    # but docutils roles can return any Node type (see rst-roles.rst)
    roles.register_local_role("hope", hope_role)  # type: ignore[arg-type]
    roles.register_local_role("hopedim", hopedim_role)  # type: ignore[arg-type]

    # Register the node types with their visitors
    app.add_node(
        hope_node,
        html=(visit_hope_html, depart_hope_html),
        latex=(visit_hope_latex, depart_hope_latex),
    )
    app.add_node(
        hopedim_node,
        html=(visit_hopedim_html, depart_hopedim_html),
        latex=(visit_hopedim_latex, depart_hopedim_latex),
    )

    # Add CSS for HTML output
    app.add_css_file("necropolis.css")

    return {
        "version": "0.1",
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
