How to wire the reference-data fixed-output derivation
=======================================================

.. note::
   **Status: PLANNED, NOT YET WIRED.** This procedure has one hard
   precondition that has not landed yet — see "Blocked on" below. Until it
   lands, ``flake.nix`` does not (and must not) declare a
   ``packages.reference-data`` output: a fixed-output derivation with a dead
   URL fails every build it touches, and per ADR104 / the T7 installer brief
   we do not ship one until the URL is real.

What this is
------------

The 4.49GB reference database (``data/sqlite/marxist-data-3NF.sqlite``, a
deterministic build product per ADR098) needs to reach players without
inflating the Nix closure players build locally. ADR104's Postgres/data
ruling routes it through the **same signed R2 cache** ``install.sh`` already
trusts (ADR094 D1) — no second trust mechanism — as a Nix **fixed-output
derivation** (FOD): a derivation whose output hash is declared up front, so
Nix verifies the download itself and the build is reproducible regardless of
where the bytes come from.

Blocked on
----------

Runbook C3's PRE-STEP (``ai/_inbox/PROGRAM_v1_0_0_ceremony_runbook.md``):
babylon-data has no public serving domain yet. The BD-run ceremony that
unblocks this doc is: attach a Custom Domain (e.g.
``data.babylon.percypedia.biz``) to the babylon-data R2 bucket. That
ceremony is owner-only — it is not this lane's to perform or fake.

Prerequisites (once the domain lands)
--------------------------------------

- The real serving URL for ``marxist-data-3NF.sqlite`` under the new domain.
- The current build's sha256, read **programmatically** from
  ``data-artifacts.yaml`` (``product.sha256``) — never hand-typed (the same
  discipline ``docs/how-to/reference-data-pipeline.rst`` already states for
  the build pipeline). At the time this doc was written that value was::

      f760bab5c63ce879decd72cfe3bf51c569a5a4ba2a4a57e0ccbb5d90f5e6fa42

  Re-read it from ``data-artifacts.yaml`` at wiring time — if the reference
  DB has been rebuilt since, the hash will have moved and this doc's copy is
  stale by design (Immutability of History: this value was correct when
  written, not a live mirror).

Steps
-----

1. Confirm the URL actually serves the file before touching Nix::

       curl -I https://<DATA_DOMAIN>/marxist-data-3NF.sqlite   # expect 200

2. Add the output to ``flake.nix`` (replacing the commented plan already
   there), inside the same ``packages`` set as ``pg-runtime``::

       packages.reference-data = pkgs.fetchurl {
         url    = "https://<DATA_DOMAIN>/marxist-data-3NF.sqlite";
         sha256 = "<product.sha256 from data-artifacts.yaml, current>";
       };

3. Eval-check first (no download, no full build)::

       nix eval .#packages.x86_64-linux.reference-data.drvPath
       nix flake check --no-build

4. Only then build it for real (this DOES fetch 4.49GB — not a "no-build"
   step, run it deliberately, not as part of routine CI)::

       nix build .#reference-data

   A sha256 mismatch fails the build loudly with both hashes printed — that
   is Nix's integrity check firing as designed, not a bug to route around.

5. Regenerate ``nix flake check`` output listings and confirm
   ``packages.<system>.reference-data`` appears alongside ``babylon`` and
   ``pg-runtime``.

What this does *not* cover
--------------------------

Consuming the built artifact — copying it into
``~/.local/share/babylon/data/`` on install, or the game reading it from
there — is a separate, later unit (the game-managed-cluster / first-run
provisioning code named in ADR104's consequences, gated on the keel DSN
seam, ``src/`` scope). This doc only covers landing the FOD *output* once
the URL exists.

See also
--------

- ``docs/how-to/reference-data-pipeline.rst`` — how the DB itself is built
  and re-hashed (the source of the sha256 this doc consumes).
- ``ai/decisions/ADR104_nix_bootstrap_installer.yaml`` — the ruling this
  procedure implements.
- ``ai/_inbox/PROGRAM_v1_0_0_ceremony_runbook.md`` (Runbook C2/C3) — the
  owner-run ceremonies this doc is blocked on.
