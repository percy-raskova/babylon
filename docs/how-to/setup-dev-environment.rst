Set Up a Development Environment
=================================

This guide walks you through setting up a complete development environment
for Babylon. It covers Linux, macOS, and Windows (via WSL).

.. contents:: On This Page
   :local:
   :depth: 2

Prerequisites Overview
----------------------

.. list-table::
   :widths: 20 30 50
   :header-rows: 1

   * - Tool
     - Version
     - Purpose
   * - Python
     - 3.12 or higher
     - Runtime environment
   * - Poetry
     - Any recent
     - Dependency management
   * - Git
     - Any recent
     - Version control
   * - (Windows) WSL 2
     - Ubuntu 22.04+
     - Linux environment on Windows

Linux / macOS Setup
-------------------

Step 1: Install Python 3.12+
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Ubuntu/Debian:**

.. code-block:: bash

   sudo apt update
   sudo apt install python3 python3-pip python3-venv

**macOS (with Homebrew):**

.. code-block:: bash

   brew install python@3.12

**Verify installation:**

.. code-block:: bash

   python3 --version
   # Should show: Python 3.12.x or higher

Step 2: Install Poetry
^^^^^^^^^^^^^^^^^^^^^^

Poetry manages Python dependencies and virtual environments.

.. code-block:: bash

   curl -sSL https://install.python-poetry.org | python3 -

Add Poetry to your PATH by adding this to your ``~/.bashrc`` or ``~/.zshrc``:

.. code-block:: bash

   export PATH="$HOME/.local/bin:$PATH"

Reload your shell and verify:

.. code-block:: bash

   source ~/.bashrc  # or ~/.zshrc
   poetry --version

Step 3: Install Git
^^^^^^^^^^^^^^^^^^^

**Ubuntu/Debian:**

.. code-block:: bash

   sudo apt install git

**macOS:**

.. code-block:: bash

   # Git comes with Xcode Command Line Tools
   xcode-select --install

**Verify:**

.. code-block:: bash

   git --version

Step 4: Clone and Set Up the Project
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: bash

   # Clone the repository
   git clone https://github.com/percy-raskova/babylon.git
   cd babylon

   # Install dependencies (creates virtual environment automatically)
   poetry install

   # Install pre-commit hooks
   poetry run pre-commit install --hook-type commit-msg --hook-type pre-commit

   # Verify everything works
   poetry run pytest -m "not ai" -x -q

You should see all tests passing. You're ready to develop!

Windows Setup (WSL + VSCode)
----------------------------

Windows users should use Windows Subsystem for Linux (WSL) for the best
development experience. This gives you a full Linux environment that
integrates seamlessly with VSCode.

Step 1: Install WSL 2
^^^^^^^^^^^^^^^^^^^^^

**Requirements:**

- Windows 10 version 2004+ (Build 19041+) or Windows 11
- Virtualization enabled in BIOS

**Install WSL:**

Open PowerShell as Administrator and run:

.. code-block:: powershell

   wsl --install

This command:

- Enables the WSL feature
- Installs the default Ubuntu distribution
- Sets WSL 2 as the default version

**Restart your computer** when prompted.

**Complete Ubuntu setup:**

After restart, Ubuntu will launch automatically. Create your Linux username
and password when prompted:

.. code-block:: text

   Enter new UNIX username: yourname
   New password: ********
   Retype new password: ********

.. tip::

   This is a separate user account from Windows. Choose something memorable.

**Verify WSL is working:**

.. code-block:: bash

   # In the Ubuntu terminal
   cat /etc/os-release
   # Should show Ubuntu version info

Step 2: Install VSCode with WSL Extension
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Install VSCode on Windows:**

Download from https://code.visualstudio.com/ and install normally.

**Install the WSL extension:**

1. Open VSCode
2. Press ``Ctrl+Shift+X`` to open Extensions
3. Search for "WSL"
4. Install **WSL** by Microsoft (extension ID: ``ms-vscode-remote.remote-wsl``)

.. note::

   The extension is called "WSL" (formerly "Remote - WSL"). It allows
   VSCode running on Windows to edit files inside WSL.

Step 3: Set Up Development Tools in WSL
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Open your Ubuntu terminal (search for "Ubuntu" in Windows Start menu):

**Update packages and install essentials:**

.. code-block:: bash

   sudo apt update && sudo apt upgrade -y
   sudo apt install python3 python3-pip python3-venv git curl wget ca-certificates -y

**Install Poetry:**

.. code-block:: bash

   curl -sSL https://install.python-poetry.org | python3 -

**Add Poetry to PATH:**

.. code-block:: bash

   echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
   source ~/.bashrc

**Verify installations:**

.. code-block:: bash

   python3 --version   # Should be 3.12+
   poetry --version    # Should show Poetry version
   git --version       # Should show Git version

Step 4: Clone the Project in WSL
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Important:** Clone the project inside WSL's filesystem, not on the Windows
side. This ensures proper file permissions and much better performance.

.. code-block:: bash

   # Create a projects directory in your WSL home
   mkdir -p ~/projects
   cd ~/projects

   # Clone the repository
   git clone https://github.com/percy-raskova/babylon.git
   cd babylon

   # Install dependencies
   poetry install

   # Install pre-commit hooks
   poetry run pre-commit install --hook-type commit-msg --hook-type pre-commit

   # Verify
   poetry run pytest -m "not ai" -x -q

Step 5: Open Project in VSCode (Remote)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

There are two ways to open your WSL project in VSCode:

**Method A: From the WSL terminal (recommended):**

.. code-block:: bash

   # Navigate to the project
   cd ~/projects/babylon

   # Open in VSCode
   code .

VSCode will launch on Windows but connect to WSL. You'll see
``WSL: Ubuntu`` in the bottom-left corner of the VSCode window.

**Method B: From VSCode on Windows:**

1. Open VSCode
2. Press ``Ctrl+Shift+P`` to open Command Palette
3. Type "WSL: Connect to WSL"
4. Once connected, use ``File > Open Folder``
5. Navigate to ``/home/yourname/projects/babylon``

**Install recommended extensions in WSL:**

When VSCode connects to WSL, you may need to reinstall some extensions
"in WSL". VSCode will prompt you for this. Recommended extensions:

- Python (Microsoft)
- Pylance
- Ruff
- GitLens

Step 6: Configure Git in WSL
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Set up your Git identity:

.. code-block:: bash

   git config --global user.name "Your Name"
   git config --global user.email "your.email@example.com"

**Optional: Use Windows Git Credential Manager:**

To share credentials between Windows and WSL:

.. code-block:: bash

   git config --global credential.helper "/mnt/c/Program\ Files/Git/mingw64/bin/git-credential-manager.exe"

Using Mise (Optional)
---------------------

The project uses `mise <https://mise.jdx.dev/>`_ as a task runner for common
operations. While optional, it provides convenient shortcuts.

**Install mise:**

.. code-block:: bash

   curl https://mise.run | sh
   echo 'eval "$(~/.local/bin/mise activate bash)"' >> ~/.bashrc
   source ~/.bashrc

**Common mise commands:**

.. code-block:: bash

   mise run test        # Run all non-AI tests
   mise run test-fast   # Run fast math/engine tests
   mise run lint        # Run Ruff linter
   mise run typecheck   # Run MyPy
   mise run ci          # Run all CI checks locally
   mise run docs-live   # Start live documentation server
   mise run security    # Run security audit on dependencies
   mise run coverage    # Run tests with coverage report

Verifying Your Setup
--------------------

Run through this checklist to confirm everything is working:

.. code-block:: bash

   # 1. Python version
   python3 --version
   # Expected: Python 3.12.x or higher

   # 2. Poetry works
   poetry --version

   # 3. Dependencies installed
   poetry run python -c "import babylon; print('Babylon imported!')"

   # 4. Tests pass
   poetry run pytest -m "not ai" -x -q
   # Expected: All tests pass

   # 5. Pre-commit hooks installed
   poetry run pre-commit run --all-files
   # Expected: All hooks pass (may auto-fix some files)

   # 6. Documentation builds
   cd docs && poetry run sphinx-build -b html . _build/html
   # Expected: No errors

Troubleshooting
---------------

**Poetry command not found:**

Ensure Poetry is in your PATH:

.. code-block:: bash

   export PATH="$HOME/.local/bin:$PATH"
   # Add to ~/.bashrc to make permanent

**Tests fail with import errors:**

Make sure you ran ``poetry install``:

.. code-block:: bash

   poetry install

**WSL: "code" command not found:**

Add VSCode to your WSL PATH in ``~/.bashrc``:

.. code-block:: bash

   export PATH="$PATH:/mnt/c/Users/YOURWINDOWSUSER/AppData/Local/Programs/Microsoft VS Code/bin"

Replace ``YOURWINDOWSUSER`` with your Windows username.

**WSL: Very slow file operations:**

Make sure your project is in the WSL filesystem (``~/projects/``), not
on the Windows filesystem (``/mnt/c/...``). WSL 2 has significant
performance penalties when accessing Windows files.

**Pre-commit hooks fail:**

Run the fix commands:

.. code-block:: bash

   poetry run ruff check . --fix
   poetry run ruff format .

Then try committing again.

See Also
--------

- :doc:`/how-to/contribute` - Submit a pull request
- :doc:`/how-to/run-ci-locally` - Test CI before pushing
- :doc:`/tutorials/first-simulation` - Run your first simulation
