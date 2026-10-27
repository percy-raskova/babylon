# National SQLite qualification record — 2026-10-27 (PER-354 Task 13)

Tracked pointer so the "built and qualified" claim is retrievable in-tree.
Full per-rung tables live in the Task 13 report (`.superpowers/sdd/`, gitignored);
measured vectors live in scratch (`/media/user/data/qualification-scratch/ladder-official-2`).

- Qualifying SHA: `43e913511` (contract v2). Interim 60 s advance bar, 30 s target
  as machine-readable debt (`meets_targets=false` on every rung).
- Contract digest: `c68627b4080bef4c45bd02614254f8620605eafe05cb46b7108493a3ad26eb0b`.
- Ladder: controls GREEN; smoke/window/aging advance medians 41.1 / 42.5 / 39.0 s
  (max 46.7 s) — GREEN vs interim 60 s, RED vs 30 s target. Judgment ~76% of each
  advance; encode ~8 s; commit ~2 s.
- Cold open ~0.25 s, all queries sub-ms to ~1 ms, bounded reads clean, sampling clean.
- Memory peak: 3.97 / 4.64 / 4.95 GB vs 4.0 GB (smoke GREEN, window/aging RED).
- Growth charged: 33.5–39.5 MB/period vs 10 MB (RED); total 12.83 GB vs 3.25 GB
  (RED). 92.3% of charged bytes unreachable in-horizon; physical store net
  +162 MB over 325 periods. Stored-share attribution (measured, fix round 2):
  WorldRegisters restart package 85.15% of charge at 0.969 stored/decoded;
  StableGraph 14.78% at 0.153. Target for PER-360: restart-package encoding first.

## Head delta (this branch at merge)

Commits after `43e913511` add no measured-behavior change to the ladder path:
`280915ff6` (bounded-read honestly n/a, evidence write-once, attribution fields),
`b532fb251` (guard scoped to evidence files), P9a-1 (`a65ec8d5a` decoders + v2
identity, `88d3d94fb` presence binding: +302 bytes/period = 1 flag + 269 identity
+ 32 hash, one content entry). No rung was re-run at head (timebox R-14);
the cold-reopen acceptance test (2-period, 241.6 s) exercises `run_national`
end to end at head. Re-run, don't re-evaluate, to extend attribution past 2 periods.
