"""The Archive terminal client (Program 24) — a wiki in a terminal.

Textual application implementing the Archive: every entity the
organization knows is a page, relations are wikilinks, and playing the
game is reading, navigating, and acting on documents. The client consumes
``babylon.projection`` view-models and baked vault pages only — it never
imports the engine, persistence, or the legacy web stack (enforced by
import-linter).

Stack pins and rendering rules are ADR099: fenced-directive-only markdown
(one ``MarkdownFence`` subclass dispatching on ``token.info``), a ~30-line
wikilink inline rule emitting ``babylon://`` hrefs, the section-9b ksbc
theme tokens, and the pytest-textual-snapshot golden lane.
"""
