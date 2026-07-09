"""External data source coordinates (ArcGIS + Services composed via ExternalData).

Spec 058: extracted from the historical ``babylon.config.defines`` monolith.
Re-exported via :mod:`babylon.config.defines.__init__`; composed into :class:`GameDefines` in :mod:`babylon.config.defines._assembler`.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ArcGISDefines(BaseModel):
    """ArcGIS organization and host configuration for external data sources.

    Different federal agencies host HIFLD and infrastructure data on various
    ArcGIS organizations. This configuration centralizes the organization IDs
    and hosts to allow easy updates when services migrate.

    Current organization mapping (as of 2024):
    - FEMA RAPT: Prison Boundaries, Law Enforcement (services.arcgis.com)
    - Esri US Federal: MIRTA Military Installations (services2.arcgis.com)
    - HIFLD Legacy: Some services still work (services1.arcgis.com)
    """

    model_config = ConfigDict(frozen=True)

    # FEMA RAPT (Resilience Analysis and Planning Tool) - primary HIFLD source
    fema_rapt_org: str = Field(
        default="XG15cJAlne2vxtgt",
        description="FEMA RAPT organization ID on ArcGIS",
    )
    fema_rapt_host: str = Field(
        default="services.arcgis.com",
        description="FEMA RAPT ArcGIS host domain",
    )

    # Esri US Federal Data - MIRTA military installations
    esri_federal_org: str = Field(
        default="FiaPA4ga0iQKduv3",
        description="Esri US Federal Data organization ID",
    )
    esri_federal_host: str = Field(
        default="services2.arcgis.com",
        description="Esri US Federal Data host domain",
    )

    # Legacy HIFLD organization (some services still work)
    hifld_legacy_org: str = Field(
        default="Hp6G80Pky0om7QvQ",
        description="Legacy HIFLD organization ID",
    )
    hifld_legacy_host: str = Field(
        default="services1.arcgis.com",
        description="Legacy HIFLD host domain",
    )


class ServicesDefines(BaseModel):
    """ArcGIS FeatureServer service names and layers.

    Service names can be overridden for testing or alternative data sources.
    Layer numbers are important as some services (like Prison_Boundaries)
    have data on non-default layers.
    """

    model_config = ConfigDict(frozen=True)

    # Prison Boundaries (FEMA RAPT)
    prison_boundaries: str = Field(
        default="Prison_Boundaries_RAPT",
        description="Prison Boundaries service name",
    )
    prison_boundaries_layer: int = Field(
        default=1,
        ge=0,
        description="Prison Boundaries layer (Note: Layer 1, not 0)",
    )

    # Law Enforcement (FEMA RAPT)
    law_enforcement: str = Field(
        default="Local_Law_Enforcement_Locations_RAPT",
        description="Law enforcement locations service name",
    )
    law_enforcement_layer: int = Field(
        default=0,
        ge=0,
        description="Law enforcement layer",
    )

    # MIRTA (Esri US Federal)
    mirta_polygons: str = Field(
        default="MIRTA_Polygons_A_view",
        description="MIRTA military installations service name",
    )
    mirta_layer: int = Field(
        default=0,
        ge=0,
        description="MIRTA layer",
    )

    # Electric Grid (Legacy HIFLD)
    electric_transmission: str = Field(
        default="Electric_Power_Transmission_Lines",
        description="Electric transmission lines service name",
    )
    electric_transmission_layer: int = Field(
        default=0,
        ge=0,
        description="Electric transmission layer",
    )


class ExternalDataDefines(BaseModel):
    """External data source configuration.

    Centralizes ArcGIS organization IDs, hosts, and service names for
    HIFLD and related infrastructure data sources. This enables:
    1. Easy updates when services migrate between organizations
    2. Testing with alternative data sources
    3. Clear documentation of data source provenance
    """

    model_config = ConfigDict(frozen=True)

    arcgis: ArcGISDefines = Field(
        default_factory=ArcGISDefines,
        description=(
            "ArcGIS organization IDs and host domains (FEMA RAPT, Esri US "
            "Federal, legacy HIFLD) used to build external FeatureServer URLs."
        ),
    )
    services: ServicesDefines = Field(
        default_factory=ServicesDefines,
        description=(
            "ArcGIS FeatureServer service names and layer numbers for the "
            "HIFLD/infrastructure data sources (prison boundaries, law "
            "enforcement, MIRTA, electric transmission)."
        ),
    )

    def build_service_url(
        self,
        host: str,
        org: str,
        service: str,
        layer: int = 0,
    ) -> str:
        """Build a complete ArcGIS FeatureServer URL.

        Args:
            host: ArcGIS host domain (e.g., "services.arcgis.com")
            org: Organization ID (e.g., "XG15cJAlne2vxtgt")
            service: Service name (e.g., "Prison_Boundaries_RAPT")
            layer: Layer number (default 0)

        Returns:
            Complete FeatureServer URL
        """
        return f"https://{host}/{org}/arcgis/rest/services/{service}/FeatureServer/{layer}"

    def prison_boundaries_url(self) -> str:
        """Get the Prison Boundaries FeatureServer URL."""
        return self.build_service_url(
            host=self.arcgis.fema_rapt_host,
            org=self.arcgis.fema_rapt_org,
            service=self.services.prison_boundaries,
            layer=self.services.prison_boundaries_layer,
        )

    def law_enforcement_url(self) -> str:
        """Get the Law Enforcement Locations FeatureServer URL."""
        return self.build_service_url(
            host=self.arcgis.fema_rapt_host,
            org=self.arcgis.fema_rapt_org,
            service=self.services.law_enforcement,
            layer=self.services.law_enforcement_layer,
        )

    def mirta_url(self) -> str:
        """Get the MIRTA Military Installations FeatureServer URL."""
        return self.build_service_url(
            host=self.arcgis.esri_federal_host,
            org=self.arcgis.esri_federal_org,
            service=self.services.mirta_polygons,
            layer=self.services.mirta_layer,
        )

    def electric_transmission_url(self) -> str:
        """Get the Electric Transmission Lines FeatureServer URL."""
        return self.build_service_url(
            host=self.arcgis.hifld_legacy_host,
            org=self.arcgis.hifld_legacy_org,
            service=self.services.electric_transmission,
            layer=self.services.electric_transmission_layer,
        )


__all__ = [
    "ArcGISDefines",
    "ExternalDataDefines",
    "ServicesDefines",
]
