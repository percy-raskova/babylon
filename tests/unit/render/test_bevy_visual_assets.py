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
_EXPECTED_MANIFEST_METADATA = (
    (
        "title-mark",
        "interface",
        "design/bevy-assets/sources/title-mark.svg",
        "rust/crates/babylon-client/src/visual_assets/embedded/title-mark.png",
        "png",
        768,
        192,
        1,
        1,
        "nearest",
        "16e82da48969720970de26270420487bf43f7b2d517c49bffcbfb9c141291d1e",
        "AGPL-3.0-or-later",
    ),
    (
        "interface-atlas",
        "interface",
        "design/bevy-assets/sources/interface-atlas.svg",
        "rust/crates/babylon-client/src/visual_assets/embedded/interface-atlas.png",
        "png",
        512,
        512,
        4,
        4,
        "nearest",
        "39e634e8726651ffc0288a097b332959c51cfb563b45781af12e2cf7d2f1c989",
        "AGPL-3.0-or-later",
    ),
    (
        "marker-atlas",
        "interface",
        "design/bevy-assets/sources/marker-atlas.svg",
        "rust/crates/babylon-client/src/visual_assets/embedded/marker-atlas.png",
        "png",
        384,
        256,
        3,
        2,
        "nearest",
        "a791667c4399556fb013c4642bd21f3218a847e9d796dd6f830e9f9dd00e3bac",
        "AGPL-3.0-or-later",
    ),
    (
        "provenance-atlas",
        "interface",
        "design/bevy-assets/sources/provenance-atlas.svg",
        "rust/crates/babylon-client/src/visual_assets/embedded/provenance-atlas.png",
        "png",
        256,
        256,
        2,
        2,
        "nearest",
        "a4c258c9f45983d0d6424751e2d2628aa823df9b4508a6b345cc750589d6494d",
        "AGPL-3.0-or-later",
    ),
    (
        "frame-atlas",
        "interface",
        "design/bevy-assets/sources/frame-atlas.svg",
        "rust/crates/babylon-client/src/visual_assets/embedded/frame-atlas.png",
        "png",
        256,
        64,
        4,
        1,
        "nearest",
        "d0e94ff51c25f78fdbe20724a0616d175bb40b907b7fc7278444fdaca1e41323",
        "AGPL-3.0-or-later",
    ),
    (
        "surface-atlas",
        "interface",
        "design/bevy-assets/sources/surface-atlas.svg",
        "rust/crates/babylon-client/src/visual_assets/embedded/surface-atlas.png",
        "png",
        384,
        128,
        3,
        1,
        "nearest",
        "d3592cb05b45b87b0a105b39a4d0b64b6437e0febaa5bc7206a629a6ff2170dc",
        "AGPL-3.0-or-later",
    ),
    (
        "hero-red-apparatus",
        "illustration",
        "design/bevy-assets/prompts/hero-red-apparatus.md",
        "rust/crates/babylon-client/src/visual_assets/embedded/hero-red-apparatus.webp",
        "webp",
        1536,
        864,
        1,
        1,
        "linear",
        "62069d22b8bbb4ca6346328fcf60ce4795d4344b1d76cb3356d25f1e67cc7aaa",
        "AGPL-3.0-or-later",
    ),
    (
        "hero-empire-anatomized",
        "illustration",
        "design/bevy-assets/prompts/hero-empire-anatomized.md",
        "rust/crates/babylon-client/src/visual_assets/embedded/hero-empire-anatomized.webp",
        "webp",
        1536,
        864,
        1,
        1,
        "linear",
        "0a4bb669cf33ee69f54b9299e2e3a52dc9bab7a9ea3be57c295d452c1bd617f5",
        "AGPL-3.0-or-later",
    ),
    (
        "concept-bunker-oracle",
        "illustration",
        "design/bevy-assets/prompts/concept-bunker-oracle.md",
        "rust/crates/babylon-client/src/visual_assets/embedded/concept-bunker-oracle.webp",
        "webp",
        1024,
        1024,
        1,
        1,
        "linear",
        "673b191e5ca380c2771054795fd5081cfa84b264989846526b8f1abdfed739fc",
        "AGPL-3.0-or-later",
    ),
    (
        "concept-living-map",
        "illustration",
        "design/bevy-assets/prompts/concept-living-map.md",
        "rust/crates/babylon-client/src/visual_assets/embedded/concept-living-map.webp",
        "webp",
        1024,
        1024,
        1,
        1,
        "linear",
        "c9e8ccf74f1cbb30912e21e662d917e7642a759cad54939880fe984edf1629e2",
        "AGPL-3.0-or-later",
    ),
    (
        "concept-carceral-circuit",
        "illustration",
        "design/bevy-assets/prompts/concept-carceral-circuit.md",
        "rust/crates/babylon-client/src/visual_assets/embedded/concept-carceral-circuit.webp",
        "webp",
        1024,
        1024,
        1,
        1,
        "linear",
        "37c1a7fd7c1e706f97f9a1c57aa7e112f548e365741c65ffaf8b94b587a6d0a6",
        "AGPL-3.0-or-later",
    ),
    (
        "concept-metabolic-rift",
        "illustration",
        "design/bevy-assets/prompts/concept-metabolic-rift.md",
        "rust/crates/babylon-client/src/visual_assets/embedded/concept-metabolic-rift.webp",
        "webp",
        1024,
        1024,
        1,
        1,
        "linear",
        "36f45cbf2e6a5490773e6855d3f0e69cb0e4fb5a4cbfbb48bb5351cced7e1a45",
        "AGPL-3.0-or-later",
    ),
    (
        "banner-counties",
        "illustration",
        "design/bevy-assets/prompts/banner-counties.md",
        "rust/crates/babylon-client/src/visual_assets/embedded/banner-counties.webp",
        "webp",
        1536,
        384,
        1,
        1,
        "linear",
        "1dd5d47f6cdb897a6c04c559bb8868302348694c139f5a04e8eb63759a2a8178",
        "AGPL-3.0-or-later",
    ),
    (
        "banner-carceral",
        "illustration",
        "design/bevy-assets/prompts/banner-carceral.md",
        "rust/crates/babylon-client/src/visual_assets/embedded/banner-carceral.webp",
        "webp",
        1536,
        384,
        1,
        1,
        "linear",
        "faa11ce58235098eef24461fde527acfaea4fdb221f6da610a779611af4a4d1f",
        "AGPL-3.0-or-later",
    ),
    (
        "banner-topology",
        "illustration",
        "design/bevy-assets/prompts/banner-topology.md",
        "rust/crates/babylon-client/src/visual_assets/embedded/banner-topology.webp",
        "webp",
        1536,
        384,
        1,
        1,
        "linear",
        "0fb61352b1c05583b2cff491e3761e4e97ef621c8bfe59d6ee659e29e9417a76",
        "AGPL-3.0-or-later",
    ),
    (
        "banner-collapse",
        "illustration",
        "design/bevy-assets/prompts/banner-collapse.md",
        "rust/crates/babylon-client/src/visual_assets/embedded/banner-collapse.webp",
        "webp",
        1536,
        384,
        1,
        1,
        "linear",
        "fc7e5442580ad0bee6d6b856e9d1c0727628e6a915d45c5cdf32617c5bc6ce91",
        "AGPL-3.0-or-later",
    ),
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


def _manifest_metadata(asset: dict[str, object]) -> tuple[object, ...]:
    return (
        asset["id"],
        asset["category"],
        asset["source"],
        asset["runtime"],
        asset["format"],
        asset["width"],
        asset["height"],
        asset["columns"],
        asset["rows"],
        asset["sampler"],
        asset["sha256"],
        asset["license"],
    )


def test_manifest_pins_every_complete_metadata_tuple() -> None:
    assets = _manifest_assets()
    assert len(assets) == 16
    actual = tuple(_manifest_metadata(assets[index]) for index in range(16))
    assert actual == _EXPECTED_MANIFEST_METADATA


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
