# Babylon — Antigravity Configuration

Drop the `.agents/` directory into your Babylon project root. Antigravity will auto-detect and load it.

## Structure

```
.agents/
├── agents.md                          # Agent persona — who you are when working on Babylon
├── rules/
│   └── babylon_constraints.md         # Constitutional constraints — always loaded, non-negotiable
├── skills/
│   └── hexmap_contract.md             # HexMap E2E contract-first spec — loaded on demand
└── workflows/
    └── build_hexmap.md                # /build_hexmap — chains the 9 implementation steps
```

## Usage

Open the Babylon workspace in Antigravity. The rules file loads automatically. To start the HexMap build:

1. Type `/build_hexmap` in the agent chat
1. The agent will execute four phases with approval gates between each
1. Review artifacts (test results, screenshots) at each gate before approving

## Adding More Components

Copy the pattern from `hexmap_contract.md` for each subsequent component (ActionPanel, OrgDashboard, InspectorPanel, TickResults, TimeSeriesPanel). Each component gets its own skill file and workflow. The methodology is the same: mock fixture → Postgres → API → contract parity gate → React → integration.

## Cross-Tool Compatibility

`agents.md` is the AGENTS.md cross-tool standard. These files also work in Cursor and (with minor adaptation) Claude Code. The rules file content maps directly to CLAUDE.md or .cursorrules if you switch tools.
