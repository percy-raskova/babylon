#!/usr/bin/env python3
"""Build Pinyon Script ink reveal timestamps and synchronized quill motion.

The font's glyph coverage is skeletonized with Zhang-Suen thinning. We traverse
actual centerline edges, preserve connected loops, and lift between exhausted
branches/components. Each glyph's coverage inherits the nearest stroke's time.
The result draws the contours by their centerline, rather than wiping across x.
"""

from __future__ import annotations

import argparse
import json
import math
from itertools import pairwise
from pathlib import Path
from typing import TypedDict

import numpy as np
from numpy.typing import NDArray
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage as ndi

WIDTH, HEIGHT = 2048, 1024
DURATION = 6.3
LINES: tuple[tuple[str, int, int, float, float], ...] = (
    ("Persephone", 1872, 26, 0.7, 3.7),
    ("Raskova", 1536, 600, 3.7, 6.3),
)

type Pixel = tuple[int, int]
type StrokePoint = tuple[Pixel, bool]
type PenPoint = tuple[float, float, float, bool]


class Glyph(TypedDict):
    box: tuple[int, int, int, int]
    coverage: NDArray[np.uint8]
    skeleton: NDArray[np.bool_]
    sequence: list[StrokePoint]
    distances: list[float]
    length: float


class LineMetadata(TypedDict):
    text: str
    font_size: int
    start_seconds: float
    end_seconds: float


def thin(binary: NDArray[np.bool_]) -> NDArray[np.bool_]:
    """8-connected Zhang-Suen skeleton, with a padded zero boundary."""
    if binary.ndim != 2 or binary.size == 0:
        raise ValueError("Glyph thinning requires a nonempty two-dimensional mask")
    image = np.pad(binary.astype(np.uint8), 1)
    while True:
        changed = False
        for phase in (0, 1):
            p2, p3, p4 = image[:-2, 1:-1], image[:-2, 2:], image[1:-1, 2:]
            p5, p6, p7 = image[2:, 2:], image[2:, 1:-1], image[2:, :-2]
            p8, p9 = image[1:-1, :-2], image[:-2, :-2]
            ring = [p2, p3, p4, p5, p6, p7, p8, p9, p2]
            neighbours = sum(ring[:-1])
            transitions = sum((a == 0) & (b == 1) for a, b in pairwise(ring))
            if phase == 0:
                triple1, triple2 = p2 * p4 * p6, p4 * p6 * p8
            else:
                triple1, triple2 = p2 * p4 * p8, p2 * p6 * p8
            remove = (
                (image[1:-1, 1:-1] == 1)
                & (neighbours >= 2)
                & (neighbours <= 6)
                & (transitions == 1)
                & (triple1 == 0)
                & (triple2 == 0)
            )
            if remove.any():
                image[1:-1, 1:-1][remove] = 0
                changed = True
        if not changed:
            return image[1:-1, 1:-1].astype(bool)


def trace(skeleton: NDArray[np.bool_]) -> list[StrokePoint]:
    """Walk glyph centerline edges; False marks arrival with the pen lifted."""
    coords: set[Pixel] = {(int(y), int(x)) for y, x in np.argwhere(skeleton)}
    if not coords:
        raise ValueError("Cannot trace a glyph without centerline pixels")
    adjacent: dict[Pixel, list[Pixel]] = {}
    for y, x in coords:
        neighbours = []
        for dy, dx in (
            (-1, 0),
            (0, -1),
            (0, 1),
            (1, 0),
            (-1, -1),
            (-1, 1),
            (1, -1),
            (1, 1),
        ):
            other = (y + dy, x + dx)
            if other not in coords:
                continue
            # Avoid tiny triangular circuits alongside cardinal junctions.
            if dx and dy and ((y, x + dx) in coords or (y + dy, x) in coords):
                continue
            neighbours.append(other)
        adjacent[(y, x)] = neighbours
    components: list[set[Pixel]] = []
    pending = set(coords)
    while pending:
        start = min(pending)
        component: set[Pixel] = set()
        stack: list[Pixel] = [start]
        pending.remove(start)
        while stack:
            p = stack.pop()
            component.add(p)
            for q in adjacent[p]:
                if q in pending:
                    pending.remove(q)
                    stack.append(q)
        components.append(component)
    # The continuous body precedes disconnected punctuation or fine flourishes.
    components.sort(key=lambda c: (-len(c), min(x for y, x in c)))
    sequence: list[StrokePoint] = []
    visited_edges: set[tuple[Pixel, ...]] = set()
    for component in components:
        endpoints = [p for p in component if len(adjacent[p]) <= 1]
        start = min(endpoints or component, key=lambda p: (p[1], -p[0]))
        sequence.append((start, False))
        stack = [start]
        incoming = (0, 1)
        while stack:
            p = stack[-1]
            options = [q for q in adjacent[p] if tuple(sorted((p, q))) not in visited_edges]
            if not options:
                stack.pop()
                continue
            if sequence[-1][0] != p:
                sequence.append((p, False))
                incoming = (0, 1)

            def score(q: Pixel, current: Pixel = p, arriving: Pixel = incoming) -> float:
                direction = (q[0] - current[0], q[1] - current[1])
                norm = math.hypot(*direction) * math.hypot(*arriving)
                return (
                    direction[0] * arriving[0] + direction[1] * arriving[1]
                ) / norm + 0.10 * direction[1]

            q = max(options, key=lambda q: (score(q), -q[0], q[1]))
            visited_edges.add(tuple(sorted((p, q))))
            incoming = (q[0] - p[0], q[1] - p[1])
            sequence.append((q, True))
            stack.append(q)
    return sequence


def render_glyphs(
    word: str, target_width: int, top: int, font_path: Path
) -> tuple[list[Glyph], int]:
    """Render and trace each glyph while retaining measured pair kerning."""
    if not word or target_width <= 0:
        raise ValueError("Signature text and target width must be nonempty and positive")
    probe = ImageFont.truetype(str(font_path), 400)
    b = probe.getbbox(word)
    if b[2] <= b[0]:
        raise ValueError(f"Font produces no measurable width for {word!r}")
    size = round(400 * target_width / (b[2] - b[0]))
    font = ImageFont.truetype(str(font_path), size)
    bbox = font.getbbox(word)
    origin_x = (WIDTH - (bbox[2] - bbox[0])) / 2 - bbox[0]
    origin_y = top - bbox[1]
    glyphs: list[Glyph] = []
    for i, char in enumerate(word):
        # Prefix measurement retains pair kerning while keeping each glyph's
        # independently traced centerline; this font needs no word ligatures.
        offset = font.getlength(word[: i + 1]) - font.getlength(char)
        mask = Image.new("L", (WIDTH, HEIGHT))
        ImageDraw.Draw(mask).text((origin_x + offset, origin_y), char, font=font, fill=255)
        box = mask.getbbox()
        if box is None:
            raise ValueError(f"Font produced no visible ink for glyph {char!r} in {word!r}")
        crop = np.asarray(mask.crop(box))
        skeleton = thin(crop > 24)
        sequence = trace(skeleton)
        lengths = [0.0]
        for (p, _), (q, down) in pairwise(sequence):
            dist = math.hypot(q[0] - p[0], q[1] - p[1])
            # Brief pen lifts, with a minimum pause for changing strokes.
            lengths.append(lengths[-1] + (dist if down else max(12.0, dist * 0.18)))
        glyphs.append(
            {
                "box": box,
                "coverage": crop,
                "skeleton": skeleton,
                "sequence": sequence,
                "distances": lengths,
                "length": lengths[-1] + 22.0,
            }
        )
    return glyphs, size


def main(output: Path, font_path: Path, previews: bool, metadata: bool) -> None:
    """Write shader-ready ink data and a bare numeric quill point array."""
    if not font_path.is_file():
        raise FileNotFoundError(f"Signature font file does not exist: {font_path}")
    output.mkdir(parents=True, exist_ok=True)
    coverage = np.zeros((HEIGHT, WIDTH), np.uint8)
    reveal = np.full((HEIGHT, WIDTH), np.inf, np.float32)
    trajectory: list[PenPoint] = []
    metadata_lines: list[LineMetadata] = []
    for word, target, top, start, end in LINES:
        glyphs, font_size = render_glyphs(word, target, top, font_path)
        weight = sum(g["length"] for g in glyphs)
        cursor = start
        for glyph in glyphs:
            seconds_per_px = (end - start) / weight
            glyph_start = cursor
            glyph_end = cursor + glyph["length"] * seconds_per_px
            times = glyph_start + np.asarray(glyph["distances"]) * seconds_per_px
            skel_time = np.full(glyph["skeleton"].shape, np.inf, np.float32)
            left, upper, right, lower = glyph["box"]
            for ((y, x), down), t in zip(glyph["sequence"], times, strict=True):
                skel_time[y, x] = min(skel_time[y, x], t)
                trajectory.append((float(t), (x + left) / WIDTH, (y + upper) / HEIGHT, bool(down)))
            nearest = ndi.distance_transform_edt(
                ~glyph["skeleton"], return_distances=False, return_indices=True
            )
            pixel_time = skel_time[tuple(nearest)]
            ink = glyph["coverage"] > 0
            destination = reveal[upper:lower, left:right]
            destination[ink] = np.minimum(destination[ink], pixel_time[ink])
            coverage[upper:lower, left:right] = np.maximum(
                coverage[upper:lower, left:right], glyph["coverage"]
            )
            cursor = glyph_end
        metadata_lines.append(
            {
                "text": word,
                "font_size": font_size,
                "start_seconds": start,
                "end_seconds": end,
            }
        )
    if not np.isfinite(reveal[coverage > 0]).all():
        raise RuntimeError("Some visible glyph pixels have no stroke timestamp")
    # Quantization is explicitly linear. Channels are high-byte/low-byte, not colors.
    encoded = np.rint(
        np.clip(np.where(np.isfinite(reveal), reveal, 0) / DURATION, 0, 1) * 65535
    ).astype(np.uint16)
    rgba = np.zeros((HEIGHT, WIDTH, 4), np.uint8)
    rgba[..., 0] = encoded >> 8
    rgba[..., 1] = encoded & 255
    rgba[..., 3] = coverage
    Image.fromarray(rgba).save(output / "signature-ink.png", optimize=True)
    # Retain every lift boundary and otherwise emit ~120 Hz samples. The runtime
    # linearly interpolates x/y in this list using seconds and honors pen_down.
    trajectory.sort(key=lambda p: p[0])
    sampled: list[PenPoint] = []
    for i, p in enumerate(trajectory):
        lift_boundary = not p[3] or (i + 1 < len(trajectory) and not trajectory[i + 1][3])
        if (
            not sampled
            or lift_boundary
            or p[0] - sampled[-1][0] >= 1 / 120
            or i == len(trajectory) - 1
        ):
            sampled.append(p)
    if any(a[0] >= b[0] for a, b in pairwise(sampled)):
        raise RuntimeError("Quill timestamps must be strictly increasing")
    if any(not (0 <= x <= 1 and 0 <= y <= 1) for _, x, y, _ in sampled):
        raise RuntimeError("Quill coordinates must remain inside the ink texture")
    # Runtime deserializes Vec<[f32; 4]>: the fourth value must be numeric.
    points = [
        [round(t, 6), round(x, 7), round(y, 7), 1.0 if down else 0.0] for t, x, y, down in sampled
    ]
    (output / "signature-pen.json").write_text(
        json.dumps(points, separators=(",", ":"), allow_nan=False) + "\n",
        encoding="utf-8",
    )
    if metadata:
        payload = {
            "width": WIDTH,
            "height": HEIGHT,
            "duration_seconds": DURATION,
            "timestamp_encoding": "linear RG16: (R*256+G)/65535*6.3; alpha is ink coverage",
            "font": "Pinyon Script",
            "lines": metadata_lines,
            "point_count": len(points),
            "pen_down_encoding": "Fourth point value is 1 for ink, 0 for a lift; describes arrival from the preceding point",
        }
        (output / "signature-metadata.json").write_text(
            json.dumps(payload, indent=2, allow_nan=False) + "\n", encoding="utf-8"
        )
    if not previews:
        print(f"Wrote {len(sampled)} quill points and {WIDTH}x{HEIGHT} reveal texture to {output}")
        return
    # Preview in the splash's warm ivory ink on near-black, with a pink nib.
    bg = np.array([7, 5, 12], np.float32)
    color = np.array([255, 224, 240], np.float32)
    a = coverage[..., None] / 255
    still = np.rint(bg * (1 - a) + color * a).astype(np.uint8)
    Image.fromarray(still).save(output / "signature_preview.png")
    preview_size = (1024, 512)
    small_alpha = (
        np.asarray(Image.fromarray(coverage).resize(preview_size, Image.Resampling.LANCZOS)) / 255
    )
    small_time = np.asarray(
        Image.fromarray(reveal, mode="F").resize(preview_size, Image.Resampling.NEAREST)
    )
    frames: list[Image.Image] = []
    path_times = np.array([p[0] for p in trajectory])
    for t in np.arange(0, 7.35, 1 / 24):
        visible = np.clip((t - small_time) / 0.035, 0, 1) * small_alpha
        rgb = np.rint(bg * (1 - visible[..., None]) + color * visible[..., None]).astype(np.uint8)
        frame = Image.fromarray(rgb)
        if 0.7 <= t <= 6.3:
            idx = min(len(trajectory) - 1, max(0, int(np.searchsorted(path_times, t)) - 1))
            p = trajectory[idx]
            d = ImageDraw.Draw(frame)
            x, y = p[1] * 1024, p[2] * 512
            d.ellipse(
                (x - 4, y - 4, x + 4, y + 4),
                fill=(255, 124, 207) if p[3] else (100, 60, 100),
            )
        frames.append(frame)
    frames[0].save(
        output / "signature_preview.gif",
        save_all=True,
        append_images=frames[1:],
        duration=42,
        loop=0,
        optimize=True,
    )
    print(
        json.dumps(
            {
                "canvas": [WIDTH, HEIGHT],
                "points": len(sampled),
                "raw_points": len(trajectory),
                "lines": metadata_lines,
                "files": [p.name for p in output.iterdir()],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--font", type=Path, required=True, help="PinyonScript-Regular.ttf")
    parser.add_argument("--output", type=Path, required=True, help="Destination directory")
    parser.add_argument(
        "--previews",
        action="store_true",
        help="Also render PNG and animated GIF previews",
    )
    parser.add_argument(
        "--metadata",
        action="store_true",
        help="Write optional generation metadata separately",
    )
    args = parser.parse_args()
    try:
        main(args.output, args.font, args.previews, args.metadata)
    except (OSError, ValueError) as error:
        parser.exit(2, f"Signature generation failed: {error}\n")
