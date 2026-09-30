# output/ — demonstration & artifact directory

A durable home for **demonstration artifacts** — screenshots, recordings,
exported reports, and other "here's what it looks like / here's what it does"
outputs that are worth keeping and sharing, as distinct from the ephemeral
session scratchpad (`/tmp/...`).

## Why this exists

Demos and visual artifacts kept turning up in the throwaway scratchpad, where
they vanish between sessions and can't be reviewed or shared. This directory is
version-controlled so an artifact captured today is still here — and linkable —
next week.

## Layout

```
output/
  demos/
    <program-or-spec>/      # one folder per program/spec/feature
      NN-<name>.png          # numbered so they sort in narrative order
```

## Conventions

- **Number for order** (`01-login`, `02-shell`, …) so a folder reads as a story.
- **Name for content**, not date (git already has the date).
- **Curate, don't dump** — keep the artifacts that demonstrate something; delete
  superseded ones. This is a showcase, not a log.
- **Scaling:** keep each artifact within the repo-hygiene 1 MiB budget. The
  repository does not use Git LFS; publish heavier artifacts as sha256-pinned
  `ci-data` release assets or keep them on the babylon-data drive.

## Current contents

- `demos/spec-113-living-map/` — Program 16 "The Living Map" cockpit (the
  Guix-Installer UI): login, the map-first game shell across lens modes, chrome
  states. Captured 2026-07-11. Note: the map shows only county borders in these
  shots — polity **fills** need a live engine session (the shots are rendered
  against mocked state to exercise the chrome deterministically).
