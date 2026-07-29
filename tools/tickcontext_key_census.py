"""Enumerates every ad hoc key stamped onto TickContext (extra="allow").

Program 27 spec §6.5: these are undeclared run_tick parameters; the census
is the contract the Rust TickContext types. AST-based: finds subscript
assignments and setattr-style writes on names bound to a TickContext.
Heuristic: any ``<name>[<str-literal>] = ...`` or ``<name>.<attr> = ...``
where <name> is 'context' or 'ctx' or annotated TickContext.
"""

import ast
from pathlib import Path

REPO_SRC = Path(__file__).resolve().parents[1] / "src" / "babylon"
DECLARED_FIELDS = {"tick", "persistent_data", "displacement_mode"}


def stamped_keys() -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for py in sorted(REPO_SRC.rglob("*.py")):
        tree = ast.parse(py.read_text(), filename=str(py))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Assign):
                continue
            for target in node.targets:
                key: str | None = None
                if (
                    isinstance(target, ast.Subscript)
                    and isinstance(target.value, ast.Name)
                    and target.value.id in ("context", "ctx")
                    and isinstance(target.slice, ast.Constant)
                    and isinstance(target.slice.value, str)
                ):
                    key = target.slice.value
                elif (
                    isinstance(target, ast.Attribute)
                    and isinstance(target.value, ast.Name)
                    and target.value.id in ("context", "ctx")
                ):
                    key = target.attr
                if key and key not in DECLARED_FIELDS:
                    rel = str(py.relative_to(REPO_SRC.parent.parent))
                    out.setdefault(key, []).append(f"{rel}:{node.lineno}")
    return dict(sorted(out.items()))


if __name__ == "__main__":
    for key, sites in stamped_keys().items():
        print(f"{key}\t{', '.join(sites)}")
