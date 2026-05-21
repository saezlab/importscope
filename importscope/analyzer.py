from __future__ import annotations

import ast
from pathlib import Path
from collections import defaultdict
from collections.abc import Iterable

from .model import ImportEdge, ModuleInfo, AnalysisResult


IGNORED_PARTS = {
    '.git',
    '.hg',
    '.svn',
    '.mypy_cache',
    '.pytest_cache',
    '.ruff_cache',
    '.tox',
    '.venv',
    'venv',
    '__pycache__',
    '.ipynb_checkpoints',
    'node_modules',
}


def discover_module_roots(
    repo: Path,
    explicit_roots: Iterable[Path] = (),
) -> list[Path]:
    roots: list[Path] = []
    seen: set[Path] = set()

    candidates = [repo]
    src_root = repo / 'src'
    if src_root.exists():
        candidates.append(src_root)

    for child in repo.iterdir():
        if child.is_dir() and (child / '__init__.py').exists():
            candidates.append(child.parent)

    candidates.extend(explicit_roots)

    for candidate in candidates:
        resolved = candidate.resolve()
        if resolved.exists() and resolved not in seen:
            seen.add(resolved)
            roots.append(resolved)

    return sorted(roots, key=lambda item: (len(item.parts), str(item)))


def should_skip_file(path: Path, excludes: Iterable[str]) -> bool:
    text = str(path)
    if any(part in IGNORED_PARTS for part in path.parts):
        return True
    return any(
        path.match(pattern) or text.endswith(pattern) for pattern in excludes
    )


def py_file_to_module(root: Path, py_file: Path) -> tuple[str, bool]:
    rel = py_file.relative_to(root)
    parts = list(rel.with_suffix('').parts)
    is_package = parts[-1] == '__init__'
    if is_package:
        parts = parts[:-1]
    return '.'.join(parts), is_package


def best_root_for_file(roots: list[Path], py_file: Path) -> Path | None:
    candidates: list[tuple[int, Path]] = []
    for root in roots:
        try:
            rel = py_file.relative_to(root)
        except ValueError:
            continue
        if any(part in IGNORED_PARTS for part in rel.parts):
            continue
        candidates.append((len(rel.parts), root))
    if not candidates:
        return None
    candidates.sort(key=lambda item: (item[0], str(item[1])))
    return candidates[0][1]


def parse_top_level_definitions(py_file: Path) -> set[str]:
    try:
        tree = ast.parse(py_file.read_text(encoding='utf-8'))
    except (OSError, SyntaxError, UnicodeDecodeError):
        return set()

    names: set[str] = set()
    for node in tree.body:
        if isinstance(
            node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
        ):
            names.add(node.name)
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                names.update(extract_assigned_names(target))
        elif isinstance(node, ast.AnnAssign):
            names.update(extract_assigned_names(node.target))
    return names


def extract_assigned_names(target: ast.AST) -> set[str]:
    if isinstance(target, ast.Name):
        return {target.id}
    if isinstance(target, (ast.Tuple, ast.List)):
        out: set[str] = set()
        for elt in target.elts:
            out.update(extract_assigned_names(elt))
        return out
    return set()


def collect_modules(
    repo: Path,
    roots: list[Path],
    includes: Iterable[str] = (),
    excludes: Iterable[str] = (),
    package_filter: str | None = None,
) -> dict[str, ModuleInfo]:
    modules: dict[str, ModuleInfo] = {}

    include_patterns = list(includes)
    exclude_patterns = list(excludes)

    for py_file in repo.rglob('*.py'):
        if should_skip_file(py_file, exclude_patterns):
            continue
        if include_patterns and not any(
            py_file.match(pattern) for pattern in include_patterns
        ):
            continue

        root = best_root_for_file(roots, py_file)
        if root is None:
            continue

        module, is_package = py_file_to_module(root, py_file)
        if not module:
            continue
        if (
            package_filter
            and module != package_filter
            and not module.startswith(package_filter + '.')
        ):
            continue

        existing = modules.get(module)
        if existing is not None and len(py_file.relative_to(root).parts) >= len(
            existing.path.parts
        ):
            continue

        modules[module] = ModuleInfo(
            module=module,
            path=py_file,
            is_package=is_package,
            definitions=parse_top_level_definitions(py_file),
        )

    return dict(sorted(modules.items()))


def source_package(module: str, is_package: bool) -> str:
    if is_package:
        return module
    return module.rsplit('.', 1)[0] if '.' in module else module


def resolve_relative_import(
    source_module: str,
    source_is_package: bool,
    level: int,
    imported_module: str | None,
) -> str | None:
    if level == 0:
        return imported_module
    pkg = source_package(source_module, source_is_package)
    parts = pkg.split('.')
    up = level - 1
    if up > len(parts):
        return None
    base = '.'.join(parts[: len(parts) - up])
    if imported_module:
        return base + '.' + imported_module
    return base


def is_type_checking_if(node: ast.If) -> bool:
    test = node.test
    if isinstance(test, ast.Name) and test.id == 'TYPE_CHECKING':
        return True
    return (
        isinstance(test, ast.Attribute)
        and test.attr == 'TYPE_CHECKING'
        and isinstance(test.value, ast.Name)
        and test.value.id == 'typing'
    )


def longest_existing_module(
    candidate: str, known_modules: set[str]
) -> str | None:
    parts = candidate.split('.')
    for i in range(len(parts), 0, -1):
        prefix = '.'.join(parts[:i])
        if prefix in known_modules:
            return prefix
    return None


def detect_importlib_aliases(tree: ast.AST) -> tuple[set[str], set[str]]:
    importlib_module_aliases = {'importlib'}
    import_module_aliases: set[str] = set()

    if not isinstance(tree, ast.Module):
        return importlib_module_aliases, import_module_aliases

    for node in tree.body:
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == 'importlib':
                    importlib_module_aliases.add(alias.asname or alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module == 'importlib':
            for alias in node.names:
                if alias.name == 'import_module':
                    import_module_aliases.add(alias.asname or alias.name)

    return importlib_module_aliases, import_module_aliases


def dynamic_import_target(
    node: ast.Call,
    known_modules: set[str],
    importlib_module_aliases: set[str],
    import_module_aliases: set[str],
) -> str | None:
    func = node.func
    is_import_module_call = False

    if (
        isinstance(func, ast.Attribute)
        and func.attr == 'import_module'
        and isinstance(func.value, ast.Name)
        and func.value.id in importlib_module_aliases
    ):
        is_import_module_call = True
    elif isinstance(func, ast.Name) and func.id in import_module_aliases:
        is_import_module_call = True

    if not is_import_module_call or not node.args:
        return None

    first_arg = node.args[0]
    if not isinstance(first_arg, ast.Constant) or not isinstance(
        first_arg.value, str
    ):
        return None

    return longest_existing_module(first_arg.value, known_modules)


def parse_imports(
    modules: dict[str, ModuleInfo],
    package_filter: str | None = None,
) -> tuple[list[ImportEdge], list[dict[str, object]]]:
    known = set(modules)
    edges: list[ImportEdge] = []
    coverage_gaps: list[dict[str, object]] = []

    def is_internal_module_name(name: str) -> bool:
        if package_filter:
            return name == package_filter or name.startswith(
                package_filter + '.'
            )
        return longest_existing_module(name, known) is not None

    def record_import_node(
        node: ast.Import | ast.ImportFrom,
        source: str,
        info: ModuleInfo,
        *,
        lazy_kind: str,
    ) -> None:
        if isinstance(node, ast.Import):
            for alias in node.names:
                raw = alias.name
                if not is_internal_module_name(raw):
                    continue
                target = longest_existing_module(raw, known)
                if target is None or target == source:
                    continue
                edges.append(
                    ImportEdge(
                        source=source,
                        target=target,
                        imported=(),
                        import_type='import',
                        lazy_kind=lazy_kind,
                        line=node.lineno,
                        source_file=str(info.path),
                    )
                )
            return

        raw_module = resolve_relative_import(
            source_module=source,
            source_is_package=info.is_package,
            level=node.level,
            imported_module=node.module,
        )
        if raw_module is None:
            return

        if node.module is None:
            for alias in node.names:
                candidate = raw_module + '.' + alias.name
                if candidate in known:
                    target = candidate
                    imported: tuple[str, ...] = ()
                else:
                    target = longest_existing_module(raw_module, known)
                    if target is None:
                        continue
                    imported = (alias.name,)
                if target == source:
                    continue
                edges.append(
                    ImportEdge(
                        source=source,
                        target=target,
                        imported=imported,
                        import_type='from',
                        lazy_kind=lazy_kind,
                        line=node.lineno,
                        source_file=str(info.path),
                    )
                )
            return

        if not is_internal_module_name(raw_module):
            return
        target = longest_existing_module(raw_module, known)
        if target is None or target == source:
            return
        imported = tuple(alias.name for alias in node.names)
        edges.append(
            ImportEdge(
                source=source,
                target=target,
                imported=imported,
                import_type='from',
                lazy_kind=lazy_kind,
                line=node.lineno,
                source_file=str(info.path),
            )
        )

    def visit_runtime_nodes(
        node: ast.AST,
        source: str,
        info: ModuleInfo,
        *,
        function_depth: int,
        importlib_module_aliases: set[str],
        import_module_aliases: set[str],
    ) -> None:
        if isinstance(node, ast.If) and is_type_checking_if(node):
            for child in node.orelse:
                visit_runtime_nodes(
                    child,
                    source,
                    info,
                    function_depth=function_depth,
                    importlib_module_aliases=importlib_module_aliases,
                    import_module_aliases=import_module_aliases,
                )
            return

        if isinstance(node, (ast.Import, ast.ImportFrom)):
            record_import_node(
                node,
                source,
                info,
                lazy_kind='lazy_local' if function_depth > 0 else 'eager',
            )
            return

        if isinstance(node, ast.Call):
            dynamic_target = dynamic_import_target(
                node,
                known,
                importlib_module_aliases,
                import_module_aliases,
            )
            if dynamic_target is not None and dynamic_target != source:
                edges.append(
                    ImportEdge(
                        source=source,
                        target=dynamic_target,
                        imported=(),
                        import_type='dynamic_import',
                        lazy_kind='lazy_dynamic',
                        line=node.lineno,
                        source_file=str(info.path),
                    )
                )
            elif dynamic_target is None:
                func = node.func
                if (
                    isinstance(func, ast.Attribute)
                    and func.attr == 'import_module'
                    and node.args
                ) or (
                    isinstance(func, ast.Name)
                    and func.id in import_module_aliases
                    and node.args
                ):
                    coverage_gaps.append(
                        {
                            'module': source,
                            'line': getattr(node, 'lineno', 0),
                            'kind': 'dynamic_import_unresolved',
                            'source_file': str(info.path),
                        }
                    )

        next_function_depth = function_depth + int(
            isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        )
        for child in ast.iter_child_nodes(node):
            visit_runtime_nodes(
                child,
                source,
                info,
                function_depth=next_function_depth,
                importlib_module_aliases=importlib_module_aliases,
                import_module_aliases=import_module_aliases,
            )

    for source, info in modules.items():
        try:
            tree = ast.parse(info.path.read_text(encoding='utf-8'))
        except (OSError, SyntaxError, UnicodeDecodeError):
            coverage_gaps.append(
                {
                    'module': source,
                    'line': 0,
                    'kind': 'syntax_or_decode_error',
                    'source_file': str(info.path),
                }
            )
            continue
        importlib_aliases, import_module_aliases = detect_importlib_aliases(
            tree
        )
        visit_runtime_nodes(
            tree,
            source,
            info,
            function_depth=0,
            importlib_module_aliases=importlib_aliases,
            import_module_aliases=import_module_aliases,
        )

    return dedupe_edges(edges), coverage_gaps


def dedupe_edges(edges: Iterable[ImportEdge]) -> list[ImportEdge]:
    seen: set[tuple[object, ...]] = set()
    out: list[ImportEdge] = []
    for edge in sorted(
        edges,
        key=lambda item: (item.source, item.target, item.line, item.imported),
    ):
        key = (
            edge.source,
            edge.target,
            edge.imported,
            edge.import_type,
            edge.lazy_kind,
            edge.line,
            edge.source_file,
        )
        if key not in seen:
            seen.add(key)
            out.append(edge)
    return out


def strongly_connected_components(
    nodes: Iterable[str],
    edges: Iterable[tuple[str, str]],
) -> list[list[str]]:
    graph: dict[str, list[str]] = defaultdict(list)
    rev_graph: dict[str, list[str]] = defaultdict(list)

    for src, tgt in edges:
        graph[src].append(tgt)
        rev_graph[tgt].append(src)

    for node in nodes:
        graph.setdefault(node, [])
        rev_graph.setdefault(node, [])

    visited: set[str] = set()
    order: list[str] = []

    def dfs1(node: str) -> None:
        visited.add(node)
        for nxt in graph[node]:
            if nxt not in visited:
                dfs1(nxt)
        order.append(node)

    for node in graph:
        if node not in visited:
            dfs1(node)

    visited.clear()
    components: list[list[str]] = []

    def dfs2(node: str, component: list[str]) -> None:
        visited.add(node)
        component.append(node)
        for nxt in rev_graph[node]:
            if nxt not in visited:
                dfs2(nxt, component)

    for node in reversed(order):
        if node not in visited:
            component: list[str] = []
            dfs2(node, component)
            if len(component) > 1:
                components.append(sorted(component))

    return sorted(components)


def analyze(
    repo: Path,
    *,
    package_filter: str | None = None,
    explicit_roots: Iterable[Path] = (),
    includes: Iterable[str] = (),
    excludes: Iterable[str] = (),
) -> AnalysisResult:
    roots = discover_module_roots(repo, explicit_roots)
    modules = collect_modules(
        repo,
        roots,
        includes=includes,
        excludes=excludes,
        package_filter=package_filter,
    )
    edges, coverage_gaps = parse_imports(modules, package_filter=package_filter)
    cycle_edges = [
        (edge.source, edge.target)
        for edge in edges
        if edge.lazy_kind != 'lazy_dynamic'
    ]
    cycles = strongly_connected_components(modules, cycle_edges)
    return AnalysisResult(
        repo=repo,
        module_roots=roots,
        modules=modules,
        edges=edges,
        cycles=cycles,
        coverage_gaps=coverage_gaps,
    )
