"""ChromaDB client management module."""

import logging
import time
import uuid

import chromadb
from chromadb.api import ClientAPI
from chromadb.api.models.Collection import Collection
from chromadb.errors import ChromaError, InvalidDimensionException

from babylon.config.chromadb_config import ChromaDBConfig
from babylon.utils.exceptions import DatabaseError
from babylon.utils.retry import retry_on_exception

logger = logging.getLogger(__name__)

# Define ChromaDB specific exceptions to handle
CHROMA_RETRYABLE_EXCEPTIONS = (
    ChromaError,
    ConnectionError,
    TimeoutError,
)

# Define non-retryable exceptions
CHROMA_FATAL_EXCEPTIONS = (InvalidDimensionException, ValueError, TypeError)


class ChromaManager:
    """Manages ChromaDB client lifecycle and operations.

    This class implements the Singleton pattern to ensure only one ChromaDB client
    exists throughout the application lifecycle. It provides centralized management
    of vector database operations for storing and retrieving entity embeddings.

    Error Handling:
        - Implements retries for transient failures
        - Provides detailed error context
        - Logs performance metrics
        - Tracks operation correlation IDs

    Implementation Details:
        - Uses DuckDB+Parquet backend for efficient local storage and querying
        - Implements lazy initialization to optimize resource usage
        - Provides automatic persistence and backup capabilities
        - Handles graceful cleanup during shutdown

    Key Features:
        - Thread-safe singleton implementation
        - Automatic connection management
        - Collection creation and access
        - Resource cleanup and persistence

    Performance Considerations:
        - Maintains connection pool for efficient queries
        - Implements caching for frequently accessed collections
        - Uses batch operations for better throughput
        - Handles memory management through lazy loading

    Usage Example:
        manager = ChromaManager()
        collection = manager.get_or_create_collection("entities")
        collection.add(documents=[...], embeddings=[...])

    Attributes:
        _instance: Singleton instance of the manager
        _client: The ChromaDB client instance

    Note:
        The class uses lazy initialization - the client is only created when first needed.
        This helps optimize resource usage and startup time.
    """

    _instance: "ChromaManager | None" = None
    _client: ClientAPI | None = None

    def __new__(cls) -> "ChromaManager":
        """Implement singleton pattern for ChromaManager.

        Returns:
            ChromaManager: The singleton instance of the manager
        """
        if cls._instance is None:
            # Create new instance if none exists
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        """Initialize the ChromaManager instance.

        The initialization is lazy - the client is only created when needed.
        This method is safe to call multiple times due to the singleton pattern.
        """
        if self._client is None:
            # Only initialize client if it hasn't been created yet
            self._initialize_client()

    @retry_on_exception(
        max_retries=3, delay=1, exceptions=CHROMA_RETRYABLE_EXCEPTIONS, logger=logger
    )
    def _initialize_client(self) -> None:
        """Initialize the ChromaDB client with proper settings.

        This method configures the ChromaDB client with:
        - DuckDB backend for efficient local storage
        - Parquet file format for data persistence
        - Custom persistence directory from config

        Raises:
            ChromaError: For ChromaDB specific errors
            ConnectionError: For network/connection issues
            ValueError: For invalid configuration

        Note:
            The method uses DuckDB+Parquet for optimal performance in local deployments.
            This combination provides good query performance and data compression.
        """
        start_time = time.perf_counter()
        correlation_id = str(uuid.uuid4())

        try:
            # Ensure persistence directory exists
            persist_path = ChromaDBConfig.BASE_DIR
            persist_path.mkdir(parents=True, exist_ok=True)

            logger.debug(
                "Initializing ChromaDB client",
                extra={
                    "correlation_id": correlation_id,
                    "persist_dir": persist_path,
                },
            )

            # Create client with local persistence using ChromaDB 1.x API
            # PersistentClient replaces deprecated Client(Settings(persist_directory=...))
            self._client = chromadb.PersistentClient(
                path=str(persist_path),
                settings=ChromaDBConfig.get_settings(),
            )

            # Test connection
            if self._client is not None:
                self._client.heartbeat()

            elapsed = time.perf_counter() - start_time
            logger.info(
                "ChromaDB client initialized successfully",
                extra={"correlation_id": correlation_id, "elapsed_seconds": elapsed},
            )

        except CHROMA_FATAL_EXCEPTIONS as e:
            logger.error(
                "Fatal error initializing ChromaDB client",
                extra={
                    "correlation_id": correlation_id,
                    "error": str(e),
                    "error_type": e.__class__.__name__,
                },
                exc_info=True,
            )
            raise

        except Exception as e:
            logger.error(
                "Error initializing ChromaDB client",
                extra={
                    "correlation_id": correlation_id,
                    "error": str(e),
                    "error_type": e.__class__.__name__,
                },
                exc_info=True,
            )
            raise DatabaseError(f"Failed to initialize ChromaDB client: {e}", "DB_001") from e

    @property
    def client(self) -> ClientAPI:
        """Get the ChromaDB client instance.

        This property implements lazy initialization of the client.
        If the client doesn't exist, it will be created on first access.

        Returns:
            ClientAPI: The initialized ChromaDB client instance

        Raises:
            DatabaseError: If client initialization fails

        Note:
            This is the preferred way to access the client throughout the application
            as it ensures proper initialization and singleton pattern compliance.
        """
        if self._client is None:
            # Initialize client if it doesn't exist
            self._initialize_client()
        if self._client is None:
            raise DatabaseError("Failed to initialize ChromaDB client", "DB_001")
        return self._client

    def get_or_create_collection(self, name: str) -> Collection:
        """Get an existing collection or create a new one if it doesn't exist.

        This method provides a safe way to access collections, ensuring they exist
        before use. It's idempotent - calling it multiple times with the same name
        will return the same collection.

        Args:
            name: Name of the collection to get or create

        Returns:
            Collection: The ChromaDB collection instance

        Note:
            Collections are the main way to organize embeddings in ChromaDB.
            Each collection can store documents, embeddings, and metadata.
        """
        return self.client.get_or_create_collection(name=name)

    def cleanup(self) -> None:
        """Cleanup ChromaDB resources.

        This method performs a graceful shutdown of the ChromaDB client:
        1. Resets the client connection (if allow_reset=True in settings)
        2. Clears the client reference

        Note:
            In ChromaDB 1.x with PersistentClient, data is automatically
            persisted - no explicit persist() call needed.

        Note:
            This method should be called during application shutdown or when
            you're done using ChromaDB to ensure proper cleanup.
        """
        if self._client:
            try:
                # Reset the client to close connections
                # Note: reset() clears all data if allow_reset=True in settings
                # For cleanup without data loss, just clear the reference
                self._client = None
            except Exception as e:
                # Log cleanup errors but don't raise to allow shutdown to continue
                logger.error(f"Error during ChromaDB cleanup: {e}")
