"""Babylon - The Fall of America simulation engine.

A geopolitical simulation modeling the collapse of American hegemony
through MLM-TW (Marxist-Leninist-Maoist Third Worldist) theory and
topological manifolds.

The simulation models class struggle as deterministic output of material
conditions within a compact topological phase space.

Example:
    >>> import babylon
    >>> babylon.__version__
    '0.3.0'
"""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__: str = version("babylon")
except PackageNotFoundError:
    # Package not installed (running from source without pip install -e)
    __version__ = "0.0.0+unknown"

__all__ = ["__version__"]
