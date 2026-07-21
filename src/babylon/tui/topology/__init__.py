"""Terminal renderers for The Archive's Lane T topology surfaces.

Each module here turns a pure ordering from
:mod:`babylon.projection.topology` (or, for a baked page, a fence body
encoding one) into deterministic text art — never a force-directed layout
(S9 canon, ``ai/_inbox/tui/20260719archiveinterfacedesign.md``). Dispatch
from a page's fenced directive lives in :mod:`babylon.tui.directives`
(``BabylonFence``); this package holds the rendering + fence-body-parsing
logic each directive method delegates to.
"""
