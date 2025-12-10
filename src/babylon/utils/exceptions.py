"""Exception hierarchy for Babylon/Babylon.

Exceptions are contradictions made manifest in code.
They represent the system's failure to reproduce itself.

Error Code Schema:
- CFG_XXX: Configuration errors
- DB_XXX: Database/persistence errors
- EMB_XXX: Embedding/vector errors
- VAL_XXX: Validation errors
- SYS_XXX: System-level errors
- LLM_XXX: LLM generation errors
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
        self,
        message: str,
        error_code: str | None = None,
        details: dict[str, object] | None = None,
    ) -> None:
        self.message = message
        self.error_code = error_code or "SYS_000"
        self.details: dict[str, object] = details or {}
        super().__init__(self.message)

    def __str__(self) -> str:
        return f"[{self.error_code}] {self.message}"

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}(message={self.message!r}, error_code={self.error_code!r})"
        )

    def to_dict(self) -> dict[str, object]:
        """Serialize exception for logging/API responses."""
        return {
            "error_type": self.__class__.__name__,
            "error_code": self.error_code,
            "message": self.message,
            "details": self.details,
        }


# =============================================================================
# LAYER 1: Infrastructure Errors (retryable I/O, network, DB)
# =============================================================================


class InfrastructureError(BabylonError):
    """Base class for infrastructure-related errors.

    These errors are typically retryable and represent external system failures
    (database, network, filesystem). The simulation can often recover from these.

    Error codes: INFRA_XXX
    """

    def __init__(
        self,
        message: str,
        error_code: str | None = None,
        details: dict[str, object] | None = None,
    ) -> None:
        super().__init__(message, error_code=error_code or "INFRA_001", details=details)


class StorageError(InfrastructureError):
    """Raised when file/storage operations fail.

    Covers checkpoints, backups, and file I/O.

    Error codes:
    - STOR_001: File not found
    - STOR_002: File corrupted
    - STOR_003: Schema validation failed
    - STOR_004: Write failed
    """

    def __init__(
        self,
        message: str,
        error_code: str | None = None,
        details: dict[str, object] | None = None,
    ) -> None:
        super().__init__(message, error_code=error_code or "STOR_001", details=details)


# =============================================================================
# LAYER 4: Observer Errors (non-fatal AI/RAG layer)
# =============================================================================


class ObserverError(BabylonError):
    """Base class for AI/RAG observer layer errors.

    These errors are non-fatal and represent failures in the narrative/observation
    layer. The simulation can and should continue without the observer.

    Error codes: OBS_XXX
    """

    def __init__(
        self,
        message: str,
        error_code: str | None = None,
        details: dict[str, object] | None = None,
    ) -> None:
        super().__init__(message, error_code=error_code or "OBS_001", details=details)


# DatabaseError is now under InfrastructureError
class DatabaseError(InfrastructureError):
    """Raised when database operations fail.

    The Ledger cannot record the material reality.
    """

    def __init__(
        self,
        message: str,
        error_code: str | None = None,
        details: dict[str, object] | None = None,
    ) -> None:
        super().__init__(message, error_code=error_code or "DB_001", details=details)


# =============================================================================
# LAYER 2: Validation Errors (bad input, schema violations)
# =============================================================================


class ValidationError(BabylonError):
    """Raised when data validation fails.

    The input does not conform to the schema of material reality.
    """

    def __init__(
        self,
        message: str,
        error_code: str | None = None,
        details: dict[str, object] | None = None,
    ) -> None:
        super().__init__(message, error_code=error_code or "VAL_001", details=details)


class ConfigurationError(ValidationError):
    """Raised when configuration is invalid or missing.

    The material conditions for operation have not been established.
    """

    def __init__(
        self,
        message: str,
        error_code: str | None = None,
        details: dict[str, object] | None = None,
    ) -> None:
        super().__init__(message, error_code=error_code or "CFG_001", details=details)


# =============================================================================
# LAYER 3: Simulation Errors (fatal engine/math failures)
# =============================================================================


class SimulationError(BabylonError):
    """Raised when simulation logic fails.

    The dialectical process has encountered a fatal contradiction.
    """

    def __init__(
        self,
        message: str,
        error_code: str | None = None,
        details: dict[str, object] | None = None,
    ) -> None:
        super().__init__(message, error_code=error_code or "SIM_001", details=details)


class TopologyError(SimulationError):
    """Raised when graph/topology operations fail.

    The relations of production cannot be computed.
    """

    def __init__(
        self,
        message: str,
        error_code: str | None = None,
        details: dict[str, object] | None = None,
    ) -> None:
        super().__init__(message, error_code=error_code or "TOP_001", details=details)


# =============================================================================
# Observer Layer Errors (under ObserverError, defined above)
# =============================================================================


class LLMError(ObserverError):
    """Raised when LLM generation fails.

    The ideological superstructure cannot produce narrative.

    Error codes:
    - LLM_001: General API error
    - LLM_002: Timeout error
    - LLM_003: Rate limit exceeded
    """

    def __init__(
        self,
        message: str,
        error_code: str | None = None,
        details: dict[str, object] | None = None,
    ) -> None:
        super().__init__(message, error_code=error_code or "LLM_001", details=details)


# Backwards compatibility alias
LLMGenerationError = LLMError


# =============================================================================
# DEPRECATED: Will be removed in future versions
# =============================================================================


class EmbeddingError(BabylonError):
    """DEPRECATED: Use RagError instead.

    Raised when embedding operations fail.
    The Archive cannot encode semantic meaning.
    """

    def __init__(
        self,
        message: str,
        error_code: str | None = None,
        details: dict[str, object] | None = None,
    ) -> None:
        super().__init__(message, error_code=error_code or "EMB_001", details=details)
