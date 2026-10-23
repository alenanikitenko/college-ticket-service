"""УП3. Слои импортируют только разрешённые модули; циклов нет."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

APP_DIR = Path(__file__).resolve().parents[1] / "app"

# слой -> запрещённые для импорта префиксы
FORBIDDEN = {
    "core": ("app.routers", "app.services", "app.repositories", "app.schemas", "app.models", "fastapi"),
    "models": ("app.routers", "app.services", "app.repositories", "app.schemas", "fastapi"),
    "repositories": ("app.routers", "app.services", "app.schemas", "fastapi", "starlette"),
    "schemas": ("app.routers", "app.services", "app.repositories", "fastapi"),
    "services": ("app.routers", "fastapi", "starlette"),
    "routers": ("app.repositories",),
}


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found |= {a.name for a in node.names}
        elif isinstance(node, ast.ImportFrom) and node.module:
            found.add(node.module)
    return found


@pytest.mark.parametrize("layer", sorted(FORBIDDEN))
def test_layer_respects_forbidden_imports(layer):
    for path in (APP_DIR / layer).glob("*.py"):
        for module in _imports(path):
            assert not module.startswith(FORBIDDEN[layer]), f"{layer}/{path.name} импортирует {module}"


def test_layer_graph_is_acyclic():
    graph: dict[str, set[str]] = {}
    for layer in FORBIDDEN:
        deps: set[str] = set()
        for path in (APP_DIR / layer).glob("*.py"):
            for module in _imports(path):
                parts = module.split(".")
                if parts[0] == "app" and len(parts) > 1 and parts[1] in FORBIDDEN and parts[1] != layer:
                    deps.add(parts[1])
        graph[layer] = deps

    visiting, done = set(), set()

    def visit(node):
        assert node not in visiting, f"цикл зависимостей через {node}"
        if node in done:
            return
        visiting.add(node)
        for nxt in graph.get(node, ()):
            visit(nxt)
        visiting.discard(node)
        done.add(node)

    for layer in graph:
        visit(layer)
