"""Launcher for the WO-29 directive-hardening snapshot delta.

A FRESH ``ArchiveApp`` is built here (never a re-exported singleton — see
``babylon.tui.app``'s own snapshot launcher for why: ``runpy`` re-executes
this file per snapshot run, but an imported module-level instance would
carry stale mounted state across runs, an order-dependent flake).

The page exercises, in one composed dossier, every hardened path this WO
touches: a baked statblock row whose value is a bracket-laden real string
(``sovereign_id``, an unconstrained ``str``), a real absence block in the
production ``county.md.j2`` shape (empty body, ``"{field} — {remedy}"`` in
the fence arg), a cache-keyed narrative byline with bracket-laden prose, and
a still-uncached (empty-body) cache-keyed narrative — the literal shape the
design canon's own template fragment produces before WO-42 wires the async
narrator writer (``ai/_inbox/tui/20260719archiveinterfacedesign.md`` line
100). Never touches ``babylon.tui.app`` itself — this only *constructs*
``ArchiveApp`` with the ``page=`` it already accepts.
"""

from babylon.tui.app import ArchiveApp

_HARDENING_PAGE = """\
# county/26163 — WO-29 hardening delta

```{statblock} county/26163
population: 1749343
sovereign_id: SOV_USA [contested]
```

```{absence} class_composition — Census(Territory) to attribute class shares
```

```{narrative} cached:847:local-chat
The picket line held, though the tape was [unclear] near the end.
```

```{narrative} cached:900:local-chat
```
"""

app = ArchiveApp(page=_HARDENING_PAGE)

__all__ = ["app"]
