# Babylon game assets — interface SFX suite

Ready-to-roll **General MIDI** interface sounds for the Babylon terminal client:
39 sounds in 5 families, generated deterministically from a single data file.

**License: CC0-1.0** (`LICENSE` in this directory) — the sounds, the manifest and
the generator are dedicated to the public domain. Reuse them anywhere, for anything.
(The wider repository currently declares no license; this directory carries its own.)

## Layout

```
sfx/
  manifest.toml     ← the source of truth: every note, bend and CC, as data
  generate_sfx.py   ← pure-function renderer: manifest → .mid (byte-identical)
  ui/              10  menu micro-sounds (move, select, back, deny, open, close, tab,
                       hover, toggle on/off)
  state/            8  simulation state (tick_advance, save/load/fault, autosave,
                       order_committed, game_start/quit)
  alert/            6  notification ladder (info → favorable → warning → tritone klaxon,
                       event minor/major)
  stinger/         10  dialectical punctuation (rupture, solidarity + its dark mirror
                       false_solidarity, atomization, repression, imperial_rent,
                       market_correction, election, policy pass/fail)
  endgame/          5  one terminal stinger per canonical outcome
```

The suite passed a three-lens adversarial critique (thematic power, coverage,
in-UI usability); both arms of the bifurcation are sounded, pitch-bend gestures
carry a declared ±12-semitone RPN range, and the whole set was re-audited for
loudness and MIDI integrity after the fix round.

Each sound's `concept` (why it sounds the way it does) and `trigger_hint` (the
engine `EventType` / system it punctuates) live in `manifest.toml` — that file is
the integration guide.

## Sonic identity

Follows `ai/epochs/epoch3/music-system.yaml`: root note **E**; the Phrygian ♭2
(E–F) is denial; the tritone **E–B♭ is the crisis signal**; minor→major resolution
is reserved for revolutionary outcomes; harmony is solidarity, unison is conformity;
CC93 chorus = solidarity, CC94 detune = atomization, CC71 resonance = repression.
`game_start` and `stinger_imperial_rent` quote the Φ theme's D–A–D–F motif.

## Regenerate / verify

```sh
mise run midi:generate-sfx        # manifest.toml → 32 .mid files (deterministic)
mise run test:q -- tests/unit/assets/test_sfx_assets.py   # byte-identity contract
```

Rendering is a pure function of the manifest: same manifest bytes → same `.mid`
bytes, pinned by `tests/unit/assets/test_sfx_assets.py`. Edit `manifest.toml`,
regenerate, commit both.

## Audition / render

```sh
mise run midi:play -- src/assets/sfx/alert/alert_critical.mid       # hear one
for f in src/assets/sfx/*/*.mid; do mise run midi:play -- "$f"; done  # hear all
mise run midi:to-ogg -- src/assets/sfx/ui/ui_select.mid             # game-format render
```

**Recommended synth gain: 0.45** (e.g. `fluidsynth -g 0.45` with FluidR3_GM).
The suite is mixed hot — at gain 0.45 the largest stingers peak at −0.8…−4 dBFS
with **zero clipped samples**, verified computationally across all 39 sounds
(the revolutionary-victory orchestra hit is the suite's absolute peak and clears
full scale up to gain 0.47). Bell and reverb tails ring past the notated end by
design; every note-off is present (integrity-audited: no stuck notes, all pitch
bends reset). Mix priority between concurrently-firing sounds is the client
mixer's job — assets ship full-scale.

Every `.mid` re-asserts its own channel state (program, volume, expression,
reverb, chorus, pan, bend reset) at tick 0, so files are safe to fire in any
order on a shared synth.
