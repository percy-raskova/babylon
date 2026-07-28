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
    cell_width: int | None
    cell_height: int | None


@runtime_checkable
class TerminalQuerier(Protocol):
    """Injection seam for the facts a probe cannot read from env alone."""

    def is_a_tty(self) -> bool: ...

    def detect_pixel_protocol(self) -> str | None: ...

    def detect_cell_size(self) -> tuple[int, int] | None: ...


def probe(env: Mapping[str, str], queries: TerminalQuerier) -> CapabilityReport:
    """Derive a single capability verdict from env + the injected querier."""
    term = env.get("TERM", "")
    colorterm = env.get("COLORTERM", "")
    truecolor = colorterm.strip().lower() in _TRUECOLOR_TOKENS
    has_256 = truecolor or "256color" in term
    in_tmux = "TMUX" in env or term.startswith(("tmux", "screen"))
    is_tty = queries.is_a_tty()

    # Guard: only consult the pixel queries on a real TTY outside tmux. Non-TTY
    # (CI/pipes) and tmux passthrough are treated as honest glyph (III.11).
    # Cell size shares the guard: it exists solely to serve the pixel path
    # (contract §7's FontSize prerequisite), so it is only meaningful where a
    # pixel protocol could be too.
    pixel_protocol: str | None = None
    cell_size: tuple[int, int] | None = None
    if is_tty and not in_tmux:
        pixel_protocol = queries.detect_pixel_protocol()
        cell_size = queries.detect_cell_size()

    return CapabilityReport(
        term=term,
        colorterm=colorterm,
        truecolor=truecolor,
        has_256=has_256,
        in_tmux=in_tmux,
        is_tty=is_tty,
        pixel_protocol=pixel_protocol,
        cell_width=cell_size[0] if cell_size else None,
        cell_height=cell_size[1] if cell_size else None,
    )


def derive_tiers(report: CapabilityReport) -> tuple[RenderTier, PaletteTier]:
    """Map a report to the persisted (render tier, palette tier) pair.

    Task 35 (contract §7): the pixel tier requires BOTH a kitty protocol and
    known cell pixel dimensions — ``StatefulProtocol::new`` needs a FontSize,
    and re-probing at runtime is banned (ADR097 D4). Sixel is recorded as
    evidence but never yields the pixel tier (ADR099: sixel is not a target).
    """
    pixel_capable = (
        report.pixel_protocol == "kitty"
        and report.cell_width is not None
        and report.cell_height is not None
    )
    tier = RenderTier.PIXEL if pixel_capable else RenderTier.GLYPH
    palette = PaletteTier.TRUECOLOR if report.truecolor else PaletteTier.DEGRADED_256
    return tier, palette


def verdict_lines(report: CapabilityReport, tier: RenderTier, palette: PaletteTier) -> list[str]:
    """Human-readable doctor verdict — degradation is always stated aloud."""
    cell = (
        f"{report.cell_width}x{report.cell_height}px"
        if report.cell_width is not None and report.cell_height is not None
        else "unknown"
    )
    lines = [
        f"render tier: {tier.value}",
        f"palette: {palette.value}",
        (
            f"evidence: TERM={report.term or '(unset)'} "
            f"COLORTERM={report.colorterm or '(unset)'} "
            f"tty={report.is_tty} tmux={report.in_tmux} "
            f"pixel-protocol={report.pixel_protocol or 'none'} "
            f"cell={cell}"
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
    if tier is RenderTier.GLYPH and report.pixel_protocol == "sixel":
        lines.append(
            "note: degraded — sixel detected but sixel is not a target (ADR099); "
            "Tier-0 glyph floor."
        )
    if (
        tier is RenderTier.GLYPH
        and report.pixel_protocol == "kitty"
        and (report.cell_width is None or report.cell_height is None)
    ):
        lines.append(
            "note: degraded — kitty detected but the terminal cell pixel size is "
            "unknown; the pixel tier needs it for FontSize (contract §7), so the "
            "glyph floor carries the session."
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

    def detect_cell_size(self) -> tuple[int, int] | None:
        """Terminal cell pixel dimensions via ``TIOCGWINSZ`` (Task 35, §7).

        ``struct winsize`` carries ``ws_xpixel``/``ws_ypixel`` alongside the
        row/col counts; one ioctl, no escape-sequence round trip. Terminals
        that do not fill the pixel fields report 0 — honest ``None`` (the
        probe verdict then demotes to glyph, declared aloud). POSIX-only by
        construction; Windows support is a post-1.0 obligation (Amendment AA)
        and off-POSIX this degrades to ``None``, never raises.
        """
        try:
            import fcntl
            import struct
            import termios

            packed = fcntl.ioctl(
                sys.stdout.fileno(), termios.TIOCGWINSZ, struct.pack("HHHH", 0, 0, 0, 0)
            )
            rows, cols, xpixel, ypixel = struct.unpack("HHHH", packed)
        except ImportError:
            logger.debug("termios/fcntl unavailable; cell size unknown")
            return None
        except OSError:
            logger.debug("TIOCGWINSZ failed; cell size unknown", exc_info=True)
            return None
        if rows == 0 or cols == 0 or xpixel == 0 or ypixel == 0:
            return None
        return (xpixel // cols, ypixel // rows)
