from __future__ import annotations

import hashlib
import re
import tomllib
import xml.etree.ElementTree as ET
from itertools import islice
from pathlib import Path

from PIL import Image

_ROOT = Path(__file__).resolve().parents[3]
_DESIGN = _ROOT / "design" / "bevy-assets"
_RUNTIME = _ROOT / "rust" / "crates" / "babylon-client" / "src" / "visual_assets" / "embedded"
_INTERFACE_IDS = (
    "title-mark",
    "interface-atlas",
    "marker-atlas",
    "provenance-atlas",
    "frame-atlas",
    "surface-atlas",
)
_ILLUSTRATION_IDS = (
    "hero-red-apparatus",
    "hero-empire-anatomized",
    "concept-bunker-oracle",
    "concept-living-map",
    "concept-carceral-circuit",
    "concept-metabolic-rift",
    "banner-counties",
    "banner-carceral",
    "banner-topology",
    "banner-collapse",
)
_PALETTE = {
    "#1a0000",
    "#e8e8e8",
    "#dc143c",
    "#ffd700",
    "#404040",
    "#202020",
    "#4169e1",
    "#228b22",
}
_HEX_COLOR = re.compile(r"#[0-9a-fA-F]{6}")


def _manifest_assets() -> tuple[dict[str, object], ...]:
    data = tomllib.loads((_DESIGN / "manifest.toml").read_text(encoding="utf-8"))
    return tuple(data["asset"])


def test_interface_sources_and_rasters_match_the_manifest() -> None:
    manifest = _manifest_assets()
    assert len(manifest) in (6, 16)
    assets = manifest[:6]
    assert tuple(assets[index]["id"] for index in range(6)) == _INTERFACE_IDS
    for index in range(6):
        asset = assets[index]
        source = _ROOT / str(asset["source"])
        runtime = _ROOT / str(asset["runtime"])
        ET.parse(source)  # noqa: S314 - version-controlled SVG master only
        with Image.open(runtime) as image:
            assert image.size == (asset["width"], asset["height"])
            assert image.mode == "RGBA"
        assert runtime.stat().st_size < 1_048_576
        assert hashlib.sha256(runtime.read_bytes()).hexdigest() == asset["sha256"]
        assert asset["license"] == "AGPL-3.0-or-later"


def test_interface_svg_colors_are_palette_roles() -> None:
    colors = set()
    for index in range(6):
        source = _DESIGN / "sources" / f"{_INTERFACE_IDS[index]}.svg"
        colors.update(
            value.lower() for value in _HEX_COLOR.findall(source.read_text(encoding="utf-8"))
        )
    assert colors <= _PALETTE


def test_illustrations_decode_and_match_the_manifest() -> None:
    manifest = _manifest_assets()
    assert len(manifest) == 16
    assets = manifest[6:16]
    assert tuple(assets[index]["id"] for index in range(10)) == _ILLUSTRATION_IDS
    for index in range(10):
        asset = assets[index]
        assert (_ROOT / str(asset["source"])).is_file()
        runtime = _ROOT / str(asset["runtime"])
        with Image.open(runtime) as image:
            assert image.size == (asset["width"], asset["height"])
            assert image.mode == "RGB"
            assert image.format == "WEBP"
        assert runtime.stat().st_size < 1_048_576
        assert hashlib.sha256(runtime.read_bytes()).hexdigest() == asset["sha256"]
        assert asset["license"] == "AGPL-3.0-or-later"


def test_manifest_and_runtime_directory_have_exactly_the_same_files() -> None:
    assets = _manifest_assets()
    assert len(assets) == 16
    declared = {Path(str(assets[index]["runtime"])).name for index in range(16)}
    actual = {path.name for path in islice(_RUNTIME.iterdir(), 17)}
    assert actual == declared
