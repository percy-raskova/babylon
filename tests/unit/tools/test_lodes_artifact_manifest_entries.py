"""Regeneration-safety tripwire for the hand-maintained LODES manifest entries
(Vol II Circulation program, Unit U2).

``data-artifacts.yaml``'s ``lodes_xwalk_tri_county_hex`` /
``lodes_od_tri_county_hex_*`` rows are hand-maintained by
``tools/make_lodes_tri_county_artifact.py`` — they carry no backing sqlite
reference-DB table, so ``tools/make_data_artifacts.py``'s ``ARTIFACTS`` tuple
never names them. ``make_data_artifacts.main()`` (no ``--check``) calls
``generate()`` (which enumerates ONLY ``ARTIFACTS`` — plus, with
``--full-coverage``, one parquet spec per governed table, still never these)
and then ``_rewrite_manifest_preserving_blocks(entries)``, which REWRITES the
manifest's whole ``artifacts:`` list from those entries alone — silently
dropping the LODES tail. This is a known, undischarged risk (see the
``EXCEPTION`` note at the top of ``data-artifacts.yaml``): no change to a
shared, actively-maintained generator without an owner ruling.

This test is the mitigation the risk note promises: it pins the LODES entries'
presence + content in the COMMITTED manifest, directly (not through the
generator). If a future ``make_data_artifacts.py`` run replaces
``data-artifacts.yaml`` and that replacement gets committed, this test reds —
turning a silent regeneration wipe into a loud, immediate failure instead of a
dormant data-path regression discovered later.
"""

from __future__ import annotations

import sys
from pathlib import Path

import yaml

_REPO_ROOT = Path(__file__).resolve().parents[3]
_MANIFEST = _REPO_ROOT / "data-artifacts.yaml"

_TOOLS_DIR = _REPO_ROOT / "tools"
sys.path.insert(0, str(_TOOLS_DIR))

import make_data_artifacts  # type: ignore[import-not-found]  # noqa: E402

# Pinned from tools/make_lodes_tri_county_artifact.py's generation run (see
# tests/unit/economics/circulation/test_lodes_tri_county_artifact.py for the
# matching per-year nnz proof against the artifact files themselves).
_EXPECTED_ENTRIES: dict[str, dict[str, object]] = {
    "lodes_xwalk_tri_county_hex": {
        "rows": 813,
        "sha256": "5672337f7a54fea10625ed5f11f0c9501dfad67933beac39bde50b1fd5b7bd69",
        "home": "src/babylon/data/reference/lodes/tri_county_hex_xwalk.csv.gz",
    },
    "lodes_od_tri_county_hex_2010": {
        "rows": 191332,
        "sha256": "d0036c7a0d4383a9535afefed9acadc114fc86909fcba42abc3585079db54e97",
        "home": "src/babylon/data/reference/lodes/od/mi_od_main_JT00_2010.csv.gz",
    },
    "lodes_od_tri_county_hex_2011": {
        "rows": 189957,
        "sha256": "b0947ad40e6ad0951f77ae3047d91d8acff302aa00248f71efbb41f43bdf3107",
        "home": "src/babylon/data/reference/lodes/od/mi_od_main_JT00_2011.csv.gz",
    },
    "lodes_od_tri_county_hex_2012": {
        "rows": 194577,
        "sha256": "5977626229bbe40b9d3caa43e96f199f547dbcae696c923ca1419ffee7106308",
        "home": "src/babylon/data/reference/lodes/od/mi_od_main_JT00_2012.csv.gz",
    },
    "lodes_od_tri_county_hex_2013": {
        "rows": 195680,
        "sha256": "ba5dfc842e2c5b5d0ff1654905a18f8ffec20a8e8d52bc4ac81bc504db51c86c",
        "home": "src/babylon/data/reference/lodes/od/mi_od_main_JT00_2013.csv.gz",
    },
    "lodes_od_tri_county_hex_2014": {
        "rows": 195892,
        "sha256": "dc62322ee5cc5e297c1af6f36d94185f4f2ad4a604221ce0013b61b98224477d",
        "home": "src/babylon/data/reference/lodes/od/mi_od_main_JT00_2014.csv.gz",
    },
    "lodes_od_tri_county_hex_2015": {
        "rows": 203144,
        "sha256": "32fc70ad4125f0f3f2542d5ff0d3a3a98a2184fea9b7e591aec1cbb055e1342a",
        "home": "src/babylon/data/reference/lodes/od/mi_od_main_JT00_2015.csv.gz",
    },
    "lodes_od_tri_county_hex_2016": {
        "rows": 205839,
        "sha256": "f611f106271f68a23093850632e7c8bf741f18a1dc52ef225677135e7faec1df",
        "home": "src/babylon/data/reference/lodes/od/mi_od_main_JT00_2016.csv.gz",
    },
    "lodes_od_tri_county_hex_2017": {
        "rows": 205778,
        "sha256": "08b05b000d3d38c52edb681bab4b4f02a3c968efa736c5be77d6d91bda557ef6",
        "home": "src/babylon/data/reference/lodes/od/mi_od_main_JT00_2017.csv.gz",
    },
    "lodes_od_tri_county_hex_2018": {
        "rows": 207309,
        "sha256": "fe8bdbecdc085ad9ef0121f1b345b0e36626e708028a35239b24dced20985dd0",
        "home": "src/babylon/data/reference/lodes/od/mi_od_main_JT00_2018.csv.gz",
    },
    "lodes_od_tri_county_hex_2019": {
        "rows": 205325,
        "sha256": "b1898a4e3539204862e54c8ac73d9cc6d9a0d2bdd3d7eaa56987f36abc19bf4e",
        "home": "src/babylon/data/reference/lodes/od/mi_od_main_JT00_2019.csv.gz",
    },
    "lodes_od_tri_county_hex_2020": {
        "rows": 195984,
        "sha256": "f12858b5d3e0472d0e7cc53f953feb9e273ba78374063addfce1148c7e1862cd",
        "home": "src/babylon/data/reference/lodes/od/mi_od_main_JT00_2020.csv.gz",
    },
    "lodes_od_tri_county_hex_2021": {
        "rows": 200596,
        "sha256": "1814931bb7901a9cf54cf1e8e581852936cd7d0f3037f34136d8fcca4651e413",
        "home": "src/babylon/data/reference/lodes/od/mi_od_main_JT00_2021.csv.gz",
    },
}


def _manifest_entries_by_name() -> dict[str, dict[str, object]]:
    manifest = yaml.safe_load(_MANIFEST.read_text())
    return {entry["name"]: entry for entry in manifest["artifacts"]}


def test_lodes_entries_present_in_committed_manifest_with_pinned_content() -> None:
    """The tripwire itself: every hand-registered LODES entry survives in the
    committed manifest, with its rows/sha256/home unchanged. A real
    ``make_data_artifacts.py`` regeneration (no ``--check``) would drop all
    thirteen — this assertion is what turns that into a loud, immediate CI
    failure instead of a silent data-path regression."""
    by_name = _manifest_entries_by_name()
    missing = set(_EXPECTED_ENTRIES) - set(by_name)
    assert not missing, f"LODES manifest entries missing (regeneration wipe?): {sorted(missing)}"
    for name, expected in _EXPECTED_ENTRIES.items():
        entry = by_name[name]
        assert entry["rows"] == expected["rows"], f"{name}: row count drifted"
        assert entry["sha256"] == expected["sha256"], f"{name}: sha256 drifted"
        assert entry["home"] == expected["home"], f"{name}: home path drifted"
        assert entry["generator"] == "tools/make_lodes_tri_county_artifact.py"
        assert entry["mode"] == "generate"


def test_lodes_entries_are_not_managed_by_make_data_artifacts() -> None:
    """Documents WHY the risk exists: these names are absent from the
    ``ARTIFACTS`` tuple ``generate()`` enumerates, so
    ``_rewrite_manifest_preserving_blocks(generate(db))`` — what ``main()``
    actually runs — would never reproduce them. If this assertion ever fails
    (a name collides with a real ``ARTIFACTS`` entry), the risk this test
    guards has changed shape and both this module and the ``EXCEPTION`` note
    in ``data-artifacts.yaml`` need re-reading."""
    managed_names = {spec.name for spec in make_data_artifacts.ARTIFACTS}
    collision = managed_names & set(_EXPECTED_ENTRIES)
    assert not collision, f"LODES names now managed by ARTIFACTS: {sorted(collision)}"
