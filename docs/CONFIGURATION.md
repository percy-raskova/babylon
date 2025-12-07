# Configuration System Documentation

## Overview

The configuration system provides centralized management of application settings through:
- Environment variables
- Configuration files
- Runtime configuration

## Base Configuration

The BaseConfig class serves as the foundation for all configuration management:

### Database Settings
- `DATABASE_URL`: SQLite connection string (default: `sqlite:///babylon.db`)

### ChromaDB Settings
- `CHROMA_PERSIST_DIR`: Vector database persistence directory
- `CHROMA_COLLECTION_NAME`: Default collection name
- `EMBEDDING_MODEL`: Model name for embeddings

### Metrics Collection
- `METRICS_ENABLED`: Enable/disable metrics collection
- `METRICS_INTERVAL`: Collection interval in seconds
- `METRICS_RETENTION_DAYS`: Data retention period

### Logging Configuration
- `LOG_LEVEL`: Minimum logging level
- `LOG_FORMAT`: Log message format
- `LOG_DIR`: Log file directory

### Performance Thresholds
- `MAX_QUERY_LATENCY_MS`: Maximum acceptable query latency
- `MIN_CACHE_HIT_RATE`: Minimum acceptable cache hit rate
- `MAX_MEMORY_USAGE_GB`: Maximum memory usage threshold

## Usage Examples

```python
from babylon.config.base import BaseConfig

# Access configuration
db_url = BaseConfig.DATABASE_URL
log_level = BaseConfig.LOG_LEVEL

# Override settings
BaseConfig.METRICS_ENABLED = False
```

## Environment Variables

The following environment variables can be used to override default settings:

```bash
# Database (SQLite)
DATABASE_URL=sqlite:///babylon.db

# ChromaDB
BABYLON_CHROMA_PERSIST_DIR=/path/to/persist
BABYLON_EMBEDDING_MODEL=all-MiniLM-L6-v2

# Metrics
BABYLON_METRICS_ENABLED=true
BABYLON_METRICS_INTERVAL=60

# Logging
BABYLON_LOG_LEVEL=INFO
BABYLON_LOG_DIR=/path/to/logs
```

## Best Practices

1. Use environment variables for sensitive information
2. Keep defaults reasonable for development
3. Document all configuration changes
4. Validate configuration at startup
5. Use type hints for all settings
