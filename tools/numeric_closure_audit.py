"""Finds every numpy/scipy call site reachable from the engine tree.

Program 27 spec §6.2: each site needs a Director ruling —
(a) same-LAPACK linkage, (b) tolerance-bounded re-derivation, (c) III.10
retirement. Static import-graph closure over src/babylon/{engine,domain,
formulas,kernel,topology}; call-site extraction via ast.
"""

import ast
from pathlib import Path

ROOTS = ("engine", "domain", "formulas", "kernel", "topology")
TARGETS = ("numpy", "scipy")
REPO_SRC = Path(__file__).resolve().parents[1] / "src" / "babylon"


def call_sites() -> list[tuple[str, int, str]]:
    hits: list[tuple[str, int, str]] = []
    for root in ROOTS:
        for py in sorted((REPO_SRC / root).rglob("*.py")):
            tree = ast.parse(py.read_text(), filename=str(py))
            aliases: dict[str, str] = {}
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for a in node.names:
                        if a.name.split(".")[0] in TARGETS:
                            aliases[a.asname or a.name.split(".")[0]] = a.name
                elif isinstance(node, ast.ImportFrom) and node.module:
                    if node.module.split(".")[0] in TARGETS:
                        for a in node.names:
                            aliases[a.asname or a.name] = f"{node.module}.{a.name}"
            if not aliases:
                continue
            for node in ast.walk(tree):
                if isinstance(node, ast.Attribute) or isinstance(node, ast.Name):
                    base = node
                    while isinstance(base, ast.Attribute):
                        base = base.value
                    if isinstance(base, ast.Name) and base.id in aliases:
                        rel = py.relative_to(REPO_SRC.parent.parent)
                        hits.append((str(rel), node.lineno, ast.unparse(node)))
    return sorted(set(hits))


if __name__ == "__main__":
    for path, line, expr in call_sites():
        print(f"{path}:{line}\t{expr}")
