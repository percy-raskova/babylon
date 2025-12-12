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
        "Persephone Raskova",
        "manual",
    ),
    # 2. Meta-commentary book (design philosophy, theoretical foundations)
    (
        "commentary/index",
        "babylon-commentary.tex",
        "Babylon: The Fall of America\\\\{\\large Design Philosophy \\& Theoretical Foundations}",
        "Persephone Raskova",
        "manual",
    ),
]

# LaTeX styling for professional book output
# "Bunker Constructivism" aesthetic from docs/concepts/aesthetics.rst
latex_elements = {
    "papersize": "letterpaper",
    "pointsize": "11pt",
    # Book-style layout
    "extraclassoptions": "openany,twoside",
    # CRITICAL: Pass options to xcolor BEFORE Sphinx loads it
    # This fixes "Option clash for package xcolor" errors
    "passoptionstopackages": r"\PassOptionsToPackage{svgnames,dvipsnames,table}{xcolor}",
    # Professional fonts via fontspec (requires xelatex)
    # DejaVu Sans Mono has better Unicode coverage (box-drawing chars, etc.)
    "fontpkg": r"""
\usepackage{fontspec}
\setmainfont{TeX Gyre Termes}
\setsansfont{TeX Gyre Heros}
\setmonofont{DejaVu Sans Mono}
""",
    # Custom preamble: Bunker Constructivism Professional Book Edition
    "preamble": r"""
% ============================================================================
% BUNKER CONSTRUCTIVISM THEME - Professional Book Edition
% "Damp Basement Cyberinsurgency" - CRT aesthetic for PDF output
% ============================================================================

% Better typography - subtle kerning and spacing improvements
\usepackage{microtype}

% Fix fancyhdr headheight warning
\setlength{\headheight}{24pt}
\addtolength{\topmargin}{-12pt}

% ============================================================================
% COLOR DEFINITIONS - Bunker Constructivism Palette
% Colors are LIGHT EMISSIONS in a dark room, not paint on surfaces.
% The UI is a CRT monitor in a concrete bunker. See docs/concepts/aesthetics.rst
% ============================================================================

% PRIMARY COLORS (Light Emissions)
\definecolor{PhosphorBurn}{HTML}{D40000}    % The Laser - alerts, critical thresholds, rupture
                                            % "When red appears, it burns" - chapters, titles
\definecolor{WetConcrete}{HTML}{1A1A1A}     % The Void - the Room itself, darkness is information
\definecolor{TerminalGlare}{HTML}{F5F5F5}   % High intensity text (60-80% opacity in UI)
\definecolor{ExposedCircuitry}{HTML}{FFD700} % The Circuit - truth data, verified connections,
                                            % SOLIDARITY EDGES - the real infrastructure

% SECONDARY COLORS
\definecolor{ThermalWarning}{HTML}{8B0000}  % Overheating indicators, system stress, hot paths
\definecolor{TheChassis}{HTML}{404040}      % Inactive panels, server racks, cold metal
\definecolor{TheDust}{HTML}{C0C0C0}         % Terminal prompts, secondary text, the dust that settles

% ============================================================================
% COVER PAGE COLORS - Royal purple void with phosphor green CRT text
% ============================================================================
\definecolor{RoyalVoid}{HTML}{1E1033}       % Deep royal purple - the command bunker
\definecolor{PhosphorGreen}{HTML}{39FF14}   % Neon CRT green - terminal awakening
\definecolor{PhosphorGreenDim}{HTML}{2AAE0F} % Dimmer green for subtitles

% ============================================================================
% PAGE COLORS - Quasi-dark mode for eye comfort
% Not harsh white, not full dark - the amber glow of aged paper in bunker light
% ============================================================================
\definecolor{BunkerPaper}{HTML}{F5F0E8}     % Warm cream - aged paper under dim light
\definecolor{BunkerInk}{HTML}{2D2A26}       % Warm dark gray - softer than pure black

% ============================================================================
% PAGE STYLING - Quasi-dark mode for comfortable reading
% ============================================================================
\pagecolor{BunkerPaper}                     % Warm cream background on all pages
\color{BunkerInk}                           % Warm dark gray body text

% Enhanced PDF bookmarks (better than hyperref alone)
\usepackage{bookmark}

% TikZ for cover page graphics (must be loaded BEFORE sphinxmaketitle definition)
\usepackage{tikz}

% ============================================================================
% CUSTOM COVER PAGE - Royal purple void with phosphor green terminal text
% Overrides Sphinx's default maketitle
% ============================================================================
\makeatletter
\renewcommand{\sphinxmaketitle}{%
  % Set purple background for title page
  \pagecolor{RoyalVoid}%
  \begin{titlepage}%
    % Title content on purple background
    \vspace*{4cm}%
    \begin{center}%
      % Main title in phosphor green
      {\fontsize{48}{56}\selectfont\bfseries\color{PhosphorGreen}\@title\par}%
      \vspace{2cm}%
      % Subtitle/tagline
      {\Large\color{PhosphorGreenDim}A Geopolitical Simulation Engine\par}%
      \vspace{0.8cm}%
      {\large\color{PhosphorGreenDim}Modeling Imperial Collapse Through Material Conditions\par}%
      \vspace{4cm}%
      % Decorative line
      {\color{PhosphorGreen}\rule{0.5\textwidth}{2pt}\par}%
      \vspace{3cm}%
      % Author
      {\Large\color{PhosphorGreenDim}\@author\par}%
      \vspace{1.5cm}%
      % Version/date
      {\normalsize\color{TheDust}Version \py@release\par}%
    \end{center}%
  \end{titlepage}%
  % Reset to cream background for all content pages
  \pagecolor{BunkerPaper}%
  \clearpage%
}
\makeatother

% ============================================================================
% HYPERLINK STYLING - Thematic Color Assignment
% ============================================================================
\hypersetup{
    colorlinks=true,
    % Internal links (linkcolor): ThermalWarning - "hot paths" through the document
    linkcolor=ThermalWarning,
    % External URLs (urlcolor): ExposedCircuitry - "solidarity edges to external truth"
    % Gold represents verified connections to outside knowledge infrastructure
    urlcolor=ExposedCircuitry,
    % Citations: TheChassis - supporting material, inactive reference
    citecolor=TheChassis,
    % PDF bookmarks and metadata
    bookmarks=true,
    bookmarksnumbered=true,
    bookmarksopen=true,
    bookmarksopenlevel=2,
    pdfstartview=FitH,
}

% ============================================================================
% HEADING COLORS - Hierarchy through light intensity
% PhosphorBurn (chapters) → ThermalWarning (sections) → TheChassis (subsections)
% ============================================================================
\usepackage{sectsty}
\chapterfont{\color{PhosphorBurn}}      % Critical thresholds - burns into attention
\sectionfont{\color{ThermalWarning}}    % System stress - navigating deeper
\subsectionfont{\color{TheChassis}}     % Inactive panels - lower intensity

% ============================================================================
% TABLE OF CONTENTS - Same color hierarchy
% ============================================================================
\usepackage[titles]{tocloft}
\renewcommand{\cftchapfont}{\bfseries\color{PhosphorBurn}}
\renewcommand{\cftsecfont}{\color{ThermalWarning}}
\renewcommand{\cftsubsecfont}{\color{TheChassis}}
\renewcommand{\cftchappagefont}{\bfseries\color{TheChassis}}
\renewcommand{\cftsecpagefont}{\color{TheChassis}}
\renewcommand{\cftsubsecpagefont}{\color{TheDust}}

% ============================================================================
% FANCY HEADERS - Book feel with softer colors
% ============================================================================
\usepackage{fancyhdr}
\pagestyle{fancy}
\fancyhf{}
\fancyhead[LE,RO]{\color{TheChassis}\thepage}
\fancyhead[RE]{\color{TheChassis}\nouppercase{\leftmark}}
\fancyhead[LO]{\color{TheChassis}\nouppercase{\rightmark}}
\renewcommand{\headrulewidth}{0.4pt}
\renewcommand{\headrule}{\hbox to\headwidth{%
    \color{TheChassis!50}\leaders\hrule height \headrulewidth\hfill}}

% Admonition styling
\usepackage{tcolorbox}
\tcbuselibrary{skins,breakable}

% Custom title page elements
\newcommand{\babylonsubtitle}[1]{%
    \vspace{0.5em}%
    {\Large\color{TheDust}#1}%
}
""",
    # Chapter heading style - Bjornstrup is professional book-like
    "fncychap": r"\usepackage[Bjornstrup]{fncychap}",
    # Sphinx-specific styling (matches preamble colors)
    # TitleColor: PhosphorBurn (212,0,0) - critical thresholds
    # InnerLinkColor: ThermalWarning (139,0,0) - hot paths
    # OuterLinkColor: ExposedCircuitry (255,215,0) - solidarity edges to external truth
    "sphinxsetup": r"""
        TitleColor={RGB}{212,0,0},
        InnerLinkColor={RGB}{139,0,0},
        OuterLinkColor={RGB}{255,215,0},
    """,
    # Index formatting
    "printindex": r"\footnotesize\raggedright\printindex",
}

# LaTeX engine (xelatex has native Unicode support for Greek letters, arrows, etc.)
latex_engine = "xelatex"

# Use makeindex instead of xindy to avoid encoding issues
latex_use_xindy = False
