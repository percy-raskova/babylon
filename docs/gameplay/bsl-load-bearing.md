# BSL/BSCN must be load-bearing, not decorative — 2026-10-25

BSL/BSCN is Babylon's Clausewitz: the exe is generic physics (hashing,
chunks, ticks, conservation, default-deny execution); **all laws live in
content**. If the engine can play our game with the content deleted, the
wiring has failed. Every hardcoded threshold, faction check, and magic
number in Rust is a vote that BSL is a mascot — treat each as a defect
with a number on it.

## The three proofs (acceptance-grade)

1. **Swap test (Task 12 acceptance).** `michigan-regional-v6` and
   `authored-graph-v1` run on the same binary and produce different
   games with zero Rust deltas. Total-conversion equivalence is the
   Clausewitz bar.
2. **Refusal test (loader gates).** Unknown rule IDs, unconsumed dials,
   unlisted transition pairs fail load loudly — witnessed against
   HOI4's 6 phantom keys, Stellaris's 278 unauthored dials, Civ 6's
   dangling `DEAL_ITEM_TECHNOLOGY`. A cute interpreter accepts
   everything; a load-bearing one has opinions.
3. **Deletion test (standing review question).** For every mechanic PR:
   "why isn't this in content?" Numeric literals in mechanic code,
   content-shaped conditionals in Rust, and "temporary" hardcodes are
   BSL being carried.

## Why it matters beyond architecture

Moddability is the loyalty engine. Players skip work for games they
co-own — games where they feel creativity and participation, not just
consumption. A truly load-bearing BSL means players (and modders) can
build scenarios, factions, and histories for a fraction of the tokens
the core cost to make. Ownership converts players into stakeholders;
stakeholders show up. The audience is built into the architecture, not
bolted on after.
