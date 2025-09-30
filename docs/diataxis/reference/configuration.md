# Configuration Reference

Complete reference for all Babylon configuration options. This document provides detailed information about every setting available in the system.

## Environment Variables

### Core Game Settings

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `GAME_DIFFICULTY` | string | `normal` | Game difficulty level: `easy`, `normal`, `hard`, `expert` |
| `AUTO_SAVE` | boolean | `true` | Enable automatic game saving |
| `AUTO_SAVE_INTERVAL` | integer | `300` | Auto-save interval in seconds |
| `MAX_SESSION_LENGTH` | integer | `7200` | Maximum session duration in seconds |
| `PAUSE_ON_CRISIS` | boolean | `false` | Auto-pause during crisis events |

### Display and Interface

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `COLORED_OUTPUT` | boolean | `true` | Enable colored terminal output |
| `ANIMATION_SPEED` | string | `medium` | Animation speed: `slow`, `medium`, `fast`, `off` |
| `SHOW_DETAILED_STATS` | boolean | `true` | Show extended statistical information |
| `UI_THEME` | string | `default` | UI color theme: `default`, `dark`, `light`, `custom` |
| `TERMINAL_WIDTH` | integer | `120` | Terminal display width in characters |

### AI Configuration

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `AI_COMPLEXITY` | string | `intermediate` | AI complexity: `basic`, `intermediate`, `advanced` |
| `AI_RESPONSE_LENGTH` | string | `medium` | Response length: `short`, `medium`, `long` |
| `AI_CREATIVITY` | float | `0.7` | Creativity level (0.0-1.0) |
| `AI_HISTORICAL_ACCURACY` | float | `0.8` | Historical accuracy (0.0-1.0) |
| `AI_CACHE_SIZE` | integer | `1000` | Number of AI responses to cache |
| `AI_TIMEOUT` | integer | `30` | AI request timeout in seconds |
| `AI_MAX_RETRIES` | integer | `3` | Maximum retry attempts for AI requests |
| `AI_RETRY_DELAY` | integer | `5` | Delay between retries in seconds |
| `USE_MOCK_AI` | boolean | `false` | Use mock AI for testing/development |

### Database Configuration

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `DATABASE_URL` | string | *required* | PostgreSQL connection string |
| `DB_POOL_SIZE` | integer | `10` | Database connection pool size |
| `DB_MAX_OVERFLOW` | integer | `20` | Maximum connection pool overflow |
| `DB_TIMEOUT` | integer | `30` | Database connection timeout |
| `DB_ECHO` | boolean | `false` | Log all database queries |
| `TEST_DATABASE_URL` | string | *optional* | Test database connection string |

### ChromaDB Configuration

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `CHROMA_PERSIST_DIR` | string | `./data/chroma` | ChromaDB storage directory |
| `CHROMA_COLLECTION_NAME` | string | `babylon_entities` | Default collection name |
| `CHROMA_MEMORY_LIMIT_MB` | integer | `2048` | Memory limit in megabytes |
| `CHROMA_BATCH_SIZE` | integer | `50` | Batch processing size |
| `CHROMA_MAX_BATCH_SIZE` | integer | `1000` | Maximum batch size |
| `CHROMA_BACKEND` | string | `duckdb` | Backend: `duckdb`, `sqlite` |
| `CHROMA_ANONYMIZED_TELEMETRY` | boolean | `false` | Enable usage telemetry |
| `CHROMA_PRELOAD_EMBEDDINGS` | boolean | `true` | Preload embeddings into memory |
| `CHROMA_PARALLEL_PROCESSING` | boolean | `true` | Enable parallel processing |
| `CHROMA_COMPRESSION` | boolean | `false` | Compress stored vectors |
| `CHROMA_LAZY_LOADING` | boolean | `false` | Load vectors on demand only |

### Embedding Configuration  

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `EMBEDDING_MODEL` | string | `all-MiniLM-L12-v2` | Sentence transformer model |
| `EMBEDDING_DIMENSIONS` | integer | `384` | Vector embedding dimensions |
| `EMBEDDING_CACHE_SIZE` | integer | `10000` | Number of embeddings to cache |
| `EMBEDDING_BATCH_SIZE` | integer | `32` | Embedding generation batch size |
| `EMBEDDING_DEVICE` | string | `auto` | Device: `cpu`, `cuda`, `auto` |

### Logging Configuration

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `LOG_LEVEL` | string | `INFO` | Logging level: `DEBUG`, `INFO`, `WARNING`, `ERROR` |
| `LOG_FORMAT` | string | `simple` | Log format: `simple`, `detailed`, `json` |
| `LOG_DIR` | string | `./logs` | Log file directory |
| `LOG_ROTATION` | boolean | `true` | Enable log file rotation |
| `LOG_MAX_SIZE_MB` | integer | `10` | Maximum log file size |
| `LOG_BACKUP_COUNT` | integer | `5` | Number of backup log files |
| `ENABLE_FUNCTION_TRACING` | boolean | `false` | Trace function calls |

### Performance Settings

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `MAX_MEMORY_USAGE_GB` | integer | `4` | Maximum memory usage limit |
| `MAX_WORKER_THREADS` | integer | `4` | Maximum worker threads |
| `BATCH_PROCESSING` | boolean | `true` | Enable batch processing |
| `PRELOAD_GAME_DATA` | boolean | `true` | Preload common game data |
| `GC_THRESHOLD` | integer | `1000` | Garbage collection threshold |
| `ENABLE_PROFILING` | boolean | `false` | Enable performance profiling |
| `PROFILE_MEMORY` | boolean | `false` | Profile memory usage |
| `PROFILE_CPU` | boolean | `false` | Profile CPU usage |

### Metrics and Monitoring

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `METRICS_ENABLED` | boolean | `true` | Enable metrics collection |
| `METRICS_INTERVAL` | integer | `60` | Metrics collection interval (seconds) |
| `METRICS_RETENTION_DAYS` | integer | `30` | Data retention period |
| `PERFORMANCE_LOGGING` | boolean | `false` | Log performance metrics |
| `SLOW_QUERY_THRESHOLD_MS` | integer | `1000` | Slow query logging threshold |
| `MEMORY_WARNING_THRESHOLD` | float | `0.8` | Memory usage warning threshold |

### Game Mechanics

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `CONTRADICTION_ANALYSIS` | boolean | `true` | Enable contradiction analysis system |
| `CONTRADICTION_INTENSITY_THRESHOLD` | float | `0.1` | Minimum intensity for active contradictions |
| `EVENT_GENERATION` | boolean | `true` | Enable dynamic event generation |
| `EVENT_FREQUENCY` | float | `1.0` | Event generation frequency multiplier |
| `POPULATION_GROWTH_RATE` | float | `0.02` | Base population growth rate |
| `ECONOMIC_VOLATILITY` | float | `0.3` | Economic system volatility |
| `POLITICAL_STABILITY_FACTOR` | float | `0.5` | Political stability influence |

### Development and Debug

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `ENABLE_DEBUG_MODE` | boolean | `false` | Enable development debug mode |
| `DEBUG_SQL_QUERIES` | boolean | `false` | Log SQL queries in debug mode |
| `DEBUG_AI_PROMPTS` | boolean | `false` | Log AI prompts and responses |
| `DEBUG_VECTOR_OPERATIONS` | boolean | `false` | Log vector database operations |
| `ENABLE_HOT_RELOAD` | boolean | `false` | Enable code hot-reloading |
| `MOCK_EXTERNAL_APIS` | boolean | `false` | Use mock implementations |

## Configuration Files

### Base Configuration (`config/base.py`)

The base configuration class defines default values and validation:

```python
class BaseConfig:
    """Base configuration with sensible defaults"""
    
    # Core settings
    GAME_DIFFICULTY: str = "normal"
    AUTO_SAVE: bool = True
    AUTO_SAVE_INTERVAL: int = 300
    
    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")
    DB_POOL_SIZE: int = int(os.getenv("DB_POOL_SIZE", "10"))
    
    # AI Settings  
    AI_COMPLEXITY: str = os.getenv("AI_COMPLEXITY", "intermediate")
    AI_TIMEOUT: int = int(os.getenv("AI_TIMEOUT", "30"))
    
    @classmethod
    def validate(cls) -> bool:
        """Validate configuration settings"""
        errors = []
        
        if not cls.DATABASE_URL:
            errors.append("DATABASE_URL is required")
            
        if cls.AI_COMPLEXITY not in ["basic", "intermediate", "advanced"]:
            errors.append("AI_COMPLEXITY must be basic, intermediate, or advanced")
            
        if errors:
            raise ValueError(f"Configuration errors: {', '.join(errors)}")
            
        return True
```

### Logging Configuration (`logging.yaml`)

Complete logging configuration:

```yaml
version: 1
disable_existing_loggers: false

formatters:
  simple:
    format: '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    datefmt: '%Y-%m-%d %H:%M:%S'
  
  detailed:
    format: '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(funcName)s - %(message)s'
    datefmt: '%Y-%m-%d %H:%M:%S'
  
  json:
    class: pythonjsonlogger.jsonlogger.JsonFormatter
    format: '%(asctime)s %(name)s %(levelname)s %(filename)s %(lineno)d %(message)s'

handlers:
  console:
    class: logging.StreamHandler
    level: INFO
    formatter: simple
    stream: ext://sys.stdout
  
  file:
    class: logging.handlers.RotatingFileHandler
    level: DEBUG
    formatter: detailed
    filename: logs/babylon.log
    maxBytes: 10485760  # 10MB
    backupCount: 5
    
  error_file:
    class: logging.handlers.RotatingFileHandler
    level: ERROR
    formatter: detailed
    filename: logs/babylon_error.log
    maxBytes: 10485760
    backupCount: 5
    
  json_file:
    class: logging.handlers.RotatingFileHandler
    level: INFO
    formatter: json
    filename: logs/babylon.json
    maxBytes: 10485760
    backupCount: 3

loggers:
  babylon:
    level: INFO
    handlers: [console, file, error_file]
    propagate: false
    
  babylon.ai:
    level: WARNING
    handlers: [file]
    propagate: false
    
  babylon.db:
    level: INFO
    handlers: [file]
    propagate: false
    
  babylon.metrics:
    level: INFO
    handlers: [json_file]
    propagate: false

root:
  level: WARNING
  handlers: [console]
```

## Validation and Type Checking

### Configuration Validation

The system validates configurations at startup:

```python
# Validation rules
VALIDATION_RULES = {
    'GAME_DIFFICULTY': {
        'type': str,
        'choices': ['easy', 'normal', 'hard', 'expert']
    },
    'AI_COMPLEXITY': {
        'type': str, 
        'choices': ['basic', 'intermediate', 'advanced']
    },
    'AUTO_SAVE_INTERVAL': {
        'type': int,
        'min': 60,
        'max': 3600
    },
    'AI_CREATIVITY': {
        'type': float,
        'min': 0.0,
        'max': 1.0
    },
    'DATABASE_URL': {
        'type': str,
        'pattern': r'^postgresql://.*'
    }
}
```

### Environment Variable Types

| Type | Parsing Function | Example |
|------|------------------|---------|
| `string` | `str(value)` | `GAME_DIFFICULTY=normal` |
| `boolean` | `value.lower() in ('true', '1', 'yes')` | `AUTO_SAVE=true` |
| `integer` | `int(value)` | `DB_POOL_SIZE=10` |
| `float` | `float(value)` | `AI_CREATIVITY=0.7` |
| `list` | `value.split(',')` | `LOG_HANDLERS=file,console` |

## Configuration Profiles

### Profile Structure

Profiles are stored in `config/profiles/`:

```
config/profiles/
├── development.env
├── production.env
├── testing.env
└── custom.env
```

### Profile Loading

```bash
# Load specific profile
python -m babylon --profile development

# Load profile with overrides
python -m babylon --profile production --env-file custom_overrides.env
```

### Profile Inheritance

```yaml
# config/profiles/custom.yaml
inherits: production

overrides:
  AI_COMPLEXITY: advanced
  METRICS_ENABLED: true
  LOG_LEVEL: DEBUG
```

## Configuration Best Practices

### Security

- Never commit `.env` files with secrets
- Use environment-specific configurations
- Rotate API keys regularly
- Limit database permissions

### Performance

- Tune memory limits based on available RAM
- Adjust batch sizes for your hardware
- Enable compression for large datasets
- Monitor resource usage

### Development

- Use separate databases for development/testing
- Enable debug logging during development
- Use mock services for external APIs
- Profile performance regularly

### Production

- Use conservative resource limits
- Enable comprehensive logging
- Set up monitoring and alerts
- Backup configurations regularly

## Environment-Specific Examples

### Development Environment
```env
# Development optimized for fast iteration
GAME_DIFFICULTY=easy
AI_COMPLEXITY=basic
LOG_LEVEL=DEBUG
AUTO_SAVE_INTERVAL=60
ENABLE_DEBUG_MODE=true
USE_MOCK_AI=true
METRICS_ENABLED=true
```

### Production Environment  
```env
# Production optimized for performance and stability
GAME_DIFFICULTY=normal
AI_COMPLEXITY=advanced
LOG_LEVEL=INFO
AUTO_SAVE_INTERVAL=300
ENABLE_DEBUG_MODE=false
USE_MOCK_AI=false
METRICS_ENABLED=true
MAX_MEMORY_USAGE_GB=8
```

### Testing Environment
```env
# Testing optimized for reliability
GAME_DIFFICULTY=normal
AI_COMPLEXITY=basic
LOG_LEVEL=WARNING
AUTO_SAVE_INTERVAL=30
USE_MOCK_AI=true
BATCH_PROCESSING=false
PRELOAD_GAME_DATA=false
```

---

For configuration troubleshooting, see the [Troubleshooting Guide](../how-to/troubleshooting.md#configuration-issues).