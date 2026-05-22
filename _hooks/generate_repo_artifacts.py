"""Generate checked-in docs artifacts before the MkDocs build."""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

from importscope.app import analyze_repo


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _generated_root() -> Path:
    return _repo_root() / 'docs' / 'assets' / 'generated' / 'importscope-self'


def _demo_repo_root() -> Path:
    return _repo_root() / 'docs' / 'examples' / 'demo-shop-repo'


def _demo_generated_root() -> Path:
    return _repo_root() / 'docs' / 'assets' / 'generated' / 'demo-shop'


def _self_config_path() -> Path:
    return _repo_root() / 'docs' / 'examples' / 'importscope-self.yml'


def _finalize_report(out_dir: Path) -> None:
    report_md = out_dir / 'architecture_report.md'
    report_txt = out_dir / 'architecture_report.txt'
    if report_md.exists():
        report_txt.write_text(
            report_md.read_text(encoding='utf-8'), encoding='utf-8'
        )
        report_md.unlink()


def _assert_expected_outputs(out_dir: Path, names: list[str]) -> None:
    missing = [name for name in names if not (out_dir / name).exists()]
    if missing:
        missing_text = ', '.join(missing)
        raise RuntimeError(
            f'Missing generated docs artifacts in {out_dir}: {missing_text}'
        )


def _generate_demo_no_config_layout(
    demo_repo: Path, demo_out_dir: Path
) -> None:
    with tempfile.TemporaryDirectory(
        prefix='importscope-demo-no-config-'
    ) as tmp:
        tmp_repo = Path(tmp) / 'demo-shop-repo'
        shutil.copytree(demo_repo, tmp_repo)
        config_path = tmp_repo / '.importscope.yml'
        if config_path.exists():
            config_path.unlink()
        analyze_repo(
            repo=tmp_repo,
            out=tmp_repo / '.cache' / 'importscope',
            graph_names=['module-layout'],
            formats=['svg'],
            render='svg',
        )
        source = tmp_repo / '.cache' / 'importscope' / 'module_layout_graph.svg'
        target = demo_out_dir / 'module_layout_graph_no_config.svg'
        if source.exists():
            shutil.copy2(source, target)


def on_pre_build(config: object, **kwargs: object) -> None:
    """Regenerate the checked-in graphs and reports used by the docs site."""
    repo = _repo_root()
    out_dir = _generated_root()
    demo_repo = _demo_repo_root()
    demo_out_dir = _demo_generated_root()
    self_config = _self_config_path()
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    if demo_out_dir.exists():
        shutil.rmtree(demo_out_dir)
    demo_out_dir.mkdir(parents=True, exist_ok=True)

    analyze_repo(
        repo=repo,
        out=out_dir,
        config_path=self_config,
        profile='all',
        graph_names=[
            'package-dependency',
            'symbol-labeled-module-dependency',
            'symbol-import',
        ],
        formats=['svg', 'md'],
        render='svg',
    )
    _finalize_report(out_dir)
    _assert_expected_outputs(
        out_dir,
        [
            'group_dependency_graph.svg',
            'module_dependency_with_symbols.svg',
            'symbol_import_graph.svg',
            'architecture_report.txt',
        ],
    )
    analyze_repo(
        repo=demo_repo,
        out=demo_out_dir,
        config_path=demo_repo / '.importscope.yml',
        profile='all',
        graph_names=[
            'module-layout',
            'package-dependency',
            'symbol-labeled-module-dependency',
            'symbol-import',
        ],
        formats=['svg', 'md', 'json'],
        render='svg',
        policy_enabled_override=True,
    )
    _finalize_report(demo_out_dir)
    _generate_demo_no_config_layout(demo_repo, demo_out_dir)
    _assert_expected_outputs(
        demo_out_dir,
        [
            'group_dependency_graph.svg',
            'module_dependency_with_symbols.svg',
            'symbol_import_graph.svg',
            'module_layout_graph.svg',
            'module_layout_graph_no_config.svg',
            'architecture_report.txt',
        ],
    )
