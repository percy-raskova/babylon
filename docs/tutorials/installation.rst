Installation
============

This guide covers how to install Babylon and set up your development environment.

Requirements
------------

- Python 3.12 or higher
- uv for dependency management
- Git

Installation Steps
------------------

1. Clone the repository:

   .. code-block:: bash

      git clone https://github.com/percy-raskova/babylon.git
      cd babylon

2. Install dependencies using uv:

   .. code-block:: bash

      uv sync --extra server

3. Install pre-commit hooks:

   .. code-block:: bash

      uv run pre-commit install --hook-type commit-msg --hook-type pre-commit

4. Verify the installation:

   .. code-block:: bash

      uv run pytest -m "not ai" --tb=short -q

Development Tools
-----------------

The project uses several development tools:

- **Ruff**: Linting and formatting
- **MyPy**: Static type checking
- **Pytest**: Testing framework
- **Commitizen**: Conventional commit messages

Running Tests
^^^^^^^^^^^^^

.. code-block:: bash

   # Run fast math/logic tests
   uv run pytest -m "not ai"

   # Run AI/narrative evaluation tests
   uv run pytest -m "ai"

   # Run a specific test
   uv run pytest tests/unit/test_foo.py::test_specific

Linting and Formatting
^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: bash

   # Check and fix linting issues
   uv run ruff check . --fix

   # Format code
   uv run ruff format .

   # Type check
   uv run mypy src
