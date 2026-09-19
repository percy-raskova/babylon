"""Health discovery and configuration contracts; injected clients never infer."""

from __future__ import annotations

import os
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
from pydantic import SecretStr

from babylon.intelligence.providers import (
    DEFAULT_BUNDLED_BASE_URL,
    DEFAULT_EXTERNAL_BASE_URL,
    IntelligenceSettings,
    MuteProbe,
    OpenAICompatProbe,
    ProviderEndpoint,
    ProviderError,
    ProviderKind,
    ProviderProbe,
    load_settings,
    resolve_provider_probe,
)


class FakeClient:
    """Only the model-list health surface is admitted by these tests."""

    def __init__(self, *, healthy: bool = True) -> None:
        self.healthy = healthy
        self.options: list[tuple[float, int]] = []
        self.requests = 0

    @property
    def models(self) -> FakeClient:
        return self

    def list(self) -> object:
        self.requests += 1
        if not self.healthy:
            raise ConnectionError("connection refused")
        return object()

    def with_options(self, *, timeout: float, max_retries: int) -> FakeClient:
        self.options.append((timeout, max_retries))
        return self


def factory_for(clients: dict[str, FakeClient]) -> Callable[..., FakeClient]:
    def factory(*, base_url: str, **_: Any) -> FakeClient:
        return clients.get(base_url, FakeClient(healthy=False))

    return factory


def settings_with(**overrides: Any) -> IntelligenceSettings:
    base: dict[str, Any] = {"mode": "auto", "timeout_s": 5.0}
    base.update(overrides)
    return IntelligenceSettings(**base)


CF_URL = "https://babylon-api.example.workers.dev/v1"


# ---------------------------------------------------------------------------
# Settings (§A3)
# ---------------------------------------------------------------------------


def test_settings_defaults_are_local_first() -> None:
    s = load_settings(config_path=Path("/nonexistent/config.toml"), env={})
    assert s.mode == "auto"
    assert s.bundled_base_url == DEFAULT_BUNDLED_BASE_URL
    assert s.external_base_url == DEFAULT_EXTERNAL_BASE_URL
    assert s.cloudflare_base_url is None  # cloud is opt-in, never default (D2)
    assert s.cloudflare_api_key is None


def test_settings_config_toml_over_defaults(tmp_path: Path) -> None:
    cfg = tmp_path / "config.toml"
    cfg.write_text(
        f'[intelligence]\nmode = "external"\ntimeout_s = 9.5\ncloudflare_base_url = "{CF_URL}"\n'
    )
    s = load_settings(config_path=cfg, env={})
    assert s.mode == "external"
    assert s.timeout_s == 9.5
    assert s.cloudflare_base_url == CF_URL


def test_settings_env_over_config(tmp_path: Path) -> None:
    cfg = tmp_path / "config.toml"
    cfg.write_text('[intelligence]\nmode = "external"\n')
    s = load_settings(config_path=cfg, env={"BABYLON_INTEL_MODE": "mute"})
    assert s.mode == "mute"  # wrapper/env authority beats file (§A3)


def test_credentials_file_loads_key_and_warns_on_loose_perms(
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    cfg_dir = tmp_path / "babylon"
    cfg_dir.mkdir()
    creds = cfg_dir / "credentials"
    creds.write_text('[cloudflare]\napi_key = "bk_testtoken1234567890"\n')
    os.chmod(creds, 0o644)  # deliberately loose
    with caplog.at_level("WARNING", logger="babylon.intelligence.providers"):
        s = load_settings(
            config_path=cfg_dir / "config.toml",
            env={"BABYLON_CONFIG_DIR": str(cfg_dir)},
        )
    assert s.cloudflare_api_key is not None
    assert s.cloudflare_api_key.get_secret_value() == "bk_testtoken1234567890"
    assert any("0600" in r.message for r in caplog.records)  # loud, not fatal


def test_env_key_overrides_credentials_file(tmp_path: Path) -> None:
    cfg_dir = tmp_path / "babylon"
    cfg_dir.mkdir()
    (cfg_dir / "credentials").write_text('[cloudflare]\napi_key = "bk_from_file"\n')
    s = load_settings(
        config_path=cfg_dir / "config.toml",
        env={
            "BABYLON_CONFIG_DIR": str(cfg_dir),
            "BABYLON_INTEL_CLOUDFLARE_KEY": "bk_from_env",
        },
    )
    assert s.cloudflare_api_key is not None
    assert s.cloudflare_api_key.get_secret_value() == "bk_from_env"


# ---------------------------------------------------------------------------
# Resolution (§A7.6: bundled → external → cloudflare-if-keyed → mute)
# ---------------------------------------------------------------------------


def test_resolve_prefers_bundled_when_healthy() -> None:
    clients = {
        DEFAULT_BUNDLED_BASE_URL: FakeClient(healthy=True),
        DEFAULT_EXTERNAL_BASE_URL: FakeClient(healthy=True),
    }
    p = resolve_provider_probe(settings_with(), client_factory=factory_for(clients))
    assert p.endpoint.kind is ProviderKind.BUNDLED


def test_resolve_falls_through_to_external() -> None:
    clients = {
        DEFAULT_BUNDLED_BASE_URL: FakeClient(healthy=False),
        DEFAULT_EXTERNAL_BASE_URL: FakeClient(healthy=True),
    }
    p = resolve_provider_probe(settings_with(), client_factory=factory_for(clients))
    assert p.endpoint.kind is ProviderKind.EXTERNAL


def test_resolve_cloudflare_only_when_keyed() -> None:
    clients = {CF_URL: FakeClient(healthy=True)}
    # url configured but NO key → lane not even considered → mute
    p = resolve_provider_probe(
        settings_with(cloudflare_base_url=CF_URL),
        client_factory=factory_for(clients),
    )
    assert isinstance(p, MuteProbe)
    # keyed → lane considered and wins over dead local lanes
    p2 = resolve_provider_probe(
        settings_with(cloudflare_base_url=CF_URL, cloudflare_api_key="bk_x" * 6),
        client_factory=factory_for(clients),
    )
    assert p2.endpoint.kind is ProviderKind.CLOUDFLARE


def test_resolve_everything_dead_yields_mute_never_raises() -> None:
    p = resolve_provider_probe(settings_with(), client_factory=factory_for({}))
    assert isinstance(p, MuteProbe)
    assert p.health().ok  # silence is always available


def test_mode_override_mute_skips_probing() -> None:
    def exploding_factory(**_: Any) -> FakeClient:  # pragma: no cover
        raise AssertionError("mute mode must not build clients")

    p = resolve_provider_probe(settings_with(mode="mute"), client_factory=exploding_factory)
    assert isinstance(p, MuteProbe)


def test_mode_override_cloudflare_unconfigured_degrades_to_mute() -> None:
    p = resolve_provider_probe(settings_with(mode="cloudflare"), client_factory=factory_for({}))
    assert isinstance(p, MuteProbe)


@pytest.mark.parametrize("timeout_s, expected", [(30.0, 2.0), (0.25, 0.25)])
def test_health_uses_bounded_timeout_without_retries(timeout_s: float, expected: float) -> None:
    client = FakeClient()
    probe = OpenAICompatProbe(
        ProviderEndpoint(
            kind=ProviderKind.EXTERNAL, base_url=DEFAULT_EXTERNAL_BASE_URL, timeout_s=timeout_s
        ),
        client_factory=lambda **_: client,
    )
    assert isinstance(probe, ProviderProbe)
    assert probe.health().ok
    assert client.options == [(expected, 0)]
    assert client.requests == 1


def test_health_passes_credential_only_to_client() -> None:
    observed: dict[str, Any] = {}

    def factory(**kwargs: Any) -> FakeClient:
        observed.update(kwargs)
        return FakeClient()

    endpoint = ProviderEndpoint(
        kind=ProviderKind.CLOUDFLARE, base_url=CF_URL, api_key=SecretStr("operator-key")
    )
    probe = OpenAICompatProbe(endpoint, client_factory=factory)
    assert probe.health().ok
    assert observed["api_key"] == "operator-key"
    assert "operator-key" not in repr(endpoint)
    assert "operator-key" not in probe.health().detail


def test_unreachable_health_reports_failure() -> None:
    probe = OpenAICompatProbe(
        ProviderEndpoint(kind=ProviderKind.EXTERNAL, base_url=DEFAULT_EXTERNAL_BASE_URL),
        client_factory=lambda **_: FakeClient(healthy=False),
    )
    health = probe.health()
    assert not health.ok
    assert health.kind is ProviderKind.EXTERNAL
    assert "connection refused" in health.detail


def test_explicit_external_mode_does_not_probe_other_lanes() -> None:
    bundled = FakeClient()
    external = FakeClient()
    probe = resolve_provider_probe(
        settings_with(mode="external"),
        client_factory=factory_for(
            {
                DEFAULT_BUNDLED_BASE_URL: bundled,
                DEFAULT_EXTERNAL_BASE_URL: external,
            }
        ),
    )
    assert probe.endpoint.kind is ProviderKind.EXTERNAL
    assert bundled.requests == 0
    assert external.requests == 1


@pytest.mark.parametrize("timeout", ["0", "-1", "nan", "inf", "invalid"])
def test_invalid_timeout_has_actionable_config_error(tmp_path: Path, timeout: str) -> None:
    with pytest.raises(ProviderError, match="timeout"):
        load_settings(
            config_path=tmp_path / "missing.toml",
            env={
                "BABYLON_CONFIG_DIR": str(tmp_path),
                "BABYLON_INTEL_TIMEOUT_S": timeout,
            },
        )


def test_invalid_config_is_not_silently_ignored(tmp_path: Path) -> None:
    cfg = tmp_path / "config.toml"
    cfg.write_text("[invalid syntax")
    with pytest.raises(ProviderError, match="cannot read"):
        load_settings(config_path=cfg, env={"BABYLON_CONFIG_DIR": str(tmp_path)})


def test_health_failure_redacts_credential() -> None:
    class RejectedClient(FakeClient):
        def list(self) -> object:
            raise ConnectionError("rejected operator-secret")

    probe = OpenAICompatProbe(
        ProviderEndpoint(
            kind=ProviderKind.CLOUDFLARE, base_url=CF_URL, api_key=SecretStr("operator-secret")
        ),
        client_factory=lambda **_: RejectedClient(),
    )
    health = probe.health()
    assert not health.ok
    assert health.detail == "rejected [redacted]"


def test_removed_model_configuration_fails_clearly(tmp_path: Path) -> None:
    cfg = tmp_path / "config.toml"
    cfg.write_text('[intelligence]\nexternal_chat_model = "unused"\n')
    with pytest.raises(ProviderError, match="unknown intelligence settings: external_chat_model"):
        load_settings(config_path=cfg, env={"BABYLON_CONFIG_DIR": str(tmp_path)})
