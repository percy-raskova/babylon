# Contributing to Babylon RPG

Thank you for your interest in contributing to The Fall of Babylon! This document provides guidelines for contributing to this Marxist text-based RPG project.

## Quick Start

1. **Fork and Clone**
   ```bash
   git clone https://github.com/your-username/babylon.git
   cd babylon
   ```

2. **Set Up Development Environment**
   ```bash
   # Install Poetry (if not already installed)
   curl -sSL https://install.python-poetry.org | python3 -
   
   # Install dependencies using Poetry
   poetry install
   
   # Activate the virtual environment
   poetry shell
   
   # Alternative: switching to Poetry soon
   # python -m venv venv
   # source venv/bin/activate  # On Windows: venv\Scripts\activate
   # pip install -r requirements.txt
   # pip install -r requirements-dev.txt  # Development dependencies
   ```

3. **Run Tests**
   ```bash
   poetry run pytest tests/
   ```

4. **Run the Game**
   ```bash
   poetry run python src/babylon/__main__.py
   ```

## Development Setup Issues?

If you encounter issues during setup, please check our [troubleshooting guide](docs/TROUBLESHOOTING.md) or open an issue.

## Code Style

We use the following tools to maintain code quality:

- **Ruff** for code formatting and linting
- **mypy** for type checking
- **isort** for import sorting

Before submitting a PR, run:
```bash
poetry run ruff format src/ tests/
poetry run ruff check src/ tests/
poetry run mypy src/
```

## Testing Guidelines

- Write tests for new functionality
- Maintain or improve test coverage
- Use descriptive test names
- Include integration tests for AI/ML components

## Pull Request Process

1. Create a feature branch: `git checkout -b feature/your-feature-name`
2. Make your changes following our code style
3. Add or update tests as needed
4. Update documentation if required
5. Commit your changes with descriptive messages
6. Push to your fork and submit a pull request

## Reporting Issues

When reporting bugs, please include:
- Python version and operating system
- Steps to reproduce the issue
- Expected vs actual behavior
- Error messages (if any)

## Areas for Contribution

- **Core Game Mechanics**: Politics, economy, contradiction systems
- **AI/ML Integration**: RAG system, ChromaDB optimization
- **User Interface**: Terminal UI improvements, web interface
- **User Experience**: Art, narrative storytelling, creative pizzazz
- **Testing**: Unit tests, integration tests, performance tests
- **DevOps**: CI/CD, deployment, monitoring

## Questions?

Feel free to open an issue with the `question` label or start a discussion on GitHub Discussions.

## Code of Conduct

Please note that this project is governed by our [Code of Conduct](CODE_OF_CONDUCT.md). By participating, you agree to abide by its terms.