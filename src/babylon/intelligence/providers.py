"""Operator endpoint configuration and health probes.

``babylon doctor`` checks configured OpenAI-compatible ``/models`` endpoints
in local-first order: bundled, external, keyed Cloudflare, then mute. This
module does not start a server or provide generation or embedding APIs.
Credentials stay in the operator configuration; the engine never reads them.
"""

from __future__ import annotations

import logging
import os
import stat
import tomllib
from collections.abc import Mapping
from enum import StrEnum
from pathlib import Path
from typing import Any, Literal, Protocol, runtime_checkable

from openai import OpenAI
from pydantic import BaseModel, ConfigDict, Field, SecretStr, ValidationError

logger = logging.getLogger("babylon.intelligence.providers")

__all__ = [
    "ProviderKind",
    "ProviderEndpoint",
    "IntelligenceSettings",
    "ProviderHealth",
    "ProviderError",
    "ProviderProbe",
    "OpenAICompatProbe",
    "MuteProbe",
    "load_settings",
    "resolve_provider_probe",
]

DEFAULT_BUNDLED_BASE_URL = "http://127.0.0.1:8737/v1"
DEFAULT_EXTERNAL_BASE_URL = "http://127.0.0.1:11434/v1"
DEFAULT_TIMEOUT_S = 30.0
PROBE_TIMEOUT_S = 2.0


class ProviderKind(StrEnum):
    BUNDLED = "bundled"
    EXTERNAL = "external"
    CLOUDFLARE = "cloudflare"
    MUTE = "mute"


class ProviderError(RuntimeError):
    """An operator configuration could not be loaded or validated."""


class ProviderEndpoint(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    kind: ProviderKind
    base_url: str
    api_key: SecretStr | None = None
    timeout_s: float = Field(default=DEFAULT_TIMEOUT_S, gt=0, allow_inf_nan=False)


class ProviderHealth(BaseModel):
    model_config = ConfigDict(frozen=True)

    ok: bool
    kind: ProviderKind
    detail: str = ""


@runtime_checkable
class ProviderProbe(Protocol):
    """An endpoint and its current reachability; no inference surface."""

    endpoint: ProviderEndpoint

    def health(self) -> ProviderHealth: ...


class IntelligenceSettings(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    mode: Literal["auto", "bundled", "external", "cloudflare", "mute"] = "auto"
    timeout_s: float = Field(default=DEFAULT_TIMEOUT_S, gt=0, allow_inf_nan=False)
    bundled_base_url: str = DEFAULT_BUNDLED_BASE_URL
    external_base_url: str = DEFAULT_EXTERNAL_BASE_URL
    cloudflare_base_url: str | None = None
    cloudflare_api_key: SecretStr | None = None


def _config_dir(env: Mapping[str, str]) -> Path:
    if "BABYLON_CONFIG_DIR" in env:
        return Path(env["BABYLON_CONFIG_DIR"])
    xdg = env.get("XDG_CONFIG_HOME")
    base = Path(xdg) if xdg else Path.home() / ".config"
    return base / "babylon"


def _read_toml(path: Path) -> dict[str, Any]:
    try:
        with path.open("rb") as fh:
            return tomllib.load(fh)
    except FileNotFoundError:
        return {}
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise ProviderError(f"cannot read {path}: {exc}") from exc


def _load_credentials(path: Path) -> SecretStr | None:
    if not path.exists():
        return None
    mode = stat.S_IMODE(path.stat().st_mode)
    if mode & 0o077:
        logger.warning(
            "credentials file %s has mode %o; expected 0600 — run: chmod 600 %s",
            path,
            mode,
            path,
        )
    data = _read_toml(path)
    cloudflare = data.get("cloudflare", {})
    if not isinstance(cloudflare, dict):
        raise ProviderError(f"{path}: cloudflare must be a TOML table")
    key = cloudflare.get("api_key")
    return SecretStr(key) if isinstance(key, str) and key else None


def load_settings(
    config_path: Path | None = None,
    env: Mapping[str, str] | None = None,
) -> IntelligenceSettings:
    """Load environment overrides, then config.toml values, then defaults."""
    env = os.environ if env is None else env
    cfg_dir = _config_dir(env)
    cfg = _read_toml(config_path if config_path is not None else cfg_dir / "config.toml")
    intel = cfg.get("intelligence", {})
    if not isinstance(intel, dict):
        raise ProviderError("intelligence must be a TOML table")
    unknown = set(intel) - (IntelligenceSettings.model_fields.keys() - {"cloudflare_api_key"})
    if unknown:
        raise ProviderError(f"unknown intelligence settings: {', '.join(sorted(unknown))}")
    credentials = _load_credentials(cfg_dir / "credentials")

    def pick(env_key: str, toml_key: str, default: Any) -> Any:
        return env.get(env_key) or intel.get(toml_key, default)

    api_key_env = env.get("BABYLON_INTEL_CLOUDFLARE_KEY")
    api_key = SecretStr(api_key_env) if api_key_env else credentials
    try:
        return IntelligenceSettings.model_validate(
            {
                "mode": str(pick("BABYLON_INTEL_MODE", "mode", "auto")).lower(),
                "timeout_s": pick("BABYLON_INTEL_TIMEOUT_S", "timeout_s", DEFAULT_TIMEOUT_S),
                "bundled_base_url": pick(
                    "BABYLON_INTEL_BUNDLED_URL", "bundled_base_url", DEFAULT_BUNDLED_BASE_URL
                ),
                "external_base_url": pick(
                    "BABYLON_INTEL_EXTERNAL_URL", "external_base_url", DEFAULT_EXTERNAL_BASE_URL
                ),
                "cloudflare_base_url": pick(
                    "BABYLON_INTEL_CLOUDFLARE_URL", "cloudflare_base_url", None
                )
                or None,
                "cloudflare_api_key": api_key,
            }
        )
    except ValidationError as exc:
        # Field names and reasons are useful; input values may contain secrets.
        detail = "; ".join(f"{error['loc'][0]}: {error['msg']}" for error in exc.errors())
        raise ProviderError(f"invalid intelligence configuration: {detail}") from exc


class _ModelsClient(Protocol):
    def list(self) -> object: ...


class _ProbeClient(Protocol):
    @property
    def models(self) -> _ModelsClient: ...

    def with_options(self, *, timeout: float, max_retries: int) -> _ProbeClient: ...


class ClientFactory(Protocol):
    def __call__(
        self, *, base_url: str, api_key: str, timeout: float, max_retries: int
    ) -> _ProbeClient: ...


def _default_client_factory(
    *, base_url: str, api_key: str, timeout: float, max_retries: int
) -> _ProbeClient:
    return OpenAI(base_url=base_url, api_key=api_key, timeout=timeout, max_retries=max_retries)


class OpenAICompatProbe:
    """Check model-list reachability without generating text or embeddings."""

    def __init__(
        self, endpoint: ProviderEndpoint, client_factory: ClientFactory | None = None
    ) -> None:
        self.endpoint = endpoint
        factory = client_factory or _default_client_factory
        self._client = factory(
            base_url=endpoint.base_url,
            api_key=endpoint.api_key.get_secret_value() if endpoint.api_key else "babylon-local",
            timeout=min(endpoint.timeout_s, PROBE_TIMEOUT_S),
            max_retries=0,
        )

    def health(self) -> ProviderHealth:
        try:
            self._client.with_options(
                timeout=min(self.endpoint.timeout_s, PROBE_TIMEOUT_S), max_retries=0
            ).models.list()
        except Exception as exc:
            detail = str(exc)
            if self.endpoint.api_key:
                detail = detail.replace(self.endpoint.api_key.get_secret_value(), "[redacted]")
            return ProviderHealth(ok=False, kind=self.endpoint.kind, detail=detail)
        return ProviderHealth(ok=True, kind=self.endpoint.kind, detail=self.endpoint.base_url)


class MuteProbe:
    """An available, network-free operator mode."""

    def __init__(self) -> None:
        self.endpoint = ProviderEndpoint(kind=ProviderKind.MUTE, base_url="about:mute")

    def health(self) -> ProviderHealth:
        return ProviderHealth(ok=True, kind=ProviderKind.MUTE, detail="no endpoint required")


def _candidates(settings: IntelligenceSettings) -> list[ProviderEndpoint]:
    lanes = [
        ProviderEndpoint(
            kind=ProviderKind.BUNDLED,
            base_url=settings.bundled_base_url,
            timeout_s=settings.timeout_s,
        ),
        ProviderEndpoint(
            kind=ProviderKind.EXTERNAL,
            base_url=settings.external_base_url,
            timeout_s=settings.timeout_s,
        ),
    ]
    if settings.cloudflare_base_url and settings.cloudflare_api_key:
        lanes.append(
            ProviderEndpoint(
                kind=ProviderKind.CLOUDFLARE,
                base_url=settings.cloudflare_base_url,
                api_key=settings.cloudflare_api_key,
                timeout_s=settings.timeout_s,
            )
        )
    return lanes


def resolve_provider_probe(
    settings: IntelligenceSettings | None = None,
    client_factory: ClientFactory | None = None,
) -> ProviderProbe:
    """Return the first reachable configured endpoint, otherwise mute."""
    settings = settings if settings is not None else load_settings()
    if settings.mode == "mute":
        return MuteProbe()
    lanes = _candidates(settings)
    if settings.mode != "auto":
        lanes = [ep for ep in lanes if ep.kind.value == settings.mode]
        if not lanes:
            logger.warning(
                "provider %r requested but not configured (missing base_url or credential); "
                "using mute",
                settings.mode,
            )
            return MuteProbe()
    for endpoint in lanes:
        probe = OpenAICompatProbe(endpoint, client_factory=client_factory)
        health = probe.health()
        if health.ok:
            logger.info("provider endpoint: %s (%s)", endpoint.kind.value, endpoint.base_url)
            return probe
        logger.debug("provider %s unavailable: %s", endpoint.kind.value, health.detail)
    logger.warning("no provider endpoint reachable; using mute")
    return MuteProbe()
