"""Contract: VerificationProtocol for loader source file verification.

This is a reference implementation showing the expected interface.
The actual implementation is in the babylon-data package.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Protocol

# PreflightCheck moved to babylon-data package
PreflightCheck = Any  # type: ignore[assignment,misc]


class VerificationProtocol(Protocol):
    """Protocol for loaders that can verify their source file requirements.

    Loaders implementing this protocol can be registered with the preflight
    system to validate data availability before simulation starts.

    Example implementation::

        class LodesCrosswalkLoader(DataLoader):
            def check_source_files(
                self,
                data_dir: Path,
                online: bool = False,
            ) -> list[PreflightCheck]:
                checks = []
                crosswalk_path = data_dir / "lodes" / "us_xwalk.csv"
                if not crosswalk_path.exists():
                    checks.append(PreflightCheck(
                        check_id="lodes:crosswalk",
                        status="fail",
                        message=f"Missing LODES crosswalk: {crosswalk_path}",
                        hint="Download from https://lehd.ces.census.gov/data/lodes/",
                    ))
                else:
                    checks.append(PreflightCheck(
                        check_id="lodes:crosswalk",
                        status="ok",
                        message=f"Found {crosswalk_path}",
                    ))
                return checks
    """

    def check_source_files(
        self,
        data_dir: Path,
        online: bool = False,
    ) -> list[PreflightCheck]:
        """Verify required source files exist and are valid.

        Args:
            data_dir: Base data directory (e.g., Path("data/")).
            online: If True, validate network endpoints (API reachability).
                    If False, skip network checks and report warnings instead.

        Returns:
            List of PreflightCheck results. Each check should have:
            - check_id: Unique identifier (e.g., "lodes:crosswalk")
            - status: "ok", "warn", or "fail"
            - message: Human-readable description
            - hint: Actionable guidance for failures (download URL, command)

        Raises:
            Nothing. All errors should be captured as PreflightCheck objects.
        """
        ...


# Type alias for the loader registry
VERIFICATION_LOADERS_TYPE = dict[str, type[VerificationProtocol]]
