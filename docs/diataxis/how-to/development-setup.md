# Set Up Development Environment

This guide walks you through setting up a complete development environment for contributing to Babylon. You'll configure code editing, testing, debugging, and contribution workflows.

## Prerequisites

- Git installed and configured
- Python 3.12+ installed
- Basic familiarity with Python development
- Text editor or IDE of choice

## Step 1: Fork and Clone

### Fork the Repository

1. Go to https://github.com/bogdanscarwash/babylon
2. Click "Fork" to create your copy
3. Clone your fork:

```bash
git clone https://github.com/YOUR_USERNAME/babylon.git
cd babylon
```

### Set Up Remote Tracking

```bash
# Add upstream remote to sync with main repo
git remote add upstream https://github.com/bogdanscarwash/babylon.git

# Verify remotes
git remote -v
```

## Step 2: Environment Setup

### Create Development Environment

```bash
# Create isolated Python environment
python -m venv venv_dev
source venv_dev/bin/activate  # Windows: venv_dev\Scripts\activate

# Upgrade core tools
pip install --upgrade pip setuptools wheel
```

### Install Development Dependencies

```bash
# Install runtime dependencies
pip install -r requirements.txt

# Install development tools
pip install -e .  # Editable install
pip install pytest pytest-cov pytest-mock black flake8 isort mypy pre-commit
```

### Development Configuration

Create `.env.dev` for development settings:

```env
# Development-specific settings
DATABASE_URL=postgresql://babylon_dev:dev_password@localhost:5432/babylon_dev
CHROMA_PERSIST_DIR=./dev_data/chroma
LOG_LEVEL=DEBUG
AUTO_SAVE_INTERVAL=60          # Save frequently during development
ENABLE_PROFILING=true
METRICS_ENABLED=true

# AI Development
AI_COMPLEXITY=basic            # Faster responses during development
AI_CACHE_SIZE=100             # Small cache for development
USE_MOCK_AI=true              # Use mock AI for faster testing

# Testing
TEST_DATABASE_URL=postgresql://babylon_test:test_password@localhost:5432/babylon_test
```

## Step 3: Database Setup

### Create Development Database

```bash
# Connect to PostgreSQL
sudo -u postgres psql

# Create development database
CREATE DATABASE babylon_dev;
CREATE USER babylon_dev WITH PASSWORD 'dev_password';
GRANT ALL PRIVILEGES ON DATABASE babylon_dev TO babylon_dev;

# Create test database  
CREATE DATABASE babylon_test;
CREATE USER babylon_test WITH PASSWORD 'test_password';
GRANT ALL PRIVILEGES ON DATABASE babylon_test TO babylon_test;
\q
```

### Initialize Development Data

```bash
# Load development configuration
python -m babylon --env-file .env.dev --init-db

# Create sample development data
python -m babylon.dev --create-sample-data
```

## Step 4: Development Tools Configuration

### Set Up Pre-commit Hooks

```bash
# Install pre-commit
pre-commit install

# Test the hooks
pre-commit run --all-files
```

This runs:
- Code formatting (Black)
- Import sorting (isort)  
- Linting (flake8)
- Type checking (mypy)
- Basic tests

### Configure Your IDE

#### VS Code Setup

Install recommended extensions:
```bash
# Create VS Code settings
mkdir -p .vscode
cat > .vscode/extensions.json << 'EOF'
{
    "recommendations": [
        "ms-python.python",
        "ms-python.black-formatter", 
        "ms-python.flake8",
        "ms-python.mypy-type-checker",
        "ms-python.isort",
        "redhat.vscode-yaml"
    ]
}
EOF
```

Configure workspace settings:
```json
{
    "python.defaultInterpreterPath": "./venv_dev/bin/python",
    "python.linting.enabled": true,
    "python.linting.flake8Enabled": true,
    "python.formatting.provider": "black",
    "python.linting.mypyEnabled": true,
    "python.testing.pytestEnabled": true,
    "python.testing.pytestArgs": [
        "tests"
    ],
    "files.exclude": {
        "**/__pycache__": true,
        "**/*.pyc": true,
        "**/venv*": true
    }
}
```

#### PyCharm Setup

1. Open Babylon project in PyCharm
2. Go to File > Settings > Project > Python Interpreter
3. Select your `venv_dev` environment
4. Configure code style to use Black formatter
5. Enable pytest as test runner

## Step 5: Testing Setup

### Run the Test Suite

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=babylon

# Run specific test categories
pytest tests/unit/           # Unit tests only
pytest tests/integration/    # Integration tests only
pytest -k "test_contradiction"  # Tests matching pattern
```

### Test Configuration

The project uses `pyproject.toml` for pytest configuration:

```toml
[tool.pytest.ini_options]
pythonpath = ["src"]
testpaths = ["tests"]
asyncio_mode = "strict"
asyncio_default_fixture_loop_scope = "function"

# Test markers for categorization
markers = [
    "unit: Unit tests",
    "integration: Integration tests", 
    "slow: Slow-running tests",
    "ai: Tests requiring AI services"
]
```

### Writing Tests

Example test structure:
```python
# tests/unit/test_contradiction_analysis.py
import pytest
from babylon.systems.contradiction_analysis import ContradictionAnalysis

class TestContradictionAnalysis:
    def test_contradiction_detection(self):
        """Test that contradictions are properly detected."""
        ca = ContradictionAnalysis()
        # Test implementation
        
    def test_intensity_calculation(self):
        """Test contradiction intensity calculations."""
        # Test implementation

    @pytest.mark.slow
    def test_full_analysis_cycle(self):
        """Test complete analysis cycle (slow test)."""
        # Test implementation
```

## Step 6: Development Workflow

### Daily Development Routine

```bash
# Start development session
cd babylon
source venv_dev/bin/activate

# Sync with upstream
git fetch upstream
git rebase upstream/main

# Start development server with auto-reload
python -m babylon.dev --watch --debug

# In another terminal, run tests in watch mode
pytest --watch
```

### Code Quality Checks

```bash
# Run all quality checks
./scripts/check_code_quality.sh

# Or run individually:
black src/ tests/                    # Format code
isort src/ tests/                    # Sort imports  
flake8 src/ tests/                   # Lint code
mypy src/                            # Type check
pytest --cov=babylon                 # Test with coverage
```

### Performance Profiling

```bash
# Profile memory usage
python -m babylon.dev --profile-memory

# Profile CPU usage
python -m babylon.dev --profile-cpu

# Generate performance report
python -m babylon.dev --performance-report > perf_report.txt
```

## Step 7: Debugging Setup

### Enable Debug Mode

```bash
# Run with comprehensive debugging
python -m babylon --debug --verbose --log-file dev_debug.log

# Debug specific systems
python -m babylon --debug-ai --debug-chroma --debug-contradictions
```

### Debug Configuration

Add to `.env.dev`:
```env
# Debugging options
ENABLE_DEBUG_MODE=true
DEBUG_SQL_QUERIES=true
DEBUG_AI_PROMPTS=true
DEBUG_VECTOR_OPERATIONS=true
ENABLE_PERFORMANCE_PROFILING=true

# Detailed logging
LOG_LEVEL=DEBUG
LOG_FORMAT=detailed
ENABLE_FUNCTION_TRACING=true
```

### Using Python Debugger

```python
# In your code, add breakpoints:
import pdb; pdb.set_trace()

# Or use ipdb for enhanced debugging:
import ipdb; ipdb.set_trace()
```

## Step 8: Contributing Workflow

### Create Feature Branch

```bash
# Create feature branch from main
git checkout main
git pull upstream main
git checkout -b feature/your-feature-name
```

### Make Changes

1. Write code following project conventions
2. Add tests for new functionality  
3. Update documentation if needed
4. Run quality checks frequently

### Commit Changes

```bash
# Stage changes
git add .

# Pre-commit hooks run automatically
git commit -m "feat: add new contradiction detection algorithm

- Implement dynamic threshold adjustment
- Add unit tests for edge cases
- Update documentation with usage examples"
```

### Submit Pull Request

```bash
# Push to your fork
git push origin feature/your-feature-name

# Create pull request on GitHub
# Include:
# - Clear description of changes
# - Link to related issues
# - Screenshots if UI changes
# - Test results
```

## Step 9: Advanced Development

### Custom Development Commands

Create development scripts in `scripts/dev/`:

```bash
#!/bin/bash
# scripts/dev/start_dev_session.sh

echo "Starting Babylon development session..."

# Activate environment
source venv_dev/bin/activate

# Check system status
python -m babylon --diagnose

# Start with development settings  
python -m babylon --env-file .env.dev --debug --watch

echo "Development session ready!"
```

### Performance Testing

```bash
# Load testing
python -m babylon.dev --load-test --concurrent-users 10

# Memory leak testing
python -m babylon.dev --memory-test --duration 3600

# Stress testing
python -m babylon.dev --stress-test --iterations 1000
```

### Database Development

```bash
# Create migration
python -m babylon.db --create-migration "add_new_field"

# Apply migrations
python -m babylon.db --migrate

# Rollback migration
python -m babylon.db --rollback

# Reset development database
python -m babylon.db --reset --env dev
```

## Step 10: Documentation Development

### Build Documentation Locally

```bash
# Install documentation tools
pip install sphinx sphinx-rtd-theme

# Build docs
cd docs/
make html

# Serve docs locally  
python -m http.server 8000 --directory _build/html
```

### Live Documentation Updates

```bash
# Auto-rebuild docs on changes
pip install sphinx-autobuild
sphinx-autobuild docs/ docs/_build/html --host 0.0.0.0 --port 8000
```

## Troubleshooting Development Issues

### Common Development Problems

**Tests failing in development but passing in CI:**
```bash
# Ensure consistent environment
pip freeze > requirements-dev.txt
pip install -r requirements-dev.txt --force-reinstall
```

**Import errors in development:**
```bash
# Reinstall in development mode
pip uninstall babylon
pip install -e .
```

**Database issues:**
```bash
# Reset development database
dropdb babylon_dev
createdb babylon_dev  
python -m babylon --env-file .env.dev --init-db
```

### Development Environment Reset

Nuclear option for environment issues:
```bash
# Backup any important changes first!
deactivate
rm -rf venv_dev/
python -m venv venv_dev
source venv_dev/bin/activate
pip install -r requirements.txt
pip install -e .
```

## Next Steps

With your development environment ready:

- **Start contributing**: Check the [Development Guide](../reference/development.md)
- **Understand architecture**: Read [Architecture Overview](../explanation/architecture.md)  
- **Join discussions**: Participate in community channels
- **Explore advanced topics**: See [Advanced Development](../reference/advanced-development.md)

## Quick Reference

**Essential Development Commands:**
```bash
# Environment
source venv_dev/bin/activate
python -m babylon --env-file .env.dev

# Testing  
pytest --cov=babylon
pytest -k "test_name"

# Quality
black src/ tests/
flake8 src/ tests/
mypy src/

# Git workflow
git checkout -b feature/name
git commit -m "feat: description"
git push origin feature/name
```

---

**Development environment issues?** Check the [Troubleshooting Guide](troubleshooting.md) or ask in the developer chat.