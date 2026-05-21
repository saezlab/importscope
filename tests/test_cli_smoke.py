from __future__ import annotations

from pathlib import Path

import yaml
from pytest import MonkeyPatch

from importscope.app import (
    edit_config,
    init_config,
    show_config,
    analyze_repo,
    render_snapshot_path_graph,
)
from importscope.cli import build_parser, _path_graph_default_out
from importscope.model import ImportEdge, ModuleInfo, AnalysisResult
from importscope.policy import (
    group_order,
    default_config,
    display_group_key,
    module_cluster_key,
    module_cluster_style,
    package_group_identifier,
)
from importscope.renderers import write_dot_graph, write_symbol_import_dot


def test_analyze_repo_dry_run_uses_default_profile(tmp_path: Path) -> None:
    result = analyze_repo(
        repo=Path.cwd(),
        out=tmp_path,
        dry_run=True,
    )
    assert result['mode'] == 'dry-run'
    assert result['plan']['profile'] == 'overview'


def test_analyze_repo_skips_empty_graph_artifacts(
    tmp_path: Path, monkeypatch: MonkeyPatch
) -> None:
    repo = tmp_path / 'repo'
    package_dir = repo / 'sample'
    package_dir.mkdir(parents=True)
    (package_dir / '__init__.py').write_text('', encoding='utf-8')
    (package_dir / 'solo.py').write_text('VALUE = 1\n', encoding='utf-8')

    rendered: list[str] = []

    def record_render(dot_file: Path) -> None:
        rendered.append(dot_file.name)
        dot_file.with_suffix('.svg').write_text('<svg />\n', encoding='utf-8')

    monkeypatch.setattr('importscope.app.render_svg', record_render)

    out = tmp_path / 'out'
    result = analyze_repo(
        repo=repo,
        out=out,
        package='sample',
        profile='overview',
        formats=['dot', 'mmd', 'svg', 'json', 'csv', 'md'],
        render='both',
    )

    assert result['modules'] == 2
    assert result['edges'] == 0
    assert rendered == ['module_layout_graph.dot']
    assert (out / 'module_layout_graph.dot').exists()
    assert (out / 'module_layout_graph.mmd').exists()
    assert (out / 'module_layout_graph.svg').exists()
    assert not (out / 'group_dependency_graph.dot').exists()
    assert not (out / 'group_dependency_graph.mmd').exists()
    assert not (out / 'group_dependency_graph.svg').exists()
    assert not (out / 'module_dependency_graph.dot').exists()
    assert not (out / 'module_dependency_graph.mmd').exists()
    assert not (out / 'module_dependency_graph.svg').exists()
    assert (out / 'analysis_snapshot.json').exists()
    assert (out / 'architecture_report.md').exists()


def test_analyze_repo_default_overview_writes_only_svg_and_report(
    tmp_path: Path, monkeypatch: MonkeyPatch
) -> None:
    repo = tmp_path / 'repo'
    package_dir = repo / 'sample'
    package_dir.mkdir(parents=True)
    (package_dir / '__init__.py').write_text('', encoding='utf-8')
    (package_dir / 'a.py').write_text('from . import b\n', encoding='utf-8')
    (package_dir / 'b.py').write_text('VALUE = 1\n', encoding='utf-8')

    def record_render(dot_file: Path) -> None:
        dot_file.with_suffix('.svg').write_text('<svg />\n', encoding='utf-8')

    monkeypatch.setattr('importscope.app.render_svg', record_render)

    out = tmp_path / 'out'
    analyze_repo(
        repo=repo,
        out=out,
        package='sample',
        profile='overview',
    )

    assert (out / 'module_layout_graph.svg').exists()
    assert (out / 'group_dependency_graph.svg').exists()
    assert (out / 'module_dependency_graph.svg').exists()
    assert (out / 'architecture_report.md').exists()
    assert not (out / 'module_layout_graph.dot').exists()
    assert not (out / 'group_dependency_graph.dot').exists()
    assert not (out / 'module_dependency_graph.dot').exists()
    assert not (out / 'module_layout_graph.mmd').exists()
    assert not (out / 'group_dependency_graph.mmd').exists()
    assert not (out / 'module_dependency_graph.mmd').exists()
    assert not (out / 'analysis_snapshot.json').exists()
    assert not (out / 'internal_import_edges.csv').exists()


def test_analyze_repo_policy_cli_override(tmp_path: Path) -> None:
    repo = tmp_path / 'repo'
    package_dir = repo / 'sample'
    package_dir.mkdir(parents=True)
    (package_dir / '__init__.py').write_text('', encoding='utf-8')
    (package_dir / 'api.py').write_text('VALUE = 1\n', encoding='utf-8')
    (package_dir / 'core.py').write_text(
        'from . import api\n', encoding='utf-8'
    )
    config_path = repo / '.importscope.yml'
    config_path.write_text(
        yaml.safe_dump(
            {
                'package': 'sample',
                'policy': {
                    'enabled': False,
                    'policy_areas': [
                        {
                            'name': 'sample.core',
                            'match_prefixes': ['sample.core'],
                        },
                        {
                            'name': 'sample.api',
                            'match_prefixes': ['sample.api'],
                        },
                    ],
                    'forbidden_imports': [
                        {
                            'source_prefixes': ['sample.core'],
                            'target_prefixes': ['sample.api'],
                        }
                    ],
                },
            },
            sort_keys=False,
        ),
        encoding='utf-8',
    )

    disabled = analyze_repo(
        repo=repo,
        out=tmp_path / 'out-disabled',
        config_path=config_path,
        package='sample',
        formats=['json'],
        render='source',
    )
    enabled = analyze_repo(
        repo=repo,
        out=tmp_path / 'out-enabled',
        config_path=config_path,
        package='sample',
        formats=['json'],
        render='source',
        policy_enabled_override=True,
    )
    forced_off = analyze_repo(
        repo=repo,
        out=tmp_path / 'out-forced-off',
        config_path=config_path,
        package='sample',
        formats=['json'],
        render='source',
        policy_enabled_override=False,
    )

    assert disabled['findings'] == 0
    assert enabled['findings'] > 0
    assert enabled['snapshot']['finding_counts']['forbidden_import'] == 1
    assert forced_off['findings'] == 0


def test_allowed_private_target_keeps_cross_area_private_finding(
    tmp_path: Path,
) -> None:
    repo = tmp_path / 'repo'
    package_dir = repo / 'sample'
    package_dir.mkdir(parents=True)
    (package_dir / '__init__.py').write_text('', encoding='utf-8')
    (package_dir / '_support.py').write_text('VALUE = 1\n', encoding='utf-8')
    (package_dir / 'io.py').write_text(
        'from . import _support\n', encoding='utf-8'
    )
    config_path = repo / '.importscope.yml'
    config_path.write_text(
        yaml.safe_dump(
            {
                'package': 'sample',
                'policy': {
                    'enabled': True,
                    'policy_areas': [
                        {'name': 'sample.io', 'match_prefixes': ['sample.io']},
                        {
                            'name': 'sample._support',
                            'match_prefixes': ['sample._support'],
                        },
                    ],
                    'allowed_private_target_prefixes': ['sample._support'],
                },
            },
            sort_keys=False,
        ),
        encoding='utf-8',
    )

    result = analyze_repo(
        repo=repo,
        out=tmp_path / 'out',
        config_path=config_path,
        package='sample',
        formats=['json', 'csv'],
        render='source',
    )

    assert (
        result['snapshot']['finding_counts']['cross_area_private_import'] == 1
    )


def test_cli_parser_accepts_policy_overrides() -> None:
    parser = build_parser()

    enabled = parser.parse_args(['analyze', '--policy'])
    disabled = parser.parse_args(['analyze', '--no-policy'])

    assert enabled.policy_enabled is True
    assert disabled.policy_enabled is False


def test_cli_parser_accepts_path_graph_flags() -> None:
    parser = build_parser()

    args = parser.parse_args(
        [
            'inspect',
            '--snapshot',
            'snap.json',
            'path',
            'sample.api',
            'sample.core',
            '--graph-out',
            'out/path.svg',
            '--graph-format',
            'both',
            '--path-index',
            '1',
        ]
    )

    assert args.graph_out == 'out/path.svg'
    assert args.graph_format == 'both'


def test_init_config_defaults_to_compact_starter(tmp_path: Path) -> None:
    repo = tmp_path / 'repo'
    package_dir = repo / 'sample'
    package_dir.mkdir(parents=True)
    (package_dir / '__init__.py').write_text('', encoding='utf-8')
    (package_dir / 'core.py').write_text('VALUE = 1\n', encoding='utf-8')

    config_path = repo / '.importscope.yml'
    init_config(repo=repo, path=config_path, minimal=True)

    config = yaml.safe_load(config_path.read_text(encoding='utf-8'))
    assert config['package'] == 'sample'
    assert config['tool']['default_profile'] == 'overview'
    assert config['policy']['enabled'] is False
    assert 'display_groups' not in config.get('policy', {})
    assert 'outputs' not in config


def test_edit_config_updates_common_sections(tmp_path: Path) -> None:
    repo = tmp_path / 'repo'
    package_dir = repo / 'sample'
    package_dir.mkdir(parents=True)
    (package_dir / '__init__.py').write_text('', encoding='utf-8')
    (package_dir / 'api.py').write_text('VALUE = 1\n', encoding='utf-8')
    (package_dir / 'core.py').write_text(
        'from . import api\n', encoding='utf-8'
    )

    config_path = repo / '.importscope.yml'
    init_config(repo=repo, path=config_path, minimal=True)
    edit_config(repo=repo, action='exclude:add', values=['tests/**', 'docs/**'])
    edit_config(repo=repo, action='policy:enable')
    edit_config(
        repo=repo, action='forbid:add', values=['sample.core', 'sample.api']
    )

    shown = show_config(repo=repo)
    config = shown['config']
    assert 'tests/**' in config['discovery']['exclude']
    assert 'docs/**' in config['discovery']['exclude']
    assert config['policy']['enabled'] is True
    assert config['policy']['forbidden_imports'] == [
        {
            'source_prefixes': ['sample.core'],
            'target_prefixes': ['sample.api'],
        }
    ]

    edit_config(repo=repo, action='exclude:remove', values=['docs/**'])
    edit_config(
        repo=repo, action='forbid:remove', values=['sample.core', 'sample.api']
    )
    config = show_config(repo=repo)['config']
    assert 'docs/**' not in config['discovery']['exclude']
    assert config['policy']['forbidden_imports'] == []


def test_cli_parser_accepts_config_commands() -> None:
    parser = build_parser()

    show_args = parser.parse_args(['config', 'show', '--effective'])
    forbid_args = parser.parse_args(
        ['config', 'forbid', 'add', 'sample.core', 'sample.api']
    )

    assert show_args.command == 'config'
    assert show_args.config_command == 'show'
    assert show_args.effective is True
    assert forbid_args.config_command == 'forbid'
    assert forbid_args.config_forbid_command == 'add'


def test_cli_parser_accepts_highlight_flag() -> None:
    parser = build_parser()

    args = parser.parse_args(
        [
            'inspect',
            'path',
            'sample.api',
            'sample.backend',
            '--highlight',
        ]
    )

    assert args.highlight is True


def test_default_path_graph_out_uses_snapshot_directory() -> None:
    snapshot = Path('/tmp/repo/.cache/importscope/analysis_snapshot.json')

    out = _path_graph_default_out(snapshot, 'sample.api', 'sample.backend.impl')

    assert out == Path(
        '/tmp/repo/.cache/importscope/path_sample.api__to__sample.backend.impl'
    )


def test_module_inventory_graph_writes_nodes_without_import_edges(
    tmp_path: Path,
) -> None:
    repo = tmp_path / 'repo'
    package_dir = repo / 'sample'
    package_dir.mkdir(parents=True)
    (package_dir / '__init__.py').write_text('', encoding='utf-8')
    (package_dir / 'alpha.py').write_text('VALUE = 1\n', encoding='utf-8')
    (package_dir / 'beta.py').write_text('VALUE = 2\n', encoding='utf-8')

    result = analyze_repo(
        repo=repo,
        out=tmp_path / 'out',
        package='sample',
        profile='overview',
        formats=['dot'],
        render='source',
        graph_names=['module-layout'],
    )

    dot = (tmp_path / 'out' / 'module_layout_graph.dot').read_text(
        encoding='utf-8'
    )
    assert result['modules'] == 3
    assert '"sample.alpha"' in dot
    assert '"sample.beta"' in dot
    edge_lines = [line.strip() for line in dot.splitlines() if '->' in line]
    assert edge_lines
    assert all('style="invis"' in line for line in edge_lines)


def test_render_snapshot_path_graph_highlights_selected_path(
    tmp_path: Path, monkeypatch: MonkeyPatch
) -> None:
    repo = tmp_path / 'repo'
    package_dir = repo / 'sample'
    package_dir.mkdir(parents=True)
    (package_dir / '__init__.py').write_text(
        'from . import api\n', encoding='utf-8'
    )
    (package_dir / 'api.py').write_text(
        'from . import service\n', encoding='utf-8'
    )
    (package_dir / 'service.py').write_text(
        'from . import backend\n', encoding='utf-8'
    )
    (package_dir / 'backend.py').write_text('VALUE = 1\n', encoding='utf-8')

    out = tmp_path / 'analysis'
    analyze_repo(
        repo=repo,
        out=out,
        package='sample',
        formats=['json'],
        render='source',
    )

    def record_render(dot_file: Path) -> None:
        dot_file.with_suffix('.svg').write_text('<svg />\n', encoding='utf-8')

    monkeypatch.setattr('importscope.app.render_svg', record_render)

    graph_result = render_snapshot_path_graph(
        snapshot_path=out / 'analysis_snapshot.json',
        source='sample',
        target='sample.backend',
        out_path=tmp_path / 'path-highlight',
        image_format='both',
    )

    dot = (tmp_path / 'path-highlight.dot').read_text(encoding='utf-8')
    assert graph_result['path_found'] is True
    assert graph_result['selected_path'] == [
        'sample',
        'sample.api',
        'sample.service',
        'sample.backend',
    ]
    assert 'color="#ea580c"' in dot
    assert '"sample" [label="sample", fillcolor="white", color="#ea580c"' in dot
    assert '"sample.api" -> "sample.service"' in dot


def test_default_grouping_splits_second_level_subpackages() -> None:
    repo = Path('/tmp/fake-omnipath')
    result = AnalysisResult(
        repo=repo,
        module_roots=[repo],
        modules={
            'omnipath': ModuleInfo(
                'omnipath', repo / 'omnipath/__init__.py', True
            ),
            'omnipath._core.base': ModuleInfo(
                'omnipath._core.base', repo / 'omnipath/_core/base.py', False
            ),
            'omnipath._core.query': ModuleInfo(
                'omnipath._core.query', repo / 'omnipath/_core/query.py', False
            ),
            'omnipath.requests': ModuleInfo(
                'omnipath.requests', repo / 'omnipath/requests.py', False
            ),
        },
        edges=[],
        cycles=[],
        coverage_gaps=[],
    )
    config = default_config()
    config['package'] = 'omnipath'

    groups = group_order(config, result)
    group_names = [str(group['name']) for group in groups]

    assert 'omnipath' in group_names
    assert 'omnipath._core' in group_names
    assert 'omnipath.requests' in group_names
    assert (
        display_group_key('omnipath._core.base', config, result)
        == 'omnipath._core'
    )
    assert (
        display_group_key('omnipath._core.query', config, result)
        == 'omnipath._core'
    )
    assert (
        display_group_key('omnipath.requests', config, result)
        == 'omnipath.requests'
    )


def test_module_group_depth_refines_configured_broad_groups() -> None:
    repo = Path('/tmp/fake-omnipath')
    result = AnalysisResult(
        repo=repo,
        module_roots=[repo],
        modules={
            'omnipath': ModuleInfo(
                'omnipath', repo / 'omnipath/__init__.py', True
            ),
            'omnipath._core.base': ModuleInfo(
                'omnipath._core.base', repo / 'omnipath/_core/base.py', False
            ),
            'omnipath._core.query': ModuleInfo(
                'omnipath._core.query', repo / 'omnipath/_core/query.py', False
            ),
            'omnipath.requests': ModuleInfo(
                'omnipath.requests', repo / 'omnipath/requests.py', False
            ),
        },
        edges=[],
        cycles=[],
        coverage_gaps=[],
    )
    config = default_config()
    config['package'] = 'omnipath'
    config['policy']['display_groups'] = [
        {
            'name': 'root',
            'label': 'omnipath',
            'match_prefixes': ['omnipath'],
            'fill': '#f8fafc',
            'stroke': '#334155',
            'class': 'rootpkg',
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
    config['policy']['module_group_depth'] = 2

    assert display_group_key('omnipath._core.base', config, result) == 'root'
    assert (
        module_cluster_key('omnipath._core.base', config, result)
        == 'omnipath._core'
    )
    assert (
        module_cluster_key('omnipath._core.query', config, result)
        == 'omnipath._core'
    )
    assert (
        module_cluster_key('omnipath.requests', config, result)
        == 'omnipath.requests'
    )
    assert (
        module_cluster_style('omnipath._core', config, result)['fill']
        == '#f8fafc'
    )


def test_derived_leaf_cluster_inherits_parent_color() -> None:
    repo = Path('/tmp/fake-annnet')
    result = AnalysisResult(
        repo=repo,
        module_roots=[repo],
        modules={
            'annnet': ModuleInfo('annnet', repo / 'annnet/__init__.py', True),
            'annnet.adapters._common': ModuleInfo(
                'annnet.adapters._common',
                repo / 'annnet/adapters/_common.py',
                False,
            ),
        },
        edges=[],
        cycles=[],
        coverage_gaps=[],
    )
    config = default_config()
    config['package'] = 'annnet'
    config['policy']['display_groups'] = [
        {
            'name': 'annnet',
            'match_prefixes': ['annnet'],
            'fill': '#f8fafc',
            'stroke': '#334155',
            'class': 'rootpkg',
        },
        {
            'name': 'annnet.adapters',
            'match_prefixes': ['annnet.adapters'],
            'fill': '#dbeafe',
            'stroke': '#1d4ed8',
            'class': 'adapters',
        },
        {
            'name': 'other',
            'match_prefixes': [],
            'fill': '#f8fafc',
            'stroke': '#64748b',
            'class': 'other',
        },
    ]
    config['policy']['module_group_depth'] = 3

    assert (
        module_cluster_style('annnet.adapters._common', config, result)['fill']
        == '#dbeafe'
    )


def test_derived_parent_cluster_gets_tinted_parent_color() -> None:
    repo = Path('/tmp/fake-annnet')
    result = AnalysisResult(
        repo=repo,
        module_roots=[repo],
        modules={
            'annnet': ModuleInfo('annnet', repo / 'annnet/__init__.py', True),
            'annnet.benchmarks.basic_api': ModuleInfo(
                'annnet.benchmarks.basic_api',
                repo / 'annnet/benchmarks/basic_api.py',
                False,
            ),
            'annnet.benchmarks.construction_scaling': ModuleInfo(
                'annnet.benchmarks.construction_scaling',
                repo / 'annnet/benchmarks/construction_scaling.py',
                False,
            ),
        },
        edges=[],
        cycles=[],
        coverage_gaps=[],
    )
    config = default_config()
    config['package'] = 'annnet'
    config['policy']['display_groups'] = [
        {
            'name': 'annnet',
            'match_prefixes': ['annnet'],
            'fill': '#f8fafc',
            'stroke': '#334155',
            'class': 'rootpkg',
        },
        {
            'name': 'other',
            'match_prefixes': [],
            'fill': '#f8fafc',
            'stroke': '#64748b',
            'class': 'other',
        },
    ]
    config['policy']['module_group_depth'] = 3

    assert (
        module_cluster_style('annnet.benchmarks', config, result)['fill']
        != '#f8fafc'
    )


def test_leaf_under_derived_parent_inherits_derived_parent_color() -> None:
    repo = Path('/tmp/fake-annnet')
    result = AnalysisResult(
        repo=repo,
        module_roots=[repo],
        modules={
            'annnet': ModuleInfo('annnet', repo / 'annnet/__init__.py', True),
            'annnet.benchmarks.basic_api': ModuleInfo(
                'annnet.benchmarks.basic_api',
                repo / 'annnet/benchmarks/basic_api.py',
                False,
            ),
            'annnet.benchmarks.construction_scaling': ModuleInfo(
                'annnet.benchmarks.construction_scaling',
                repo / 'annnet/benchmarks/construction_scaling.py',
                False,
            ),
        },
        edges=[],
        cycles=[],
        coverage_gaps=[],
    )
    config = default_config()
    config['package'] = 'annnet'
    config['policy']['display_groups'] = [
        {
            'name': 'annnet',
            'match_prefixes': ['annnet'],
            'fill': '#f8fafc',
            'stroke': '#334155',
            'class': 'rootpkg',
        },
        {
            'name': 'other',
            'match_prefixes': [],
            'fill': '#f8fafc',
            'stroke': '#64748b',
            'class': 'other',
        },
    ]
    config['policy']['module_group_depth'] = 3

    assert (
        module_cluster_style('annnet.benchmarks.basic_api', config, result)[
            'fill'
        ]
        == module_cluster_style(
            'annnet.benchmarks',
            config,
            result,
        )['fill']
    )


def test_package_level_identifier_uses_canonical_prefix_not_human_label() -> (
    None
):
    repo = Path('/tmp/fake-omnipath')
    result = AnalysisResult(
        repo=repo,
        module_roots=[repo],
        modules={
            'omnipath.constants._constants': ModuleInfo(
                'omnipath.constants._constants',
                repo / 'omnipath/constants/_constants.py',
                False,
            ),
        },
        edges=[],
        cycles=[],
        coverage_gaps=[],
    )
    config = default_config()
    config['package'] = 'omnipath'
    config['policy']['display_groups'] = [
        {
            'name': 'constants',
            'label': 'omnipath constants',
            'match_prefixes': ['omnipath.constants'],
            'fill': '#ede9fe',
            'stroke': '#6d28d9',
            'class': 'constants',
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

    assert (
        package_group_identifier(
            'omnipath.constants._constants', config, result
        )
        == 'omnipath.constants'
    )


def test_module_cluster_exact_prefix_match_uses_group_color_even_with_alias_name() -> (
    None
):
    repo = Path('/tmp/fake-omnipath')
    result = AnalysisResult(
        repo=repo,
        module_roots=[repo],
        modules={
            'omnipath': ModuleInfo(
                'omnipath', repo / 'omnipath/__init__.py', True
            ),
            'omnipath.requests': ModuleInfo(
                'omnipath.requests', repo / 'omnipath/requests.py', False
            ),
            'omnipath._core.downloader._downloader': ModuleInfo(
                'omnipath._core.downloader._downloader',
                repo / 'omnipath/_core/downloader/_downloader.py',
                False,
            ),
        },
        edges=[],
        cycles=[],
        coverage_gaps=[],
    )
    config = default_config()
    config['package'] = 'omnipath'
    config['policy']['display_groups'] = [
        {
            'name': 'omnipath.facade',
            'match_prefixes': ['omnipath.requests'],
            'fill': '#f8fafc',
            'stroke': '#334155',
            'class': 'facade',
        },
        {
            'name': 'omnipath.transport',
            'match_prefixes': ['omnipath._core.downloader'],
            'fill': '#dbeafe',
            'stroke': '#1d4ed8',
            'class': 'transport',
        },
        {
            'name': 'other',
            'match_prefixes': [],
            'fill': '#f8fafc',
            'stroke': '#64748b',
            'class': 'other',
        },
    ]
    config['policy']['module_group_depth'] = 3

    assert (
        module_cluster_style('omnipath.requests', config, result)['fill']
        == '#f8fafc'
    )
    assert (
        module_cluster_style('omnipath._core.downloader', config, result)[
            'fill'
        ]
        == '#dbeafe'
    )


def test_dot_graph_nests_child_clusters_inside_parent_clusters(
    tmp_path: Path,
) -> None:
    repo = Path('/tmp/fake-omnipath')
    result = AnalysisResult(
        repo=repo,
        module_roots=[repo],
        modules={
            'omnipath': ModuleInfo(
                'omnipath', repo / 'omnipath/__init__.py', True
            ),
            'omnipath._core': ModuleInfo(
                'omnipath._core', repo / 'omnipath/_core/__init__.py', True
            ),
            'omnipath._core.requests': ModuleInfo(
                'omnipath._core.requests',
                repo / 'omnipath/_core/requests/__init__.py',
                True,
            ),
            'omnipath._core.requests.interactions': ModuleInfo(
                'omnipath._core.requests.interactions',
                repo / 'omnipath/_core/requests/interactions/__init__.py',
                True,
            ),
            'omnipath._core.requests.interactions._json': ModuleInfo(
                'omnipath._core.requests.interactions._json',
                repo / 'omnipath/_core/requests/interactions/_json.py',
                False,
            ),
        },
        edges=[],
        cycles=[],
        coverage_gaps=[],
    )
    config = default_config()
    config['package'] = 'omnipath'
    config['policy']['module_group_depth'] = 4
    dot_path = tmp_path / 'nested.dot'

    write_dot_graph(
        [
            ImportEdge(
                source='omnipath._core',
                target='omnipath._core.requests',
            ),
            ImportEdge(
                source='omnipath._core.requests',
                target='omnipath._core.requests.interactions',
            ),
            ImportEdge(
                source='omnipath._core.requests.interactions',
                target='omnipath._core.requests.interactions._json',
            ),
        ],
        dot_path,
        config,
        result,
        package_level=False,
    )
    dot = dot_path.read_text(encoding='utf-8')
    assert 'subgraph cluster_omnipath {' not in dot
    parent = dot.index('subgraph cluster_omnipath__core {')
    child = dot.index('subgraph cluster_omnipath__core_requests {')
    grandchild = dot.index(
        'subgraph cluster_omnipath__core_requests_interactions {'
    )
    json_node = dot.index('"omnipath._core.requests.interactions._json"')
    assert parent < child < grandchild < json_node


def test_symbol_import_graph_nests_child_clusters_inside_parent_clusters(
    tmp_path: Path,
) -> None:
    repo = Path('/tmp/fake-omnipath')
    result = AnalysisResult(
        repo=repo,
        module_roots=[repo],
        modules={
            'omnipath': ModuleInfo(
                'omnipath', repo / 'omnipath/__init__.py', True
            ),
            'omnipath._core': ModuleInfo(
                'omnipath._core', repo / 'omnipath/_core/__init__.py', True
            ),
            'omnipath._core.requests': ModuleInfo(
                'omnipath._core.requests',
                repo / 'omnipath/_core/requests/__init__.py',
                True,
            ),
            'omnipath._core.requests.interactions': ModuleInfo(
                'omnipath._core.requests.interactions',
                repo / 'omnipath/_core/requests/interactions/__init__.py',
                True,
            ),
            'omnipath._core.requests.interactions._json': ModuleInfo(
                'omnipath._core.requests.interactions._json',
                repo / 'omnipath/_core/requests/interactions/_json.py',
                False,
            ),
        },
        edges=[],
        cycles=[],
        coverage_gaps=[],
    )
    config = default_config()
    config['package'] = 'omnipath'
    config['policy']['module_group_depth'] = 4
    dot_path = tmp_path / 'symbol-nested.dot'

    write_symbol_import_dot(
        [
            ImportEdge(
                source='omnipath._core.requests',
                target='omnipath._core.requests.interactions',
                imported=('run',),
            ),
            ImportEdge(
                source='omnipath._core.requests.interactions',
                target='omnipath._core.requests.interactions._json',
                imported=('parse',),
            ),
        ],
        dot_path,
        config,
        result,
    )
    dot = dot_path.read_text(encoding='utf-8')
    assert 'subgraph cluster_importing_omnipath__core {' in dot
    assert 'subgraph cluster_importing_omnipath__core_requests {' in dot
    assert (
        'subgraph cluster_importing_omnipath__core_requests_interactions {'
        not in dot
    )
    assert (
        '"module:omnipath._core.requests.interactions" [label="omnipath._core.requests.interactions"'
        in dot
    )
    assert 'subgraph cluster_symbols_omnipath__core_requests {' in dot
    assert (
        'subgraph cluster_symbols_omnipath__core_requests_interactions {' in dot
    )


def test_leaf_package_cluster_collapses_to_single_node(tmp_path: Path) -> None:
    repo = Path('/tmp/fake-annnet')
    result = AnalysisResult(
        repo=repo,
        module_roots=[repo],
        modules={
            'annnet': ModuleInfo('annnet', repo / 'annnet/__init__.py', True),
            'annnet.io': ModuleInfo(
                'annnet.io', repo / 'annnet/io/__init__.py', True
            ),
            'annnet.io.csv': ModuleInfo(
                'annnet.io.csv', repo / 'annnet/io/csv/__init__.py', True
            ),
        },
        edges=[
            ImportEdge(source='annnet.io', target='annnet.io.csv'),
        ],
        cycles=[],
        coverage_gaps=[],
    )
    config = default_config()
    config['package'] = 'annnet'
    config['policy']['module_group_depth'] = 3
    dot_path = tmp_path / 'leaf-collapse.dot'

    write_dot_graph(result.edges, dot_path, config, result, package_level=False)
    dot = dot_path.read_text(encoding='utf-8')

    assert 'subgraph cluster_annnet__io_csv {' not in dot
    assert '"annnet.io.csv" [label="annnet.io.csv"' in dot
