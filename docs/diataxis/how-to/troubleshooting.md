# Troubleshoot Common Issues

This guide helps you diagnose and fix the most common problems when running Babylon. Issues are organized by symptoms with step-by-step solutions.

## Quick Diagnostics

### Run the Built-in Diagnostics

```bash
python -m babylon --diagnose
```

This checks:
- System requirements
- Database connectivity  
- AI system status
- Configuration validity
- Common file/permission issues

## Installation and Setup Issues

### Problem: Dependencies Won't Install

**Symptoms:**
- `pip install` fails with compilation errors
- Missing Python packages
- Version conflicts

**Solutions:**

1. **Check Python version:**
```bash
python --version    # Must be 3.12+
```

2. **Update pip and setuptools:**
```bash
pip install --upgrade pip setuptools wheel
```

3. **Install system dependencies (Ubuntu/Debian):**
```bash
sudo apt update
sudo apt install build-essential python3-dev postgresql-dev libpq-dev
```

4. **Install system dependencies (macOS):**
```bash
brew install postgresql
```

5. **Use virtual environment:**
```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

6. **Clear pip cache:**
```bash
pip cache purge
pip install --no-cache-dir -r requirements.txt
```

### Problem: Database Connection Fails

**Symptoms:**
```
psycopg2.OperationalError: FATAL: database "babylon" does not exist
```

**Solutions:**

1. **Verify PostgreSQL is running:**
```bash
# Check status
sudo systemctl status postgresql    # Linux
brew services list postgresql       # macOS

# Start if needed
sudo systemctl start postgresql     # Linux  
brew services start postgresql      # macOS
```

2. **Create database:**
```bash
# Connect to PostgreSQL
sudo -u postgres psql

# Create database and user
CREATE DATABASE babylon;
CREATE USER babylon_user WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE babylon TO babylon_user;
\q
```

3. **Update connection string in `.env`:**
```env
DATABASE_URL=postgresql://babylon_user:your_password@localhost:5432/babylon
```

4. **Test connection:**
```bash
python -c "
from sqlalchemy import create_engine
import os
from dotenv import load_dotenv
load_dotenv()
engine = create_engine(os.getenv('DATABASE_URL'))
print('✅ Database connection successful!')
"
```

### Problem: ChromaDB Issues

**Symptoms:**
- Vector database errors
- Embedding generation failures
- Slow AI responses

**Solutions:**

1. **Reset ChromaDB:**
```bash
rm -rf ./data/chroma
python -m babylon --init-chroma
```

2. **Check disk space:**
```bash
df -h    # Need at least 1GB free
```

3. **Verify ChromaDB installation:**
```bash
python -c "import chromadb; print('ChromaDB OK')"
```

4. **Test embedding model:**
```bash
python -c "
from sentence_transformers import SentenceTransformer
model = SentenceTransformer('all-MiniLM-L12-v2')
print('Embedding model OK')
"
```

## Runtime Issues  

### Problem: Game Won't Start

**Symptoms:**
- Import errors
- Configuration errors
- Immediate crashes

**Solutions:**

1. **Check for configuration errors:**
```bash
python -m babylon.config --validate
```

2. **Run in debug mode:**
```bash
python -m babylon --debug --verbose
```

3. **Clear cached files:**
```bash
find . -name "*.pyc" -delete
find . -name "__pycache__" -type d -exec rm -rf {} +
```

4. **Check file permissions:**
```bash
# Ensure you own the babylon directory
chown -R $USER:$USER /path/to/babylon

# Make main script executable
chmod +x src/babylon/__main__.py
```

### Problem: Poor Performance

**Symptoms:**
- Slow responses (>10 seconds)
- High memory usage
- System freezes

**Solutions:**

1. **Reduce AI complexity:**
```env
# In .env file
AI_COMPLEXITY=basic
CHROMA_MEMORY_LIMIT_MB=512
BATCH_PROCESSING=false
```

2. **Check system resources:**
```bash
# Monitor while game runs
htop        # or 'top' on macOS
free -h     # Check available memory
df -h       # Check disk space
```

3. **Profile memory usage:**
```bash
python -m babylon --profile-memory
```

4. **Clear AI cache:**
```bash
python -c "
from babylon.data.chroma_manager import ChromaManager
manager = ChromaManager()
manager.clear_cache()
print('Cache cleared')
"
```

### Problem: AI System Not Responding

**Symptoms:**
- Generic/repetitive AI responses
- "AI system unavailable" messages
- Long delays in AI processing

**Solutions:**

1. **Check AI configuration:**
```bash
python -m babylon.ai --test-connection
```

2. **Verify API keys (if using OpenAI):**
```env
# In .env - ensure valid API key
OPENAI_API_KEY=sk-your-actual-key-here
```

3. **Test embedding generation:**
```bash
python -c "
from babylon.rag.embeddings import EmbeddingManager
manager = EmbeddingManager()
result = manager.generate_embedding('test text')
print('Embeddings working:', len(result))
"
```

4. **Reset AI cache:**
```bash
rm -rf ./data/ai_cache
python -m babylon --reset-ai-cache
```

## Game Logic Issues

### Problem: Contradictions Not Working

**Symptoms:**
- No events generate
- Static game world
- Contradictions don't change intensity

**Solutions:**

1. **Verify contradiction system:**
```bash
python -c "
from babylon.systems.contradiction_analysis import ContradictionAnalysis
ca = ContradictionAnalysis()
print('Contradictions loaded:', len(ca.active_contradictions))
"
```

2. **Check game configuration:**
```env
# Ensure contradictions are enabled
CONTRADICTION_ANALYSIS=true
CONTRADICTION_INTENSITY_THRESHOLD=0.1
EVENT_GENERATION=true
```

3. **Reset game state:**
```bash
python -m babylon --new-game --reset-state
```

4. **Enable debug logging:**
```bash
python -m babylon --log-level DEBUG --log-contradictions
```

### Problem: Save/Load Issues

**Symptoms:**
- Games won't save
- Corrupted save files
- Load errors

**Solutions:**

1. **Check save directory permissions:**
```bash
mkdir -p ./saves
chmod 755 ./saves
```

2. **Verify save file integrity:**
```bash
python -m babylon --verify-save ./saves/your_save.json
```

3. **Backup and restore:**
```bash
# Backup saves
cp -r ./saves ./saves_backup

# Restore from backup if needed
cp -r ./saves_backup/* ./saves/
```

4. **Clear corrupted saves:**
```bash
# List saves
python -m babylon --list-saves

# Remove corrupted save
python -m babylon --remove-save corrupted_save_name
```

## Network and API Issues

### Problem: External API Timeouts

**Symptoms:**
- OpenAI API timeouts
- Network connection errors
- Rate limiting messages

**Solutions:**

1. **Check internet connectivity:**
```bash
ping google.com
curl -I https://api.openai.com/v1/models
```

2. **Increase timeout values:**
```env
AI_TIMEOUT=60              # Increase from default 30
OPENAI_REQUEST_TIMEOUT=45
```

3. **Implement retry logic:**
```env
AI_MAX_RETRIES=3
AI_RETRY_DELAY=5          # Seconds between retries
```

4. **Use local AI models (if available):**
```env
USE_LOCAL_AI=true
LOCAL_MODEL_PATH=./models/local_model
```

## Environment and Configuration Issues

### Problem: Environment Variables Not Loading

**Symptoms:**
- Default settings used instead of custom ones
- Configuration seems ignored
- Missing API keys

**Solutions:**

1. **Verify .env file location:**
```bash
ls -la .env    # Should be in project root
```

2. **Check .env file format:**
```bash
# Correct format (no spaces around =)
DATABASE_URL=postgresql://user:pass@host:port/db
AI_COMPLEXITY=intermediate

# Incorrect format (spaces cause issues)
DATABASE_URL = postgresql://user:pass@host:port/db
```

3. **Test environment loading:**
```bash
python -c "
import os
from dotenv import load_dotenv
load_dotenv()
print('DATABASE_URL:', os.getenv('DATABASE_URL'))
print('AI_COMPLEXITY:', os.getenv('AI_COMPLEXITY'))
"
```

4. **Use absolute paths:**
```bash
# If relative paths don't work
python -m babylon --env-file /absolute/path/to/.env
```

### Problem: Permission Denied Errors

**Symptoms:**
```
PermissionError: [Errno 13] Permission denied: './data/chroma'
```

**Solutions:**

1. **Fix directory permissions:**
```bash
sudo chown -R $USER:$USER ./data
chmod -R 755 ./data
```

2. **Create directories with correct permissions:**
```bash
mkdir -p ./data/{chroma,saves,logs,cache}
chmod 755 ./data ./data/*
```

3. **Run as current user:**
```bash
# Don't use sudo unless necessary
python -m babylon

# If you must use sudo, fix ownership after:
sudo python -m babylon
sudo chown -R $USER:$USER ./data
```

## Advanced Troubleshooting

### Enable Comprehensive Logging

```bash
# Create detailed log
python -m babylon --log-level DEBUG --log-file debug.log --verbose

# In another terminal, watch the log
tail -f debug.log
```

### Memory and Performance Debugging

```bash
# Run with memory profiling
python -m babylon --profile-memory --profile-cpu

# Generate performance report
python -m babylon --performance-report
```

### System Information Collection

```bash
# Collect system info for bug reports
python -m babylon --system-info > system_report.txt
```

This generates a report with:
- Python version and packages
- System specifications
- Configuration summary
- Recent error logs

## Getting Additional Help

### Create a Bug Report

If troubleshooting doesn't resolve your issue:

1. **Collect diagnostic information:**
```bash
python -m babylon --diagnose --full-report > bug_report.txt
```

2. **Include recent logs:**
```bash
tail -n 100 logs/babylon.log >> bug_report.txt
```

3. **Document steps to reproduce:**
   - What you were doing when the problem occurred
   - Exact error messages
   - Your system specifications
   - Configuration settings

### Community Resources

- **Community Forum**: Share your issue with other users
- **GitHub Issues**: Report bugs and request features
- **Discord Channel**: Real-time help from developers
- **Documentation**: Check [Reference Documentation](../reference/)

## Quick Reference Checklist

**Before reporting issues, verify:**

- [ ] Python 3.12+ installed
- [ ] All dependencies installed successfully
- [ ] PostgreSQL running and accessible
- [ ] .env file properly configured
- [ ] Sufficient disk space (>1GB)
- [ ] Sufficient RAM (>2GB available)
- [ ] File permissions correct
- [ ] Recent logs checked for error details

**Emergency recovery:**
```bash
# Nuclear option - complete reset
rm -rf ./data/chroma
rm -rf ./saves  
cp .env.example .env
python -m babylon --init-all --force
```

---

**Issue not covered here?** Check the [Reference Documentation](../reference/) or ask in the community forum with your diagnostic report.