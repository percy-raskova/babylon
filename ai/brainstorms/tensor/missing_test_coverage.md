# Missing Test Coverage: Empirical Validation

Your current tests validate *internal consistency* (math works, theory checks out with constructed examples). What's missing are tests that validate *empirical fidelity* — do the tensors match reality?

---

## 1. ACCOUNTING IDENTITY TESTS (Real Data)

**Gap**: You test `allocated + excluded = total` with mocks. Need it against real QCEW.

```python
# tests/integration/data/test_qcew_accounting.py

class TestQCEWAccountingIdentity:
    """Total wages from QCEW must equal tensor allocation + exclusions."""

    @pytest.fixture
    def wayne_qcew_2022(self, qcew_session):
        """Load actual Wayne County QCEW for 2022."""
        return qcew_session.query(QcewRaw2022).filter(
            QcewRaw2022.area_fips == "26163",
            QcewRaw2022.own_code == "5",  # Private sector
            QcewRaw2022.qtr == "A",
        ).all()

    def test_wage_conservation(self, wayne_qcew_2022, production_hydrator):
        """Sum of department allocations + excluded = total QCEW wages."""
        # Raw total from QCEW
        qcew_total = sum(r.total_annual_wages or 0 for r in wayne_qcew_2022)

        tensor = production_hydrator.hydrate("26163", 2022)

        # Tensor accounts for all value
        tensor_total = (
            tensor.dept_I.v + tensor.dept_IIa.v +
            tensor.dept_IIb.v + tensor.dept_III.v +
            tensor.excluded_wages
        )

        # Allow small tolerance for floating point
        assert tensor_total == pytest.approx(qcew_total, rel=0.001), (
            f"Wage leak: QCEW={qcew_total:,.0f}, Tensor={tensor_total:,.0f}, "
            f"Diff={qcew_total - tensor_total:,.0f}"
        )
```

---

## 2. PIKETTY GUARDRAIL TESTS

**Gap**: You mention Piketty's stable r ≈ 4-5% in the system prompt but don't test it.

```python
# tests/integration/tensors/test_profit_rate_bounds.py

class TestPikettyCalibratedProfitRate:
    """Computed profit rates should match empirical macro data."""

    # Piketty/WID calibration: r ≈ 4-5% over long run
    PIKETTY_R_MIN = 0.03   # 3% floor (recessionary)
    PIKETTY_R_MAX = 0.08   # 8% ceiling (boom)
    PIKETTY_R_STABLE = (0.04, 0.05)  # Long-run equilibrium

    @pytest.mark.empirical
    def test_county_profit_rate_within_piketty_bounds(
        self, production_hydrator, detroit_metro_counties
    ):
        """Individual county profit rates should be 3-8%."""
        for fips in detroit_metro_counties:
            tensor = production_hydrator.hydrate(fips, 2022)

            if tensor.total_value == 0:
                continue  # Skip empty counties

            assert self.PIKETTY_R_MIN <= tensor.profit_rate <= self.PIKETTY_R_MAX, (
                f"County {fips} profit rate {tensor.profit_rate:.2%} "
                f"outside Piketty bounds [{self.PIKETTY_R_MIN:.0%}, {self.PIKETTY_R_MAX:.0%}]"
            )

    @pytest.mark.empirical
    def test_aggregate_profit_rate_near_piketty_stable(
        self, production_hydrator, michigan_counties
    ):
        """State-level aggregate r should approach 4-5%."""
        total_s = total_c = total_v = 0

        for fips in michigan_counties:
            tensor = production_hydrator.hydrate(fips, 2022)
            total_s += tensor.dept_I.s + tensor.dept_IIa.s + tensor.dept_IIb.s + tensor.dept_III.s
            total_c += tensor.dept_I.c + tensor.dept_IIa.c + tensor.dept_IIb.c + tensor.dept_III.c
            total_v += tensor.dept_I.v + tensor.dept_IIa.v + tensor.dept_IIb.v + tensor.dept_III.v

        agg_r = total_s / (total_c + total_v) if (total_c + total_v) > 0 else 0

        assert self.PIKETTY_R_STABLE[0] <= agg_r <= self.PIKETTY_R_STABLE[1], (
            f"Aggregate r={agg_r:.2%} outside Piketty stable range "
            f"[{self.PIKETTY_R_STABLE[0]:.0%}, {self.PIKETTY_R_STABLE[1]:.0%}]"
        )
```

---

## 3. DETROIT TEST CASE: EMPIRICAL VALIDATION

**Gap**: Your system prompt specifies Wayne vs Oakland 2010-2025 as the validation target. You have mock tests but not real data tests.

```python
# tests/integration/tensors/test_detroit_empirical.py

class TestDetroitGentrificationSignal:
    """
    Validate gentrification hypothesis against real Wayne/Oakland data.

    Hypothesis: Oakland County (affluent suburb) has higher IIb/IIa ratio
    than Wayne County (deindustrialized core) due to luxury consumption
    concentration in suburbs.
    """

    WAYNE_FIPS = "26163"
    OAKLAND_FIPS = "26125"

    @pytest.mark.empirical
    @pytest.mark.parametrize("year", range(2010, 2023))
    def test_oakland_higher_luxury_ratio_than_wayne(
        self, production_hydrator, year
    ):
        """Oakland IIb/IIa > Wayne IIb/IIa for every year 2010-2022."""
        wayne = production_hydrator.hydrate(self.WAYNE_FIPS, year)
        oakland = production_hydrator.hydrate(self.OAKLAND_FIPS, year)

        # Skip if degenerate
        if wayne.dept_IIa.v == 0 or oakland.dept_IIa.v == 0:
            pytest.skip(f"Zero IIa for year {year}")

        wayne_ratio = wayne.dept_IIb.v / wayne.dept_IIa.v
        oakland_ratio = oakland.dept_IIb.v / oakland.dept_IIa.v

        assert oakland_ratio > wayne_ratio, (
            f"Year {year}: Oakland IIb/IIa ({oakland_ratio:.3f}) should > "
            f"Wayne IIb/IIa ({wayne_ratio:.3f})"
        )

    @pytest.mark.empirical
    def test_wayne_deindustrialization_trend(self, production_hydrator):
        """Wayne County manufacturing (IIa) should decline 2010-2022."""
        wayne_2010 = production_hydrator.hydrate(self.WAYNE_FIPS, 2010)
        wayne_2022 = production_hydrator.hydrate(self.WAYNE_FIPS, 2022)

        # Manufacturing component of IIa should decline
        # (This tests that the tensor captures deindustrialization)
        assert wayne_2022.dept_IIa.v < wayne_2010.dept_IIa.v, (
            f"Wayne IIa should decline: 2010={wayne_2010.dept_IIa.v:,.0f}, "
            f"2022={wayne_2022.dept_IIa.v:,.0f}"
        )


class TestDetroitClassCompositionShift:
    """
    Validate class composition predictions from design doc:
    - Wayne: V_produced declining → workers LA → Lumpen
    - Oakland: V_produced stable, V_reproduction externalized
    """

    @pytest.mark.empirical
    def test_wayne_v_produced_declining(self, production_hydrator):
        """Total variable capital in Wayne should decline 2010-2022."""
        years = range(2010, 2023)
        wayne_v = []

        for year in years:
            tensor = production_hydrator.hydrate("26163", year)
            total_v = tensor.dept_I.v + tensor.dept_IIa.v + tensor.dept_IIb.v + tensor.dept_III.v
            wayne_v.append(total_v)

        # Linear regression slope should be negative
        slope = _compute_slope(list(years), wayne_v)
        assert slope < 0, f"Wayne V_produced slope should be negative, got {slope:.2f}"

    @pytest.mark.empirical
    def test_oakland_v_produced_stable_or_growing(self, production_hydrator):
        """Total variable capital in Oakland should be stable or growing."""
        years = range(2010, 2023)
        oakland_v = []

        for year in years:
            tensor = production_hydrator.hydrate("26125", year)
            total_v = tensor.dept_I.v + tensor.dept_IIa.v + tensor.dept_IIb.v + tensor.dept_III.v
            oakland_v.append(total_v)

        slope = _compute_slope(list(years), oakland_v)
        assert slope >= -0.01, f"Oakland V_produced should be stable, got slope {slope:.2f}"


def _compute_slope(x: list, y: list) -> float:
    """Simple linear regression slope."""
    n = len(x)
    sum_x = sum(x)
    sum_y = sum(y)
    sum_xy = sum(xi * yi for xi, yi in zip(x, y))
    sum_x2 = sum(xi ** 2 for xi in x)

    return (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x ** 2)
```

---

## 4. TEMPORAL CONSISTENCY TESTS (α-SMOOTHING)

**Gap**: Your design doc mentions "coefficients transform slowly (α-smoothing)". No tests verify this.

```python
# tests/integration/tensors/test_temporal_consistency.py

class TestTemporalSmoothing:
    """Year-over-year changes should be gradual, not discontinuous."""

    MAX_YOY_CHANGE = 0.30  # 30% max year-over-year change

    @pytest.mark.empirical
    def test_profit_rate_smoothness(self, production_hydrator, detroit_metro_counties):
        """Profit rate shouldn't jump >30% year-over-year."""
        for fips in detroit_metro_counties:
            prev_r = None
            for year in range(2010, 2023):
                tensor = production_hydrator.hydrate(fips, year)
                r = tensor.profit_rate

                if prev_r is not None and prev_r > 0:
                    pct_change = abs(r - prev_r) / prev_r
                    assert pct_change <= self.MAX_YOY_CHANGE, (
                        f"County {fips} year {year}: profit rate jumped "
                        f"{pct_change:.0%} (from {prev_r:.2%} to {r:.2%})"
                    )
                prev_r = r

    @pytest.mark.empirical
    def test_department_composition_smoothness(self, production_hydrator):
        """Department shares shouldn't shift dramatically year-to-year."""
        prev_shares = None
        for year in range(2010, 2023):
            tensor = production_hydrator.hydrate("26163", year)
            total_v = tensor.dept_I.v + tensor.dept_IIa.v + tensor.dept_IIb.v + tensor.dept_III.v

            if total_v == 0:
                continue

            shares = {
                "I": tensor.dept_I.v / total_v,
                "IIa": tensor.dept_IIa.v / total_v,
                "IIb": tensor.dept_IIb.v / total_v,
                "III": tensor.dept_III.v / total_v,
            }

            if prev_shares is not None:
                for dept, share in shares.items():
                    prev = prev_shares[dept]
                    if prev > 0.01:  # Only check non-trivial departments
                        pct_change = abs(share - prev) / prev
                        assert pct_change <= self.MAX_YOY_CHANGE, (
                            f"Dept {dept} share jumped {pct_change:.0%} in {year}"
                        )
            prev_shares = shares
```

---

## 5. OUT-OF-SAMPLE PREDICTION TESTS

**Gap**: Your falsifiability criteria mention "Train on 2010-2020, Predict 2020-2025". No tests implement this.

```python
# tests/integration/tensors/test_out_of_sample.py

class TestOutOfSamplePrediction:
    """
    Train model parameters on 2010-2019, predict 2020-2022.

    This is the core falsifiability test: can the model predict
    unseen data better than chance?
    """

    TRAIN_YEARS = range(2010, 2020)
    TEST_YEARS = range(2020, 2023)

    @pytest.mark.empirical
    @pytest.mark.slow
    def test_profit_rate_trend_extrapolation(self, production_hydrator):
        """Extrapolated profit rate trend should bracket actual values."""
        # Fit linear trend on training data
        train_r = []
        for year in self.TRAIN_YEARS:
            tensor = production_hydrator.hydrate("26163", year)
            train_r.append(tensor.profit_rate)

        slope, intercept = _fit_linear(list(self.TRAIN_YEARS), train_r)

        # Predict test years
        for year in self.TEST_YEARS:
            predicted_r = slope * year + intercept
            actual_tensor = production_hydrator.hydrate("26163", year)
            actual_r = actual_tensor.profit_rate

            # Prediction should be within 2 standard deviations
            residuals = [r - (slope * y + intercept) for y, r in zip(self.TRAIN_YEARS, train_r)]
            std_dev = (sum(r**2 for r in residuals) / len(residuals)) ** 0.5

            assert abs(actual_r - predicted_r) <= 2 * std_dev, (
                f"Year {year}: actual r={actual_r:.2%} outside 2σ of "
                f"predicted r={predicted_r:.2%} (σ={std_dev:.2%})"
            )

    @pytest.mark.empirical
    @pytest.mark.slow
    def test_luxury_ratio_trend_holds(self, production_hydrator):
        """Oakland > Wayne luxury ratio should persist into test period."""
        for year in self.TEST_YEARS:
            wayne = production_hydrator.hydrate("26163", year)
            oakland = production_hydrator.hydrate("26125", year)

            if wayne.dept_IIa.v == 0 or oakland.dept_IIa.v == 0:
                continue

            wayne_ratio = wayne.dept_IIb.v / wayne.dept_IIa.v
            oakland_ratio = oakland.dept_IIb.v / oakland.dept_IIa.v

            assert oakland_ratio > wayne_ratio, (
                f"Out-of-sample {year}: pattern broke - "
                f"Oakland ({oakland_ratio:.3f}) <= Wayne ({wayne_ratio:.3f})"
            )


def _fit_linear(x: list, y: list) -> tuple[float, float]:
    """Return (slope, intercept) for simple linear regression."""
    n = len(x)
    sum_x = sum(x)
    sum_y = sum(y)
    sum_xy = sum(xi * yi for xi, yi in zip(x, y))
    sum_x2 = sum(xi ** 2 for xi in x)

    slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x ** 2)
    intercept = (sum_y - slope * sum_x) / n
    return slope, intercept
```

---

## 6. DATA QUALITY INVARIANT TESTS

**Gap**: You have some in existing tests, but missing comprehensive real-data validation.

```python
# tests/integration/data/test_data_quality.py

class TestQCEWDataQuality:
    """Invariants that must hold for raw QCEW data."""

    @pytest.mark.empirical
    def test_employment_non_negative(self, qcew_session):
        """No negative employment counts."""
        negatives = qcew_session.query(QcewRaw2022).filter(
            QcewRaw2022.annual_avg_emplvl < 0
        ).count()

        assert negatives == 0, f"Found {negatives} records with negative employment"

    @pytest.mark.empirical
    def test_wages_consistent_with_employment(self, qcew_session):
        """Non-zero wages should imply non-zero employment."""
        inconsistent = qcew_session.query(QcewRaw2022).filter(
            QcewRaw2022.total_annual_wages > 0,
            QcewRaw2022.annual_avg_emplvl == 0
        ).count()

        assert inconsistent == 0, f"Found {inconsistent} records with wages but zero employment"

    @pytest.mark.empirical
    def test_avg_wage_plausible(self, qcew_session):
        """Average annual pay should be $10k-$500k range."""
        implausible = qcew_session.query(QcewRaw2022).filter(
            QcewRaw2022.avg_annual_pay.isnot(None),
            ~QcewRaw2022.avg_annual_pay.between(10000, 500000)
        ).count()

        assert implausible == 0, f"Found {implausible} records with implausible avg pay"


class TestTensorDataQuality:
    """Invariants that must hold for hydrated tensors."""

    @pytest.mark.empirical
    def test_no_negative_values_in_tensor(self, production_hydrator, all_michigan_counties):
        """All tensor values must be non-negative."""
        for fips in all_michigan_counties:
            tensor = production_hydrator.hydrate(fips, 2022)

            for dept_name in ["dept_I", "dept_IIa", "dept_IIb", "dept_III"]:
                dept = getattr(tensor, dept_name)
                assert dept.c >= 0, f"{fips} {dept_name}.c is negative"
                assert dept.v >= 0, f"{fips} {dept_name}.v is negative"
                assert dept.s >= 0, f"{fips} {dept_name}.s is negative"
```

---

## 7. BEA RATIO CALIBRATION TESTS

**Gap**: You have mock BEA sources but no tests validating actual BEA-derived ratios.

```python
# tests/integration/data/test_bea_calibration.py

class TestBEARatioPlausibility:
    """BEA-derived c/v and s/v ratios should be economically plausible."""

    @pytest.mark.empirical
    def test_cv_ratio_bounds(self, bea_data_source):
        """c/v ratios from BEA should be 0.1 to 10.0."""
        for naics in ["336111", "311", "4451", "6244"]:  # Sample industries
            cv = bea_data_source.get_cv_ratio(naics, 2022)
            if cv is not None:
                assert 0.1 <= cv <= 10.0, f"NAICS {naics} c/v={cv} outside bounds"

    @pytest.mark.empirical
    def test_sv_ratio_bounds(self, bea_data_source):
        """s/v ratios from BEA should be 0.1 to 5.0."""
        for naics in ["336111", "311", "4451", "6244"]:
            sv = bea_data_source.get_sv_ratio(naics, 2022)
            if sv is not None:
                assert 0.1 <= sv <= 5.0, f"NAICS {naics} s/v={sv} outside bounds"

    @pytest.mark.empirical
    def test_capital_intensive_industries_have_higher_cv(self, bea_data_source):
        """Mining (21) should have higher c/v than retail (44)."""
        mining_cv = bea_data_source.get_cv_ratio("21", 2022)
        retail_cv = bea_data_source.get_cv_ratio("44", 2022)

        if mining_cv and retail_cv:
            assert mining_cv > retail_cv, (
                f"Mining c/v ({mining_cv}) should > retail c/v ({retail_cv})"
            )
```

---

## Summary: Test Layer Matrix

| Layer | You Have | Missing |
|-------|----------|---------|
| **Unit** | ✅ Tensor models, mapper, allocation | — |
| **Theory** | ✅ Marx examples, reproduction equilibrium | — |
| **Integration (mocks)** | ✅ Hydrator, gentrification signal | — |
| **Integration (real data)** | ❌ | Accounting identity, BEA calibration |
| **Empirical validation** | ❌ | Detroit test case, temporal smoothing |
| **Predictive** | ❌ | Out-of-sample, trend extrapolation |
| **Guardrails** | ❌ | Piketty bounds, data quality |

The critical missing piece is the jump from *mocked* integration tests to *real data* empirical validation. Your mocks prove the math works; you need tests proving the math matches reality.
