"""Exception hierarchy for Babylon/Babylon.

Exceptions are contradictions made manifest in code.
They represent the system's failure to reproduce itself.

Error Code Schema:
- CFG_XXX: Configuration errors
- DB_XXX: Database/persistence errors
- EMB_XXX: Embedding/vector errors
- VAL_XXX: Validation errors
- SYS_XXX: System-level errors
"""


class BabylonError(Exception):
    """Base exception for all Babylon/Babylon errors.

    All exceptions in the system inherit from this class,
    allowing for unified error handling at the boundary.

    Attributes:
        message: Human-readable error description
        error_code: Machine-readable error identifier
        details: Additional context for debugging
    """

    def __init__(
        self, message: str, error_code: str | None = None, details: dict | None = None
    ) -> None:
        self.message = message
        self.error_code = error_code or "SYS_000"
        self.details = details or {}
        super().__init__(self.message)

    def __str__(self) -> str:
        return f"[{self.error_code}] {self.message}"

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}(message={self.message!r}, error_code={self.error_code!r})"
        )

    def to_dict(self) -> dict:
        """Serialize exception for logging/API responses."""
        return {
            "error_type": self.__class__.__name__,
            "error_code": self.error_code,
            "message": self.message,
            "details": self.details,
        }


class ConfigurationError(BabylonError):
    """Raised when configuration is invalid or missing.

    The material conditions for operation have not been established.
    """

    def __init__(
        self, message: str, error_code: str | None = None, details: dict | None = None
    ) -> None:
        super().__init__(message, error_code=error_code or "CFG_001", details=details)


class DatabaseError(BabylonError):
    """Raised when database operations fail.

    The Ledger cannot record the material reality.
    """

    def __init__(
        self, message: str, error_code: str | None = None, details: dict | None = None
    ) -> None:
        super().__init__(message, error_code=error_code or "DB_001", details=details)


class EmbeddingError(BabylonError):
    """Raised when embedding operations fail.

    The Archive cannot encode semantic meaning.
    """

    def __init__(
        self, message: str, error_code: str | None = None, details: dict | None = None
    ) -> None:
        super().__init__(message, error_code=error_code or "EMB_001", details=details)


class ValidationError(BabylonError):
    """Raised when data validation fails.

    The input does not conform to the schema of material reality.
    """

    def __init__(
        self, message: str, error_code: str | None = None, details: dict | None = None
    ) -> None:
        super().__init__(message, error_code=error_code or "VAL_001", details=details)


class TopologyError(BabylonError):
    """Raised when graph/topology operations fail.

    The relations of production cannot be computed.
    """

    def __init__(
        self, message: str, error_code: str | None = None, details: dict | None = None
    ) -> None:
        super().__init__(message, error_code=error_code or "TOP_001", details=details)


class SimulationError(BabylonError):
    """Raised when simulation logic fails.

    The dialectical process has encountered a fatal contradiction.
    """

    def __init__(
        self, message: str, error_code: str | None = None, details: dict | None = None
    ) -> None:
        super().__init__(message, error_code=error_code or "SIM_001", details=details)
