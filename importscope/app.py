from __future__ import annotations

import json
from typing import Any
from pathlib import Path
import tempfile
from collections.abc import Callable

import yaml

from .model import ImportEdge, ModuleInfo, AnalysisResult
from .policy import (
    load_config,
    default_config,
    evaluate_policy,
    snapshot_payload,
    is_boundary_helper_edge,
    package_name_from_config,
)
from .analyzer import analyze
from .renderers import (
    render_svg,
    is_policy_edge,
    write_dot_graph,
    write_cycles_csv,
    write_findings_csv,
    write_mermaid_graph,
    write_snapshot_json,
    write_summary_report,
    write_import_edges_csv,
    write_symbol_import_dot,
    write_module_symbols_csv,
    write_private_imports_csv,
    write_module_inventory_dot,
    write_symbol_import_mermaid,
    write_module_inventory_mermaid,
)


def _filter_fn(
    filter_name: str | None,
    config: dict[str, Any],
    result: AnalysisResult,
) -> Callable[[ImportEdge], bool] | None:
    if filter_name == 'boundary_helper':
        return lambda edge: is_boundary_helper_edge(edge, config)
    if filter_name == 'policy':
        return lambda edge: is_policy_edge(edge, config, result)
    return None


def _profile_spec(config: dict[str, Any], profile_name: str) -> dict[str, Any]:
    profiles = config.get('outputs', {}).get('profiles', {})
    if profile_name not in profiles:
        raise ValueError(f'Unknown profile: {profile_name}')
    return profiles[profile_name]


def _table_name(config: dict[str, Any], key: str) -> str:
    return config.get('outputs', {}).get('tables', {}).get(key, f'{key}.csv')


def _remove_graph_outputs(out: Path, stem: str) -> None:
    for suffix in ('.dot', '.mmd', '.svg'):
        path = out / f'{stem}{suffix}'
        if path.exists():
            path.unlink()


def _dot_path_for_render(
    out: Path, stem: str, persist: bool
) -> tuple[Path, bool]:
    if persist:
        return out / f'{stem}.dot', False
    handle = tempfile.NamedTemporaryFile(
        prefix=f'.{stem}.',
        suffix='.dot',
        dir=out,
        delete=False,
    )
    handle.close()
    return Path(handle.name), True


def _move_rendered_svg(dot_path: Path, final_svg_path: Path) -> None:
    rendered_svg = dot_path.with_suffix('.svg')
    if rendered_svg.exists() and rendered_svg != final_svg_path:
        rendered_svg.replace(final_svg_path)


def _default_config_path(repo: Path) -> Path:
    for candidate in (repo / '.importscope.yml', repo / 'importscope.yml'):
        if candidate.exists():
            return candidate
    return repo / '.importscope.yml'


def _load_raw_config(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    data = yaml.safe_load(path.read_text(encoding='utf-8')) or {}
    if not isinstance(data, dict):
        raise ValueError(f'Config at {path} must be a mapping')
    return data


def _write_config_yaml(path: Path, data: dict[str, Any]) -> str:
    text = yaml.safe_dump(data, sort_keys=False)
    path.write_text(text, encoding='utf-8')
    return text


def _config_path(repo: Path, config_path: Path | None) -> Path:
    return (
        config_path.resolve()
        if config_path
        else _default_config_path(repo.resolve())
    )


def _compact_init_config(
    repo: Path, profile: str | None = None
) -> dict[str, Any]:
    config = {
        'tool': {'default_profile': profile or 'overview'},
        'discovery': {'exclude': default_config()['discovery']['exclude']},
        'policy': {'enabled': False},
    }
    result = analyze(
        repo,
        excludes=config['discovery']['exclude'],
    )
    package = package_name_from_config({}, result)
    if package:
        config['package'] = package
    return config


def _ensure_mapping(parent: dict[str, Any], key: str) -> dict[str, Any]:
    value = parent.get(key)
    if isinstance(value, dict):
        return value
    value = {}
    parent[key] = value
    return value


def _ensure_list(parent: dict[str, Any], key: str) -> list[Any]:
    value = parent.get(key)
    if isinstance(value, list):
        return value
    value = []
    parent[key] = value
    return value


def _forbid_rule(
    source_prefix: str, target_prefix: str
) -> dict[str, list[str]]:
    return {
        'source_prefixes': [source_prefix],
        'target_prefixes': [target_prefix],
    }


def analyze_repo(
    *,
    repo: Path,
    out: Path,
    config_path: Path | None = None,
    profile: str | None = None,
    package: str | None = None,
    include: list[str] | None = None,
    exclude: list[str] | None = None,
    module_roots: list[Path] | None = None,
    graph_names: list[str] | None = None,
    formats: list[str] | None = None,
    render: str = 'svg',
    summary_mode: str | None = None,
    max_symbol_edges: int | None = None,
    policy_enabled_override: bool | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Run the full analyze -> evaluate -> render workflow for one repository.

    This is the main programmatic entry point behind the ``importscope analyze``
    CLI command.
    """
    config, discovered_path = load_config(
        repo, config_path=config_path, profile=profile
    )
    if policy_enabled_override is not None:
        config.setdefault('policy', {})
        config['policy']['enabled'] = policy_enabled_override
    selected_profile = profile or config.get('tool', {}).get(
        'default_profile', 'overview'
    )
    spec = _profile_spec(config, selected_profile)
    package_name = package or config.get('package')

    profile_graphs = list(spec.get('graphs', []))
    if graph_names:
        profile_graphs = [
            graph
            for graph in profile_graphs
            if graph.get('id') in set(graph_names)
        ]
        known = {graph.get('id') for graph in spec.get('graphs', [])}
        for name in graph_names:
            if name not in known:
                raise ValueError(
                    f'Graph `{name}` is not available in profile `{selected_profile}`'
                )

    selected_formats = list(formats or spec.get('formats', []))
    selected_summary = summary_mode or spec.get('summary', 'full')
    explicit_roots = [root.resolve() for root in module_roots or []]

    plan = {
        'repo': str(repo),
        'out': str(out),
        'config_path': str(discovered_path) if discovered_path else None,
        'profile': selected_profile,
        'package': package_name,
        'graphs': profile_graphs,
        'formats': selected_formats,
        'render': render,
        'summary': selected_summary,
    }
    if dry_run:
        return {'mode': 'dry-run', 'plan': plan}

    result = analyze(
        repo,
        package_filter=package_name,
        explicit_roots=explicit_roots,
        includes=include or config.get('discovery', {}).get('include', []),
        excludes=exclude or config.get('discovery', {}).get('exclude', []),
    )
    findings = evaluate_policy(result, config)

    out.mkdir(parents=True, exist_ok=True)
    if 'csv' in selected_formats:
        write_import_edges_csv(
            result.edges, out / _table_name(config, 'edges'), config, result
        )
        write_private_imports_csv(
            result.edges,
            out / _table_name(config, 'private_imports'),
            config,
            result,
        )
        write_module_symbols_csv(
            result, out / _table_name(config, 'module_symbols')
        )
        write_cycles_csv(result, out / _table_name(config, 'cycles'))
        write_findings_csv(findings, out / _table_name(config, 'findings'))

    payload = snapshot_payload(result, config, findings, selected_profile)
    render_warnings: list[str] = []
    if 'json' in selected_formats:
        write_snapshot_json(
            payload,
            out
            / config.get('outputs', {}).get(
                'snapshot_artifact', 'analysis_snapshot.json'
            ),
        )

    for graph in profile_graphs:
        stem = str(graph['stem'])
        kind = str(graph.get('kind', 'module'))
        filter_name = graph.get('filter')
        filter_fn = _filter_fn(
            str(filter_name) if filter_name else None, config, result
        )
        want_dot = 'dot' in selected_formats
        want_mmd = 'mmd' in selected_formats
        want_svg = 'svg' in selected_formats

        if kind == 'inventory':
            wrote_any = False
            if want_mmd:
                wrote_any = write_module_inventory_mermaid(
                    out / f'{stem}.mmd',
                    config,
                    result,
                )
            if want_dot or want_svg:
                dot_path, remove_after = _dot_path_for_render(
                    out, stem, persist=want_dot
                )
                svg_path = out / f'{stem}.svg'
                wrote_any = (
                    write_module_inventory_dot(
                        dot_path,
                        config,
                        result,
                    )
                    or wrote_any
                )
                try:
                    if wrote_any and want_svg:
                        try:
                            render_svg(dot_path)
                            _move_rendered_svg(dot_path, svg_path)
                        except RuntimeError as exc:
                            render_warnings.append(str(exc))
                finally:
                    if remove_after and dot_path.exists():
                        dot_path.unlink()
            if not wrote_any:
                _remove_graph_outputs(out, stem)
            continue

        if kind == 'symbol':
            wrote_any = False
            if want_mmd:
                wrote_any = write_symbol_import_mermaid(
                    result.edges,
                    out / f'{stem}.mmd',
                    config,
                    result,
                    max_edges=max_symbol_edges,
                )
            if want_dot or want_svg:
                dot_path, remove_after = _dot_path_for_render(
                    out, stem, persist=want_dot
                )
                svg_path = out / f'{stem}.svg'
                wrote_any = (
                    write_symbol_import_dot(
                        result.edges,
                        dot_path,
                        config,
                        result,
                        max_edges=max_symbol_edges,
                    )
                    or wrote_any
                )
                try:
                    if wrote_any and want_svg:
                        try:
                            render_svg(dot_path)
                            _move_rendered_svg(dot_path, svg_path)
                        except RuntimeError as exc:
                            render_warnings.append(str(exc))
                finally:
                    if remove_after and dot_path.exists():
                        dot_path.unlink()
            if not wrote_any:
                _remove_graph_outputs(out, stem)
            continue

        wrote_any = False
        if want_mmd:
            wrote_any = write_mermaid_graph(
                result.edges,
                out / f'{stem}.mmd',
                config,
                result,
                title=stem,
                labeled=bool(graph.get('labeled')),
                package_level=bool(graph.get('package_level')),
                filter_fn=filter_fn,
            )
        if want_dot or want_svg:
            dot_path, remove_after = _dot_path_for_render(
                out, stem, persist=want_dot
            )
            svg_path = out / f'{stem}.svg'
            wrote_any = (
                write_dot_graph(
                    result.edges,
                    dot_path,
                    config,
                    result,
                    labeled=bool(graph.get('labeled')),
                    package_level=bool(graph.get('package_level')),
                    filter_fn=filter_fn,
                )
                or wrote_any
            )
            try:
                if wrote_any and want_svg:
                    try:
                        render_svg(dot_path)
                        _move_rendered_svg(dot_path, svg_path)
                    except RuntimeError as exc:
                        render_warnings.append(str(exc))
            finally:
                if remove_after and dot_path.exists():
                    dot_path.unlink()
        if not wrote_any:
            _remove_graph_outputs(out, stem)

    if selected_summary != 'none' and 'md' in selected_formats:
        write_summary_report(
            result,
            findings,
            out
            / config.get('outputs', {}).get(
                'summary_artifact', 'importscope_summary.md'
            ),
            config,
        )

    return {
        'mode': 'analyze',
        'plan': plan,
        'modules': len(result.modules),
        'edges': len(result.edges),
        'cycles': len(result.cycles),
        'findings': len(findings),
        'render_warnings': render_warnings,
        'snapshot': payload,
    }


def list_profiles(
    *, repo: Path, config_path: Path | None = None
) -> dict[str, Any]:
    """Return the built-in and repo-local output profiles available for a repo."""
    config, discovered_path = load_config(repo, config_path=config_path)
    profiles = config.get('outputs', {}).get('profiles', {})
    return {
        'config_path': str(discovered_path) if discovered_path else None,
        'profiles': profiles,
    }


def init_config(
    *,
    repo: Path,
    path: Path,
    profile: str | None = None,
    minimal: bool = False,
) -> str:
    """Write a starter YAML configuration file and return its text."""
    data = (
        _compact_init_config(repo, profile=profile)
        if minimal
        else load_config(repo, profile=profile)[0]
    )
    return _write_config_yaml(path, data)


def show_config(
    *,
    repo: Path,
    config_path: Path | None = None,
    effective: bool = False,
) -> dict[str, Any]:
    """Return raw or effective config plus the resolved config path."""
    path = _config_path(repo, config_path)
    if effective:
        config, discovered_path = load_config(
            repo, config_path=path if path.exists() else None
        )
        return {
            'config_path': str(discovered_path or path),
            'config': config,
            'effective': True,
        }
    return {
        'config_path': str(path),
        'config': _load_raw_config(path),
        'effective': False,
    }


def edit_config(
    *,
    repo: Path,
    config_path: Path | None = None,
    action: str,
    values: list[str] | None = None,
) -> dict[str, Any]:
    """Apply one config mutation and write the updated YAML file."""
    path = _config_path(repo, config_path)
    config = _load_raw_config(path)
    changed = False
    payload = list(values or [])

    if action == 'package:set':
        if len(payload) != 1:
            raise ValueError('package:set expects exactly one package name')
        if config.get('package') != payload[0]:
            config['package'] = payload[0]
            changed = True
    elif action == 'package:unset':
        if 'package' in config:
            del config['package']
            changed = True
    elif action == 'policy:enable':
        policy = _ensure_mapping(config, 'policy')
        if policy.get('enabled') is not True:
            policy['enabled'] = True
            changed = True
    elif action == 'policy:disable':
        policy = _ensure_mapping(config, 'policy')
        if policy.get('enabled') is not False:
            policy['enabled'] = False
            changed = True
    elif action == 'exclude:add':
        if not payload:
            raise ValueError('exclude:add expects at least one glob')
        discovery = _ensure_mapping(config, 'discovery')
        excludes = _ensure_list(discovery, 'exclude')
        for pattern in payload:
            if pattern not in excludes:
                excludes.append(pattern)
                changed = True
    elif action == 'exclude:remove':
        if not payload:
            raise ValueError('exclude:remove expects at least one glob')
        discovery = _ensure_mapping(config, 'discovery')
        excludes = _ensure_list(discovery, 'exclude')
        original = list(excludes)
        excludes[:] = [
            pattern for pattern in excludes if pattern not in set(payload)
        ]
        changed = excludes != original
    elif action == 'include:add':
        if not payload:
            raise ValueError('include:add expects at least one glob')
        discovery = _ensure_mapping(config, 'discovery')
        includes = _ensure_list(discovery, 'include')
        for pattern in payload:
            if pattern not in includes:
                includes.append(pattern)
                changed = True
    elif action == 'include:remove':
        if not payload:
            raise ValueError('include:remove expects at least one glob')
        discovery = _ensure_mapping(config, 'discovery')
        includes = _ensure_list(discovery, 'include')
        original = list(includes)
        includes[:] = [
            pattern for pattern in includes if pattern not in set(payload)
        ]
        changed = includes != original
    elif action == 'forbid:add':
        if len(payload) != 2:
            raise ValueError('forbid:add expects source and target prefixes')
        policy = _ensure_mapping(config, 'policy')
        rules = _ensure_list(policy, 'forbidden_imports')
        rule = _forbid_rule(payload[0], payload[1])
        if rule not in rules:
            rules.append(rule)
            changed = True
    elif action == 'forbid:remove':
        if len(payload) != 2:
            raise ValueError('forbid:remove expects source and target prefixes')
        policy = _ensure_mapping(config, 'policy')
        rules = _ensure_list(policy, 'forbidden_imports')
        rule = _forbid_rule(payload[0], payload[1])
        original = list(rules)
        rules[:] = [item for item in rules if item != rule]
        changed = rules != original
    elif action == 'allowed-private:add':
        if not payload:
            raise ValueError('allowed-private:add expects at least one prefix')
        policy = _ensure_mapping(config, 'policy')
        prefixes = _ensure_list(policy, 'allowed_private_target_prefixes')
        for prefix in payload:
            if prefix not in prefixes:
                prefixes.append(prefix)
                changed = True
    elif action == 'allowed-private:remove':
        if not payload:
            raise ValueError(
                'allowed-private:remove expects at least one prefix'
            )
        policy = _ensure_mapping(config, 'policy')
        prefixes = _ensure_list(policy, 'allowed_private_target_prefixes')
        original = list(prefixes)
        prefixes[:] = [
            prefix for prefix in prefixes if prefix not in set(payload)
        ]
        changed = prefixes != original
    elif action == 'module-group-depth:set':
        if len(payload) != 1:
            raise ValueError(
                'module-group-depth:set expects exactly one integer'
            )
        policy = _ensure_mapping(config, 'policy')
        depth = int(payload[0])
        if policy.get('module_group_depth') != depth:
            policy['module_group_depth'] = depth
            changed = True
    elif action == 'module-group-depth:unset':
        policy = _ensure_mapping(config, 'policy')
        if 'module_group_depth' in policy:
            del policy['module_group_depth']
            changed = True
    else:
        raise ValueError(f'Unknown config action: {action}')

    text = _write_config_yaml(path, config)
    return {
        'config_path': str(path),
        'changed': changed,
        'config': config,
        'text': text,
    }


def check_repo(
    *,
    repo: Path,
    config_path: Path | None = None,
    profile: str | None = None,
) -> dict[str, Any]:
    """Validate config, discovery, and toolchain readiness for a repository."""
    config, discovered_path = load_config(
        repo, config_path=config_path, profile=profile
    )
    selected_profile = profile or config.get('tool', {}).get(
        'default_profile', 'overview'
    )
    spec = _profile_spec(config, selected_profile)
    dot_available = bool(
        Path('/usr/bin/dot').exists() or Path('/bin/dot').exists()
    )
    analysis = analyze(
        repo,
        package_filter=config.get('package'),
        includes=config.get('discovery', {}).get('include', []),
        excludes=config.get('discovery', {}).get('exclude', []),
    )
    problems: list[str] = []
    if not analysis.modules:
        problems.append('No Python modules discovered.')
    if 'svg' in spec.get('formats', []) and not dot_available:
        problems.append(
            'Graphviz dot not available but SVG output is requested.'
        )
    return {
        'config_path': str(discovered_path) if discovered_path else None,
        'profile': selected_profile,
        'modules': len(analysis.modules),
        'edges': len(analysis.edges),
        'problems': problems,
    }


def _load_snapshot(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding='utf-8'))


def _paths_from_snapshot_edges(
    edges: list[dict[str, Any]],
    *,
    source: str | None,
    target: str | None,
    max_paths: int,
) -> list[list[str]]:
    graph: dict[str, list[str]] = {}
    for edge in edges:
        graph.setdefault(edge['source'], []).append(edge['target'])
    paths: list[list[str]] = []
    queue: list[list[str]] = [[source]] if source else []
    while queue and len(paths) < max_paths:
        path = queue.pop(0)
        node = path[-1]
        if node == target:
            paths.append(path)
            continue
        for nxt in graph.get(node, []):
            if nxt in path:
                continue
            queue.append(path + [nxt])
    return paths


def _analysis_result_from_snapshot(payload: dict[str, Any]) -> AnalysisResult:
    analysis = payload['analysis']
    modules = {
        name: ModuleInfo(
            module=name,
            path=Path(info['path']),
            is_package=bool(info['is_package']),
            definitions=set(info.get('definitions', [])),
        )
        for name, info in analysis['modules'].items()
    }
    edges = [
        ImportEdge(
            source=edge['source'],
            target=edge['target'],
            imported=tuple(edge.get('imported', [])),
            import_type=edge.get('import_type', 'import'),
            lazy_kind=edge.get('lazy_kind', 'eager'),
            line=int(edge.get('line', 0)),
            source_file=edge.get('source_file', ''),
        )
        for edge in analysis['edges']
    ]
    return AnalysisResult(
        repo=Path(analysis['repo']),
        module_roots=[Path(root) for root in analysis.get('module_roots', [])],
        modules=modules,
        edges=edges,
        cycles=analysis.get('cycles', []),
        coverage_gaps=analysis.get('coverage_gaps', []),
    )


def inspect_snapshot(
    *,
    snapshot_path: Path,
    mode: str,
    source: str | None = None,
    target: str | None = None,
    name: str | None = None,
    max_paths: int = 5,
) -> dict[str, Any]:
    """Query a previously generated analysis snapshot without rerunning analysis."""
    payload = _load_snapshot(snapshot_path)
    analysis = payload['analysis']
    edges: list[dict[str, Any]] = analysis['edges']
    modules: dict[str, Any] = analysis['modules']

    if mode == 'edge':
        matches = [
            edge
            for edge in edges
            if edge['source'] == source and edge['target'] == target
        ]
        return {'mode': mode, 'matches': matches}

    if mode == 'module':
        direct = [edge for edge in edges if edge['source'] == name]
        reverse = [edge for edge in edges if edge['target'] == name]
        return {
            'mode': mode,
            'module': name,
            'module_exists': name in modules,
            'imports': direct,
            'imported_by': reverse,
        }

    if mode == 'cycle':
        cycles = analysis['cycles']
        if name:
            cycles = [component for component in cycles if name in component]
        return {'mode': mode, 'cycles': cycles}

    if mode == 'symbol':
        matches = []
        for module_name, info in modules.items():
            if name in info['definitions']:
                matches.append({'module': module_name, 'path': info['path']})
        references = [
            edge for edge in edges if name in edge.get('imported', [])
        ]
        return {'mode': mode, 'definitions': matches, 'references': references}

    if mode == 'path':
        paths = _paths_from_snapshot_edges(
            edges, source=source, target=target, max_paths=max_paths
        )
        return {'mode': mode, 'paths': paths}

    raise ValueError(f'Unsupported inspect mode: {mode}')


def render_snapshot_path_graph(
    *,
    snapshot_path: Path,
    source: str,
    target: str,
    out_path: Path,
    path_index: int = 0,
    max_paths: int = 5,
    image_format: str = 'svg',
) -> dict[str, Any]:
    """Render one inspected path as a highlighted module graph from a saved snapshot."""
    payload = _load_snapshot(snapshot_path)
    paths = _paths_from_snapshot_edges(
        payload['analysis']['edges'],
        source=source,
        target=target,
        max_paths=max_paths,
    )
    if not paths:
        return {
            'mode': 'path-graph',
            'path_found': False,
            'paths': [],
            'dot_path': None,
            'svg_path': None,
        }
    if path_index < 0 or path_index >= len(paths):
        raise ValueError(
            f'Path index {path_index} out of range for {len(paths)} path(s)'
        )

    selected_path = paths[path_index]
    result = _analysis_result_from_snapshot(payload)
    config = payload.get('config', {})
    highlight_nodes = set(selected_path)
    highlight_edges = set(zip(selected_path, selected_path[1:], strict=False))

    base = (
        out_path.with_suffix('')
        if out_path.suffix in {'.dot', '.svg'}
        else out_path
    )
    dot_path = base.with_suffix('.dot')
    svg_path = base.with_suffix('.svg')

    write_dot_graph(
        result.edges,
        dot_path,
        config,
        result,
        labeled=True,
        package_level=False,
        highlight_nodes=highlight_nodes,
        highlight_edges=highlight_edges,
    )
    if image_format in {'svg', 'both'}:
        render_svg(dot_path)
    if image_format == 'svg' and dot_path.exists():
        dot_path.unlink()

    return {
        'mode': 'path-graph',
        'path_found': True,
        'selected_path': selected_path,
        'path_index': path_index,
        'dot_path': str(dot_path) if image_format in {'dot', 'both'} else None,
        'svg_path': str(svg_path) if image_format in {'svg', 'both'} else None,
    }
