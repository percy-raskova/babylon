# Configuration file for the Sphinx documentation builder.
# https://www.sphinx-doc.org/en/master/usage/configuration.html

import os
import sys

# Add source directory to path for autodoc
sys.path.insert(0, os.path.abspath("../src"))

# Add _ext directory for custom extensions
sys.path.insert(0, os.path.abspath("_ext"))

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
    "hope_roles",  # Necropolis Codex :hope: role
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
html_static_path = ["_static"]  # Necropolis styling

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

# Suppress known-benign warnings that don't affect documentation quality
# This allows CI to run with -W (warnings as errors) while ignoring noise
suppress_warnings = [
    # Duplicate object descriptions from Pydantic models re-exported in __init__.py
    # These occur because autosummary documents both the original and re-exported location
    "autodoc",
    "autodoc.import_object",
    # Reference warnings (intersphinx, cross-refs)
    "ref.python",
    "ref.ref",
    # MyST cross-reference warnings
    "myst.xref_missing",
    # Docutils inline markup warnings (usually from docstrings with special chars)
    "docutils",
]

# Mermaid configuration (sphinxcontrib-mermaid)
# See: https://github.com/mgaitan/sphinxcontrib-mermaid
mermaid_version = "11.4.1"  # Latest stable from jsdelivr CDN
mermaid_init_js = """
mermaid.initialize({
    startOnLoad: true,
    theme: 'neutral',
    themeVariables: {
        primaryColor: '#4A1818',
        primaryTextColor: '#3D3A36',
        primaryBorderColor: '#6B4A3A',
        lineColor: '#6B4A3A',
        secondaryColor: '#D4C9B8',
        tertiaryColor: '#8B7B6B'
    }
});
"""

# HTML output: use 'raw' for browser-side JavaScript rendering (fast, no mmdc needed)
# LaTeX/PDF output: sphinxcontrib-mermaid automatically uses mmdc for LaTeX regardless
mermaid_output_format = "raw"

# PDF/LaTeX builds require mermaid-cli (mmdc) with Puppeteer
# Install: npm install -g @mermaid-js/mermaid-cli
# Then: npx puppeteer browsers install chrome-headless-shell
mermaid_cmd = "mmdc"
mermaid_cmd_shell = True
mermaid_params = [
    "-p",
    "puppeteer-config.json",  # Puppeteer config for headless Chrome
    "--theme",
    "neutral",
    "--backgroundColor",
    "transparent",
    "--width",
    "800",
]
# Enable verbose output to debug mmdc issues
mermaid_verbose = True

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
% NECROPOLIS CODEX THEME - The Machinery of Death Made Visible
% "Leaked documents from the collapsing apparatus" - institutional, archival,
% stained with historical violence. Hope appears only where organization is discussed.
% See docs/concepts/aesthetics.rst
% ============================================================================

% Better typography - subtle kerning and spacing improvements
\usepackage{microtype}

% Fix overfull hbox warnings - allow flexible line breaking
% Long function names in API docs cause strict width violations
\sloppy
\emergencystretch=2em

% Fix fancyhdr headheight warning
\setlength{\headheight}{24pt}
\addtolength{\topmargin}{-12pt}

% ============================================================================
% COLOR DEFINITIONS - Necropolis Codex Palette
% The grim machinery of death made visible. Institutional archive colors.
% See: /home/user/.claude/plans/splendid-inventing-sutton.md
% ============================================================================

% PRIMARY COLORS (The Machinery of Death)
\definecolor{AbsoluteVoid}{HTML}{0A0707}    % Cover top - deepest darkness, death camp night
\definecolor{DriedBlood}{HTML}{4A1818}      % Chapter headings - oxidized, historical violence
\definecolor{Rust}{HTML}{6B4A3A}            % Section headings - decaying infrastructure
\definecolor{Bone}{HTML}{8B7B6B}            % Grave markers, monuments - cover title text
\definecolor{AshPaper}{HTML}{D4C9B8}        % Page backgrounds - cold institutional archive
\definecolor{AshInk}{HTML}{3D3A36}          % Body text - charcoal, readable but grim

% ACCENT COLORS (Buried Hope - Conditional on Organization)
\definecolor{BuriedHope}{HTML}{1A3A1A}      % Cover line - barely visible seed underground
\definecolor{ForestDim}{HTML}{2A6B2A}       % Section headings in revolutionary content
\definecolor{PhosphorGreen}{HTML}{39FF14}   % Key phrases only - "Organization is the difference"

% LEGACY COLORS (For compatibility during transition)
\definecolor{ThermalWarning}{HTML}{4A1818}  % Alias to DriedBlood for existing refs
\definecolor{TheChassis}{HTML}{6B4A3A}      % Alias to Rust
\definecolor{TheDust}{HTML}{8B7B6B}         % Alias to Bone

% ============================================================================
% PAGE COLORS - Cold institutional archive aesthetic
% Documents from the apparatus - under fluorescent light, stained with history
% ============================================================================
\definecolor{BunkerPaper}{HTML}{D4C9B8}     % Alias to AshPaper for compatibility
\definecolor{BunkerInk}{HTML}{3D3A36}       % Alias to AshInk for compatibility

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
% CUSTOM COVER PAGE - Necropolis Codex
% Black-to-Rust gradient, institutional archive aesthetic
% Hope appears only in the mantra - "The only escape is revolutionary organization."
% ============================================================================
\makeatletter
\renewcommand{\sphinxmaketitle}{%
  \begin{titlepage}%
    % Full-page TikZ gradient background: AbsoluteVoid at top → DriedBlood at bottom
    \begin{tikzpicture}[remember picture,overlay]
      \fill[top color=AbsoluteVoid, bottom color=DriedBlood]
        (current page.north west) rectangle (current page.south east);
    \end{tikzpicture}%
    % Title content on gradient background
    \vspace*{3cm}%
    \begin{center}%
      % Main title in Bone (grave marker, monument)
      {\fontsize{48}{56}\selectfont\bfseries\color{Bone}\@title\par}%
      \vspace{1.8cm}%
      % Subtitle in AshInk (documents of the system)
      {\Large\color{AshInk}A Simulation of Imperial Collapse\par}%
      \vspace{0.6cm}%
      {\large\color{AshInk}The Necropolitical Prison-Plantation\par}%
      \vspace{3cm}%
      % Decorative line - BuriedHope (thin, barely visible - the seed underground)
      {\color{BuriedHope}\rule{0.6\textwidth}{0.3pt}\par}%
      \vspace{1.5cm}%
      % The Mantra - ForestDim italic (conditional hope, only for those who read)
      {\large\itshape\color{ForestDim}``The only escape is revolutionary organization.''\par}%
      \vspace{3cm}%
      % Author in Bone
      {\Large\color{Bone}\@author\par}%
      \vspace{1.2cm}%
      % Version in Bone (dimmer)
      {\normalsize\color{Bone!70}Version \py@release\par}%
    \end{center}%
  \end{titlepage}%
  % Reset to AshPaper background for all content pages
  \pagecolor{AshPaper}%
  \clearpage%
}
\makeatother

% ============================================================================
% HYPERLINK STYLING - Necropolis Navigation
% Internal paths through the apparatus (Rust), external connections to knowledge (Bone)
% ============================================================================
\hypersetup{
    colorlinks=true,
    % Internal links (linkcolor): Rust - hot paths through the decaying apparatus
    linkcolor=Rust,
    % External URLs (urlcolor): Bone - connections to outside knowledge
    urlcolor=Bone,
    % Citations: AshInk - supporting material
    citecolor=AshInk,
    % PDF bookmarks and metadata
    bookmarks=true,
    bookmarksnumbered=true,
    bookmarksopen=true,
    bookmarksopenlevel=2,
    pdfstartview=FitH,
}

% ============================================================================
% HEADING COLORS - Necropolis Codex Hierarchy
% DriedBlood (chapters) → Rust (sections) → AshInk (subsections)
% Historical violence burns into memory, decaying infrastructure guides navigation
% ============================================================================
\usepackage{sectsty}
\chapterfont{\color{DriedBlood}}        % Historical violence - burns into memory
\sectionfont{\color{Rust}}              % Decaying infrastructure - navigating the apparatus
\subsectionfont{\color{AshInk}}         % The fine print - details of the machinery

% ============================================================================
% TABLE OF CONTENTS - Same hierarchical palette
% ============================================================================
\usepackage[titles]{tocloft}
\renewcommand{\cftchapfont}{\bfseries\color{DriedBlood}}
\renewcommand{\cftsecfont}{\color{Rust}}
\renewcommand{\cftsubsecfont}{\color{AshInk}}
\renewcommand{\cftchappagefont}{\bfseries\color{Bone}}
\renewcommand{\cftsecpagefont}{\color{Bone}}
\renewcommand{\cftsubsecpagefont}{\color{Bone!70}}

% ============================================================================
% FANCY HEADERS - Necropolis archive aesthetic
% ============================================================================
\usepackage{fancyhdr}
\pagestyle{fancy}
\fancyhf{}
\fancyhead[LE,RO]{\color{Bone}\thepage}
\fancyhead[RE]{\color{Rust}\nouppercase{\leftmark}}
\fancyhead[LO]{\color{Rust}\nouppercase{\rightmark}}
\renewcommand{\headrulewidth}{0.4pt}
\renewcommand{\headrule}{\hbox to\headwidth{%
    \color{Bone!30}\leaders\hrule height \headrulewidth\hfill}}

% Admonition styling
\usepackage{tcolorbox}
\tcbuselibrary{skins,breakable}

% Custom title page elements
\newcommand{\babylonsubtitle}[1]{%
    \vspace{0.5em}%
    {\Large\color{Bone}#1}%
}

% ============================================================================
% REVOLUTIONARY HOPE STYLING - Conditional hope for content about organization
% Use \hope{text} for PhosphorGreen text - only for:
% - "Organization is the difference"
% - P(S|R) > P(S|A) / Warsaw Ghetto Dynamic
% - Solidarity transmission, critical window, enforcer radicalization
% ============================================================================
\newcommand{\hope}[1]{{\color{PhosphorGreen}#1}}
\newcommand{\hopedim}[1]{{\color{ForestDim}#1}}
""",
    # Chapter heading style - Bjornstrup is professional book-like
    "fncychap": r"\usepackage[Bjornstrup]{fncychap}",
    # Sphinx-specific styling (matches Necropolis Codex preamble colors)
    # TitleColor: DriedBlood (74,24,24) - historical violence
    # InnerLinkColor: Rust (107,74,58) - hot paths through apparatus
    # OuterLinkColor: Bone (139,123,107) - connections to external knowledge
    "sphinxsetup": r"""
        TitleColor={RGB}{74,24,24},
        InnerLinkColor={RGB}{107,74,58},
        OuterLinkColor={RGB}{139,123,107},
    """,
    # Index formatting
    "printindex": r"\footnotesize\raggedright\printindex",
}

# LaTeX engine (xelatex has native Unicode support for Greek letters, arrows, etc.)
latex_engine = "xelatex"

# Use makeindex instead of xindy to avoid encoding issues
latex_use_xindy = False


# -- Custom RST Roles for Necropolis Codex -----------------------------------
# The :hope: and :hopedim: roles are defined in _ext/hope_roles.py
# They render as \hope{} and \hopedim{} in LaTeX (PhosphorGreen/ForestDim)
# See that module for usage instructions.
