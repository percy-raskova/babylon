"""Probe-once terminal capability detection (ADR097 D4).

``probe`` is a pure function over an environment mapping plus an injected
``TerminalQuerier``; it is run exactly once by ``babylon doctor`` and its verdict
is persisted to config. Runtime never re-probes (no silent tier switches). The
concrete ``TextualImageQuerier`` is the only part that touches a real terminal and
is therefore not unit-tested; the pure core is fully covered by env-dict cases.
"""

from __future__ import annotations

import logging
import sys
from collections.abc import Mapping
from typing import Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict

from babylon.render.tiers import PaletteTier, RenderTier

logger = logging.getLogger("babylon.render.capability")

_TRUECOLOR_TOKENS = frozenset({"truecolor", "24bit"})


class CapabilityReport(BaseModel):
    """Frozen record of one probe. Persisted (as evidence) into ``[render]``."""

    model_config = ConfigDict(frozen=True)

    term: str
    colorterm: str
    truecolor: bool
    has_256: bool
    in_tmux: bool
    is_tty: bool
    pixel_protocol: str | None


@runtime_checkable
class TerminalQuerier(Protocol):
    """Injection seam for the two facts a probe cannot read from env alone."""

    def is_a_tty(self) -> bool: ...

    def detect_pixel_protocol(self) -> str | None: ...


def probe(env: Mapping[str, str], queries: TerminalQuerier) -> CapabilityReport:
    """Derive a single capability verdict from env + the injected querier."""
    term = env.get("TERM", "")
    colorterm = env.get("COLORTERM", "")
    truecolor = colorterm.strip().lower() in _TRUECOLOR_TOKENS
    has_256 = truecolor or "256color" in term
    in_tmux = "TMUX" in env or term.startswith(("tmux", "screen"))
    is_tty = queries.is_a_tty()

    # Guard: only consult the pixel query on a real TTY outside tmux. Non-TTY
    # (CI/pipes) and tmux passthrough are treated as honest glyph (III.11).
    pixel_protocol: str | None = None
    if is_tty and not in_tmux:
        pixel_protocol = queries.detect_pixel_protocol()

    return CapabilityReport(
        term=term,
        colorterm=colorterm,
        truecolor=truecolor,
        has_256=has_256,
        in_tmux=in_tmux,
        is_tty=is_tty,
        pixel_protocol=pixel_protocol,
    )


def derive_tiers(report: CapabilityReport) -> tuple[RenderTier, PaletteTier]:
    """Map a report to the persisted (render tier, palette tier) pair."""
    tier = RenderTier.PIXEL if report.pixel_protocol else RenderTier.GLYPH
    palette = PaletteTier.TRUECOLOR if report.truecolor else PaletteTier.DEGRADED_256
    return tier, palette


def verdict_lines(report: CapabilityReport, tier: RenderTier, palette: PaletteTier) -> list[str]:
    """Human-readable doctor verdict — degradation is always stated aloud."""
    lines = [
        f"render tier: {tier.value}",
        f"palette: {palette.value}",
        (
            f"evidence: TERM={report.term or '(unset)'} "
            f"COLORTERM={report.colorterm or '(unset)'} "
            f"tty={report.is_tty} tmux={report.in_tmux} "
            f"pixel-protocol={report.pixel_protocol or 'none'}"
        ),
    ]
    if palette is PaletteTier.DEGRADED_256:
        lines.append(
            "note: degraded — no truecolor detected; using the declared 256-color "
            "palette (DESIGN_BIBLE §9b)."
        )
    if tier is RenderTier.GLYPH and report.pixel_protocol is None and report.is_tty:
        lines.append(
            "note: degraded — no pixel protocol; Tier-0 glyph canon carries all "
            "information (ADR097 D1)."
        )
    return lines


class TextualImageQuerier:
    """Production querier. Wraps textual-image's terminal detection.

    NOT unit-tested (requires a live TTY). Any detection failure degrades to
    glyph honestly rather than raising into the CLI.

    Deviation from the original brief: the resolved textual-image version
    (0.13.2) has no ``textual_image._terminal.get_tgp_output_format`` symbol.
    The actual detection entry points in this version are the module-level
    ``query_terminal_support() -> bool`` probes in
    ``textual_image.renderable.tgp`` (Kitty Terminal Graphics Protocol) and
    ``textual_image.renderable.sixel`` (Sixel) — both real escape-sequence
    round trips against the live terminal, hence still only exercised here.
    """

    def is_a_tty(self) -> bool:
        return sys.stdout.isatty()

    def detect_pixel_protocol(self) -> str | None:
        try:
            from textual_image.renderable import sixel, tgp

            if tgp.query_terminal_support():
                return "kitty"
            if sixel.query_terminal_support():
                return "sixel"
        except ImportError:
            logger.debug("textual-image not importable; treating as glyph")
            return None
        except Exception:  # noqa: BLE001 - detection must never crash the CLI
            logger.debug("pixel-protocol detection failed; treating as glyph", exc_info=True)
            return None
        return None
