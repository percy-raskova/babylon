"""The Archive client's Python side (Program 24 → the M7 cutover).

Since ``test(cutover)!: retire Textual Archive lane`` (ADR150, Amendment
AC) the terminal client is the in-tree Rust/Ratatui client (``rust/``,
shipped as the ``babylon_tui`` extension in the default install). What
remains in THIS package is the textual-free Python half of that client:

- :mod:`babylon.tui.host` — ``RustClientHost``, the FFI seam every
  client call crosses;
- :mod:`babylon.tui.contract` — the durable client contract
  (``CampaignHandle`` & friends, the WO-37 structural seams);
- shared read-path logic both the host and the game layer consume
  (chronicle, salience, watchlist, peek, nav, router, campaign menu,
  trade dossier, backlinks, the wikilink grammar, the ksbc palette
  constants).

The package consumes ``babylon.projection`` view-models and baked vault
pages only — it never imports the engine, persistence, or the legacy web
stack (enforced by import-linter).
"""
