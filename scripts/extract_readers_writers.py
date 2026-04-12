import ast
import os


def find_usages(root_dir: str) -> None:
    writers = []
    readers = []

    consciousness_attrs = {
        "r",
        "l",
        "f",
        "collective_identity",
        "dominant_tendency",
        "ideological_contestation",
        "assimilation_ratio",
    }
    buffer_attrs = {
        "agitation",
        "education_pressure",
        "practice_agitation",
        "solidarity_factor",
        "institutional_factor",
        "repression_backfire",
    }

    for dirpath, _, filenames in os.walk(root_dir):
        for filename in filenames:
            if not filename.endswith(".py"):
                continue

            filepath = os.path.join(dirpath, filename)

            try:
                with open(filepath, encoding="utf-8") as f:
                    content = f.read()
                tree = ast.parse(content)
            except Exception:
                continue

            code_lines = content.splitlines()

            for node in ast.walk(tree):
                # Check for Writes
                if isinstance(node, ast.Assign):
                    for target in node.targets:
                        if isinstance(target, ast.Attribute) and target.attr in (
                            consciousness_attrs | buffer_attrs
                        ):
                            writers.append(
                                (
                                    filepath,
                                    target.lineno,
                                    target.attr,
                                    code_lines[target.lineno - 1].strip(),
                                )
                            )
                elif isinstance(node, ast.AugAssign):
                    if isinstance(node.target, ast.Attribute) and node.target.attr in (
                        consciousness_attrs | buffer_attrs
                    ):
                        writers.append(
                            (
                                filepath,
                                node.target.lineno,
                                node.target.attr,
                                code_lines[node.target.lineno - 1].strip(),
                            )
                        )
                elif isinstance(node, ast.keyword) and node.arg in buffer_attrs:
                    # In initialization of the Buffer
                    writers.append(
                        (
                            filepath,
                            node.value.lineno,
                            node.arg,
                            code_lines[node.value.lineno - 1].strip(),
                        )
                    )

                # Check for Reads
                if (
                    isinstance(node, ast.Attribute)
                    and isinstance(node.ctx, ast.Load)
                    and node.attr in consciousness_attrs
                ):
                    readers.append(
                        (filepath, node.lineno, node.attr, code_lines[node.lineno - 1].strip())
                    )

    with open("/home/user/projects/game/babylon/ast_usages.txt", "w") as f:
        f.write("WRITERS:\n")
        for w in writers:
            f.write(f"{w[0]}:{w[1]} - {w[2]} - {w[3]}\n")
        f.write("\nREADERS:\n")
        for r in readers:
            f.write(f"{r[0]}:{r[1]} - {r[2]} - {r[3]}\n")


if __name__ == "__main__":
    find_usages("/home/user/projects/game/babylon/src/babylon")
