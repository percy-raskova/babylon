"""The public-surface baseline sentinel — sixth discovered error class.

A scoped, per-task test run cannot see repo-wide public-surface baselines: a
package's ``__all__`` can gain a symbol while the frozenset baseline test
(``EXPECTED_*_PUBLIC`` in ``tests/unit/test_public_import_surface.py``) that
pins it is left unedited, and no scoped test run reds — only the full gate's
``test_all_matches_baseline`` catches the drift. Live specimen: U2.3 added
``"CapitalVolumeIIIDefines"`` to ``babylon.config.defines.__all__`` without a
matching baseline edit.

This sentinel closes the blind spot **statically** (AST, no import, no test
run): it compares a package's declared ``__all__`` against its pinned baseline
frozenset and reports drift either direction — a symbol added-without-baseline
or a baseline symbol dropped-but-still-pinned.

Layer 0.5 (same rank as :mod:`babylon.config`): imports nothing above
:mod:`babylon.models`. The declared registry is pure data; the check reads
both the package ``__init__.py`` and the baseline test file statically.
"""
