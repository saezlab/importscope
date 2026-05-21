from __future__ import annotations

import re
import copy
import json
from typing import Any
from pathlib import Path

import yaml

from .model import ImportEdge, PolicyFinding, AnalysisResult


DEFAULT_DISPLAY_GROUPS = [
    {
        'name': 'package',
        'label': 'package',
        'match_prefixes': [],
        'fill': '#f8fafc',
        'stroke': '#334155',
        'class': 'package',
    },
    {
        'name': 'other',
        'label': 'other',
        'match_prefixes': [],
        'fill': '#f8fafc',
        'stroke': '#64748b',
        'class': 'other',
    },
]

AUTO_GROUP_COLORS = [
    ('#dbeafe', '#1d4ed8'),
    ('#dcfce7', '#15803d'),
    ('#fef3c7', '#b45309'),
    ('#ede9fe', '#6d28d9'),
    ('#ffe4e6', '#be123c'),
    ('#ccfbf1', '#0f766e'),
    ('#e0e7ff', '#4338ca'),
    ('#f5d0fe', '#a21caf'),
]


def _hex_to_rgb(color: str) -> tuple[int, int, int]:
    color = color.lstrip('#')
    if len(color) != 6:
        return (248, 250, 252)
    return tuple(int(color[index : index + 2], 16) for index in (0, 2, 4))


def _rgb_to_hex(rgb: tuple[int, int, int]) -> str:
    return '#' + ''.join(f'{max(0, min(255, value)):02x}' for value in rgb)


def _mix_with_white(color: str, amount: float) -> str:
    r, g, b = _hex_to_rgb(color)
    mixed = (
        int(r + (255 - r) * amount),
        int(g + (255 - g) * amount),
        int(b + (255 - b) * amount),
    )
    return _rgb_to_hex(mixed)


def _mix_colors(base: str, target: str, amount: float) -> str:
    r1, g1, b1 = _hex_to_rgb(base)
    r2, g2, b2 = _hex_to_rgb(target)
    mixed = (
        int(r1 + (r2 - r1) * amount),
        int(g1 + (g2 - g1) * amount),
        int(b1 + (b2 - b1) * amount),
    )
    return _rgb_to_hex(mixed)


def load_yaml_file(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding='utf-8')) or {}
    if not isinstance(data, dict):
        raise ValueError(f'Config at {path} must be a mapping')
    return data


def deep_merge(
    base: dict[str, Any], override: dict[str, Any]
) -> dict[str, Any]:
    merged = copy.deepcopy(base)
    for key, value in override.items():
        if (
            key in merged
            and isinstance(merged[key], dict)
            and isinstance(value, dict)
        ):
            merged[key] = deep_merge(merged[key], value)
        else:
            merged[key] = copy.deepcopy(value)
    return merged


def default_config() -> dict[str, Any]:
    return {
        'tool': {
            'name': 'importscope',
            'default_profile': 'overview',
        },
        'discovery': {
            'include': [],
            'exclude': [
                '.venv/**',
                'venv/**',
                '.tox/**',
                'build/**',
                'dist/**',
                '.git/**',
            ],
        },
        'policy': {
            'enabled': False,
            'policy_areas': [],
            'display_groups': copy.deepcopy(DEFAULT_DISPLAY_GROUPS),
            'forbidden_imports': [],
            'allowed_import_pairs': [],
            'allowed_private_target_prefixes': [],
            'boundary_helper_target_prefixes': [],
            'boundary_helper_symbols': [],
        },
        'outputs': {
            'summary_artifact': 'architecture_report.md',
            'snapshot_artifact': 'analysis_snapshot.json',
            'tables': {
                'edges': 'internal_import_edges.csv',
                'private_imports': 'private_import_edges.csv',
                'module_symbols': 'module_definitions.csv',
                'cycles': 'module_cycles.csv',
                'findings': 'policy_findings.csv',
            },
            'profiles': {
                'overview': {
                    'description': 'Repo overview with grouped dependency graphs and summary report.',
                    'graphs': [
                        {
                            'id': 'module-layout',
                            'stem': 'module_layout_graph',
                            'kind': 'inventory',
                        },
                        {
                            'id': 'package-dependency',
                            'stem': 'group_dependency_graph',
                            'kind': 'module',
                            'package_level': True,
                            'labeled': False,
                        },
                        {
                            'id': 'module-dependency',
                            'stem': 'module_dependency_graph',
                            'kind': 'module',
                            'package_level': False,
                            'labeled': False,
                        },
                    ],
                    'formats': ['svg', 'md'],
                    'summary': 'full',
                },
                'policy': {
                    'description': 'Policy-focused violation and helper cleanup outputs.',
                    'graphs': [
                        {
                            'id': 'policy-violations',
                            'stem': 'policy_violation_graph',
                            'kind': 'module',
                            'package_level': False,
                            'labeled': True,
                            'filter': 'policy',
                        },
                        {
                            'id': 'boundary-helper',
                            'stem': 'boundary_helper_candidates',
                            'kind': 'module',
                            'package_level': False,
                            'labeled': True,
                            'filter': 'boundary_helper',
                        },
                    ],
                    'formats': ['svg', 'md'],
                    'summary': 'full',
                },
                'symbols': {
                    'description': 'Comprehensive symbol import graph plus summary.',
                    'graphs': [
                        {
                            'id': 'symbol-import',
                            'stem': 'symbol_import_graph',
                            'kind': 'symbol',
                        },
                    ],
                    'formats': ['svg', 'md'],
                    'summary': 'short',
                },
                'all': {
                    'description': 'All graph families and reports.',
                    'graphs': [
                        {
                            'id': 'module-layout',
                            'stem': 'module_layout_graph',
                            'kind': 'inventory',
                        },
                        {
                            'id': 'package-dependency',
                            'stem': 'group_dependency_graph',
                            'kind': 'module',
                            'package_level': True,
                            'labeled': False,
                        },
                        {
                            'id': 'module-dependency',
                            'stem': 'module_dependency_graph',
                            'kind': 'module',
                            'package_level': False,
                            'labeled': False,
                        },
                        {
                            'id': 'symbol-labeled-module-dependency',
                            'stem': 'module_dependency_with_symbols',
                            'kind': 'module',
                            'package_level': False,
                            'labeled': True,
                        },
                        {
                            'id': 'boundary-helper',
                            'stem': 'boundary_helper_candidates',
                            'kind': 'module',
                            'package_level': False,
                            'labeled': True,
                            'filter': 'boundary_helper',
                        },
                        {
                            'id': 'symbol-import',
                            'stem': 'symbol_import_graph',
                            'kind': 'symbol',
                        },
                    ],
                    'formats': ['svg', 'md'],
                    'summary': 'full',
                },
            },
        },
    }


def normalize_profile_name(config: dict[str, Any], profile: str | None) -> str:
    if profile:
        return profile
    return config.get('tool', {}).get('default_profile', 'overview')


def load_config(
    repo: Path,
    config_path: Path | None = None,
    profile: str | None = None,
) -> tuple[dict[str, Any], Path | None]:
    config = default_config()
    discovered_path = config_path

    if discovered_path is None:
        for candidate in (repo / '.importscope.yml', repo / 'importscope.yml'):
            if candidate.exists():
                discovered_path = candidate
                break

    if discovered_path is not None:
        config = deep_merge(config, load_yaml_file(discovered_path))

    return config, discovered_path


def list_profiles(config: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return config.get('outputs', {}).get('profiles', {})


def _has_only_default_display_groups(config: dict[str, Any]) -> bool:
    groups = config.get('policy', {}).get('display_groups', [])
    if not isinstance(groups, list):
        return False
    if len(groups) != 2:
        return False
    names = [str(group.get('name')) for group in groups]
    prefixes = [list(group.get('match_prefixes', [])) for group in groups]
    return names == ['package', 'other'] and prefixes == [[], []]


def _group_class_name(prefix: str) -> str:
    safe = re.sub(r'[^0-9a-zA-Z_]+', '_', prefix).strip('_')
    return safe or 'group'


def _auto_display_groups(
    config: dict[str, Any], result: AnalysisResult
) -> list[dict[str, Any]]:
    package = package_name_from_config(config, result)
    prefixes: list[str] = []
    seen: set[str] = set()

    if package:
        prefixes.append(package)
        seen.add(package)

    for module in sorted(result.modules):
        if package and matches_prefix(module, package):
            if module == package:
                continue
            remainder = module[len(package) + 1 :]
            head = remainder.split('.', 1)[0]
            prefix = f'{package}.{head}'
        else:
            parts = module.split('.')
            prefix = '.'.join(parts[:2]) if len(parts) >= 2 else parts[0]
        if prefix and prefix not in seen:
            seen.add(prefix)
            prefixes.append(prefix)

    groups: list[dict[str, Any]] = []
    if package:
        groups.append(
            {
                'name': package,
                'label': package,
                'match_prefixes': [package],
                'fill': '#f8fafc',
                'stroke': '#334155',
                'class': 'rootpkg',
            }
        )
        prefixes = [prefix for prefix in prefixes if prefix != package]

    for index, prefix in enumerate(prefixes):
        fill, stroke = AUTO_GROUP_COLORS[index % len(AUTO_GROUP_COLORS)]
        groups.append(
            {
                'name': prefix,
                'label': prefix,
                'match_prefixes': [prefix],
                'fill': fill,
                'stroke': stroke,
                'class': _group_class_name(prefix),
            }
        )

    groups.append(
        {
            'name': 'other',
            'label': 'other',
            'match_prefixes': [],
            'fill': '#f8fafc',
            'stroke': '#64748b',
            'class': 'other',
        }
    )
    return groups


def group_order(
    config: dict[str, Any], result: AnalysisResult | None = None
) -> list[dict[str, Any]]:
    groups = config.get('policy', {}).get('display_groups', [])
    if result is not None and _has_only_default_display_groups(config):
        return _auto_display_groups(config, result)
    return groups


def module_group_depth(config: dict[str, Any]) -> int | None:
    raw = config.get('policy', {}).get('module_group_depth')
    if raw in (None, '', False):
        return None
    try:
        depth = int(raw)
    except (TypeError, ValueError):
        return None
    return depth if depth > 0 else None


def matches_prefix(value: str, prefix: str) -> bool:
    return value == prefix or value.startswith(prefix + '.')


def _best_group_match_info(
    module: str,
    groups: list[dict[str, Any]],
    package: str | None,
) -> tuple[dict[str, Any] | None, str | None]:
    best: tuple[int, dict[str, Any], str] | None = None
    fallback: dict[str, Any] | None = None
    for group in groups:
        prefixes = list(group.get('match_prefixes', []))
        if group.get('name') == 'package' and package:
            prefixes = [package]
        if group.get('name') == 'other':
            fallback = group
        for prefix in prefixes:
            if matches_prefix(module, prefix):
                score = len(prefix)
                if best is None or score > best[0]:
                    best = (score, group, prefix)
    if best is not None:
        return best[1], best[2]
    return fallback, None


def _best_group_match(
    module: str,
    groups: list[dict[str, Any]],
    package: str | None,
) -> dict[str, Any] | None:
    matched, _ = _best_group_match_info(module, groups, package)
    return matched


def first_matching_group(
    module: str, groups: list[dict[str, Any]], package: str | None
) -> dict[str, Any]:
    matched = _best_group_match(module, groups, package)
    if matched is not None:
        return matched
    return (
        groups[-1]
        if groups
        else {
            'name': 'other',
            'label': 'other',
            'class': 'other',
            'fill': '#f8fafc',
            'stroke': '#64748b',
        }
    )


def package_name_from_config(
    config: dict[str, Any], result: AnalysisResult
) -> str | None:
    package = config.get('package')
    if package:
        return str(package)
    if len(result.modules) == 1:
        return next(iter(result.modules)).split('.', 1)[0]
    top_levels = {name.split('.', 1)[0] for name in result.modules}
    return next(iter(sorted(top_levels))) if len(top_levels) == 1 else None


def display_group_key(
    module: str, config: dict[str, Any], result: AnalysisResult
) -> str:
    package = package_name_from_config(config, result)
    group = first_matching_group(module, group_order(config, result), package)
    return str(group.get('name', 'other'))


def package_group_identifier(
    module: str, config: dict[str, Any], result: AnalysisResult
) -> str:
    package = package_name_from_config(config, result)
    _, matched_prefix = _best_group_match_info(
        module, group_order(config, result), package
    )
    if matched_prefix:
        return matched_prefix
    if package and matches_prefix(module, package):
        parts = module.split('.')
        return '.'.join(parts[:2]) if len(parts) >= 2 else package
    return display_group_key(module, config, result)


def module_cluster_key(
    module: str, config: dict[str, Any], result: AnalysisResult
) -> str:
    depth = module_group_depth(config)
    if depth is None:
        return display_group_key(module, config, result)

    package = package_name_from_config(config, result)
    _, matched_prefix = _best_group_match_info(
        module, group_order(config, result), package
    )
    parts = module.split('.')
    if not parts:
        return module

    target_depth = depth
    if matched_prefix:
        target_depth = max(target_depth, len(matched_prefix.split('.')))
    target_depth = min(target_depth, len(parts))
    return '.'.join(parts[:target_depth])


def display_group_label(
    group_name: str,
    config: dict[str, Any],
    result: AnalysisResult | None = None,
) -> str:
    for group in group_order(config, result):
        if group.get('name') == group_name:
            return str(group.get('label', group_name))
    return group_name


def display_group_style(
    group_name: str,
    config: dict[str, Any],
    result: AnalysisResult | None = None,
) -> dict[str, str]:
    for group in group_order(config, result):
        if group.get('name') == group_name:
            return {
                'class': str(group.get('class', group_name)),
                'fill': str(group.get('fill', '#f8fafc')),
                'stroke': str(group.get('stroke', '#64748b')),
            }
    return {'class': group_name, 'fill': '#f8fafc', 'stroke': '#64748b'}


def module_cluster_label(
    cluster_key: str, config: dict[str, Any], result: AnalysisResult
) -> str:
    for group in group_order(config, result):
        if group.get('name') == cluster_key:
            return str(group.get('label', cluster_key))
    return cluster_key


def _cluster_has_children(
    cluster_key: str, config: dict[str, Any], result: AnalysisResult
) -> bool:
    for module in result.modules:
        other_key = module_cluster_key(module, config, result)
        if other_key != cluster_key and other_key.startswith(cluster_key + '.'):
            return True
    return False


def _cluster_parent_key(cluster_key: str) -> str | None:
    parts = cluster_key.split('.')
    if len(parts) <= 1:
        return None
    return '.'.join(parts[:-1])


def module_cluster_style(
    cluster_key: str, config: dict[str, Any], result: AnalysisResult
) -> dict[str, str]:
    for group in group_order(config, result):
        if str(group.get('name')) == cluster_key:
            return {
                'class': str(
                    group.get('class', _group_class_name(cluster_key))
                ),
                'fill': str(group.get('fill', '#f8fafc')),
                'stroke': str(group.get('stroke', '#64748b')),
            }

    package = package_name_from_config(config, result)
    group, matched_prefix = _best_group_match_info(
        cluster_key, group_order(config, result), package
    )
    if group is None:
        color_index = sum(ord(char) for char in cluster_key) % len(
            AUTO_GROUP_COLORS
        )
        fill, stroke = AUTO_GROUP_COLORS[color_index]
        return {
            'class': _group_class_name(cluster_key),
            'fill': fill,
            'stroke': stroke,
        }
    exact_group_name = str(group.get('name', ''))
    fill = str(group.get('fill', '#f8fafc'))
    stroke = str(group.get('stroke', '#64748b'))
    if cluster_key != exact_group_name and matched_prefix:
        if matched_prefix == cluster_key:
            return {
                'class': _group_class_name(cluster_key),
                'fill': fill,
                'stroke': stroke,
            }
        parent_key = _cluster_parent_key(cluster_key)
        if (
            parent_key
            and parent_key != cluster_key
            and parent_key != matched_prefix
        ):
            parent_fill = module_cluster_style(parent_key, config, result)
            if parent_fill['class'] != _group_class_name(cluster_key):
                return {
                    'class': _group_class_name(cluster_key),
                    'fill': parent_fill['fill'],
                    'stroke': parent_fill['stroke'],
                }
        if _cluster_has_children(cluster_key, config, result):
            depth_delta = max(
                1, len(cluster_key.split('.')) - len(matched_prefix.split('.'))
            )
            fill = _mix_colors(fill, stroke, min(0.10 * depth_delta, 0.22))
        return {
            'class': _group_class_name(cluster_key),
            'fill': fill,
            'stroke': stroke,
        }
    return {
        'class': _group_class_name(cluster_key),
        'fill': fill,
        'stroke': stroke,
    }


def policy_area(
    module: str, config: dict[str, Any], result: AnalysisResult
) -> str:
    areas = config.get('policy', {}).get('policy_areas', [])
    package = package_name_from_config(config, result)
    matched = _best_group_match(module, areas, package)
    if matched is not None:
        return str(matched.get('name'))
    if package and matches_prefix(module, package):
        return package
    parts = module.split('.')
    return '.'.join(parts[:2]) if len(parts) >= 2 else module


def has_private_module_segment(module: str) -> bool:
    return any(part.startswith('_') for part in module.split('.')[1:])


def private_symbols(edge: ImportEdge) -> tuple[str, ...]:
    return tuple(name for name in edge.imported if name.startswith('_'))


def is_allowed_import_pair(edge: ImportEdge, config: dict[str, Any]) -> bool:
    for pair in config.get('policy', {}).get('allowed_import_pairs', []):
        if edge.source == pair.get('source') and edge.target == pair.get(
            'target'
        ):
            return True
    return False


def policy_enabled(config: dict[str, Any]) -> bool:
    return bool(config.get('policy', {}).get('enabled', False))


def is_forbidden_import(edge: ImportEdge, config: dict[str, Any]) -> bool:
    if not policy_enabled(config):
        return False
    if is_allowed_import_pair(edge, config):
        return False
    for rule in config.get('policy', {}).get('forbidden_imports', []):
        source_prefixes = rule.get('source_prefixes', [])
        target_prefixes = rule.get('target_prefixes', [])
        if not any(
            matches_prefix(edge.source, prefix) for prefix in source_prefixes
        ):
            continue
        if any(
            matches_prefix(edge.target, prefix) for prefix in target_prefixes
        ):
            return True
    return False


def is_allowed_private_target(edge: ImportEdge, config: dict[str, Any]) -> bool:
    if not policy_enabled(config):
        return False
    return any(
        matches_prefix(edge.target, prefix)
        for prefix in config.get('policy', {}).get(
            'allowed_private_target_prefixes', []
        )
    )


def is_boundary_helper_edge(edge: ImportEdge, config: dict[str, Any]) -> bool:
    if not policy_enabled(config):
        return False
    if is_forbidden_import(edge, config):
        return True
    if is_allowed_import_pair(edge, config):
        return True
    if any(
        matches_prefix(edge.target, prefix)
        for prefix in config.get('policy', {}).get(
            'boundary_helper_target_prefixes', []
        )
    ):
        return True
    return any(
        symbol
        in set(config.get('policy', {}).get('boundary_helper_symbols', []))
        for symbol in edge.imported
    )


def graph_edge_kind(
    edge: ImportEdge, config: dict[str, Any], result: AnalysisResult
) -> str:
    if not policy_enabled(config):
        return 'normal'
    if is_forbidden_import(edge, config):
        return 'forbidden'
    if is_allowed_import_pair(edge, config):
        return 'exception'
    if is_allowed_private_target(edge, config):
        return 'normal'
    if policy_area(edge.source, config, result) != policy_area(
        edge.target, config, result
    ) and (
        has_private_module_segment(edge.target) or bool(private_symbols(edge))
    ):
        return 'cross_private'
    if has_private_module_segment(edge.target) or bool(private_symbols(edge)):
        return 'private'
    return 'normal'


def evaluate_policy(
    result: AnalysisResult, config: dict[str, Any]
) -> list[PolicyFinding]:
    if not policy_enabled(config):
        return []
    findings: list[PolicyFinding] = []
    for edge in result.edges:
        if is_forbidden_import(edge, config):
            findings.append(
                PolicyFinding(
                    finding_type='forbidden_import',
                    severity='error',
                    source=edge.source,
                    target=edge.target,
                    line=edge.line,
                    source_file=edge.source_file,
                    imported=edge.imported,
                    message='Import violates configured architectural direction.',
                )
            )
        elif is_allowed_import_pair(edge, config):
            findings.append(
                PolicyFinding(
                    finding_type='allowed_exception',
                    severity='info',
                    source=edge.source,
                    target=edge.target,
                    line=edge.line,
                    source_file=edge.source_file,
                    imported=edge.imported,
                    message='Import is explicitly allowed as an architectural exception.',
                )
            )

        if policy_area(edge.source, config, result) != policy_area(
            edge.target, config, result
        ) and (
            has_private_module_segment(edge.target)
            or bool(private_symbols(edge))
        ):
            findings.append(
                PolicyFinding(
                    finding_type='cross_area_private_import',
                    severity='warning',
                    source=edge.source,
                    target=edge.target,
                    line=edge.line,
                    source_file=edge.source_file,
                    imported=edge.imported,
                    message='Cross-area private import crosses a configured boundary.',
                )
            )

        if is_boundary_helper_edge(edge, config):
            findings.append(
                PolicyFinding(
                    finding_type='boundary_helper',
                    severity='warning',
                    source=edge.source,
                    target=edge.target,
                    line=edge.line,
                    source_file=edge.source_file,
                    imported=edge.imported,
                    message='Boundary/helper candidate edge for cleanup review.',
                )
            )
    return findings


def findings_summary(findings: list[PolicyFinding]) -> dict[str, int]:
    out: dict[str, int] = {}
    for finding in findings:
        out[finding.finding_type] = out.get(finding.finding_type, 0) + 1
    return out


def snapshot_payload(
    result: AnalysisResult,
    config: dict[str, Any],
    findings: list[PolicyFinding],
    profile_name: str,
) -> dict[str, Any]:
    return {
        'analysis': result.to_dict(),
        'config': json.loads(json.dumps(config)),
        'profile': profile_name,
        'findings': [finding.to_dict() for finding in findings],
        'finding_counts': findings_summary(findings),
    }
