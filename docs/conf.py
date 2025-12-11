# Configuration file for the Sphinx documentation builder.
# https://www.sphinx-doc.org/en/master/usage/configuration.html

import os
import sys

# Add source directory to path for autodoc
sys.path.insert(0, os.path.abspath("../src"))

# -- Project information -----------------------------------------------------
project = "Babylon"
copyright = "2025, Babylon Project Contributors"
author = "Babylon Project Contributors"

# The full version, including alpha/beta/rc tags
release = "0.2.0"
version = "0.2"

# -- General configuration ---------------------------------------------------
extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
    "sphinx.ext.intersphinx",
    "sphinx.ext.todo",
    "sphinx.ext.coverage",  # Track documentation coverage
    "sphinx.ext.doctest",  # Run doctest examples
    "sphinx_autodoc_typehints",
    "myst_parser",
    "sphinxcontrib.mermaid",  # Mermaid diagram support
]

# Templates path
templates_path = ["_templates"]

# Patterns to exclude
# Exclude legacy/orphan markdown files that aren't in any toctree
exclude_patterns = [
    "_build",
    "Thumbs.db",
    ".DS_Store",
    # Legacy markdown files not in toctree
    "AESTHETICS.md",
    "AI_COMMS.md",
    "CHANGELOG.md",
    "CHROMA.md",
    "CONFIGURATION.md",
    "CONTEXT_WINDOW.md",
    "ERROR_CODES.md",
    "GUI_PLAN.md",
    "LOGGING.md",
    "OBJECT_TRACKING.md",
    "SEMANTIC_VERSIONING_SPECIFICATION.md",
    "census/census_tool_blueprint.md",
    "census/census_tool_blueprint_v2.md",
    "chroma-troubleshooting.md",
]

# Source file suffixes
source_suffix = {
    ".rst": "restructuredtext",
    ".md": "markdown",
}

# The master toctree document
master_doc = "index"

# -- Options for HTML output -------------------------------------------------
html_theme = "sphinx_rtd_theme"
html_static_path: list[str] = []  # No static files needed

html_theme_options = {
    "navigation_depth": 4,
    "collapse_navigation": False,
    "sticky_navigation": True,
    "includehidden": True,
    "titles_only": False,
    "logo_only": False,
}

# HTML titles for search and breadcrumbs
html_title = "Babylon Documentation"
html_short_title = "Babylon"

# -- Extension configuration -------------------------------------------------

# Autodoc settings
autodoc_default_options = {
    "members": True,
    "member-order": "bysource",
    "special-members": "__init__",
    "undoc-members": True,
    "exclude-members": "__weakref__",
    "show-inheritance": True,
    # Note: inherited-members disabled to prevent Pydantic field duplication warnings
}

# Preserve default argument values in signatures
autodoc_preserve_defaults = True

autodoc_typehints = "description"
autodoc_typehints_format = "short"

# Napoleon settings (for Google/NumPy style docstrings)
napoleon_google_docstring = True
napoleon_numpy_docstring = True
napoleon_include_init_with_doc = True
napoleon_include_private_with_doc = False
napoleon_include_special_with_doc = True
napoleon_use_admonition_for_examples = True
napoleon_use_admonition_for_notes = True
napoleon_use_admonition_for_references = True
napoleon_use_ivar = False
napoleon_use_param = True
napoleon_use_rtype = True
napoleon_attr_annotations = True
napoleon_preprocess_types = True  # Enable type cross-references

# Intersphinx mapping
intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "pydantic": ("https://docs.pydantic.dev/latest/", None),
    "networkx": ("https://networkx.org/documentation/stable/", None),
}

# MyST parser settings
# Full GFM (GitHub Flavored Markdown) support plus extended features
myst_enable_extensions = [
    # Core formatting
    "colon_fence",
    "deflist",
    "fieldlist",
    "replacements",
    "smartquotes",
    "substitution",
    # GFM features
    "strikethrough",  # ~~text~~ support
    "linkify",  # Auto-link URLs
    "tasklist",  # - [ ] checkbox support
    # Extended features
    "attrs_inline",  # {#id .class} inline attributes
    "dollarmath",  # $math$ and $$math$$ support
    "html_admonition",  # HTML-style admonitions
    "html_image",  # HTML-style images
]
myst_heading_anchors = 3  # Generate anchors for h1-h3 headings

# Todo extension
todo_include_todos = True

# Autosummary
autosummary_generate = True
autosummary_imported_members = False  # Prevent documenting re-exported members twice

# Duplicate object description warnings are expected behavior with Pydantic models
# being re-exported in __init__.py files. These don't affect documentation quality.
# The warnings cannot be suppressed with suppress_warnings but don't block the build.

# Mermaid configuration (sphinxcontrib-mermaid v1.2.3)
# See: https://github.com/mgaitan/sphinxcontrib-mermaid
mermaid_version = "11.4.1"  # Latest stable from jsdelivr CDN
mermaid_init_config = {
    "startOnLoad": True,
    "theme": "neutral",  # Options: default, forest, dark, neutral
}

# Enable mermaid fences in MyST markdown files
myst_fence_as_directive = ["mermaid"]

# -- Options for LaTeX/PDF output --------------------------------------------

# 2 PDF books: main documentation + commentary
latex_documents = [
    # 1. Main documentation (tutorials, how-to, concepts, reference, API)
    (
        "docs-pdf-index",
        "babylon-docs.tex",
        "Babylon: The Fall of America",
        "Babylon Development Team",
        "manual",
    ),
    # 2. Meta-commentary book (design philosophy, theoretical foundations)
    (
        "commentary/index",
        "babylon-commentary.tex",
        "Babylon: Design Philosophy \\& Theoretical Foundations",
        "Babylon Development Team",
        "manual",
    ),
]

# LaTeX styling for professional output
latex_elements = {
    "papersize": "letterpaper",
    "pointsize": "11pt",
    # Custom preamble for typography
    "preamble": r"""
\usepackage{charter}
\usepackage[defaultsans]{lato}
\usepackage{inconsolata}
""",
    # Chapter heading style
    "fncychap": r"\usepackage[Bjornstrup]{fncychap}",
    # Index formatting
    "printindex": r"\footnotesize\raggedright\printindex",
}

# LaTeX engine (xelatex supports more fonts, pdflatex is more compatible)
latex_engine = "pdflatex"
