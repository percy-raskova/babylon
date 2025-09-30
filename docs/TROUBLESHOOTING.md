# Troubleshooting Guide

This guide helps resolve common issues when setting up and running The Fall of Babylon.

## Installation Issues

### 1. Package Installation Fails

**Problem**: `pip install -e .` fails with package discovery errors

**Solution**: 
```bash
# Ensure you're in the project root directory
cd /path/to/babylon

# Try installing dependencies first
pip install -r requirements.txt

# If still failing, check Python version
python --version  # Should be 3.12.x
```

**Alternative**: Install in development mode without editable flag:
```bash
pip install .
```

### 2. Dependency Timeout Errors

**Problem**: Network timeouts during dependency installation

**Solution**:
```bash
# Increase timeout and use alternative index
pip install -r requirements.txt --timeout 300 --extra-index-url https://pypi.org/simple/

# Or install core dependencies only
pip install numpy pandas sqlalchemy psycopg2-binary
```

### 3. ChromaDB Installation Issues

**Problem**: ChromaDB dependencies fail to install

**Solution**:
```bash
# Install system dependencies (Ubuntu/Debian)
sudo apt-get update
sudo apt-get install build-essential python3-dev

# Install system dependencies (macOS)
brew install cmake

# Then retry installation
pip install chromadb
```

## Runtime Issues

### 1. Database Connection Errors

**Problem**: PostgreSQL connection failures

**Solution**:
1. Check if PostgreSQL is running:
   ```bash
   # Ubuntu/Debian
   sudo systemctl status postgresql
   
   # macOS
   brew services list | grep postgresql
   ```

2. Verify environment variables in `.env`:
   ```env
   DATABASE_URL=postgresql://user:password@localhost:5432/babylon
   ```

3. Test connection:
   ```bash
   python -c "import psycopg2; psycopg2.connect('your_connection_string')"
   ```

### 2. ChromaDB Initialization Errors

**Problem**: ChromaDB fails to initialize

**Solution**:
1. Check disk space and permissions in `chroma/` directory
2. Clear ChromaDB data:
   ```bash
   rm -rf chroma/
   mkdir chroma
   ```

3. Verify environment variables:
   ```env
   CHROMA_PERSIST_DIRECTORY=./chroma
   CHROMA_HOST=localhost
   CHROMA_PORT=8000
   ```

### 3. AI/OpenAI API Errors

**Problem**: OpenAI API calls fail

**Solution**:
1. Verify API key in `.env`:
   ```env
   OPENAI_API_KEY=your_api_key_here
   ```

2. Check API quota and billing
3. Test API connection:
   ```bash
   python -c "
   import openai
   import os
   openai.api_key = os.getenv('OPENAI_API_KEY')
   print('API Key configured successfully')
   "
   ```

## Game Issues

### 1. Game Won't Start

**Problem**: Game fails to launch or crashes immediately

**Solution**:
1. Check Python path:
   ```bash
   python -c "import sys; print(sys.path)"
   ```

2. Verify all modules can be imported:
   ```bash
   python -c "from src.babylon import __main__"
   ```

3. Run with verbose logging:
   ```bash
   BABYLON_LOG_LEVEL=DEBUG python src/babylon/__main__.py
   ```

### 2. Save/Load Errors

**Problem**: Game state cannot be saved or loaded

**Solution**:
1. Check file permissions in the project directory
2. Verify database connectivity
3. Check available disk space
4. Review logs for specific error messages

### 3. Performance Issues

**Problem**: Game runs slowly or uses excessive memory

**Solution**:
1. Monitor resource usage:
   ```bash
   # Install and use htop or similar
   htop
   ```

2. Check ChromaDB performance:
   - Reduce batch sizes for embeddings
   - Clear unused cached data
   - Consider SSD storage for ChromaDB

3. Optimize Python environment:
   ```bash
   # Use Python with optimizations
   python -O src/babylon/__main__.py
   ```

## Development Issues

### 1. Tests Fail

**Problem**: Test suite doesn't run or fails

**Solution**:
1. Install development dependencies:
   ```bash
   pip install -r requirements-dev.txt
   ```

2. Set Python path:
   ```bash
   export PYTHONPATH="${PYTHONPATH}:${PWD}/src"
   pytest tests/
   ```

3. Run individual test files:
   ```bash
   pytest tests/unit/test_specific.py -v
   ```

### 2. Pre-commit Hooks Fail

**Problem**: Pre-commit checks fail during development

**Solution**:
1. Install pre-commit:
   ```bash
   pip install pre-commit
   pre-commit install
   ```

2. Run manually to fix issues:
   ```bash
   pre-commit run --all-files
   ```

3. Fix specific tool issues:
   ```bash
   # Fix formatting
   black src/ tests/
   
   # Fix imports
   isort src/ tests/
   ```

## Environment-Specific Issues

### Windows

- Use `venv\Scripts\activate` instead of `source venv/bin/activate`
- Install Visual Studio Build Tools if compiler errors occur
- Use PowerShell or Command Prompt with appropriate permissions

### macOS

- Install Xcode Command Line Tools: `xcode-select --install`
- Use Homebrew for system dependencies
- Check for M1/M2 compatibility issues with dependencies

### Docker

If using Docker for development:
```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "src/babylon/__main__.py"]
```

## Getting Help

If none of these solutions work:

1. **Check the logs**: Look for detailed error messages in the application logs
2. **Search existing issues**: Check GitHub issues for similar problems
3. **Create a new issue**: Use our [bug report template](.github/ISSUE_TEMPLATE/bug_report.yml)
4. **Join discussions**: Participate in GitHub Discussions for general questions

### When Reporting Issues

Please include:
- Operating system and version
- Python version (`python --version`)
- Complete error messages and stack traces
- Steps to reproduce the issue
- Your environment configuration (without sensitive data)

### Log Locations

- Application logs: `logs/` directory
- System logs: Check system-specific locations
- ChromaDB logs: `chroma/` directory
- Test logs: Generated during test runs