#!/bin/sh
# Materialize a metadata-equivalent stub of the ../hypergraph-rs sibling repo
# for CI runners (the real repo is unpublished — no remote). uv reads path-
# source metadata whenever it re-resolves (uv lock --check, and `uv run`'s
# implicit project sync), so every job that invokes uv needs this present.
# If the stub's metadata drifts from the real package's, uv's lock check
# fails loudly — that is the guard working, not a bug here. Keep in lockstep
# with ../hypergraph-rs/pyproject.toml (name, requires-python, deps; version
# is dynamic on both sides). See [tool.uv.sources] in pyproject.toml.
set -eu
[ -e ../hypergraph-rs/pyproject.toml ] && { echo "hypergraph-rs present — no stub needed"; exit 0; }
mkdir -p ../hypergraph-rs
cat > ../hypergraph-rs/pyproject.toml <<'STUB'
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "hypergraph-rs"
requires-python = ">=3.12"
dependencies = []
dynamic = ["version"]

[tool.hatch.version]
path = "version.py"

[tool.hatch.build.targets.wheel]
bypass-selection = true
STUB
echo '__version__ = "0.1.0"' > ../hypergraph-rs/version.py
echo "hypergraph-rs metadata stub materialized at ../hypergraph-rs"
