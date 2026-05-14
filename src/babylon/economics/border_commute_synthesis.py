"""Detroit-Windsor border-commute synthesis loader (Spec 063 Option B / T040).

Produces aggregate Canadian-bound commute rows from public-data sources:

  - **BTS Border Crossing Data** (monthly, southbound personal vehicles)
  - **StatCan Frontier Counts** (monthly, northbound personal vehicles)
  - **Workforce WindsorEssex 2017 anchor** (commuter share constant)

Synthesis formula (FR-035)::

  weekly_commuters[week] = monthly_vehicles[month_containing(week)]
                            × border_commute_share
                            / weeks_per_month  (≈ 4.333)

Per research §4: canonical LODES has no Canadian destinations. This loader
fills that gap (when ``enabled=True``) by emitting one ``BorderCommuteFlow``
row per (year, week_of_year, direction). Rows merge into the
:class:`LODESYearMatrix` at session-init time so the existing
:class:`Vol2CirculationStep` + :class:`CrossBorderCommuteClassifier` route
them uniformly with native LODES rows.

Gated by ``GameDefines.enable_border_commute_synthesis`` (default ``False``);
when disabled, all methods are no-ops.

See also:
    ``specs/063-vol-ii-circulation/spec.md`` FR-031..FR-036.
    ``specs/063-vol-ii-circulation/data-model.md`` §1.5b.
    ``specs/063-vol-ii-circulation/research.md`` §7.
"""

from __future__ import annotations

import csv
import logging
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import TYPE_CHECKING
from uuid import UUID

if TYPE_CHECKING:
    from babylon.persistence.protocols import RuntimePersistence

logger = logging.getLogger(__name__)

# ISO 8601 week→month convention per spec.md FR-035: the month for week W is
# the month containing the WEDNESDAY of that week.
_WEEKDAY_WEDNESDAY = 2  # date.weekday(): Monday=0 ... Sunday=6

# Constant from spec.md FR-035 — 52 weeks divided by 12 months.
_WEEKS_PER_MONTH = 52 / 12  # ≈ 4.3333


@dataclass(frozen=True)
class BorderCommuteFlow:
    """One synthesized aggregate cross-border commute flow row.

    Maps directly to one row of ``immutable_reference_border_commute_synthesis``
    per data-model.md §2.2.
    """

    year: int
    week_of_year: int
    direction: str  # "us_to_canada" | "canada_to_us"
    aggregate_origin: str
    aggregate_dest: str
    magnitude_workers: float
    source_anchor: str


def _wednesday_of_iso_week(year: int, week: int) -> date:
    """Return the Wednesday of the given ISO year+week."""
    # ISO 8601 week 1 contains January 4. Get Monday of that week, add 2 days.
    jan_4 = date(year, 1, 4)
    monday_of_week1 = jan_4 - timedelta(days=jan_4.weekday())
    monday_of_week = monday_of_week1 + timedelta(weeks=week - 1)
    return monday_of_week + timedelta(days=_WEEKDAY_WEDNESDAY)


def _month_for_iso_week(year: int, week: int) -> int:
    """Apply FR-035 week→month convention: month of the Wednesday of the week."""
    return _wednesday_of_iso_week(year, week).month


class BorderCommuteSynthesisLoader:
    """Synthesize aggregate Detroit-Windsor commute rows from BTS + StatCan + WWE.

    Construction is gated by ``enabled``: when ``False`` (the
    ``GameDefines.enable_border_commute_synthesis`` default), all methods
    return empty results and ``is_enabled()`` is ``False``.

    When ``enabled=True``, the BTS CSV path MUST exist or constructor
    raises ``FileNotFoundError`` (FR-036). StatCan absence is tolerated
    (FR-033 fall-back: us_to_canada direction only with one audit warning).
    """

    def __init__(
        self,
        *,
        bts_csv_path: Path | None,
        statcan_csv_path: Path | None,
        border_commute_share: float,
        detroit_port_codes: frozenset[str],
        tri_county_aggregate_hex: str,
        enabled: bool = False,
    ) -> None:
        if not (0.0 < border_commute_share <= 1.0):
            raise ValueError(f"border_commute_share must be in (0, 1]; got {border_commute_share}")
        if not detroit_port_codes:
            raise ValueError("detroit_port_codes MUST be non-empty")
        if not tri_county_aggregate_hex:
            raise ValueError("tri_county_aggregate_hex MUST be non-empty")

        self.border_commute_share = border_commute_share
        self.detroit_port_codes = detroit_port_codes
        self.tri_county_aggregate_hex = tri_county_aggregate_hex
        self.bts_csv_path = bts_csv_path
        self.statcan_csv_path = statcan_csv_path
        self._enabled = enabled

        if enabled:
            if bts_csv_path is None or not bts_csv_path.exists():
                raise FileNotFoundError(
                    f"BTS Border Crossing CSV required when "
                    f"enable_border_commute_synthesis=True; got {bts_csv_path}"
                )
            if statcan_csv_path is None or not statcan_csv_path.exists():
                logger.warning(
                    "StatCan Frontier Counts CSV not present; canada_to_us "
                    "direction will be skipped (us_to_canada synthesis still active)."
                )

        # Cached month→vehicle-count per file. Lazy.
        self._bts_monthly: dict[tuple[int, int], float] | None = None
        self._statcan_monthly: dict[tuple[int, int], float] | None = None

    def is_enabled(self) -> bool:
        """Return True iff synthesis is enabled AND BTS CSV is readable."""
        return self._enabled and self.bts_csv_path is not None and self.bts_csv_path.exists()

    def synthesize_year(self, year: int) -> tuple[BorderCommuteFlow, ...]:
        """Produce one BorderCommuteFlow per (week_of_year, direction) for ``year``.

        When ``enabled=False`` returns an empty tuple.
        When StatCan is absent, returns up to 52 us_to_canada rows only.
        """
        if not self.is_enabled():
            return ()

        bts = self._load_bts()
        statcan = self._load_statcan()

        rows: list[BorderCommuteFlow] = []
        for week in range(1, 53):
            month = _month_for_iso_week(year, week)
            key = (year, month)
            # us_to_canada from BTS southbound counts (US-bound is treated as
            # "workers commuting INTO the US"; spec defines us_to_canada as
            # the symmetric flow — see research §7).
            us_to_canada_vehicles = bts.get(key)
            if us_to_canada_vehicles is not None:
                rows.append(
                    BorderCommuteFlow(
                        year=year,
                        week_of_year=week,
                        direction="us_to_canada",
                        aggregate_origin=self.tri_county_aggregate_hex,
                        aggregate_dest="canada",
                        magnitude_workers=(
                            us_to_canada_vehicles * self.border_commute_share / _WEEKS_PER_MONTH
                        ),
                        source_anchor=(
                            f"WWE 2017 (share={self.border_commute_share:.2f}); "
                            f"BTS port_codes={','.join(sorted(self.detroit_port_codes))}; "
                            f"week={week} of {year}"
                        ),
                    )
                )
            if statcan is not None:
                canada_to_us_vehicles = statcan.get(key)
                if canada_to_us_vehicles is not None:
                    rows.append(
                        BorderCommuteFlow(
                            year=year,
                            week_of_year=week,
                            direction="canada_to_us",
                            aggregate_origin="canada",
                            aggregate_dest=self.tri_county_aggregate_hex,
                            magnitude_workers=(
                                canada_to_us_vehicles * self.border_commute_share / _WEEKS_PER_MONTH
                            ),
                            source_anchor=(
                                f"WWE 2017 (share={self.border_commute_share:.2f}); "
                                f"StatCan Frontier Counts; week={week} of {year}"
                            ),
                        )
                    )
        return tuple(rows)

    def persist_to_postgres(
        self,
        *,
        runtime: RuntimePersistence,
        session_id: UUID,
        years: tuple[int, ...],
    ) -> int:
        """Persist synthesized rows for ``years`` to Postgres.

        Returns total row count inserted across all years. When
        ``is_enabled()`` is False, returns 0 without touching Postgres.
        """
        if not self.is_enabled():
            return 0
        all_rows: list[BorderCommuteFlow] = []
        for year in years:
            all_rows.extend(self.synthesize_year(year))
        if not all_rows:
            return 0

        payload = [
            (
                session_id,
                f.year,
                f.week_of_year,
                f.direction,
                f.aggregate_origin,
                f.aggregate_dest,
                f.magnitude_workers,
                f.source_anchor,
            )
            for f in all_rows
        ]
        with (
            runtime._pool.connection() as pg,  # type: ignore[attr-defined]  # noqa: SLF001
            pg.cursor() as cur,
        ):
            cur.executemany(
                """
                INSERT INTO immutable_reference_border_commute_synthesis
                    (session_id, year, week_of_year, direction,
                     aggregate_origin, aggregate_dest, magnitude_workers,
                     source_anchor)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (session_id, year, week_of_year, direction)
                DO NOTHING
                """,
                payload,
            )
        return len(payload)

    # ── Internal: CSV parsing ───────────────────────────────────────────────

    def _load_bts(self) -> dict[tuple[int, int], float]:
        """Return cached {(year, month): personal_vehicle_count} from BTS CSV."""
        if self._bts_monthly is not None:
            return self._bts_monthly
        if self.bts_csv_path is None:
            self._bts_monthly = {}
            return self._bts_monthly

        self._bts_monthly = self._parse_bts_csv(self.bts_csv_path, self.detroit_port_codes)
        return self._bts_monthly

    def _load_statcan(self) -> dict[tuple[int, int], float] | None:
        """Return cached {(year, month): vehicle_count} from StatCan CSV, or None if absent."""
        if self.statcan_csv_path is None or not self.statcan_csv_path.exists():
            return None
        if self._statcan_monthly is not None:
            return self._statcan_monthly
        # StatCan format varies; minimal parser assumes
        # columns: ["Year", "Month", "Port", "Vehicles"]
        self._statcan_monthly = self._parse_simple_year_month_csv(
            self.statcan_csv_path,
            port_filter=self.detroit_port_codes,
            year_col="Year",
            month_col="Month",
            port_col="Port",
            count_col="Vehicles",
        )
        return self._statcan_monthly

    @staticmethod
    def _parse_bts_csv(path: Path, port_codes: frozenset[str]) -> dict[tuple[int, int], float]:
        """Parse BTS Border Crossing Data CSV into {(year, month): personal_vehicles}.

        BTS columns (per data.bts.gov v2025):
          Port Name, State, Port Code, Border, Date, Measure, Value, Latitude, Longitude
        We filter on Port Code ∈ port_codes AND Measure ∈
        {"Personal Vehicles", "Personal Vehicle Passengers"}.
        Date format is "MM/01/YYYY 12:00:00 AM" in older dumps, "YYYY-MM" in newer.
        """
        out: dict[tuple[int, int], float] = {}
        accepted_measures = {"Personal Vehicles", "Personal Vehicle Passengers"}
        with path.open("r", encoding="utf-8", newline="") as fh:
            reader = csv.DictReader(fh)
            for row in reader:
                port = row.get("Port Code") or row.get("port_code") or ""
                if port and port not in port_codes:
                    continue
                measure = row.get("Measure") or row.get("measure") or ""
                if measure not in accepted_measures:
                    continue
                year, month = _parse_date_field(row)
                if year is None or month is None:
                    continue
                try:
                    value = float(row.get("Value") or row.get("value") or 0)
                except ValueError:
                    continue
                key = (year, month)
                out[key] = out.get(key, 0.0) + value
        return out

    @staticmethod
    def _parse_simple_year_month_csv(
        path: Path,
        *,
        port_filter: frozenset[str],
        year_col: str,
        month_col: str,
        port_col: str,
        count_col: str,
    ) -> dict[tuple[int, int], float]:
        """Parse a generic year/month/port/count CSV (used for StatCan)."""
        out: dict[tuple[int, int], float] = {}
        with path.open("r", encoding="utf-8", newline="") as fh:
            reader = csv.DictReader(fh)
            for row in reader:
                port = row.get(port_col, "")
                if port_filter and port not in port_filter:
                    continue
                try:
                    year = int(row.get(year_col, ""))
                    month = int(row.get(month_col, ""))
                    count = float(row.get(count_col, "") or 0)
                except ValueError:
                    continue
                key = (year, month)
                out[key] = out.get(key, 0.0) + count
        return out


def _parse_date_field(row: dict[str, str]) -> tuple[int | None, int | None]:
    """Extract (year, month) from a BTS row's Date field. Returns (None, None) on parse error."""
    date_str = row.get("Date") or row.get("date") or ""
    if not date_str:
        return (None, None)
    # Try "YYYY-MM" (newer format).
    if len(date_str) >= 7 and date_str[4] == "-":
        try:
            return (int(date_str[:4]), int(date_str[5:7]))
        except ValueError:
            return (None, None)
    # Try "MM/01/YYYY ..." (older BTS format).
    parts = date_str.split("/")
    if len(parts) >= 3:
        try:
            month = int(parts[0])
            year = int(parts[2].split(" ")[0])
            return (year, month)
        except ValueError:
            return (None, None)
    return (None, None)


__all__ = [
    "BorderCommuteFlow",
    "BorderCommuteSynthesisLoader",
]
