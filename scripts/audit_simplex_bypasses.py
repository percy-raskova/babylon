import ast
import os
import sys


def audit_bypasses(root_dir: str) -> list[tuple[str, int, str, str, str]]:
    findings = []

    for dirpath, _, filenames in os.walk(root_dir):
        for filename in filenames:
            if not filename.endswith(".py"):
                continue

            filepath = os.path.join(dirpath, filename)
            if (
                "src/babylon/models/entities/consciousness.py" in filepath
                or "src/babylon/formulas/consciousness.py" in filepath
            ):
                continue

            try:
                with open(filepath, encoding="utf-8") as f:
                    content = f.read()
                tree = ast.parse(content)
            except Exception:
                continue

            lines = content.splitlines()

            # Find .r, .l, .f assignments
            for node in ast.walk(tree):
                if isinstance(node, ast.Assign):
                    for target in node.targets:
                        if isinstance(target, ast.Attribute) and target.attr in ("r", "l", "f"):
                            findings.append(
                                (
                                    filepath,
                                    target.lineno,
                                    lines[target.lineno - 1].strip(),
                                    "CRITICAL",
                                    "Direct mutation bypasses spec 043 routing formula",
                                )
                            )
                        elif isinstance(target, ast.Subscript):
                            if isinstance(target.slice, ast.Constant) and target.slice.value in (
                                "r",
                                "l",
                                "f",
                            ):
                                findings.append(
                                    (
                                        filepath,
                                        target.lineno,
                                        lines[target.lineno - 1].strip(),
                                        "CRITICAL",
                                        "Direct dict-like mutation bypasses spec 043 routing formula",
                                    )
                                )
                elif isinstance(node, ast.AugAssign):
                    if isinstance(node.target, ast.Attribute) and node.target.attr in (
                        "r",
                        "l",
                        "f",
                    ):
                        findings.append(
                            (
                                filepath,
                                node.target.lineno,
                                lines[node.target.lineno - 1].strip(),
                                "CRITICAL",
                                "Direct mutation bypasses spec 043 routing formula",
                            )
                        )
                    elif isinstance(node.target, ast.Subscript):
                        if isinstance(
                            node.target.slice, ast.Constant
                        ) and node.target.slice.value in ("r", "l", "f"):
                            findings.append(
                                (
                                    filepath,
                                    node.target.lineno,
                                    lines[node.target.lineno - 1].strip(),
                                    "CRITICAL",
                                    "Direct dict-like mutation bypasses spec 043 routing formula",
                                )
                            )
                elif isinstance(node, ast.Call):
                    if hasattr(node.func, "id") and node.func.id == "TernaryConsciousness":
                        findings.append(
                            (
                                filepath,
                                node.lineno,
                                lines[node.lineno - 1].strip(),
                                "WARNING",
                                "Direct construction outside designated factory sites",
                            )
                        )
                    elif hasattr(node.func, "id") and node.func.id == "setattr":
                        if (
                            len(node.args) >= 2
                            and isinstance(node.args[1], ast.Constant)
                            and node.args[1].value in ("r", "l", "f")
                        ):
                            findings.append(
                                (
                                    filepath,
                                    node.lineno,
                                    lines[node.lineno - 1].strip(),
                                    "CRITICAL",
                                    "Direct mutation bypasses spec 043 routing formula",
                                )
                            )

    for filepath, lineno, code, severity, reason in findings:
        print(f"{severity}: {filepath}:{lineno}")
        print(f"  {code}")
        print(f"  Reason: {reason}\n")

    return findings


if __name__ == "__main__":
    findings = audit_bypasses("/home/user/projects/game/babylon/src/babylon")
    if any(sev == "CRITICAL" for _, _, _, sev, _ in findings):
        sys.exit(1)
    if not findings:
        print("No bypasses found.")
