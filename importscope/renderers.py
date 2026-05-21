from __future__ import annotations

import re
import csv
import json
import shutil
from typing import Any
from pathlib import Path
import subprocess
from collections import defaultdict
from collections.abc import Callable, Iterable

from .model import ImportEdge, PolicyFinding, AnalysisResult
from .policy import (
    group_order,
    policy_area,
    graph_edge_kind,
    private_symbols,
    findings_summary,
    display_group_key,
    module_cluster_key,
    display_group_style,
    module_cluster_label,
    module_cluster_style,
    package_group_identifier,
    package_name_from_config,
    has_private_module_segment,
)


EDGE_STYLES = {
    'normal': {
        'color': '#64748b',
        'width': '1',
        'dash': '',
        'dot_style': 'solid',
    },
    'private': {
        'color': '#64748b',
        'width': '1.5',
        'dash': '5 4',
        'dot_style': 'dashed',
    },
    'cross_private': {
        'color': '#dc2626',
        'width': '2',
        'dash': '6 4',
        'dot_style': 'dashed',
    },
    'forbidden': {
        'color': '#991b1b',
        'width': '2.5',
        'dash': '3 3',
        'dot_style': 'bold,dashed',
    },
    'exception': {
        'color': '#7c3aed',
        'width': '1.8',
        'dash': '6 3',
        'dot_style': 'dashed',
    },
}

LOAD_STYLES = {
    'eager': {
        'label': '',
        'mermaid_dash': '',
        'dot_style': '',
        'penwidth_add': 0.0,
    },
    'lazy_local': {
        'label': '',
        'mermaid_dash': '2 6',
        'dot_style': 'dotted',
        'penwidth_add': 0.2,
    },
    'lazy_dynamic': {
        'label': 'dynamic',
        'mermaid_dash': '1 5',
        'dot_style': 'dotted',
        'penwidth_add': 0.4,
    },
}

HIGHLIGHT_STYLE = {
    'color': '#ea580c',
    'fontcolor': '#9a3412',
    'penwidth': '2.8',
    'dot_style': 'bold',
}


def is_policy_edge(
    edge: ImportEdge, config: dict[str, Any], result: AnalysisResult
) -> bool:
    return graph_edge_kind(edge, config, result) != 'normal'


def mermaid_id(label: str) -> str:
    safe = re.sub(r'[^0-9a-zA-Z_]', '_', label)
    if re.match(r'^\d', safe):
        safe = '_' + safe
    return safe


def mermaid_label(label: str) -> str:
    return label.replace('\\', '\\\\').replace('"', '\\"')


def dot_label(label: str) -> str:
    return label.replace('\\', '\\\\').replace('"', '\\"')


def dot_node_line(
    node: str,
    *,
    label: str,
    fill: str,
    stroke: str,
    highlighted: bool = False,
    indent: str = '',
) -> str:
    attrs = [
        f'label="{dot_label(label)}"',
        f'fillcolor="{fill}"',
        f'color="{HIGHLIGHT_STYLE["color"] if highlighted else stroke}"',
    ]
    if highlighted:
        attrs.append(f'penwidth="{HIGHLIGHT_STYLE["penwidth"]}"')
        attrs.append(f'fontcolor="{HIGHLIGHT_STYLE["fontcolor"]}"')
    return f'{indent}"{dot_label(node)}" [{", ".join(attrs)}];'


def module_graph_header(
    *, package_level: bool = False, labeled: bool = False
) -> str:
    if package_level:
        return (
            '  graph [rankdir="TB", bgcolor="white", compound=true, splines=spline, '
            'pad=0.25, nodesep=0.3, ranksep=0.9, ratio="compress"];'
        )
    if labeled:
        return (
            '  graph [rankdir="TB", bgcolor="white", compound=true, splines=spline, '
            'pad=0.3, nodesep=0.25, ranksep=1.5, ratio="compress"];'
        )
    return (
        '  graph [rankdir="TB", bgcolor="white", compound=true, splines=spline, '
        'pad=0.25, nodesep=0.3, ranksep=0.95, ratio="compress"];'
    )


def inventory_graph_header() -> str:
    return (
        '  graph [rankdir="TB", bgcolor="white", compound=true, splines=false, '
        'pad=0.15, nodesep=0.18, ranksep=0.45, ratio="compress"];'
    )


def short_label(symbols: Iterable[str], max_chars: int = 48) -> str:
    items = [item for item in sorted(set(symbols)) if item]
    if not items:
        return ''
    text = ', '.join(items)
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 1] + '…'


def wrapped_short_label(
    symbols: Iterable[str], max_chars: int = 42, max_lines: int = 3
) -> str:
    items = [item for item in sorted(set(symbols)) if item]
    if not items:
        return ''
    lines: list[str] = []
    current = ''
    used_items = 0
    for item in items:
        part = item if not current else f'{current}, {item}'
        if len(part) <= max_chars:
            current = part
            used_items += 1
            continue
        if current:
            lines.append(current)
        current = item
        used_items = min(used_items + 1, len(items))
        if len(lines) >= max_lines - 1:
            break
    if current and len(lines) < max_lines:
        lines.append(current)
    if used_items < len(items):
        lines[-1] = lines[-1] + ', …'
    return '\\n'.join(lines[:max_lines])


def combine_edge_kinds(kinds: set[str]) -> str:
    for kind in [
        'forbidden',
        'exception',
        'cross_private',
        'private',
        'normal',
    ]:
        if kind in kinds:
            return kind
    return 'normal'


def merge_dot_styles(*styles: str) -> str:
    out: list[str] = []
    for style in styles:
        for part in style.split(','):
            item = part.strip()
            if item and item not in out:
                out.append(item)
    return ','.join(out) if out else 'solid'


def edge_load_label(lazy_kind: str) -> str:
    return str(LOAD_STYLES[lazy_kind]['label'])


def aggregate_edges_styled(
    edges: Iterable[ImportEdge],
    *,
    config: dict[str, Any],
    result: AnalysisResult,
    source_transform: Callable[[str], str] = lambda x: x,
    target_transform: Callable[[str], str] = lambda x: x,
    skip_self: bool = False,
) -> dict[tuple[str, str, str], dict[str, object]]:
    agg: dict[tuple[str, str, str], dict[str, object]] = {}
    for edge in edges:
        src = source_transform(edge.source)
        tgt = target_transform(edge.target)
        if skip_self and src == tgt:
            continue
        key = (src, tgt, edge.lazy_kind)
        if key not in agg:
            agg[key] = {'symbols': set(), 'kinds': set(), 'count': 0}
        symbols: set[str] = agg[key]['symbols']  # type: ignore[assignment]
        kinds: set[str] = agg[key]['kinds']  # type: ignore[assignment]
        symbols.update(edge.imported if edge.imported else ('',))
        kinds.add(graph_edge_kind(edge, config, result))
        agg[key]['count'] = int(agg[key]['count']) + 1
    return agg


def grouped_nodes(
    nodes: Iterable[str], config: dict[str, Any], result: AnalysisResult
) -> dict[str, list[str]]:
    groups: dict[str, list[str]] = defaultdict(list)
    for node in sorted(nodes):
        groups[display_group_key(node, config, result)].append(node)
    return groups


def grouped_module_nodes(
    nodes: Iterable[str], config: dict[str, Any], result: AnalysisResult
) -> dict[str, list[str]]:
    groups: dict[str, list[str]] = defaultdict(list)
    for node in sorted(nodes):
        groups[module_cluster_key(node, config, result)].append(node)
    return groups


def identity_groups(nodes: Iterable[str]) -> dict[str, list[str]]:
    groups: dict[str, list[str]] = defaultdict(list)
    for node in sorted(nodes):
        groups[node].append(node)
    return groups


def module_cluster_parent(cluster_key: str, known_keys: set[str]) -> str | None:
    parts = cluster_key.split('.')
    for size in range(len(parts) - 1, 0, -1):
        candidate = '.'.join(parts[:size])
        if candidate in known_keys:
            return candidate
    return None


def module_cluster_tree(
    cluster_keys: Iterable[str],
    package_name: str | None,
) -> tuple[set[str], dict[str | None, list[str]]]:
    all_keys: set[str] = set()
    for key in cluster_keys:
        parts = key.split('.')
        stop = 0
        if package_name:
            stop = len(package_name.split('.'))
        for size in range(len(parts), stop, -1):
            candidate = '.'.join(parts[:size])
            if candidate != package_name:
                all_keys.add(candidate)

    children: dict[str | None, list[str]] = defaultdict(list)
    for key in sorted(all_keys):
        children[module_cluster_parent(key, all_keys)].append(key)
    return all_keys, children


def collapse_leaf_cluster(
    key: str,
    groups: dict[str, list[str]],
    children: dict[str | None, list[str]],
) -> bool:
    return groups.get(key, []) == [key] and not children.get(key)


def render_svg(dot_file: Path) -> None:
    dot = shutil.which('dot')
    if dot is None:
        raise RuntimeError('Graphviz dot not found on PATH')

    dot_file = dot_file.resolve()
    svg_file = dot_file.with_suffix('.svg')
    commands = [
        [dot, '-Gsplines=spline', '-Tsvg', str(dot_file), '-o', str(svg_file)],
        [dot, '-Gsplines=curved', '-Tsvg', str(dot_file), '-o', str(svg_file)],
        [
            dot,
            '-Gsplines=polyline',
            '-Tsvg',
            str(dot_file),
            '-o',
            str(svg_file),
        ],
        [dot, '-Gsplines=false', '-Tsvg', str(dot_file), '-o', str(svg_file)],
    ]
    last_error = ''
    for cmd in commands:
        try:
            subprocess.run(cmd, check=True, capture_output=True, text=True)
            return
        except subprocess.CalledProcessError as err:
            last_error = err.stderr.strip()
    raise RuntimeError(f'Could not render {dot_file.name} to SVG: {last_error}')


def write_import_edges_csv(
    edges: list[ImportEdge],
    out: Path,
    config: dict[str, Any],
    result: AnalysisResult,
) -> None:
    with out.open('w', newline='', encoding='utf-8') as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=[
                'source',
                'target',
                'imported',
                'import_type',
                'lazy_kind',
                'line',
                'source_file',
                'source_area',
                'target_area',
                'target_has_private_segment',
                'private_symbols',
                'cross_area_private_import',
                'excluded_from_cycles',
            ],
        )
        writer.writeheader()
        for edge in edges:
            writer.writerow(
                {
                    'source': edge.source,
                    'target': edge.target,
                    'imported': ';'.join(edge.imported),
                    'import_type': edge.import_type,
                    'lazy_kind': edge.lazy_kind,
                    'line': edge.line,
                    'source_file': edge.source_file,
                    'source_area': policy_area(edge.source, config, result),
                    'target_area': policy_area(edge.target, config, result),
                    'target_has_private_segment': has_private_module_segment(
                        edge.target
                    ),
                    'private_symbols': ';'.join(private_symbols(edge)),
                    'cross_area_private_import': (
                        policy_area(edge.source, config, result)
                        != policy_area(edge.target, config, result)
                        and (
                            has_private_module_segment(edge.target)
                            or bool(private_symbols(edge))
                        )
                    ),
                    'excluded_from_cycles': edge.lazy_kind == 'lazy_dynamic',
                }
            )


def write_private_imports_csv(
    edges: list[ImportEdge],
    out: Path,
    config: dict[str, Any],
    result: AnalysisResult,
) -> None:
    rows = [
        edge
        for edge in edges
        if has_private_module_segment(edge.target) or private_symbols(edge)
    ]
    with out.open('w', newline='', encoding='utf-8') as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=[
                'source',
                'target',
                'imported',
                'lazy_kind',
                'line',
                'source_area',
                'target_area',
                'cross_area_private_import',
            ],
        )
        writer.writeheader()
        for edge in rows:
            writer.writerow(
                {
                    'source': edge.source,
                    'target': edge.target,
                    'imported': ';'.join(edge.imported),
                    'lazy_kind': edge.lazy_kind,
                    'line': edge.line,
                    'source_area': policy_area(edge.source, config, result),
                    'target_area': policy_area(edge.target, config, result),
                    'cross_area_private_import': (
                        policy_area(edge.source, config, result)
                        != policy_area(edge.target, config, result)
                        and (
                            has_private_module_segment(edge.target)
                            or bool(private_symbols(edge))
                        )
                    ),
                }
            )


def write_module_symbols_csv(result: AnalysisResult, out: Path) -> None:
    with out.open('w', newline='', encoding='utf-8') as fh:
        writer = csv.DictWriter(
            fh, fieldnames=['module', 'symbol', 'is_private', 'file']
        )
        writer.writeheader()
        for module, info in sorted(result.modules.items()):
            for symbol in sorted(info.definitions):
                writer.writerow(
                    {
                        'module': module,
                        'symbol': symbol,
                        'is_private': symbol.startswith('_'),
                        'file': str(info.path),
                    }
                )


def write_cycles_csv(result: AnalysisResult, out: Path) -> None:
    with out.open('w', newline='', encoding='utf-8') as fh:
        writer = csv.DictWriter(fh, fieldnames=['component', 'module'])
        writer.writeheader()
        for index, component in enumerate(result.cycles, start=1):
            for module in component:
                writer.writerow({'component': index, 'module': module})


def write_findings_csv(findings: list[PolicyFinding], out: Path) -> None:
    with out.open('w', newline='', encoding='utf-8') as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=[
                'finding_type',
                'severity',
                'source',
                'target',
                'line',
                'source_file',
                'imported',
                'message',
            ],
        )
        writer.writeheader()
        for finding in findings:
            writer.writerow(
                {
                    'finding_type': finding.finding_type,
                    'severity': finding.severity,
                    'source': finding.source,
                    'target': finding.target,
                    'line': finding.line,
                    'source_file': finding.source_file,
                    'imported': ';'.join(finding.imported),
                    'message': finding.message,
                }
            )


def write_snapshot_json(payload: dict[str, Any], out: Path) -> None:
    out.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + '\n', encoding='utf-8'
    )


def write_mermaid_graph(
    edges: list[ImportEdge],
    out: Path,
    config: dict[str, Any],
    result: AnalysisResult,
    *,
    title: str,
    labeled: bool = False,
    package_level: bool = False,
    filter_fn: Callable[[ImportEdge], bool] | None = None,
) -> bool:
    edge_list = list(edges)
    if filter_fn is not None:
        edge_list = [edge for edge in edge_list if filter_fn(edge)]
    if package_level:
        agg = aggregate_edges_styled(
            edge_list,
            config=config,
            result=result,
            source_transform=lambda module: package_group_identifier(
                module, config, result
            ),
            target_transform=lambda module: package_group_identifier(
                module, config, result
            ),
            skip_self=True,
        )
    else:
        agg = aggregate_edges_styled(edge_list, config=config, result=result)

    if not agg:
        return False

    nodes = sorted({node for src, tgt, _ in agg for node in (src, tgt)})
    groups = (
        grouped_module_nodes(nodes, config, result)
        if not package_level
        else identity_groups(nodes)
    )

    lines = [
        'flowchart LR',
        f'  %% {title}',
        '  %% A --> B means A imports/depends on B',
        '',
    ]

    if package_level:
        package_name = package_name_from_config(config, result)
        _, children = module_cluster_tree(nodes, package_name)

        if package_name and package_name in groups:
            lines.append(
                f'  {mermaid_id(package_name)}["{mermaid_label(package_name)}"]'
            )
            lines.append('')

        def emit_package_cluster(key: str, indent: str) -> None:
            label = module_cluster_label(key, config, result)
            if collapse_leaf_cluster(key, groups, children):
                lines.append(
                    f'{indent}{mermaid_id(key)}["{mermaid_label(key)}"]'
                )
                lines.append('')
                return
            lines.append(
                f'{indent}subgraph cluster_{mermaid_id(key)}["{mermaid_label(label)}"]'
            )
            lines.append(f'{indent}  direction TB')
            for node in groups.get(key, []):
                lines.append(
                    f'{indent}  {mermaid_id(node)}["{mermaid_label(node)}"]'
                )
            for child_key in children.get(key, []):
                emit_package_cluster(child_key, indent + '  ')
            lines.append(f'{indent}end')
            lines.append('')

        for root_key in children.get(None, []):
            emit_package_cluster(root_key, '  ')
    else:
        for group in group_order(config, result):
            key = str(group.get('name'))
            group_nodes = groups.get(key, [])
            if not group_nodes:
                continue
            if group_nodes == [key]:
                lines.append(f'  {mermaid_id(key)}["{mermaid_label(key)}"]')
                lines.append('')
                continue
            label = module_cluster_label(key, config, result)
            lines.append(
                f'  subgraph cluster_{mermaid_id(key)}["{mermaid_label(label)}"]'
            )
            lines.append('    direction TB')
            for node in group_nodes:
                lines.append(f'    {mermaid_id(node)}["{mermaid_label(node)}"]')
            lines.append('  end')
            lines.append('')

    link_styles: list[str] = []
    edge_index = 0
    for (src, tgt, lazy_kind), payload in sorted(agg.items()):
        symbols: set[str] = payload['symbols']  # type: ignore[assignment]
        kinds: set[str] = payload['kinds']  # type: ignore[assignment]
        count = int(payload['count'])
        kind = combine_edge_kinds(kinds)
        style = EDGE_STYLES[kind]
        load_style = LOAD_STYLES[lazy_kind]

        if labeled:
            label = (
                short_label(symbols)
                or f'{count} import{"s" if count != 1 else ""}'
            )
        elif package_level:
            label = f'{count} edge{"s" if count != 1 else ""}'
        else:
            label = ''
        lazy_label = edge_load_label(lazy_kind)
        if lazy_label:
            label = f'{label} [{lazy_label}]'.strip() if label else lazy_label

        src_id = mermaid_id(src)
        tgt_id = mermaid_id(tgt)
        if label:
            lines.append(f'  {src_id} -->|"{mermaid_label(label)}"| {tgt_id}')
        else:
            lines.append(f'  {src_id} --> {tgt_id}')
        if kind != 'normal' or lazy_kind != 'eager':
            dash = load_style['mermaid_dash'] or style['dash']
            dash_part = f',stroke-dasharray:{dash}' if dash else ''
            link_styles.append(
                f'  linkStyle {edge_index} '
                f'stroke:{style["color"]},stroke-width:{float(style["width"]) + float(load_style["penwidth_add"])}px{dash_part};'
            )
        edge_index += 1

    lines.append('')
    for node in nodes:
        style = (
            module_cluster_style(node, config, result)
            if package_level
            else module_cluster_style(
                display_group_key(node, config, result), config, result
            )
        )
        lines.append(f'  class {mermaid_id(node)} {style["class"]};')

    style_groups = (
        [{'name': key} for key in sorted(groups)]
        if package_level
        else [{'name': key} for key in sorted(groups)]
    )
    seen_style_groups: set[str] = set()
    for group in style_groups:
        if str(group.get('name')) in seen_style_groups:
            continue
        seen_style_groups.add(str(group.get('name')))
        style = (
            module_cluster_style(str(group.get('name')), config, result)
            if package_level
            else module_cluster_style(str(group.get('name')), config, result)
        )
        lines.append(
            f'  classDef {style["class"]} '
            f'fill:{style["fill"]},stroke:{style["stroke"]},stroke-width:1px,color:#111827;'
        )
    if link_styles:
        lines.append('')
        lines.extend(link_styles)
    out.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    return True


def write_dot_graph(
    edges: list[ImportEdge],
    out: Path,
    config: dict[str, Any],
    result: AnalysisResult,
    *,
    labeled: bool = False,
    package_level: bool = False,
    filter_fn: Callable[[ImportEdge], bool] | None = None,
    highlight_nodes: set[str] | None = None,
    highlight_edges: set[tuple[str, str]] | None = None,
) -> bool:
    edge_list = list(edges)
    if filter_fn is not None:
        edge_list = [edge for edge in edge_list if filter_fn(edge)]
    highlight_nodes = highlight_nodes or set()
    highlight_edges = highlight_edges or set()

    if package_level:
        agg = aggregate_edges_styled(
            edge_list,
            config=config,
            result=result,
            source_transform=lambda module: package_group_identifier(
                module, config, result
            ),
            target_transform=lambda module: package_group_identifier(
                module, config, result
            ),
            skip_self=True,
        )
        nodes = sorted({node for src, tgt, _ in agg for node in (src, tgt)})
        groups = identity_groups(nodes)
    else:
        agg = aggregate_edges_styled(edge_list, config=config, result=result)
        nodes = sorted({node for src, tgt, _ in agg for node in (src, tgt)})
        groups = grouped_module_nodes(nodes, config, result)

    if not agg:
        return False

    lines = [
        'digraph G {',
        module_graph_header(package_level=package_level, labeled=labeled),
        '  node [shape="box", style="rounded,filled", fontname="Helvetica", fontsize=10, color="#64748b", fillcolor="white"];',
        '  edge [fontname="Helvetica", fontsize=9, color="#64748b", arrowsize=0.7];',
        '',
    ]

    if package_level:
        package_name = package_name_from_config(config, result)
        _, children = module_cluster_tree(nodes, package_name)

        if package_name and package_name in groups:
            root_style = display_group_style(
                display_group_key(package_name, config, result), config, result
            )
            lines.append(
                dot_node_line(
                    package_name,
                    label=package_name,
                    fill='white',
                    stroke=root_style['stroke'],
                    highlighted=package_name in highlight_nodes,
                    indent='  ',
                )
            )
            lines.append('')

        def emit_package_cluster(key: str, indent: int) -> None:
            prefix = ' ' * indent
            style = module_cluster_style(key, config, result)
            label = module_cluster_label(key, config, result)
            if collapse_leaf_cluster(key, groups, children):
                lines.append(
                    dot_node_line(
                        key,
                        label=key,
                        fill=style['fill'],
                        stroke=style['stroke'],
                        highlighted=key in highlight_nodes,
                        indent=prefix,
                    )
                )
                lines.append('')
                return
            lines.extend(
                [
                    f'{prefix}subgraph cluster_{style["class"]} {{',
                    f'{prefix}  label="{dot_label(label)}";',
                    f'{prefix}  style="rounded,filled";',
                    f'{prefix}  color="{style["stroke"]}";',
                    f'{prefix}  fillcolor="{style["fill"]}";',
                    f'{prefix}  penwidth=1.2;',
                    f'{prefix}  fontname="Helvetica-Bold";',
                    f'{prefix}  fontsize=12;',
                    '',
                ]
            )
            for node in groups.get(key, []):
                lines.append(
                    dot_node_line(
                        node,
                        label=node,
                        fill=style['fill'],
                        stroke=style['stroke'],
                        highlighted=node in highlight_nodes,
                        indent=f'{prefix}  ',
                    )
                )
            if groups.get(key):
                lines.append('')
            for child_key in children.get(key, []):
                emit_package_cluster(child_key, indent + 2)
            lines.extend([f'{prefix}}}', ''])

        for root_key in children.get(None, []):
            emit_package_cluster(root_key, 2)
    else:
        package_name = package_name_from_config(config, result)
        _, children = module_cluster_tree(groups, package_name)

        if package_name and package_name in groups:
            root_style = display_group_style(
                display_group_key(package_name, config, result), config, result
            )
            for node in groups[package_name]:
                lines.append(
                    dot_node_line(
                        node,
                        label=node,
                        fill='white',
                        stroke=root_style['stroke'],
                        highlighted=node in highlight_nodes,
                        indent='  ',
                    )
                )
            lines.append('')

        def emit_cluster(key: str, indent: int) -> None:
            prefix = ' ' * indent
            style = module_cluster_style(key, config, result)
            label = module_cluster_label(key, config, result)
            if collapse_leaf_cluster(key, groups, children):
                lines.append(
                    dot_node_line(
                        key,
                        label=label,
                        fill=style['fill'],
                        stroke=style['stroke'],
                        highlighted=key in highlight_nodes,
                        indent=prefix,
                    )
                )
                lines.append('')
                return
            lines.extend(
                [
                    f'{prefix}subgraph cluster_{style["class"]} {{',
                    f'{prefix}  label="{dot_label(label)}";',
                    f'{prefix}  style="rounded,filled";',
                    f'{prefix}  color="{style["stroke"]}";',
                    f'{prefix}  fillcolor="{style["fill"]}";',
                    f'{prefix}  penwidth=1.2;',
                    f'{prefix}  fontname="Helvetica-Bold";',
                    f'{prefix}  fontsize=12;',
                    '',
                ]
            )
            for node in groups.get(key, []):
                lines.append(
                    dot_node_line(
                        node,
                        label=node,
                        fill=style['fill'],
                        stroke=style['stroke'],
                        highlighted=node in highlight_nodes,
                        indent=f'{prefix}  ',
                    )
                )
            if groups.get(key):
                lines.append('')
            for child_key in children.get(key, []):
                emit_cluster(child_key, indent + 2)
            lines.extend([f'{prefix}}}', ''])

        for root_key in children.get(None, []):
            emit_cluster(root_key, 2)

    for (src, tgt, lazy_kind), payload in sorted(agg.items()):
        symbols: set[str] = payload['symbols']  # type: ignore[assignment]
        kinds: set[str] = payload['kinds']  # type: ignore[assignment]
        count = int(payload['count'])
        kind = combine_edge_kinds(kinds)
        style = EDGE_STYLES[kind]
        load_style = LOAD_STYLES[lazy_kind]
        attrs = [
            f'color="{style["color"]}"',
            f'penwidth="{float(style["width"]) + float(load_style["penwidth_add"])}"',
            f'style="{merge_dot_styles(str(style["dot_style"]), str(load_style["dot_style"]))}"',
        ]
        if (src, tgt) in highlight_edges:
            attrs = [
                f'color="{HIGHLIGHT_STYLE["color"]}"',
                f'fontcolor="{HIGHLIGHT_STYLE["fontcolor"]}"',
                f'penwidth="{float(style["width"]) + float(load_style["penwidth_add"]) + 1.4}"',
                f'style="{merge_dot_styles(str(style["dot_style"]), str(load_style["dot_style"]), str(HIGHLIGHT_STYLE["dot_style"]))}"',
            ]
        if labeled:
            label = (
                wrapped_short_label(symbols, max_chars=24, max_lines=2)
                or f'{count} import{"s" if count != 1 else ""}'
            )
        elif package_level:
            label = f'{count} edge{"" if count == 1 else "s"}'
        else:
            label = ''
        lazy_label = edge_load_label(lazy_kind)
        if lazy_label:
            label = f'{label} [{lazy_label}]'.strip() if label else lazy_label
        if label:
            attrs.append(f'label="{dot_label(label)}"')
        lines.append(
            f'  "{dot_label(src)}" -> "{dot_label(tgt)}" [{", ".join(attrs)}];'
        )

    lines.append('}')
    out.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    return True


def write_module_inventory_mermaid(
    out: Path,
    config: dict[str, Any],
    result: AnalysisResult,
) -> bool:
    nodes = sorted(result.modules)
    if not nodes:
        return False

    groups = identity_groups(nodes)
    package_name = package_name_from_config(config, result)
    _, children = module_cluster_tree(nodes, package_name)
    lines = [
        'flowchart TD',
        '  %% Module inventory graph',
        '  %% Boxes show the package/module hierarchy without import arrows.',
        '',
    ]

    def emit_cluster(key: str, indent: str) -> None:
        label = module_cluster_label(key, config, result)
        if collapse_leaf_cluster(key, groups, children):
            lines.append(f'{indent}{mermaid_id(key)}["{mermaid_label(key)}"]')
            return
        lines.append(
            f'{indent}subgraph cluster_{mermaid_id(key)}["{mermaid_label(label)}"]'
        )
        lines.append(f'{indent}  direction TB')
        if groups.get(key):
            lines.append(f'{indent}  {mermaid_id(key)}["{mermaid_label(key)}"]')
        child_keys = children.get(key, [])
        leaf_children = [
            child_key
            for child_key in child_keys
            if collapse_leaf_cluster(child_key, groups, children)
        ]
        nested_children = [
            child_key
            for child_key in child_keys
            if child_key not in leaf_children
        ]
        if len(leaf_children) > 1:
            lines.append(
                f'{indent}  subgraph cluster_{mermaid_id(key)}__modules["{mermaid_label(key + " modules")}"]'
            )
            lines.append(f'{indent}    direction TB')
            for child_key in leaf_children:
                emit_cluster(child_key, indent + '    ')
            lines.append(f'{indent}  end')
        else:
            for child_key in leaf_children:
                emit_cluster(child_key, indent + '  ')
        for child_key in nested_children:
            emit_cluster(child_key, indent + '  ')
        lines.append(f'{indent}end')

    root_keys = children.get(None, [])
    if package_name:
        lines.append(
            f'  subgraph cluster_{mermaid_id(package_name)}["{mermaid_label(package_name)}"]'
        )
        lines.append('    direction TB')
        if package_name in groups:
            lines.append(
                f'    {mermaid_id(package_name)}["{mermaid_label(package_name)}"]'
            )
        for root_key in root_keys:
            emit_cluster(root_key, '    ')
        lines.append('  end')
        lines.append('')
    else:
        for root_key in root_keys:
            emit_cluster(root_key, '  ')
            lines.append('')

    seen_styles: set[str] = set()
    for node in nodes:
        style = module_cluster_style(node, config, result)
        lines.append(f'  class {mermaid_id(node)} {style["class"]};')
        if style['class'] in seen_styles:
            continue
        seen_styles.add(style['class'])
        lines.append(
            f'  classDef {style["class"]} '
            f'fill:{style["fill"]},stroke:{style["stroke"]},stroke-width:1px,color:#111827;'
        )

    out.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    return True


def write_module_inventory_dot(
    out: Path,
    config: dict[str, Any],
    result: AnalysisResult,
) -> bool:
    nodes = sorted(result.modules)
    if not nodes:
        return False

    groups = identity_groups(nodes)
    package_name = package_name_from_config(config, result)
    _, children = module_cluster_tree(nodes, package_name)
    lines = [
        'digraph G {',
        inventory_graph_header(),
        '  node [shape="box", style="rounded,filled", fontname="Helvetica", fontsize=10, color="#64748b", fillcolor="white"];',
        '  edge [style="invis"];',
        '',
    ]

    def emit_cluster(key: str, indent: int) -> None:
        prefix = ' ' * indent
        style = module_cluster_style(key, config, result)
        label = module_cluster_label(key, config, result)
        if collapse_leaf_cluster(key, groups, children):
            lines.append(
                f'{prefix}"{dot_label(key)}" [label="{dot_label(key)}", fillcolor="{style["fill"]}", color="{style["stroke"]}"];'
            )
            lines.append('')
            return
        lines.extend(
            [
                f'{prefix}subgraph cluster_{style["class"]} {{',
                f'{prefix}  label="{dot_label(label)}";',
                f'{prefix}  style="rounded,filled";',
                f'{prefix}  color="{style["stroke"]}";',
                f'{prefix}  fillcolor="{style["fill"]}";',
                f'{prefix}  penwidth=1.2;',
                f'{prefix}  fontname="Helvetica-Bold";',
                f'{prefix}  fontsize=12;',
                '',
            ]
        )
        if groups.get(key):
            lines.append(
                f'{prefix}  "{dot_label(key)}" [label="{dot_label(key)}", fillcolor="{style["fill"]}", color="{style["stroke"]}"];'
            )
            lines.append('')
        child_keys = children.get(key, [])
        leaf_children = [
            child_key
            for child_key in child_keys
            if collapse_leaf_cluster(child_key, groups, children)
        ]
        nested_children = [
            child_key
            for child_key in child_keys
            if child_key not in leaf_children
        ]
        if len(leaf_children) > 1:
            module_box_label = f'{key} modules'
            lines.extend(
                [
                    f'{prefix}  subgraph cluster_{mermaid_id(key)}__modules {{',
                    f'{prefix}    label="{dot_label(module_box_label)}";',
                    f'{prefix}    style="rounded,dashed";',
                    f'{prefix}    color="{style["stroke"]}";',
                    f'{prefix}    fillcolor="{style["fill"]}";',
                    f'{prefix}    penwidth=1.0;',
                    '',
                ]
            )
            for child_key in leaf_children:
                emit_cluster(child_key, indent + 4)
            for left, right in zip(
                leaf_children, leaf_children[1:], strict=False
            ):
                lines.append(
                    f'{prefix}    "{dot_label(left)}" -> "{dot_label(right)}" [style="invis", weight="25"];'
                )
            lines.extend([f'{prefix}  }}', ''])
        else:
            for child_key in leaf_children:
                emit_cluster(child_key, indent + 2)
        for child_key in nested_children:
            emit_cluster(child_key, indent + 2)
        for left, right in zip(
            nested_children, nested_children[1:], strict=False
        ):
            lines.append(
                f'{prefix}  "{dot_label(left)}" -> "{dot_label(right)}" [style="invis", weight="20"];'
            )
        lines.extend([f'{prefix}}}', ''])

    root_keys = children.get(None, [])
    if package_name:
        root_style = display_group_style(
            display_group_key(package_name, config, result), config, result
        )
        lines.extend(
            [
                f'  subgraph cluster_{mermaid_id(package_name)} {{',
                f'    label="{dot_label(package_name)}";',
                '    style="rounded,filled";',
                f'    color="{root_style["stroke"]}";',
                '    fillcolor="white";',
                '    penwidth=1.2;',
                '    fontname="Helvetica-Bold";',
                '    fontsize=12;',
                '',
            ]
        )
        if package_name in groups:
            lines.append(
                f'    "{dot_label(package_name)}" [label="{dot_label(package_name)}", fillcolor="white", color="{root_style["stroke"]}"];'
            )
            lines.append('')
        for root_key in root_keys:
            emit_cluster(root_key, 4)
        for left, right in zip(root_keys, root_keys[1:], strict=False):
            lines.append(
                f'    "{dot_label(left)}" -> "{dot_label(right)}" [style="invis", weight="25"];'
            )
        lines.extend(['  }', ''])
    else:
        for root_key in root_keys:
            emit_cluster(root_key, 2)
        for left, right in zip(root_keys, root_keys[1:], strict=False):
            lines.append(
                f'  "{dot_label(left)}" -> "{dot_label(right)}" [style="invis", weight="25"];'
            )

    lines.append('}')
    out.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    return True


def build_symbol_edges(
    edges: list[ImportEdge],
    config: dict[str, Any],
    result: AnalysisResult,
    max_edges: int | None = None,
) -> list[tuple[str, str, str, str, str]]:
    symbol_edges: list[tuple[str, str, str, str, str]] = []
    for edge in edges:
        kind = graph_edge_kind(edge, config, result)
        if not edge.imported:
            symbol_edges.append(
                (edge.source, edge.target, 'module', kind, edge.lazy_kind)
            )
            continue
        for symbol in edge.imported:
            suffix = '::*' if symbol == '*' else f'::{symbol}'
            symbol_edges.append(
                (
                    edge.source,
                    edge.target + suffix,
                    'symbol',
                    kind,
                    edge.lazy_kind,
                )
            )
    symbol_edges = sorted(set(symbol_edges))
    if max_edges is not None and max_edges > 0:
        symbol_edges = symbol_edges[:max_edges]
    return symbol_edges


def write_symbol_import_mermaid(
    edges: list[ImportEdge],
    out: Path,
    config: dict[str, Any],
    result: AnalysisResult,
    *,
    max_edges: int | None = None,
) -> bool:
    symbol_edges = build_symbol_edges(
        edges, config, result, max_edges=max_edges
    )
    if not symbol_edges:
        return False
    module_nodes = sorted({src for src, _, _, _, _ in symbol_edges})
    symbol_nodes = sorted({tgt for _, tgt, _, _, _ in symbol_edges})
    lines = [
        'flowchart LR',
        '  %% Comprehensive symbol-import graph',
        '  %% This is an import graph, not a runtime call graph.',
        '',
        '  subgraph importing_modules["Importing modules"]',
        '    direction TB',
    ]
    for node in module_nodes:
        style = module_cluster_style(
            module_cluster_key(node, config, result), config, result
        )
        lines.append(
            f'    {mermaid_id("module:" + node)}["{mermaid_label(node)}"]'
        )
        lines.append(
            f'    class {mermaid_id("module:" + node)} {style["class"]};'
        )
    lines.extend(
        [
            '  end',
            '',
            '  subgraph imported_symbols["Imported modules/symbols"]',
            '    direction TB',
        ]
    )
    for node in symbol_nodes:
        base = node.split('::', 1)[0]
        style = module_cluster_style(
            module_cluster_key(base, config, result), config, result
        )
        _, _, symbol_name = node.partition('::')
        display = symbol_name if symbol_name else base
        lines.append(
            f'    {mermaid_id("symbol:" + node)}["{mermaid_label(display)}"]'
        )
        lines.append(
            f'    class {mermaid_id("symbol:" + node)} {style["class"]};'
        )
    lines.extend(['  end', ''])
    edge_index = 0
    link_styles: list[str] = []
    for src, tgt, import_kind, edge_kind, lazy_kind in symbol_edges:
        src_id = mermaid_id('module:' + src)
        tgt_id = mermaid_id('symbol:' + tgt)
        style = EDGE_STYLES[edge_kind]
        load_style = LOAD_STYLES[lazy_kind]
        edge_label = edge_load_label(lazy_kind)
        if import_kind == 'symbol' and edge_label:
            lines.append(
                f'  {src_id} -->|"{mermaid_label(edge_label)}"| {tgt_id}'
            )
        else:
            lines.append(f'  {src_id} --> {tgt_id}')
        if edge_kind != 'normal' or lazy_kind != 'eager':
            dash = load_style['mermaid_dash'] or style['dash']
            dash_part = f',stroke-dasharray:{dash}' if dash else ''
            link_styles.append(
                f'  linkStyle {edge_index} stroke:{style["color"]},stroke-width:{float(style["width"]) + float(load_style["penwidth_add"])}px{dash_part};'
            )
        edge_index += 1
    lines.append('')
    style_keys = sorted(
        {module_cluster_key(node, config, result) for node in module_nodes}
    )
    style_keys.extend(
        key
        for key in sorted(
            {
                module_cluster_key(node.split('::', 1)[0], config, result)
                for node in symbol_nodes
            }
        )
        if key not in style_keys
    )
    for key in style_keys:
        style = module_cluster_style(key, config, result)
        lines.append(
            f'  classDef {style["class"]} fill:{style["fill"]},stroke:{style["stroke"]},stroke-width:1px,color:#111827;'
        )
    if link_styles:
        lines.append('')
        lines.extend(link_styles)
    out.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    return True


def write_symbol_import_dot(
    edges: list[ImportEdge],
    out: Path,
    config: dict[str, Any],
    result: AnalysisResult,
    *,
    max_edges: int | None = None,
) -> bool:
    symbol_edges = build_symbol_edges(
        edges, config, result, max_edges=max_edges
    )
    if not symbol_edges:
        return False
    module_nodes = sorted({src for src, _, _, _, _ in symbol_edges})
    symbol_nodes = sorted({tgt for _, tgt, _, _, _ in symbol_edges})
    module_groups = grouped_module_nodes(module_nodes, config, result)
    symbol_groups: dict[str, list[str]] = defaultdict(list)
    for symbol_node in symbol_nodes:
        base = symbol_node.split('::', 1)[0]
        symbol_groups[module_cluster_key(base, config, result)].append(
            symbol_node
        )
    lines = [
        'digraph G {',
        '  graph [rankdir="LR", bgcolor="white", compound=true, splines=spline, pad=0.5, nodesep=0.45, ranksep=2.5, concentrate=false];',
        '  node [shape="box", style="rounded,filled", fontname="Helvetica", fontsize=8, margin="0.04,0.02", color="#64748b", fillcolor="white"];',
        '  edge [fontname="Helvetica", fontsize=7, color="#94a3b8", arrowsize=0.45];',
        '',
        '  subgraph cluster_importing_modules {',
        '    label="Importing modules";',
        '    style="rounded,filled";',
        '    color="#94a3b8";',
        '    fillcolor="#f8fafc";',
        '',
    ]
    package_name = package_name_from_config(config, result)
    _, module_children = module_cluster_tree(module_groups, package_name)

    def emit_module_cluster(key: str, indent: int) -> None:
        prefix = ' ' * indent
        style = module_cluster_style(key, config, result)
        label = module_cluster_label(key, config, result)
        if collapse_leaf_cluster(key, module_groups, module_children):
            node_id = 'module:' + key
            lines.append(
                f'{prefix}"{dot_label(node_id)}" [label="{dot_label(label)}", color="{style["stroke"]}", fillcolor="{style["fill"]}"];'
            )
            return
        lines.extend(
            [
                f'{prefix}subgraph cluster_importing_{style["class"]} {{',
                f'{prefix}  label="{dot_label(label)}";',
                f'{prefix}  style="rounded,filled";',
                f'{prefix}  color="{style["stroke"]}";',
                f'{prefix}  fillcolor="{style["fill"]}";',
            ]
        )
        for node in module_groups.get(key, []):
            node_id = 'module:' + node
            lines.append(
                f'{prefix}  "{dot_label(node_id)}" [label="{dot_label(node)}", color="{style["stroke"]}", fillcolor="{style["fill"]}"];'
            )
        if module_groups.get(key):
            lines.append('')
        for child_key in module_children.get(key, []):
            emit_module_cluster(child_key, indent + 2)
        lines.append(f'{prefix}}}')

    for root_key in module_children.get(None, []):
        emit_module_cluster(root_key, 4)
    lines.extend(
        [
            '  }',
            '',
            '  subgraph cluster_imported_symbols {',
            '    label="Imported modules/symbols";',
            '    style="rounded,filled";',
            '    color="#94a3b8";',
            '    fillcolor="#f8fafc";',
            '',
        ]
    )
    _, symbol_children = module_cluster_tree(symbol_groups, package_name)

    def emit_symbol_cluster(key: str, indent: int) -> None:
        prefix = ' ' * indent
        style = module_cluster_style(key, config, result)
        label = module_cluster_label(key, config, result)
        if collapse_leaf_cluster(key, symbol_groups, symbol_children):
            node = key
            node_id = 'symbol:' + node
            _, _, symbol_name = node.partition('::')
            display = symbol_name if symbol_name else node.split('::', 1)[0]
            lines.append(
                f'{prefix}"{dot_label(node_id)}" [label="{dot_label(display)}", tooltip="{dot_label(node.replace("::", "."))}", color="{style["stroke"]}", fillcolor="{style["fill"]}"];'
            )
            return
        lines.extend(
            [
                f'{prefix}subgraph cluster_symbols_{style["class"]} {{',
                f'{prefix}  label="{dot_label(label)}";',
                f'{prefix}  style="rounded,filled";',
                f'{prefix}  color="{style["stroke"]}";',
                f'{prefix}  fillcolor="{style["fill"]}";',
            ]
        )
        for node in sorted(symbol_groups.get(key, [])):
            node_id = 'symbol:' + node
            _, _, symbol_name = node.partition('::')
            display = symbol_name if symbol_name else node.split('::', 1)[0]
            lines.append(
                f'      "{dot_label(node_id)}" [label="{dot_label(display)}", tooltip="{dot_label(node.replace("::", "."))}", color="{style["stroke"]}", fillcolor="{style["fill"]}"];'
            )
        if symbol_groups.get(key):
            lines.append('')
        for child_key in symbol_children.get(key, []):
            emit_symbol_cluster(child_key, indent + 2)
        lines.append(f'{prefix}}}')

    for root_key in symbol_children.get(None, []):
        emit_symbol_cluster(root_key, 4)
    lines.extend(['  }', ''])
    for src, tgt, _, edge_kind, lazy_kind in symbol_edges:
        src_id = 'module:' + src
        tgt_id = 'symbol:' + tgt
        style = EDGE_STYLES[edge_kind]
        load_style = LOAD_STYLES[lazy_kind]
        attrs = [
            f'color="{style["color"]}55"',
            f'penwidth="{0.8 + float(load_style["penwidth_add"])}"',
            f'style="{merge_dot_styles(str(style["dot_style"]), str(load_style["dot_style"]))}"',
        ]
        edge_label = edge_load_label(lazy_kind)
        if edge_label:
            attrs.append(f'label="{dot_label(edge_label)}"')
        lines.append(
            f'  "{dot_label(src_id)}" -> "{dot_label(tgt_id)}" [{", ".join(attrs)}];'
        )
    lines.append('}')
    out.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    return True


def write_summary_report(
    result: AnalysisResult,
    findings: list[PolicyFinding],
    out: Path,
    config: dict[str, Any],
) -> None:
    private_edges = [
        edge
        for edge in result.edges
        if has_private_module_segment(edge.target) or private_symbols(edge)
    ]
    lazy_local_edges = [
        edge for edge in result.edges if edge.lazy_kind == 'lazy_local'
    ]
    lazy_dynamic_edges = [
        edge for edge in result.edges if edge.lazy_kind == 'lazy_dynamic'
    ]
    boundary_edges = [
        finding
        for finding in findings
        if finding.finding_type == 'boundary_helper'
    ]
    cross_private = [
        finding
        for finding in findings
        if finding.finding_type == 'cross_area_private_import'
    ]
    counts = findings_summary(findings)
    fan_in: dict[str, int] = defaultdict(int)
    fan_out: dict[str, int] = defaultdict(int)
    for edge in result.edges:
        fan_out[edge.source] += 1
        fan_in[edge.target] += 1

    lines = [
        '# Import graph report',
        '',
        f'- Repo: `{result.repo}`',
        f'- Modules parsed: `{len(result.modules)}`',
        f'- Internal import edges: `{len(result.edges)}`',
        f'- Lazy local edges: `{len(lazy_local_edges)}`',
        f'- Lazy dynamic edges: `{len(lazy_dynamic_edges)}`',
        f'- Strongly connected components >1: `{len(result.cycles)}`',
        f'- Private import edges: `{len(private_edges)}`',
        f'- Cross-area private import edges: `{len(cross_private)}`',
        f'- Boundary/helper cleanup candidate edges: `{len(boundary_edges)}`',
        f'- Coverage gaps: `{len(result.coverage_gaps)}`',
        '',
        '## Findings summary',
        '',
    ]
    if not counts:
        lines.append('No policy findings detected.')
    else:
        for key, value in sorted(counts.items()):
            lines.append(f'- `{key}`: `{value}`')

    lines.extend(['', '## Cycles', ''])
    if not result.cycles:
        lines.append('No module-level circular imports detected.')
    else:
        for index, component in enumerate(result.cycles, start=1):
            lines.append(f'### Component {index}')
            for module in component:
                lines.append(f'- `{module}`')
            lines.append('')

    lines.extend(['', '## Cross-area private imports', ''])
    if not cross_private:
        lines.append('No cross-area private imports detected.')
    else:
        for finding in cross_private:
            imported = (
                ', '.join(finding.imported) if finding.imported else '(module)'
            )
            lines.append(
                f'- `{finding.source}` -> `{finding.target}` at line `{finding.line}` importing `{imported}`'
            )

    lines.extend(['', '## Boundary/helper cleanup candidates', ''])
    if not boundary_edges:
        lines.append('No boundary/helper cleanup candidates detected.')
    else:
        for finding in boundary_edges:
            imported = (
                ', '.join(finding.imported) if finding.imported else '(module)'
            )
            lines.append(
                f'- `{finding.source}` -> `{finding.target}` at line `{finding.line}` importing `{imported}`'
            )

    lines.extend(['', '## Hotspots', ''])
    top_fan_in = sorted(fan_in.items(), key=lambda item: (-item[1], item[0]))[
        :5
    ]
    top_fan_out = sorted(fan_out.items(), key=lambda item: (-item[1], item[0]))[
        :5
    ]
    lines.append('### Highest fan-in')
    for module, count in top_fan_in:
        lines.append(f'- `{module}` imported by `{count}` edge(s)')
    lines.append('')
    lines.append('### Highest fan-out')
    for module, count in top_fan_out:
        lines.append(f'- `{module}` imports `{count}` edge(s)')

    if result.coverage_gaps:
        lines.extend(['', '## Coverage gaps', ''])
        for gap in result.coverage_gaps[:10]:
            lines.append(
                f'- `{gap["module"]}` at line `{gap["line"]}`: `{gap["kind"]}`'
            )

    out.write_text('\n'.join(lines) + '\n', encoding='utf-8')
