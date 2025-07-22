# Basic Configuration

This tutorial teaches you how to customize Babylon to match your preferences and system capabilities. You'll learn to configure AI behavior, performance settings, and game parameters.

## Prerequisites  

- Complete [Getting Started](getting-started.md) tutorial
- Babylon installed and working
- Text editor for configuration files

## What You'll Learn

- How to modify game settings via configuration files
- How to adjust AI complexity and behavior
- How to optimize performance for your system
- How to customize game parameters

## Understanding Configuration Files

Babylon uses several configuration files:

- **`.env`** - Main environment variables
- **`config/base.py`** - Core game settings
- **`logging.yaml`** - Logging configuration  
- **Game save files** - Session-specific settings

## Step 1: Configure Basic Game Settings

### Edit Your Environment File

Open `.env` in your text editor:

```bash
# From your babylon directory
nano .env
```

### Essential Settings to Configure

```env
# === BASIC GAME CONFIGURATION ===

# Game Difficulty (affects contradiction intensity and complexity)
GAME_DIFFICULTY=normal          # Options: easy, normal, hard, expert

# Auto-save Frequency (how often progress is saved)
AUTO_SAVE_INTERVAL=300          # Seconds (300 = 5 minutes)
AUTO_SAVE=true                  # Enable/disable auto-saving

# Session Settings
MAX_SESSION_LENGTH=7200         # Maximum session time in seconds (2 hours)
PAUSE_ON_CRISIS=true           # Auto-pause during major events

# Display Settings
COLORED_OUTPUT=true            # Colorized terminal output
ANIMATION_SPEED=medium         # slow, medium, fast, off
SHOW_DETAILED_STATS=true       # Extended information display
```

### Step 2: Configure AI Behavior

AI settings significantly affect gameplay experience and resource usage:

```env
# === AI CONFIGURATION ===

# AI Complexity (affects decision quality and resource usage)
AI_COMPLEXITY=intermediate     # Options: basic, intermediate, advanced

# Response Generation
AI_RESPONSE_LENGTH=medium      # short, medium, long
AI_CREATIVITY=0.7             # 0.0-1.0 (higher = more creative/unpredictable)
AI_HISTORICAL_ACCURACY=0.8    # 0.0-1.0 (higher = more historically grounded)

# Performance Settings
AI_CACHE_SIZE=1000            # Number of responses to cache
AI_TIMEOUT=30                 # Seconds before AI request timeout
```

### Example: Setting up for Different Use Cases

**For Learning/Exploration (Slower, More Detailed):**
```env
GAME_DIFFICULTY=easy
AI_COMPLEXITY=intermediate  
AI_RESPONSE_LENGTH=long
SHOW_DETAILED_STATS=true
ANIMATION_SPEED=slow
```

**For Quick Sessions (Faster, Streamlined):**
```env
GAME_DIFFICULTY=normal
AI_COMPLEXITY=basic
AI_RESPONSE_LENGTH=short
SHOW_DETAILED_STATS=false
ANIMATION_SPEED=fast
```

## Step 3: Configure Performance Settings

### Database Configuration

```env
# === DATABASE SETTINGS ===

# PostgreSQL Connection
DATABASE_URL=postgresql://babylon:password@localhost:5432/babylon_game
DB_POOL_SIZE=10               # Connection pool size
DB_MAX_OVERFLOW=20            # Additional connections when needed

# Vector Database (ChromaDB)
CHROMA_PERSIST_DIR=./data/chroma    # Storage location
CHROMA_MEMORY_LIMIT=2048            # MB of RAM to use
CHROMA_BATCH_SIZE=100               # Items processed together
```

### Memory and CPU Settings

```env
# === PERFORMANCE SETTINGS ===

# Memory Management
MAX_MEMORY_USAGE_GB=4         # Maximum RAM usage
CACHE_SIZE_MB=512            # Cache size for game data
GC_THRESHOLD=1000            # Garbage collection frequency

# Processing
MAX_WORKER_THREADS=4         # Parallel processing threads
BATCH_PROCESSING=true        # Process multiple items together
PRELOAD_GAME_DATA=true       # Load common data at startup
```

## Step 4: Configure Logging

Edit `logging.yaml` to control what information gets logged:

```yaml
version: 1
formatters:
  simple:
    format: '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
  detailed:
    format: '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s'

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

loggers:
  babylon:
    level: INFO
    handlers: [console, file]
    propagate: no
    
  babylon.ai:
    level: WARNING    # Reduce AI system noise
    handlers: [file]
    propagate: no

root:
  level: INFO
  handlers: [console]
```

### Logging Levels for Different Purposes

**For Development/Debugging:**
```yaml
loggers:
  babylon:
    level: DEBUG      # Show all information
  babylon.ai:
    level: INFO       # Include AI decisions
```

**For Normal Play:**
```yaml  
loggers:
  babylon:
    level: INFO       # Standard information
  babylon.ai:
    level: WARNING    # Only AI problems
```

## Step 5: Test Your Configuration

### Validate Settings

Run the configuration validator:

```bash
python -m babylon.config --validate
```

Expected output:
```
✅ Environment variables loaded successfully
✅ Database connection: OK
✅ ChromaDB configuration: OK  
✅ AI system configuration: OK
✅ Logging configuration: Valid

Configuration Summary:
- Game Difficulty: normal
- AI Complexity: intermediate
- Memory Limit: 4GB
- Auto-save: Enabled (5 min intervals)

All systems ready!
```

### Test Game Launch

Start Babylon to verify your settings work:

```bash
python -m babylon --test-config
```

This launches a quick test session to verify everything works with your new settings.

## Step 6: Advanced Configuration Options

### Custom Game Parameters

Create `config/custom_game.yaml` for specialized settings:

```yaml
# Custom Game Parameters
game_parameters:
  # Starting conditions
  population_growth_rate: 0.02      # 2% annual growth
  initial_technology_level: 0.3     # 0.0-1.0 scale
  contradiction_sensitivity: 1.2    # How quickly tensions build
  
  # Economic settings
  inflation_rate: 0.03              # 3% annual inflation
  trade_openness: 0.7               # How connected to world economy
  resource_scarcity: 0.4            # Scarcity creates more contradictions
  
  # Political settings
  democratic_institutions: 0.2       # Starting democracy level
  state_capacity: 0.6               # Government effectiveness
  civil_liberties: 0.3              # Individual freedoms
```

### Scenario Templates

Create reusable scenario configurations in `config/scenarios/`:

```yaml
# config/scenarios/learning_mode.yaml
name: "Learning Mode"
description: "Slower pace, more guidance, detailed explanations"

settings:
  game_difficulty: easy
  ai_complexity: intermediate
  auto_pause_on_events: true
  detailed_explanations: true
  contradiction_buildup_rate: 0.5   # Slower tension development
  crisis_frequency: 0.3             # Fewer random crises
  
guidance:
  show_hints: true
  explain_consequences: true
  suggest_actions: true
```

## Step 7: Profile-Based Configuration

### Create Configuration Profiles

Set up different profiles for different use cases:

```bash
# In your babylon directory
mkdir -p config/profiles

# Create profile files
touch config/profiles/development.env
touch config/profiles/teaching.env  
touch config/profiles/research.env
```

### Development Profile
```env
# config/profiles/development.env
GAME_DIFFICULTY=expert
AI_COMPLEXITY=advanced
LOG_LEVEL=DEBUG
AUTO_SAVE_INTERVAL=60      # Save frequently during development
SHOW_DEBUG_INFO=true
ENABLE_PROFILING=true
```

### Teaching Profile  
```env
# config/profiles/teaching.env
GAME_DIFFICULTY=easy
AI_COMPLEXITY=basic
PAUSE_ON_CRISIS=true
SHOW_DETAILED_STATS=true
EXPLANATION_MODE=verbose
AUTO_SAVE_INTERVAL=180
```

### Load a Specific Profile

```bash
python -m babylon --profile development
```

## Troubleshooting Configuration Issues

### Common Problems and Solutions

**Game runs slowly:**
```env
# Reduce AI complexity
AI_COMPLEXITY=basic
AI_CACHE_SIZE=500

# Limit memory usage  
MAX_MEMORY_USAGE_GB=2
BATCH_PROCESSING=false
```

**Too much logging output:**
```yaml
# In logging.yaml
loggers:
  babylon:
    level: WARNING    # Only show problems
```

**Database connection errors:**
```env
# Check your database URL format
DATABASE_URL=postgresql://username:password@host:port/database

# Reduce connection pool if limited connections
DB_POOL_SIZE=3
DB_MAX_OVERFLOW=5
```

## Backup Your Configuration

### Save Your Settings

Once you have a working configuration, back it up:

```bash
# Create backup directory
mkdir -p backups/config

# Backup configuration files
cp .env backups/config/env_backup_$(date +%Y%m%d)
cp logging.yaml backups/config/logging_backup_$(date +%Y%m%d)
cp -r config/ backups/config/config_backup_$(date +%Y%m%d)/
```

### Version Control Configuration

Track configuration changes:

```bash
# Initialize git in config directory  
cd config
git init
git add .
git commit -m "Initial configuration setup"

# Track changes over time
git add .
git commit -m "Optimized for performance"
```

## What You've Accomplished

You can now:

✅ **Configure core game settings** for your preferred experience
✅ **Adjust AI behavior** to match your system capabilities  
✅ **Optimize performance** for smooth gameplay
✅ **Customize logging** to get the information you need
✅ **Create reusable profiles** for different use cases
✅ **Troubleshoot common issues** with configuration

## Next Steps

With your configuration complete:

- **Play with your optimized settings**: Start a new game session
- **Learn advanced techniques**: Check out [Advanced Configuration](../how-to/advanced-configuration.md)  
- **Optimize further**: Read about [Performance Tuning](../how-to/performance-tuning.md)
- **Share configurations**: Contribute to the [Community Configurations](../reference/community-configs.md)

---

**Configuration not working as expected?** Check the [Configuration Troubleshooting](../how-to/troubleshooting.md#configuration-issues) guide.