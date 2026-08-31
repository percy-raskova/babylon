#!/usr/bin/env python3
"""Invoke the Rust-owned durable runtime probe."""

from __future__ import annotations

import subprocess


def main() -> None:
    subprocess.run(["babylon-runtime", "probe"], check=True)


if __name__ == "__main__":
    main()
