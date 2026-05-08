"""Class composition and accumulation dynamics (FRED DFA-derived).

Spec 058: extracted from the historical ``babylon.config.defines`` monolith.
Re-exported via :mod:`babylon.config.defines.__init__`; composed into :class:`GameDefines` in :mod:`babylon.config.defines._assembler`.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ClassDynamicsDefines(BaseModel):
    """Class dynamics coefficients (FRED DFA-derived, Feature 016).

    Parameters fitted to FRED Distributional Financial Accounts (2015-2025)
    for class wealth flow dynamics.
    """

    model_config = ConfigDict(frozen=True)

    alpha_21: float = Field(
        default=0.0006,
        ge=0.0,
        le=0.01,
        description="Extraction rate from petty bourgeoisie to bourgeoisie (quarterly)",
    )
    gamma_3: float = Field(
        default=0.0057,
        ge=0.0,
        le=0.1,
        description="Imperial rent formation rate — superwages to core workers (quarterly)",
    )
    equilibrium_w1: float = Field(
        default=0.305,
        ge=0.0,
        le=1.0,
        description="Target equilibrium wealth share for class 1 (bourgeoisie)",
    )
    equilibrium_w2: float = Field(
        default=0.382,
        ge=0.0,
        le=1.0,
        description="Target equilibrium wealth share for class 2 (petty bourgeoisie)",
    )
    equilibrium_w3: float = Field(
        default=0.294,
        ge=0.0,
        le=1.0,
        description="Target equilibrium wealth share for class 3 (proletariat)",
    )
    equilibrium_w4: float = Field(
        default=0.020,
        ge=0.0,
        le=1.0,
        description="Target equilibrium wealth share for class 4 (lumpenproletariat)",
    )

    # --- Extraction rates (FRED DFA-fitted, per quarter) ---
    alpha_41: float = Field(
        default=0.0000,
        ge=0.0,
        le=0.01,
        description="FRED DFA-fitted: proletariat -> bourgeoisie extraction rate (quarterly)",
    )
    alpha_31: float = Field(
        default=0.0000,
        ge=0.0,
        le=0.01,
        description="FRED DFA-fitted: labor aristocracy -> bourgeoisie extraction rate (quarterly)",
    )
    alpha_32: float = Field(
        default=0.0000,
        ge=0.0,
        le=0.01,
        description="FRED DFA-fitted: labor aristocracy -> petty bourgeoisie extraction rate (quarterly)",
    )
    alpha_42: float = Field(
        default=0.0000,
        ge=0.0,
        le=0.01,
        description="FRED DFA-fitted: proletariat -> petty bourgeoisie extraction rate (quarterly)",
    )
    alpha_43: float = Field(
        default=0.0000,
        ge=0.0,
        le=0.01,
        description="FRED DFA-fitted: proletariat -> labor aristocracy extraction rate (quarterly)",
    )

    # --- Redistribution rates (FRED DFA-fitted) ---
    delta_1: float = Field(
        default=0.0010,
        ge=0.0,
        le=0.1,
        description="FRED DFA-fitted: redistribution from bourgeoisie (taxation, quarterly)",
    )
    delta_2: float = Field(
        default=0.0020,
        ge=0.0,
        le=0.1,
        description="FRED DFA-fitted: redistribution from petty bourgeoisie (quarterly)",
    )
    delta_3: float = Field(
        default=0.0010,
        ge=0.0,
        le=0.1,
        description="FRED DFA-fitted: redistribution from labor aristocracy (quarterly)",
    )

    # --- Damping coefficients (game design, negative = mean-reverting) ---
    beta_1: float = Field(
        default=-0.10,
        ge=-1.0,
        le=0.0,
        description="Game design: bourgeoisie damping coefficient",
    )
    beta_2: float = Field(
        default=-0.15,
        ge=-1.0,
        le=0.0,
        description="Game design: petty bourgeoisie damping coefficient",
    )
    beta_3: float = Field(
        default=-0.10,
        ge=-1.0,
        le=0.0,
        description="Game design: labor aristocracy damping coefficient",
    )
    beta_4: float = Field(
        default=-0.05,
        ge=-1.0,
        le=0.0,
        description="Game design: proletariat damping coefficient",
    )

    # --- Oscillation frequencies (game design, strictly positive) ---
    omega_1: float = Field(
        default=0.05,
        gt=0.0,
        le=1.0,
        description="Game design: bourgeoisie oscillation frequency",
    )
    omega_2: float = Field(
        default=0.08,
        gt=0.0,
        le=1.0,
        description="Game design: petty bourgeoisie oscillation frequency",
    )
    omega_3: float = Field(
        default=0.05,
        gt=0.0,
        le=1.0,
        description="Game design: labor aristocracy oscillation frequency",
    )
    omega_4: float = Field(
        default=0.03,
        gt=0.0,
        le=1.0,
        description="Game design: proletariat oscillation frequency",
    )


class RentCircuitDefines(BaseModel):
    """Parameters for ground rent extraction in Volume III equalization (Feature 043)."""

    model_config = ConfigDict(frozen=True)

    absolute_rent_fraction: float = Field(
        default=0.15,
        ge=0.0,
        le=0.5,
        description="Fraction of extracted volume III rent considered absolute rent.",
    )
    differential_rent_elasticity: float = Field(
        default=1.2,
        ge=0.1,
        le=5.0,
        description="Responsiveness of differential rent given local surplus intensity.",
    )


class ClassSystemDefines(BaseModel):
    """Unified class system coefficients (Feature 038).

    Centralizes all tunable coefficients for the unified class system:
    filtration parameters, home ownership proxy, and the 5x5 class-pair
    solidarity matrix.

    Args:
        trust_land_discount: Fed SCF / BIA discount on effective wealth for
            FIRST_NATIONS trust land property. 0.5 = 50% reduction.
        documentation_exclusion_factor: Discount on effective wealth for
            UNDOCUMENTED households. 0.6 = 40% reduction.
        equity_factor: Fraction of homeowners with meaningful equity.
            Calibrated: 65% ownership * 0.6 = 39% ~ 40% LA share.
        base_class_solidarity: Symmetric 5x5 class-pair base solidarity
            matrix (15 unique values in upper triangle including diagonal).
    """

    model_config = ConfigDict(frozen=True)

    trust_land_discount: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description=(
            "Fed SCF / BIA: discount on effective wealth for FIRST_NATIONS "
            "trust land property. 0.5 = 50% reduction in effective wealth percentile."
        ),
    )
    documentation_exclusion_factor: float = Field(
        default=0.6,
        ge=0.0,
        le=1.0,
        description=(
            "Game design: discount on effective wealth for UNDOCUMENTED households. "
            "0.6 = 40% reduction. Reflects structural exclusion from formal "
            "property/banking/labor protections."
        ),
    )
    equity_factor: float = Field(
        default=0.6,
        ge=0.0,
        le=1.0,
        description=(
            "Feature 043: Absolute threshold test on equity required for LA classification. "
            "Formerly a population-level numeric scaler."
        ),
    )
    base_class_solidarity: dict[str, dict[str, float]] = Field(
        default_factory=lambda: {
            "BOURGEOISIE": {
                "BOURGEOISIE": 0.70,
                "PETIT_BOURGEOISIE": 0.30,
                "LABOR_ARISTOCRACY": 0.10,
                "PROLETARIAT": 0.00,
                "LUMPENPROLETARIAT": 0.00,
            },
            "PETIT_BOURGEOISIE": {
                "PETIT_BOURGEOISIE": 0.50,
                "LABOR_ARISTOCRACY": 0.40,
                "PROLETARIAT": 0.15,
                "LUMPENPROLETARIAT": 0.05,
            },
            "LABOR_ARISTOCRACY": {
                "LABOR_ARISTOCRACY": 0.60,
                "PROLETARIAT": 0.30,
                "LUMPENPROLETARIAT": 0.10,
            },
            "PROLETARIAT": {
                "PROLETARIAT": 0.80,
                "LUMPENPROLETARIAT": 0.50,
            },
            "LUMPENPROLETARIAT": {
                "LUMPENPROLETARIAT": 0.60,
            },
        },
        description=(
            "Game design: symmetric 5x5 class-pair base solidarity matrix. "
            "15 unique values (upper triangle including diagonal). "
            "Class proximity yields higher base solidarity."
        ),
    )

    @model_validator(mode="after")
    def _validate_solidarity_matrix(self) -> ClassSystemDefines:
        """Ensure all matrix entries are in [0.0, 1.0]."""
        for outer_key, inner_dict in self.base_class_solidarity.items():
            for inner_key, value in inner_dict.items():
                if not 0.0 <= value <= 1.0:
                    msg = (
                        f"base_class_solidarity[{outer_key!r}][{inner_key!r}] = {value} "
                        f"is outside [0.0, 1.0]"
                    )
                    raise ValueError(msg)
        return self

    def get_base_solidarity(self, class_a: str, class_b: str) -> float:
        """Symmetric lookup into the class-pair solidarity matrix.

        Args:
            class_a: ClassPosition name (e.g. "PROLETARIAT").
            class_b: ClassPosition name (e.g. "LABOR_ARISTOCRACY").

        Returns:
            Base solidarity value, or 0.0 for unknown pairs.
        """
        if class_a in self.base_class_solidarity:
            inner = self.base_class_solidarity[class_a]
            if class_b in inner:
                return inner[class_b]
        if class_b in self.base_class_solidarity:
            inner = self.base_class_solidarity[class_b]
            if class_a in inner:
                return inner[class_a]
        return 0.0


__all__ = [
    "ClassDynamicsDefines",
    "ClassSystemDefines",
    "RentCircuitDefines",
]
