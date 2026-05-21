from __future__ import annotations

import re
import json
from pathlib import Path
import argparse

import yaml

from .app import (
    check_repo,
    edit_config,
    init_config,
    show_config,
    analyze_repo,
    list_profiles,
    inspect_snapshot,
    render_snapshot_path_graph,
)


def _print_json(data: object) -> None:
    """Pretty-print a Python object as JSON."""
    print(json.dumps(data, indent=2, sort_keys=True))


def _path_graph_default_out(snapshot: Path, source: str, target: str) -> Path:
    """Build a default output stem for a highlighted path graph near the snapshot."""

    def _slug(value: str) -> str:
        text = re.sub(r'[^0-9A-Za-z._-]+', '-', value.strip()).strip('-')
        return text or 'path'

    stem = f'path_{_slug(source)}__to__{_slug(target)}'
    return snapshot.resolve().parent / stem


def build_parser() -> argparse.ArgumentParser:
    """Build the top-level ``importscope`` command parser."""
    parser = argparse.ArgumentParser(prog='importscope')
    subparsers = parser.add_subparsers(dest='command', required=True)

    analyze_parser = subparsers.add_parser(
        'analyze', help='Analyze a repo and write outputs.'
    )
    analyze_parser.add_argument('--repo', default='.', help='Repository root')
    analyze_parser.add_argument('--config', help='Config file path')
    analyze_parser.add_argument('--profile', help='Profile name')
    analyze_parser.add_argument(
        '--graph', action='append', default=[], help='Graph id to render'
    )
    analyze_parser.add_argument(
        '--format', action='append', default=[], help='Output format'
    )
    analyze_parser.add_argument(
        '--render', choices=['svg', 'source', 'both'], default='svg'
    )
    analyze_parser.add_argument(
        '--out', default='.cache/importscope', help='Output directory'
    )
    analyze_parser.add_argument(
        '--package', help='Restrict analysis to one package'
    )
    analyze_parser.add_argument(
        '--module-root',
        action='append',
        default=[],
        help='Explicit module root',
    )
    analyze_parser.add_argument(
        '--include', action='append', default=[], help='Include glob'
    )
    analyze_parser.add_argument(
        '--exclude', action='append', default=[], help='Exclude glob'
    )
    analyze_parser.add_argument('--max-symbol-edges', type=int, default=400)
    analyze_parser.add_argument(
        '--summary', choices=['none', 'short', 'full'], help='Summary mode'
    )
    analyze_parser.add_argument(
        '--fail-on',
        choices=['none', 'cycles', 'violations', 'warnings'],
        default='none',
    )
    analyze_parser.add_argument('--dry-run', action='store_true')
    analyze_parser.add_argument(
        '--json',
        action='store_true',
        help='Print machine-readable command output',
    )
    policy_group = analyze_parser.add_mutually_exclusive_group()
    policy_group.add_argument(
        '--policy',
        dest='policy_enabled',
        action='store_true',
        help='Enable policy classification for this run',
    )
    policy_group.add_argument(
        '--no-policy',
        dest='policy_enabled',
        action='store_false',
        help='Disable policy classification for this run',
    )
    analyze_parser.set_defaults(policy_enabled=None)

    profiles_parser = subparsers.add_parser(
        'profiles', help='List available profiles.'
    )
    profiles_parser.add_argument('--repo', default='.', help='Repository root')
    profiles_parser.add_argument('--config', help='Config file path')
    profiles_parser.add_argument(
        '--format', choices=['table', 'json'], default='table'
    )

    init_parser = subparsers.add_parser('init', help='Write a starter config.')
    init_parser.add_argument('--repo', default='.', help='Repository root')
    init_parser.add_argument(
        '--path', default='.importscope.yml', help='Config output path'
    )
    init_parser.add_argument('--profile', help='Profile name')
    init_mode = init_parser.add_mutually_exclusive_group()
    init_mode.add_argument(
        '--minimal',
        dest='minimal',
        action='store_true',
        help='Write a compact starter config',
    )
    init_mode.add_argument(
        '--full',
        dest='minimal',
        action='store_false',
        help='Write the full expanded config template',
    )
    init_parser.set_defaults(minimal=True)
    init_parser.add_argument('--force', action='store_true')
    init_parser.add_argument('--stdout', action='store_true')

    config_parser = subparsers.add_parser(
        'config', help='Show or edit .importscope.yml programmatically.'
    )
    config_parser.add_argument('--repo', default='.', help='Repository root')
    config_parser.add_argument('--config', help='Config file path')
    config_subparsers = config_parser.add_subparsers(
        dest='config_command', required=True
    )

    config_show = config_subparsers.add_parser(
        'show', help='Print the current config.'
    )
    config_show.add_argument(
        '--format', choices=['yaml', 'json'], default='yaml'
    )
    config_show.add_argument(
        '--effective',
        action='store_true',
        help='Show merged defaults instead of only the file contents',
    )

    config_package = config_subparsers.add_parser(
        'package', help='Set or unset the package filter.'
    )
    config_package_subparsers = config_package.add_subparsers(
        dest='config_package_command', required=True
    )
    config_package_set = config_package_subparsers.add_parser(
        'set', help='Set the package name'
    )
    config_package_set.add_argument('name')
    config_package_subparsers.add_parser(
        'unset', help='Remove the explicit package name'
    )

    config_policy = config_subparsers.add_parser(
        'policy', help='Enable or disable policy mode in the config.'
    )
    config_policy_subparsers = config_policy.add_subparsers(
        dest='config_policy_command', required=True
    )
    config_policy_subparsers.add_parser(
        'enable', help='Set policy.enabled to true'
    )
    config_policy_subparsers.add_parser(
        'disable', help='Set policy.enabled to false'
    )

    config_exclude = config_subparsers.add_parser(
        'exclude', help='Add or remove discovery exclude globs.'
    )
    config_exclude_subparsers = config_exclude.add_subparsers(
        dest='config_exclude_command', required=True
    )
    config_exclude_add = config_exclude_subparsers.add_parser(
        'add', help='Add one or more exclude globs'
    )
    config_exclude_add.add_argument('patterns', nargs='+')
    config_exclude_remove = config_exclude_subparsers.add_parser(
        'remove', help='Remove one or more exclude globs'
    )
    config_exclude_remove.add_argument('patterns', nargs='+')

    config_include = config_subparsers.add_parser(
        'include', help='Add or remove discovery include globs.'
    )
    config_include_subparsers = config_include.add_subparsers(
        dest='config_include_command', required=True
    )
    config_include_add = config_include_subparsers.add_parser(
        'add', help='Add one or more include globs'
    )
    config_include_add.add_argument('patterns', nargs='+')
    config_include_remove = config_include_subparsers.add_parser(
        'remove', help='Remove one or more include globs'
    )
    config_include_remove.add_argument('patterns', nargs='+')

    config_forbid = config_subparsers.add_parser(
        'forbid', help='Add or remove forbidden import rules.'
    )
    config_forbid_subparsers = config_forbid.add_subparsers(
        dest='config_forbid_command', required=True
    )
    config_forbid_add = config_forbid_subparsers.add_parser(
        'add', help='Add one forbidden import rule'
    )
    config_forbid_add.add_argument('source_prefix')
    config_forbid_add.add_argument('target_prefix')
    config_forbid_remove = config_forbid_subparsers.add_parser(
        'remove', help='Remove one forbidden import rule'
    )
    config_forbid_remove.add_argument('source_prefix')
    config_forbid_remove.add_argument('target_prefix')

    config_allowed_private = config_subparsers.add_parser(
        'allowed-private', help='Add or remove allowed private target prefixes.'
    )
    config_allowed_private_subparsers = config_allowed_private.add_subparsers(
        dest='config_allowed_private_command', required=True
    )
    config_allowed_private_add = config_allowed_private_subparsers.add_parser(
        'add', help='Add one or more allowed private prefixes'
    )
    config_allowed_private_add.add_argument('prefixes', nargs='+')
    config_allowed_private_remove = (
        config_allowed_private_subparsers.add_parser(
            'remove', help='Remove one or more allowed private prefixes'
        )
    )
    config_allowed_private_remove.add_argument('prefixes', nargs='+')

    config_module_depth = config_subparsers.add_parser(
        'module-group-depth', help='Set or unset policy.module_group_depth.'
    )
    config_module_depth_subparsers = config_module_depth.add_subparsers(
        dest='config_module_depth_command', required=True
    )
    config_module_depth_set = config_module_depth_subparsers.add_parser(
        'set', help='Set module group depth'
    )
    config_module_depth_set.add_argument('depth', type=int)
    config_module_depth_subparsers.add_parser(
        'unset', help='Remove module group depth from the config'
    )

    inspect_parser = subparsers.add_parser(
        'inspect', help='Inspect a saved analysis snapshot.'
    )
    inspect_parser.add_argument(
        '--snapshot', default='.cache/importscope/analysis_snapshot.json'
    )
    inspect_subparsers = inspect_parser.add_subparsers(
        dest='inspect_command', required=True
    )
    edge_parser = inspect_subparsers.add_parser(
        'edge', help='Inspect one directed edge'
    )
    edge_parser.add_argument('source')
    edge_parser.add_argument('target')
    module_parser = inspect_subparsers.add_parser(
        'module', help='Inspect one module'
    )
    module_parser.add_argument('name')
    path_parser = inspect_subparsers.add_parser(
        'path', help='Inspect paths between two modules'
    )
    path_parser.add_argument('source')
    path_parser.add_argument('target')
    path_parser.add_argument('--max-paths', type=int, default=5)
    path_parser.add_argument(
        '--highlight',
        action='store_true',
        help='Render the selected path to a highlighted module graph next to the snapshot',
    )
    path_parser.add_argument(
        '--graph-out',
        help='Write a highlighted module path graph to this output path stem or file path',
    )
    path_parser.add_argument(
        '--graph-format', choices=['svg', 'dot', 'both'], default='svg'
    )
    path_parser.add_argument(
        '--path-index',
        type=int,
        default=0,
        help='Select which returned path to highlight',
    )
    cycle_parser = inspect_subparsers.add_parser(
        'cycle', help='Inspect cycle components'
    )
    cycle_parser.add_argument('--module')
    symbol_parser = inspect_subparsers.add_parser(
        'symbol', help='Inspect one symbol'
    )
    symbol_parser.add_argument('name')

    check_parser = subparsers.add_parser(
        'check', help='Validate config, discovery, and toolchain.'
    )
    check_parser.add_argument('--repo', default='.', help='Repository root')
    check_parser.add_argument('--config', help='Config file path')
    check_parser.add_argument('--profile', help='Profile name')
    check_parser.add_argument(
        '--format', choices=['text', 'json'], default='text'
    )

    return parser


def main(argv: list[str] | None = None) -> None:
    """Run the CLI entry point.

    Parameters
    ----------
    argv
        Optional argument vector. When omitted, arguments are read from
        ``sys.argv`` through ``argparse``.
    """
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == 'analyze':
        result = analyze_repo(
            repo=Path(args.repo).resolve(),
            out=Path(args.out).resolve(),
            config_path=Path(args.config).resolve() if args.config else None,
            profile=args.profile,
            package=args.package,
            include=args.include,
            exclude=args.exclude,
            module_roots=[Path(item).resolve() for item in args.module_root],
            graph_names=args.graph or None,
            formats=args.format or None,
            render=args.render,
            summary_mode=args.summary,
            max_symbol_edges=args.max_symbol_edges,
            policy_enabled_override=args.policy_enabled,
            dry_run=args.dry_run,
        )
        if args.json:
            _print_json(result)
        else:
            if result['mode'] == 'dry-run':
                print('Dry run plan:')
                _print_json(result['plan'])
            else:
                print(f'Wrote outputs to: {result["plan"]["out"]}')
                print(f'Modules parsed: {result["modules"]}')
                print(f'Internal import edges: {result["edges"]}')
                print(f'Cycles detected: {result["cycles"]}')
                print(f'Policy findings: {result["findings"]}')
                if result.get('render_warnings'):
                    print(f'Render warnings: {len(result["render_warnings"])}')
        fail_on = args.fail_on
        if fail_on == 'cycles' and result.get('cycles', 0):
            raise SystemExit(1)
        if fail_on == 'violations':
            findings = result.get('snapshot', {}).get('finding_counts', {})
            if findings.get('forbidden_import', 0):
                raise SystemExit(1)
        if fail_on == 'warnings' and result.get('findings', 0):
            raise SystemExit(1)
        return

    if args.command == 'profiles':
        result = list_profiles(
            repo=Path(args.repo).resolve(),
            config_path=Path(args.config).resolve() if args.config else None,
        )
        if args.format == 'json':
            _print_json(result)
        else:
            for name, spec in sorted(result['profiles'].items()):
                print(f'{name}: {spec.get("description", "")}')
        return

    if args.command == 'init':
        path = Path(args.path).resolve()
        if path.exists() and not args.force and not args.stdout:
            raise SystemExit(f'Refusing to overwrite existing file: {path}')
        text = init_config(
            repo=Path(args.repo).resolve(),
            path=path,
            profile=args.profile,
            minimal=args.minimal,
        )
        if args.stdout:
            print(text, end='')
        else:
            print(f'Wrote config to: {path}')
        return

    if args.command == 'config':
        repo = Path(args.repo).resolve()
        config_path = Path(args.config).resolve() if args.config else None
        if args.config_command == 'show':
            result = show_config(
                repo=repo,
                config_path=config_path,
                effective=args.effective,
            )
            if args.format == 'json':
                _print_json(result)
            else:
                print(result['config_path'])
                print(yaml.safe_dump(result['config'], sort_keys=False), end='')
            return

        if args.config_command == 'package':
            if args.config_package_command == 'set':
                result = edit_config(
                    repo=repo,
                    config_path=config_path,
                    action='package:set',
                    values=[args.name],
                )
            else:
                result = edit_config(
                    repo=repo,
                    config_path=config_path,
                    action='package:unset',
                )
        elif args.config_command == 'policy':
            result = edit_config(
                repo=repo,
                config_path=config_path,
                action=f'policy:{args.config_policy_command}',
            )
        elif args.config_command == 'exclude':
            result = edit_config(
                repo=repo,
                config_path=config_path,
                action=f'exclude:{args.config_exclude_command}',
                values=args.patterns,
            )
        elif args.config_command == 'include':
            result = edit_config(
                repo=repo,
                config_path=config_path,
                action=f'include:{args.config_include_command}',
                values=args.patterns,
            )
        elif args.config_command == 'allowed-private':
            result = edit_config(
                repo=repo,
                config_path=config_path,
                action=f'allowed-private:{args.config_allowed_private_command}',
                values=args.prefixes,
            )
        elif args.config_command == 'module-group-depth':
            values = (
                [str(args.depth)]
                if args.config_module_depth_command == 'set'
                else None
            )
            result = edit_config(
                repo=repo,
                config_path=config_path,
                action=f'module-group-depth:{args.config_module_depth_command}',
                values=values,
            )
        else:
            result = edit_config(
                repo=repo,
                config_path=config_path,
                action=f'forbid:{args.config_forbid_command}',
                values=[args.source_prefix, args.target_prefix],
            )
        print(f'Updated config: {result["config_path"]}')
        return

    if args.command == 'inspect':
        snapshot = Path(args.snapshot).resolve()
        if args.inspect_command == 'edge':
            result = inspect_snapshot(
                snapshot_path=snapshot,
                mode='edge',
                source=args.source,
                target=args.target,
            )
        elif args.inspect_command == 'module':
            result = inspect_snapshot(
                snapshot_path=snapshot, mode='module', name=args.name
            )
        elif args.inspect_command == 'path':
            result = inspect_snapshot(
                snapshot_path=snapshot,
                mode='path',
                source=args.source,
                target=args.target,
                max_paths=args.max_paths,
            )
            if args.graph_out or args.highlight:
                graph_out = (
                    Path(args.graph_out).resolve()
                    if args.graph_out
                    else _path_graph_default_out(
                        snapshot, args.source, args.target
                    )
                )
                graph_result = render_snapshot_path_graph(
                    snapshot_path=snapshot,
                    source=args.source,
                    target=args.target,
                    out_path=graph_out,
                    path_index=args.path_index,
                    max_paths=args.max_paths,
                    image_format=args.graph_format,
                )
                result['graph'] = graph_result
        elif args.inspect_command == 'cycle':
            result = inspect_snapshot(
                snapshot_path=snapshot, mode='cycle', name=args.module
            )
        else:
            result = inspect_snapshot(
                snapshot_path=snapshot, mode='symbol', name=args.name
            )
        _print_json(result)
        return

    if args.command == 'check':
        result = check_repo(
            repo=Path(args.repo).resolve(),
            config_path=Path(args.config).resolve() if args.config else None,
            profile=args.profile,
        )
        if args.format == 'json':
            _print_json(result)
        else:
            print(f'Profile: {result["profile"]}')
            print(f'Modules: {result["modules"]}')
            print(f'Edges: {result["edges"]}')
            if result['problems']:
                print('Problems:')
                for problem in result['problems']:
                    print(f'- {problem}')
            else:
                print('No problems detected.')
        if result['problems']:
            raise SystemExit(1)
        return
