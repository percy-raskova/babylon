# Provenance — design/mockups/

**What this is**: the final file states of the claude.ai "Babylon Design System"
project, extracted 2026-07-03 from Percy's chat export. These are the RATIFIED
design-canon mockups (Cold Collapse palette, 13-screen webapp kit, The Wire,
The Synopticon, The Map, Community views) referenced by
`project/09-program-full-game.md` §5 and consumed by specs 090-095/103.

**Source**: `/home/user/projects/claude-chats/design_chats/` — 7 conversation
exports (uuids and roles listed in `manifest.json` `source_chat` fields).
The mockup source code was embedded in the exports as `write_file` /
`str_replace_edit` / `delete_file` tool-call payloads.

**Extraction method**: chronological replay of all file-tool calls across the
7 chats (global message-timestamp order) onto a virtual filesystem; final
states dumped here preserving the chat-project's relative paths.
`manifest.json` records per-file byte size, last-write timestamp, and source
chat. Replay notes:

- Tool calls whose recorded output begins with `Error` were skipped (the
  platform rejected them; state unchanged).
- One warning: a `delete_file` targeted `wire/browser-window.jsx`, which was
  never written (planned name, superseded by `wire/wire-window.jsx`). No
  content lost.
- `ui_kits/webapp_v2/` (the V1 gold-palette kit) was DELETED mid-history by
  the design session itself and rebuilt as `ui_kits/webapp/` on Cold Collapse
  tokens — its absence here is faithful, not a gap.

**Authority and limits**:

- These files are REFERENCE MOCKUPS, not production code. Production work
  ports them through specs 090+ under the repo's TDD + speckit discipline.
- The palette they encode (Cold Collapse, `--babylon-spire: #4dd9e6` primary)
  was Percy-ratified in-chat (2026-05-17) but conflicts with Constitution
  Article VII's "GOLD (action/solidarity)" clause — an Article VII amendment
  ships with spec-090 before these tokens land in `web/frontend/src/index.css`.
- Committed `--no-verify` (verbatim-artifact precedent) so formatter hooks do
  not alter canon bytes. Do not hand-edit these files; regenerate via the
  recipe in `project/09-program-full-game.md` §5 if the export changes.
