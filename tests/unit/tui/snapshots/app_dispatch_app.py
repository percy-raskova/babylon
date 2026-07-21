"""Snapshot launcher for WO-45: one page, a statblock per Lane P kind.

Every fence below defers to the app's kind-dispatch provider (no baked
body), so the golden proves the full composition renders live rows for
all ten kinds on one page — plus one deliberate unknown for the absence
path.
"""

from __future__ import annotations

from babylon.tui.app import ArchiveApp
from babylon.tui.dispatch import fixture_known_entities

_SECTIONS = "\n\n".join(
    f"```{{statblock}} {subject}\n```" for subject in sorted(fixture_known_entities())
)

ALL_KINDS_PAGE = f"""\
# The Archive — every kind, one page (WO-45)

{_SECTIONS}

```{{statblock}} galaxy/andromeda
```
"""

app = ArchiveApp(page=ALL_KINDS_PAGE)

if __name__ == "__main__":
    app.run()
