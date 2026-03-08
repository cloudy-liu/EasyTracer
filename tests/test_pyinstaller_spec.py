"""Regression checks for PyInstaller's PySide6 keep-list."""

from __future__ import annotations

import ast
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src" / "easy_tracer"
SPEC_PATH = REPO_ROOT / "easy_tracer.spec"


def _read_tree(path: Path) -> ast.AST:
    """Parses a Python file into an abstract syntax tree.

    Args:
        path: The Python file to parse.

    Returns:
        The parsed abstract syntax tree for the file.
    """
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def _extract_string_set(path: Path, variable_name: str) -> set[str]:
    """Extracts a string set literal assigned to a variable.

    Args:
        path: The Python file to inspect.
        variable_name: The variable name to look up.

    Returns:
        The set of string literals assigned to the variable.

    Raises:
        AssertionError: If the variable is missing or is not a string set.
    """
    tree = _read_tree(path)
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue

        target_names = {
            target.id for target in node.targets if isinstance(target, ast.Name)
        }
        if variable_name not in target_names:
            continue

        if not isinstance(node.value, ast.Set):
            raise AssertionError(
                f"{variable_name} is expected to be a set literal in {path}"
            )

        values: set[str] = set()
        for item in node.value.elts:
            if not isinstance(item, ast.Constant) or not isinstance(item.value, str):
                raise AssertionError(
                    f"{variable_name} must contain only string literals in {path}"
                )
            values.add(item.value)
        return values

    raise AssertionError(f"{variable_name} not found in {path}")


def _collect_direct_pyside_modules(root: Path) -> set[str]:
    """Collects directly imported PySide6 modules under a source tree.

    Args:
        root: The source root to scan.

    Returns:
        A set of imported `PySide6.*` module names.
    """
    modules: set[str] = set()
    for path in root.rglob("*.py"):
        source = path.read_text(encoding="utf-8")
        if "PySide6" not in source:
            continue

        tree = ast.parse(source, filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.ImportFrom) or node.module is None:
                continue

            if node.module == "PySide6":
                for alias in node.names:
                    if alias.name.startswith("Qt"):
                        modules.add(f"PySide6.{alias.name}")
                continue

            if node.module.startswith("PySide6."):
                modules.add(node.module)

    return modules


def test_spec_keeps_all_direct_pyside_modules() -> None:
    """Ensures PyInstaller keeps every directly imported PySide6 module."""
    kept_modules = _extract_string_set(SPEC_PATH, "PYSIDE6_KEEP")
    imported_modules = _collect_direct_pyside_modules(SRC_ROOT)
    missing_modules = sorted(imported_modules - kept_modules)

    assert not missing_modules, (
        "PyInstaller keep-list is missing directly imported PySide6 modules: "
        f"{missing_modules}"
    )
