Installation
============

This guide covers how to install Babylon and set up your development environment.

Requirements
------------

- mise for the pinned Python, Rust, and uv toolchains
- Git

Installation Steps
------------------

1. Clone the repository:

   .. code-block:: bash

      git clone https://github.com/percy-raskova/babylon.git
      cd babylon

2. Install the pinned toolchain and locked dependencies:

   .. code-block:: bash

      mise install
      mise run install

3. Install pre-commit hooks:

   .. code-block:: bash

      mise run hooks

4. Verify the installation:

   .. code-block:: bash

      mise run check

Development Tools
-----------------

The project uses several development tools:

- **Ruff**: Linting and formatting
- **MyPy**: Static type checking
- **Pytest**: Testing framework
- **Cargo**: Rust formatting, linting, and tests
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
