"""Tree-sitter based parser for Python, JavaScript, and TypeScript."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from tree_sitter import Language, Node, Parser, Tree

# Compound statement types that increase nesting depth
PYTHON_NESTING_TYPES = frozenset({
    "if_statement", "elif_clause", "for_statement", "while_statement",
    "try_statement", "except_clause", "except_group_clause", "with_clause",
    "match_statement", "match_case",
})
JS_TS_NESTING_TYPES = frozenset({
    "if_statement", "for_statement", "for_in_statement", "for_of_statement",
    "while_statement", "do_statement", "switch_statement", "try_statement",
    "catch_clause", "with_statement",
})

# Branch node types that increase cyclomatic complexity (per language)
PYTHON_BRANCH_TYPES = frozenset({
    "if_statement",
    "elif_clause",
    "for_statement",
    "while_statement",
    "try_statement",
    "except_clause",
    "except_group_clause",
    "finally_clause",
    "with_clause",
    "match_statement",
    "match_case",
    "conditional_expression",  # x if y else z
    "boolean_operator",  # and, or
})

JS_TS_BRANCH_TYPES = frozenset({
    "if_statement",
    "for_statement",
    "for_in_statement",
    "for_of_statement",
    "while_statement",
    "do_statement",
    "switch_case",
    "ternary_expression",
    "binary_expression",  # &&, ||
    "catch_clause",
})


def _get_language(lang_name: str) -> Language:
    """Load a tree-sitter Language by name."""
    if lang_name == "python":
        import tree_sitter_python as tspython
        return Language(tspython.language())
    if lang_name == "javascript":
        import tree_sitter_javascript as tsjs
        return Language(tsjs.language())
    if lang_name == "typescript":
        import tree_sitter_typescript as tsts
        return Language(tsts.language())
    raise ValueError(f"Unsupported language: {lang_name}")


# Lazy-loaded languages
_LANGUAGES: dict[str, Language] = {}
_PARSERS: dict[str, Parser] = {}


def _get_parser(lang_name: str) -> Parser:
    """Get or create a parser for the given language."""
    if lang_name not in _PARSERS:
        lang = _get_language(lang_name)
        parser = Parser(lang)
        _PARSERS[lang_name] = parser
    return _PARSERS[lang_name]


def _get_branch_types(lang_name: str) -> frozenset[str]:
    """Return branch node types for cyclomatic complexity."""
    if lang_name == "python":
        return PYTHON_BRANCH_TYPES
    if lang_name in ("javascript", "typescript"):
        return JS_TS_BRANCH_TYPES
    return frozenset()


def _get_nesting_types(lang_name: str) -> frozenset[str]:
    """Return compound statement types for nesting depth."""
    if lang_name == "python":
        return PYTHON_NESTING_TYPES
    if lang_name in ("javascript", "typescript"):
        return JS_TS_NESTING_TYPES
    return frozenset()


def _max_nesting_in_subtree(node: Node, nesting_types: frozenset[str], depth: int) -> int:
    """Compute max nesting depth in a subtree."""
    if node.type in nesting_types:
        depth += 1
    max_d = depth
    for child in node.children:
        max_d = max(max_d, _max_nesting_in_subtree(child, nesting_types, depth))
    return max_d


def _get_function_name(node: Node, source: bytes) -> str:
    """Extract function/method name from a definition node."""
    for child in node.children:
        if child.type == "identifier":
            return source[child.start_byte : child.end_byte].decode("utf-8", errors="replace")
        if child.type in ("name", "attribute"):  # Python: def foo.bar
            return source[child.start_byte : child.end_byte].decode("utf-8", errors="replace")
    return "<anonymous>"


def _count_branches_in_subtree(node: Node, source: bytes, branch_types: frozenset[str]) -> int:
    """Recursively count branch nodes within a subtree (for cyclomatic complexity)."""
    count = 0
    if node.type in branch_types:
        count += 1
    for child in node.children:
        count += _count_branches_in_subtree(child, source, branch_types)
    return count


def _get_nesting_depth(node: Node, root: Node, depth: int = 0) -> int:
    """Get maximum nesting depth of a node within the tree."""
    if node == root:
        return depth
    # Walk up via parent - we need parent ref. Tree-sitter Node doesn't have parent.
    # Instead, we compute depth during traversal by passing depth down.
    return depth


def _extract_functions_python(node: Node, source: bytes, functions: list[dict[str, Any]]) -> None:
    """Extract function definitions from Python AST."""
    if node.type == "function_definition":
        name = _get_function_name(node, source)
        start_line = node.start_point[0] + 1
        end_line = node.end_point[0] + 1
        param_count = sum(1 for c in node.children if c.type == "parameters")
        functions.append({
            "name": name,
            "line_start": start_line,
            "line_end": end_line,
            "line_count": end_line - start_line + 1,
            "param_count": param_count,
        })
    for child in node.children:
        _extract_functions_python(child, source, functions)


def _extract_functions_js_ts(node: Node, source: bytes, functions: list[dict[str, Any]]) -> None:
    """Extract function/method definitions from JS/TS AST."""
    func_types = (
        "function_declaration",
        "generator_function_declaration",
        "method_definition",
        "arrow_function",
        "function_expression",
        "generator_function",
    )
    if node.type in func_types:
        name = _get_function_name(node, source)
        start_line = node.start_point[0] + 1
        end_line = node.end_point[0] + 1
        functions.append({
            "name": name,
            "line_start": start_line,
            "line_end": end_line,
            "line_count": end_line - start_line + 1,
            "param_count": 0,  # Could parse params if needed
        })
    for child in node.children:
        _extract_functions_js_ts(child, source, functions)


def _extract_imports_python(node: Node, source: bytes, imports: list[str]) -> None:
    """Extract import statements from Python AST (full module path for dependency analysis)."""
    if node.type == "import_statement":
        # import foo, bar
        for n in node.children_by_field_name("name"):
            if n.type == "dotted_name":
                mod = source[n.start_byte : n.end_byte].decode("utf-8", errors="replace")
                imports.append(mod)
            elif n.type == "aliased_import":
                sub = n.child_by_field_name("name")
                if sub and sub.type == "dotted_name":
                    mod = source[sub.start_byte : sub.end_byte].decode("utf-8", errors="replace")
                    imports.append(mod)
    elif node.type == "import_from_statement":
        # from foo import bar
        mod_node = node.child_by_field_name("module_name")
        if mod_node and mod_node.type == "dotted_name":
            mod = source[mod_node.start_byte : mod_node.end_byte].decode("utf-8", errors="replace")
            imports.append(mod)
    for child in node.children:
        _extract_imports_python(child, source, imports)


def _extract_require_import(node: Node, source: bytes) -> str | None:
    """Extract module from require('foo') call, or None if not a require call or relative path."""
    if node.type != "call_expression":
        return None
    fn_node = node.child_by_field_name("function")
    if not fn_node or source[fn_node.start_byte : fn_node.end_byte] != b"require":
        return None
    args = node.child_by_field_name("arguments")
    if not args:
        return None
    for arg in args.children:
        if arg.type == "string":
            s = source[arg.start_byte : arg.end_byte].decode("utf-8", errors="replace")
            s = s.strip("'\"")
            if not s.startswith("."):
                return s.split("/")[0]
            return None
    return None


def _extract_imports_js_ts(node: Node, source: bytes, imports: list[str]) -> None:
    """Extract import/require from JS/TS AST."""
    if node.type == "import_statement":
        for child in node.children:
            if child.type == "string":
                s = source[child.start_byte : child.end_byte].decode("utf-8", errors="replace")
                s = s.strip("'\"")
                if not s.startswith(".") and "/" not in s:
                    imports.append(s.split("/")[0])
                elif s.startswith("."):
                    imports.append(s)
                break
    elif node.type == "call_expression":
        req = _extract_require_import(node, source)
        if req is not None:
            imports.append(req)
    for child in node.children:
        _extract_imports_js_ts(child, source, imports)


def _compute_complexity_for_function(
    func_node: Node,
    tree: Tree,
    source: bytes,
    branch_types: frozenset[str],
) -> int:
    """Compute cyclomatic complexity for a function (1 + branch count)."""
    count = _count_branches_in_subtree(func_node, source, branch_types)
    return 1 + count


FUNC_NODE_TYPES = (
    "function_definition",
    "function_declaration",
    "generator_function_declaration",
    "method_definition",
    "arrow_function",
    "function_expression",
    "generator_function",
)


def _annotate_functions_with_metrics(
    root: Node,
    functions: list[dict[str, Any]],
    branch_types: frozenset[str],
    nesting_types: frozenset[str],
    tree: Tree,
    source: bytes,
) -> None:
    """Annotate functions list with complexity and nesting_depth from AST."""

    def visit(node: Node) -> None:
        if node.type in FUNC_NODE_TYPES:
            complexity = _compute_complexity_for_function(node, tree, source, branch_types)
            nesting = _max_nesting_in_subtree(node, nesting_types, 0)
            start_line = node.start_point[0] + 1
            for f in functions:
                if f["line_start"] == start_line:
                    f["complexity"] = complexity
                    f["nesting_depth"] = nesting
                    break
        for child in node.children:
            visit(child)

    visit(root)


def detect_language(path: Path) -> str | None:
    """Detect language from file extension."""
    ext = path.suffix.lower()
    if ext == ".py":
        return "python"
    if ext in (".js", ".mjs", ".cjs"):
        return "javascript"
    if ext in (".ts", ".mts", ".cts"):
        return "typescript"
    return None


def parse_file(path: Path) -> dict[str, Any] | None:
    """
    Parse a source file and extract metrics.

    Returns a dict with:
        - language: str
        - line_count: int
        - functions: list of {name, line_start, line_end, line_count, param_count, complexity}
        - imports: list of module names
    Returns None if the language is not supported.
    """
    lang_name = detect_language(path)
    if not lang_name:
        return None

    source = path.read_bytes()
    parser = _get_parser(lang_name)
    tree = parser.parse(source)
    root = tree.root_node

    if root.has_error:
        # Still try to extract what we can
        pass

    functions: list[dict[str, Any]] = []
    imports: list[str] = []

    if lang_name == "python":
        _extract_functions_python(root, source, functions)
        _extract_imports_python(root, source, imports)
    else:
        _extract_functions_js_ts(root, source, functions)
        _extract_imports_js_ts(root, source, imports)

    branch_types = _get_branch_types(lang_name)
    nesting_types = _get_nesting_types(lang_name)
    _annotate_functions_with_metrics(
        root, functions, branch_types, nesting_types, tree, source
    )

    for f in functions:
        if "complexity" not in f:
            f["complexity"] = 1
        if "nesting_depth" not in f:
            f["nesting_depth"] = 0

    line_count = len(source.decode("utf-8", errors="replace").splitlines())

    return {
        "language": lang_name,
        "line_count": line_count,
        "functions": functions,
        "imports": imports,
    }


def get_source_lines(path: Path) -> list[str]:
    """Get source lines for a file (for duplication detection)."""
    return path.read_text(encoding="utf-8", errors="replace").splitlines()
