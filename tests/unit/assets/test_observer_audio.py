"""Shipped observer audio must resolve to the original named sources and exact renders."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from pathlib import Path

import pytest
import yaml
from tools import check_repo_hygiene as hygiene
from tools.audio import render_observer_audio as renderer

ROOT = Path(__file__).resolve().parents[3]
THEMES = {
    "assets/music/babylon_theme_phi.ogg",
    "assets/music/babylon_theme_panopticon.ogg",
}
MUSIC = {
    path.relative_to(ROOT).with_suffix(".ogg").as_posix()
    for path in (ROOT / "assets/music").rglob("*.mid")
}
SFX = {
    "assets/sfx/ui/ui_select.ogg",
    "assets/sfx/ui/ui_tab.ogg",
    "assets/sfx/ui/ui_open.ogg",
    "assets/sfx/ui/ui_back.ogg",
    "assets/sfx/state/tick_advance.ogg",
    "assets/sfx/state/state_fault.ogg",
    "assets/sfx/stinger/production_fanfare.ogg",
}
EXPECTED = MUSIC | SFX


def test_repo_hygiene_bounds_only_the_named_authored_soundtrack() -> None:
    assert {
        path for path in hygiene.RUNTIME_ASSET_BLOB_LIMITS if path.startswith("assets/music/")
    } == MUSIC
    for path in sorted(MUSIC):
        limit = 2_097_152 if path in THEMES else 12_582_912
        assert hygiene.check_large_non_lfs_blobs([f"100644 blob abc123 {limit}\t{path}"]) == []
        assert hygiene.check_large_non_lfs_blobs([f"100644 blob abc123 {limit + 1}\t{path}"]) == [
            f"{path} ({limit + 1} bytes)"
        ]
    for path in [
        "assets/music/unrelated.ogg",
        "assets/music/revolutionary/other.ogg",
        *(f"{path}.bak" for path in MUSIC),
        *(f"other/{path}" for path in MUSIC),
    ]:
        size = hygiene.MAX_BLOB_BYTES + 1
        assert hygiene.check_large_non_lfs_blobs([f"100644 blob abc123 {size}\t{path}"]) == [
            f"{path} ({size} bytes)"
        ]


def test_shipped_observer_renders_are_not_ignored() -> None:
    result = subprocess.run(
        ["git", "check-ignore", "--no-index", "--stdin"],
        input="\n".join(sorted(EXPECTED)) + "\n",
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 1, result.stdout + result.stderr
    assert not result.stdout


def test_observer_music_catalog_and_renderer_cover_every_authored_midi() -> None:
    assert len(MUSIC) == 36
    catalog = (ROOT / "rust/crates/babylon-client/src/observer_audio/catalog.rs").read_text()
    paths = re.findall(r'"(music/[^"\n]+)"', catalog)
    assert len(paths) == len(set(paths)) == len(MUSIC)
    assert {f"assets/{path}.ogg" for path in paths} == MUSIC
    assert {f"assets/{cue.path}.ogg" for cue in renderer.CUES} == EXPECTED
    assert len(renderer.CUES) == len(EXPECTED)


def test_renderer_refuses_unpinned_soundfont_before_invoking_tools(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    soundfont = tmp_path / "other.sf2"
    soundfont.write_bytes(b"not the committed FluidR3 soundfont")

    def unexpected_tool(_command: list[str], *, timeout: int = 180) -> None:
        pytest.fail(f"renderer invoked an external tool before checking its soundfont: {timeout}")

    monkeypatch.setattr(renderer, "run", unexpected_tool)
    monkeypatch.setattr(renderer.shutil, "which", lambda _binary: str(soundfont))
    with pytest.raises(ValueError, match="soundfont SHA-256 mismatch"):
        renderer.main(["--soundfont", str(soundfont)])


def test_observer_audio_inventory_is_complete_and_pins_real_source_and_render_bytes() -> None:
    manifest = json.loads((ROOT / "assets/audio-renders.json").read_text())
    assert {row["output"] for row in manifest["assets"]} == EXPECTED
    assert len(manifest["assets"]) == len(EXPECTED)
    assert {row["output"] for row in manifest["assets"] if row["kind"] == "music"} == MUSIC
    assert {row["output"] for row in manifest["assets"] if row["kind"] == "sfx"} == SFX
    for row in manifest["assets"]:
        source = ROOT / row["source"]
        output = ROOT / row["output"]
        assert source.suffix == ".mid"
        assert source.read_bytes().startswith(b"MThd")
        assert output.read_bytes().startswith(b"OggS")
        assert hashlib.sha256(source.read_bytes()).hexdigest() == row["source_sha256"]
        assert hashlib.sha256(output.read_bytes()).hexdigest() == row["output_sha256"]
        assert row["duration_seconds"] > 0
    assert manifest["soundfont"]["license"] == "MIT"
    assert manifest["soundfont"]["sha256"] == (
        "74594e8f4250680adf590507a306655a299935343583256f3b722c48a1bc1cb0"
    )
    assert (ROOT / manifest["soundfont"]["notice"]).is_file()
    assert manifest["recipe"]["sample_rate_hz"] == 44100
    assert manifest["recipe"]["channels"] == 2
    assert manifest["recipe"]["codec"] == "vorbis"


def test_shipped_bytes_have_one_root_and_composition_code_is_tooling() -> None:
    assert (ROOT / "assets/map/county_atlas.bin").is_file()
    assert len(list((ROOT / "assets/visual").iterdir())) == 17
    assert not (ROOT / "rust/crates/babylon-client/assets/map").exists()
    assert not (ROOT / "rust/crates/babylon-client/src/visual_assets/embedded").exists()
    assert not (ROOT / "src/assets").exists()
    assert not list((ROOT / "assets").rglob("*.py"))
    assert (ROOT / "tools/audio/music/generate_music.py").is_file()
    assert (ROOT / "tools/audio/sfx/generate_sfx.py").is_file()


def test_large_audio_hook_bounds_only_named_renders_and_preserves_existing_budgets() -> None:
    config = yaml.safe_load((ROOT / ".pre-commit-config.yaml").read_text())
    hooks = [
        hook
        for repo in config["repos"]
        for hook in repo["hooks"]
        if hook["id"] == "check-added-large-files"
    ]
    assert len(hooks) == 3
    general = next(hook for hook in hooks if "files" not in hook)
    bounded = [hook for hook in hooks if "files" in hook]
    themes = next(hook for hook in bounded if "--maxkb=2048" in hook["args"])
    soundtrack = next(hook for hook in bounded if "--maxkb=12288" in hook["args"])
    assert general["args"] == ["--maxkb=1024"]
    assert themes["args"] == ["--maxkb=2048", "--enforce-all"]
    assert soundtrack["args"] == ["--maxkb=12288", "--enforce-all"]
    for path in MUSIC:
        budget = themes if path in THEMES else soundtrack
        assert re.search(general["exclude"], path)
        assert re.search(budget["files"], path)
        assert sum(bool(re.search(hook["files"], path)) for hook in bounded) == 1
        assert (ROOT / path).stat().st_size <= (2_097_152 if path in THEMES else 12_582_912)
    for path in [
        "assets/music/babylon_theme_phi.ogg.bak",
        "assets/music/babylon_theme_other.ogg",
        "assets/music/unrelated.ogg",
        "assets/music/revolutionary/other.ogg",
        "other/assets/music/babylon_theme_phi.ogg",
        *(f"{path}.bak" for path in MUSIC),
        *(f"other/{path}" for path in MUSIC),
    ]:
        assert not re.search(general["exclude"], path)
        assert not any(re.search(hook["files"], path) for hook in bounded)
    road_paths = "content/scenarios/michigan/statewide-physical.json.gz"
    assert re.search(themes["files"], road_paths)
    assert not re.search(soundtrack["files"], road_paths)
    assert re.search(general["exclude"], "assets/map/county_atlas.bin")
    assert not re.search(
        general["exclude"], "rust/crates/babylon-client/assets/map/county_atlas.bin"
    )
