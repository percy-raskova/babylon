"""Data source configuration loader for ingestion."""

from __future__ import annotations

import copy
import json
from functools import cache
from importlib import resources
from typing import Any

from babylon.utils.exceptions import ConfigurationError


@cache
def _load_source_config(source: str) -> dict[str, Any]:
    """Load a data source JSON config into memory."""
    filename = f"{source}.json"
    try:
        resource = resources.files(__package__).joinpath(filename)
    except Exception as exc:  # pragma: no cover - importlib edge case
        raise ConfigurationError(
            "Data source config not found",
            details={"source": source, "file": filename},
        ) from exc

    try:
        with resource.open("r", encoding="utf-8") as handle:
            config = json.load(handle)
    except FileNotFoundError as exc:
        raise ConfigurationError(
            "Data source config not found",
            details={"source": source, "file": filename},
        ) from exc
    except json.JSONDecodeError as exc:
        raise ConfigurationError(
            "Data source config JSON is invalid",
            details={"source": source, "file": filename, "error": str(exc)},
        ) from exc

    if not isinstance(config, dict):
        raise ConfigurationError(
            "Data source config must be a JSON object",
            details={"source": source, "file": filename},
        )

    return config


def get_source_config(source: str) -> dict[str, Any]:
    """Return a copy of the named data source configuration."""
    return copy.deepcopy(_load_source_config(source))


def _get_arcgis_section(source: str, section: str | None) -> dict[str, Any]:
    config = _load_source_config(source)
    arcgis = config.get("arcgis")
    if not isinstance(arcgis, dict):
        raise ConfigurationError(
            "Missing ArcGIS config",
            details={"source": source},
        )

    if section is None:
        return arcgis

    section_config = arcgis.get(section)
    if not isinstance(section_config, dict):
        raise ConfigurationError(
            "Missing ArcGIS section",
            details={"source": source, "section": section},
        )

    return section_config


def get_arcgis_service_url(source: str, section: str | None = None) -> str:
    """Return the ArcGIS service URL for a configured source."""
    arcgis = _get_arcgis_section(source, section)
    url = arcgis.get("service_url")
    if not isinstance(url, str) or not url:
        raise ConfigurationError(
            "ArcGIS service_url missing",
            details={"source": source, "section": section},
        )
    return url


def get_arcgis_out_fields(source: str, section: str | None = None) -> str:
    """Return out_fields for an ArcGIS source as a comma-separated string."""
    arcgis = _get_arcgis_section(source, section)
    out_fields = arcgis.get("out_fields", "*")
    if isinstance(out_fields, list):
        return ",".join(str(field) for field in out_fields)
    if isinstance(out_fields, str):
        return out_fields
    raise ConfigurationError(
        "ArcGIS out_fields must be a list or string",
        details={"source": source, "section": section},
    )


def get_arcgis_return_geometry(source: str, section: str | None = None) -> bool:
    """Return whether ArcGIS queries should include geometry."""
    arcgis = _get_arcgis_section(source, section)
    return bool(arcgis.get("return_geometry", False))


def get_data_source_meta(source: str) -> dict[str, Any]:
    """Return dimension metadata for a data source."""
    config = _load_source_config(source)
    meta = config.get("data_source")
    if not isinstance(meta, dict):
        raise ConfigurationError(
            "Missing data_source metadata",
            details={"source": source},
        )
    return copy.deepcopy(meta)


def get_type_map(source: str) -> dict[str, tuple[str, str, str, str]]:
    """Return a normalized type map for coercive infrastructure sources."""
    config = _load_source_config(source)
    raw_map = config.get("type_map")
    if not isinstance(raw_map, dict):
        raise ConfigurationError(
            "Missing type_map configuration",
            details={"source": source},
        )

    type_map: dict[str, tuple[str, str, str, str]] = {}
    for key, value in raw_map.items():
        if not isinstance(value, dict):
            raise ConfigurationError(
                "Invalid type_map entry",
                details={"source": source, "entry": key},
            )
        try:
            type_map[key] = (
                str(value["code"]),
                str(value["name"]),
                str(value["category"]),
                str(value["command_chain"]),
            )
        except KeyError as exc:
            raise ConfigurationError(
                "Incomplete type_map entry",
                details={"source": source, "entry": key, "missing": str(exc)},
            ) from exc

    return type_map


def get_default_type(source: str) -> tuple[str, str, str, str]:
    """Return the default coercive type tuple for a source."""
    config = _load_source_config(source)
    raw_default = config.get("default_type")
    if not isinstance(raw_default, dict):
        raise ConfigurationError(
            "Missing default_type configuration",
            details={"source": source},
        )
    try:
        return (
            str(raw_default["code"]),
            str(raw_default["name"]),
            str(raw_default["category"]),
            str(raw_default["command_chain"]),
        )
    except KeyError as exc:
        raise ConfigurationError(
            "Incomplete default_type configuration",
            details={"source": source, "missing": str(exc)},
        ) from exc


def get_list_field(source: str, field_name: str) -> list[str]:
    """Return a required list field from a source configuration."""
    config = _load_source_config(source)
    raw_list = config.get(field_name)
    if not isinstance(raw_list, list):
        raise ConfigurationError(
            "Expected list field in data source config",
            details={"source": source, "field": field_name},
        )
    return [str(item) for item in raw_list]


__all__ = [
    "get_arcgis_out_fields",
    "get_arcgis_return_geometry",
    "get_arcgis_service_url",
    "get_data_source_meta",
    "get_default_type",
    "get_list_field",
    "get_source_config",
    "get_type_map",
]
