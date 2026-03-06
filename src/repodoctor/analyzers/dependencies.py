"""Dependency analyzer: import graph, circular dependencies, coupling metrics."""

from pathlib import Path

from repodoctor.config import Config
from repodoctor.utils import try_relative_to
from repodoctor.models import CircularDependency, Finding, FindingKind, FileMetrics, ScanResult, Severity


def _module_key(path: str, root: Path) -> str:
    """Convert file path to module identifier for graph (Python style)."""
    p = Path(path)
    if not p.is_absolute():
        p = root / p
    rel = try_relative_to(p, root)
    if rel is None:
        return path
    parts = list(rel.parts)
    if not parts:
        return path
    name = parts[-1]
    base = name.rsplit(".", 1)[0] if "." in name else name
    if base == "__init__":
        base = parts[-2] if len(parts) > 1 else "."
    if len(parts) > 1:
        return ".".join(parts[:-1] + [base])
    return base


def _resolve_import_to_module(imp: str, current_file: str, root: Path, all_modules: set[str]) -> str | None:
    """Resolve import string to module key in all_modules, or None."""
    if imp.startswith("."):
        # Relative: current_file is like src/repodoctor/parsers/foo.py
        current_key = _module_key(current_file, root)
        parts = current_key.split(".")
        rel = imp.lstrip(".")
        dot_count = len(imp) - len(rel)
        if dot_count == 0:
            return None
        parent_parts = parts[: -(dot_count)] if dot_count <= len(parts) else []
        if rel:
            candidate = ".".join(parent_parts + [rel.split(".")[0]])
        else:
            candidate = ".".join(parent_parts) if parent_parts else None
        if candidate and candidate in all_modules:
            return candidate
        # Try prefix match
        for m in all_modules:
            if m == candidate or (candidate and m.startswith(candidate + ".")):
                return m
        return candidate
    # Absolute: imp is like "repodoctor.parsers.treesitter"
    if imp in all_modules:
        return imp
    for m in all_modules:
        if m == imp or m.startswith(imp + ".") or imp.startswith(m + "."):
            return m
    return imp.split(".")[0] if imp else None


def _resolve_and_add_edge(
    src_key: str,
    imp: str,
    current_file: str,
    root: Path,
    all_modules: set[str],
    graph: dict[str, set[str]],
) -> None:
    """Resolve import to module and add edge to graph if internal."""
    tgt = _resolve_import_to_module(imp, current_file, root, all_modules)
    if tgt and tgt in all_modules and tgt != src_key:
        graph[src_key].add(tgt)
        return
    if not tgt:
        return
    for m in all_modules:
        if m == tgt or m.startswith(tgt + "."):
            if m != src_key:
                graph[src_key].add(m)
            break


def _build_graph(
    file_metrics: list[FileMetrics],
    root: Path,
) -> tuple[dict[str, set[str]], dict[str, str]]:
    """
    Build directed graph: module -> set of modules it imports.
    Returns (graph, module_to_file).
    """
    module_to_file: dict[str, str] = {}
    for fm in file_metrics:
        key = _module_key(str(fm.path), root)
        module_to_file[key] = str(fm.path)

    all_modules = set(module_to_file.keys())
    graph: dict[str, set[str]] = {m: set() for m in all_modules}

    for fm in file_metrics:
        src_key = _module_key(str(fm.path), root)
        for imp in fm.imports:
            _resolve_and_add_edge(
                src_key, imp, str(fm.path), root, all_modules, graph
            )

    return graph, module_to_file


def _find_cycles_dfs(
    graph: dict[str, set[str]],
) -> list[list[str]]:
    """Find cycles in directed graph using DFS with recursion stack."""
    cycles: list[list[str]] = []
    visited: set[str] = set()
    rec_stack: set[str] = set()
    path: list[str] = []
    path_set: set[str] = set()
    node_to_index: dict[str, int] = {}

    def dfs(node: str) -> bool:
        visited.add(node)
        rec_stack.add(node)
        path.append(node)
        path_set.add(node)
        node_to_index[node] = len(path) - 1

        for neighbor in graph.get(node, []):
            if neighbor not in visited:
                if dfs(neighbor):
                    return True
            elif neighbor in rec_stack:
                # Cycle found
                idx = node_to_index[neighbor]
                cycle = path[idx:]
                if len(cycle) > 1:
                    cycles.append(cycle.copy())
                return True

        path.pop()
        path_set.discard(node)
        rec_stack.discard(node)
        return False

    for node in graph:
        if node not in visited:
            dfs(node)

    return cycles


def analyze_dependencies(
    path: Path,
    result: ScanResult,
    config: Config,
    file_metrics: list[FileMetrics],
) -> None:
    """
    Build import graph, detect circular dependencies, compute coupling.
    """
    if len(file_metrics) < 2:
        return

    graph, module_to_file = _build_graph(file_metrics, path)
    cycles = _find_cycles_dfs(graph)

    seen_cycles: set[frozenset[str]] = set()
    for cycle in cycles:
        key = frozenset(cycle)
        if key in seen_cycles:
            continue
        seen_cycles.add(key)
        cycle_path = " -> ".join(cycle) + " -> " + cycle[0]
        result.circular_dependencies.append(
            CircularDependency(modules=cycle, path=cycle_path)
        )
        result.findings.append(
            Finding(
                kind=FindingKind.CIRCULAR_DEPENDENCY,
                severity=Severity.HIGH,
                file_path=module_to_file.get(cycle[0], cycle[0]),
                message=f"Circular dependency: {cycle_path}",
                extra={"modules": cycle, "path": cycle_path},
            )
        )

    # Risky modules: high fan-in
    fan_in: dict[str, int] = {m: 0 for m in graph}
    for node, deps in graph.items():
        for d in deps:
            fan_in[d] = fan_in.get(d, 0) + 1

    for module, count in sorted(fan_in.items(), key=lambda x: -x[1])[:5]:
        if count >= 3:  # Threshold for "risky"
            result.findings.append(
                Finding(
                    kind=FindingKind.RISKY_MODULE,
                    severity=Severity.MEDIUM if count < 5 else Severity.HIGH,
                    file_path=module_to_file.get(module, module),
                    message=f"Module '{module}' has high fan-in ({count} dependents)",
                    metric_value=count,
                    extra={"fan_in": count},
                )
            )
