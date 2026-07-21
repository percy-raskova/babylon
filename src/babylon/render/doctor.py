"""The render half of ``babylon doctor`` — probe once, persist, hand back lines.

Kept out of the Typer command so it is testable without a CLI runner; the CLI
``doctor`` command imports and prints these lines (ADR097 D4).
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

from babylon.render.capability import (
    TerminalQuerier,
    TextualImageQuerier,
    derive_tiers,
    probe,
    verdict_lines,
)
from babylon.render.config import write_render_section


def run_render_probe(
    env: Mapping[str, str],
    queries: TerminalQuerier | None = None,
    config_path: Path | None = None,
) -> list[str]:
    """Probe the terminal once, persist ``[render]``, return verdict lines."""
    querier = queries if queries is not None else TextualImageQuerier()
    report = probe(env, querier)
    tier, palette = derive_tiers(report)
    if config_path is not None:
        write_render_section(config_path, report, tier, palette)
    return verdict_lines(report, tier, palette)
