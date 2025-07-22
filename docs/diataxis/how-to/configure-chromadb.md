# How to Configure ChromaDB Integration

This guide shows you how to set up, optimize, and troubleshoot ChromaDB for Babylon's AI-powered game mechanics. ChromaDB handles vector storage for game entities, enabling semantic search and AI reasoning about game state.

## When to Use This Guide

- Setting up ChromaDB for the first time
- Optimizing ChromaDB performance
- Troubleshooting vector database issues
- Migrating ChromaDB data

## Prerequisites

- Babylon installed and running
- Basic understanding of vector databases (optional)
- Administrator access to your system

## Quick Setup (Recommended)

### Step 1: Use Default Configuration

For most users, the default ChromaDB setup works immediately:

```bash
# ChromaDB will automatically initialize on first run
python -m babylon
```

The game creates:
- Vector database in `./data/chroma/`
- Default collection named `babylon_entities`
- Automatic embeddings for all game objects

Skip to [Verify Setup](#verify-setup) if this works for you.

## Advanced Setup

### Step 2: Custom ChromaDB Configuration

Edit your `.env` file for custom settings:

```env
# === CHROMADB CONFIGURATION ===

# Storage location
CHROMA_PERSIST_DIR=./data/chroma_custom
CHROMA_COLLECTION_NAME=my_babylon_world

# Performance settings
CHROMA_MEMORY_LIMIT_MB=2048          # RAM allocation
CHROMA_BATCH_SIZE=50                 # Items processed together
CHROMA_MAX_BATCH_SIZE=1000          # Maximum batch size

# Backend configuration
CHROMA_BACKEND=duckdb               # Options: duckdb, sqlite
CHROMA_ANONYMIZED_TELEMETRY=false   # Disable usage tracking
```

### Step 3: Initialize Custom Database

```bash
# Remove existing database (if any)
rm -rf ./data/chroma

# Initialize with new settings
python -m babylon.chroma --init --config-check
```

Expected output:
```
Initializing ChromaDB...
✅ Database path: ./data/chroma_custom
✅ Collection: my_babylon_world  
✅ Backend: DuckDB
✅ Memory limit: 2048 MB
ChromaDB ready for use.
```

## Verify Setup

### Step 4: Test ChromaDB Integration

Run the built-in test suite:

```bash
python -m babylon.chroma --test
```

This verifies:
- Database connectivity
- Embedding generation
- Search functionality  
- Performance benchmarks

Expected results:
```
ChromaDB Integration Test
========================

✅ Connection: OK
✅ Collection access: OK
✅ Embedding generation: OK (avg: 45ms)
✅ Vector search: OK (avg: 12ms)  
✅ Batch operations: OK (500 items/sec)

Performance Summary:
- Query latency: 12ms (target: <100ms)
- Throughput: 500 items/sec
- Memory usage: 1.2GB (limit: 2.0GB)
- Storage size: 45MB

All systems operational!
```

## Performance Optimization

### Step 5: Optimize for Your System

#### For Development (Small datasets)
```env
CHROMA_MEMORY_LIMIT_MB=512          # Minimal memory usage
CHROMA_BATCH_SIZE=25               # Smaller batches
CHROMA_PRELOAD_EMBEDDINGS=false    # Load on demand
```

#### For Production (Large worlds)
```env  
CHROMA_MEMORY_LIMIT_MB=4096        # Use more memory
CHROMA_BATCH_SIZE=200              # Larger batches
CHROMA_PRELOAD_EMBEDDINGS=true     # Cache in memory
CHROMA_PARALLEL_PROCESSING=true    # Multi-threading
```

#### For Resource-Constrained Systems
```env
CHROMA_MEMORY_LIMIT_MB=256         # Very low memory
CHROMA_BATCH_SIZE=10              # Tiny batches
CHROMA_COMPRESSION=true           # Compress stored vectors
CHROMA_LAZY_LOADING=true          # Load only when needed
```

### Step 6: Monitor Performance

Enable ChromaDB metrics:

```env
CHROMA_METRICS_ENABLED=true
CHROMA_METRICS_INTERVAL=60         # Collect every minute
CHROMA_PERFORMANCE_LOGGING=true    # Log slow queries
```

Check performance with:
```bash
python -m babylon.chroma --metrics
```

Output shows:
```
ChromaDB Performance Metrics
===========================

Query Performance:
- Average latency: 15ms
- 95th percentile: 32ms  
- Slow queries (>100ms): 2 in last hour

Memory Usage:
- Current: 1.4GB / 2.0GB (70%)
- Peak: 1.8GB
- Collections: 3 active

Storage:
- Database size: 234MB
- Embedding count: 15,247
- Growth rate: +1,200 vectors/day

Recommendations:
⚠️  Consider increasing batch size for better throughput
✅ Memory usage is optimal
```

## Data Management

### Step 7: Backup ChromaDB Data

Babylon includes backup utilities:

```bash
# Create backup
python -m babylon.chroma --backup ./backups/chroma_$(date +%Y%m%d)

# Verify backup
python -m babylon.chroma --verify-backup ./backups/chroma_20240121
```

### Step 8: Restore from Backup

```bash
# Stop Babylon first
# Then restore
python -m babylon.chroma --restore ./backups/chroma_20240121

# Verify restoration  
python -m babylon.chroma --test
```

## Troubleshooting Common Issues

### Problem: "Collection not found" Error

**Symptoms:**
```
ChromaCollectionError: Collection 'babylon_entities' does not exist
```

**Solution:**
```bash
# Reinitialize database
python -m babylon.chroma --init --force

# Or create collection manually
python -c "
from babylon.data.chroma_manager import ChromaManager
manager = ChromaManager()
manager.create_collection('babylon_entities')
"
```

### Problem: Slow Query Performance  

**Symptoms:**
- Game responses take >10 seconds
- High CPU usage
- Memory warnings

**Solutions:**

1. **Reduce batch size:**
```env
CHROMA_BATCH_SIZE=25    # Down from default 50
```

2. **Increase memory allocation:**
```env
CHROMA_MEMORY_LIMIT_MB=4096
```

3. **Enable compression:**
```env
CHROMA_COMPRESSION=true
```

4. **Clear cache:**
```bash
python -m babylon.chroma --clear-cache
```

### Problem: "Out of Memory" Errors

**Symptoms:**
```
MemoryError: Unable to allocate array with shape (10000, 384)
```

**Solutions:**

1. **Reduce memory limit:**
```env
CHROMA_MEMORY_LIMIT_MB=1024    # Reduce from 2048
```

2. **Enable lazy loading:**
```env
CHROMA_LAZY_LOADING=true
CHROMA_PRELOAD_EMBEDDINGS=false
```

3. **Use smaller embedding model:**
```env
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2    # Smaller model
```

### Problem: Database Corruption

**Symptoms:**
- Random crashes
- "Database is locked" errors  
- Inconsistent search results

**Solutions:**

1. **Rebuild database:**
```bash
# Backup existing data
python -m babylon.chroma --backup ./emergency_backup

# Remove corrupted database
rm -rf ./data/chroma  

# Restore from backup
python -m babylon.chroma --restore ./emergency_backup
```

2. **Integrity check:**
```bash
python -m babylon.chroma --integrity-check --repair
```

## Advanced Configuration

### Step 9: Custom Embedding Models

Use different embedding models for specific needs:

```env
# For multilingual support
EMBEDDING_MODEL=sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2

# For domain-specific content
EMBEDDING_MODEL=sentence-transformers/all-mpnet-base-v2

# For fast, lightweight processing
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
```

### Step 10: Multiple Collections

Organize data into specialized collections:

```python
# In custom configuration
CHROMA_COLLECTIONS = {
    'entities': 'game_entities',
    'events': 'historical_events', 
    'contradictions': 'social_contradictions',
    'decisions': 'player_decisions'
}
```

Enable in `.env`:
```env
CHROMA_USE_MULTIPLE_COLLECTIONS=true
CHROMA_AUTO_CREATE_COLLECTIONS=true
```

## Integration with Game Systems

### Step 11: Verify Game Integration

Test ChromaDB with actual game mechanics:

```bash
# Start game with ChromaDB debugging
python -m babylon --debug-chroma

# In game console:
> debug chroma_status
ChromaDB Status:
- Collections: 4 active
- Total vectors: 12,487  
- Query cache: 89% hit rate
- Average query time: 8ms

> debug search_entities "economic inequality"
Found 15 related entities:
1. Worker-Capitalist Contradiction (similarity: 0.92)
2. Wealth Distribution Event (similarity: 0.87)
3. Class Struggle Dynamics (similarity: 0.83)
[...]

> debug embedding_health
Embedding System Health:
✅ Model loaded: sentence-transformers/all-MiniLM-L12-v2
✅ Vector dimensions: 384  
✅ Embedding cache: 1,247 cached (78% hit rate)
✅ Performance: 15ms average generation time
```

## Maintenance Tasks

### Step 12: Regular Maintenance

Add to your maintenance routine:

```bash
#!/bin/bash
# chroma_maintenance.sh

echo "ChromaDB Maintenance - $(date)"

# Performance check
echo "Checking performance..."
python -m babylon.chroma --metrics --brief

# Cleanup old data
echo "Cleaning up..."  
python -m babylon.chroma --cleanup --older-than 30d

# Backup
echo "Creating backup..."
python -m babylon.chroma --backup ./backups/auto_backup_$(date +%Y%m%d)

# Optimize database
echo "Optimizing..."
python -m babylon.chroma --optimize

echo "Maintenance complete!"
```

Run weekly:
```bash
# Add to crontab
0 2 * * 0 /path/to/babylon/chroma_maintenance.sh >> /var/log/babylon_maintenance.log
```

## Next Steps

With ChromaDB configured:

- **Optimize further**: Check [Performance Tuning](performance-tuning.md)
- **Explore AI features**: See [AI Integration Guide](ai-integration.md)  
- **Monitor system health**: Set up [Monitoring](monitoring-setup.md)
- **Contribute improvements**: Read [Development Guide](../reference/development.md)

## Quick Reference

**Essential Commands:**
```bash
# Initialize
python -m babylon.chroma --init

# Test setup
python -m babylon.chroma --test  

# Check performance
python -m babylon.chroma --metrics

# Backup data
python -m babylon.chroma --backup <path>

# Restore data  
python -m babylon.chroma --restore <path>
```

**Configuration Variables:**
```env
CHROMA_PERSIST_DIR=./data/chroma
CHROMA_MEMORY_LIMIT_MB=2048
CHROMA_BATCH_SIZE=50
CHROMA_COLLECTION_NAME=babylon_entities
```

---

**Still having issues?** Check the [Troubleshooting Guide](troubleshooting.md) or ask on the community forum.