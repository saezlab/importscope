# Importscope

Analyze Python import structure and render policy-aware dependency graphs.

![What importscope does](./docs/assets/importscope-overview.png)

## Fastest Local Workflow

Install once from this checkout:

```bash
uv sync
```

Then run it inside any local Python repository:

```bash
cd /path/to/your-repo
importscope analyze
```

By default this writes to `.cache/importscope`.

Start with:

- `.cache/importscope/module_layout_graph.svg`
- `.cache/importscope/group_dependency_graph.svg`
- `.cache/importscope/architecture_report.md`

If you want one specific import chain instead of the full graph:

```bash
importscope inspect path mypackage.api mypackage.core.module_a
```

If you also want that path highlighted on a graph:

```bash
importscope inspect path mypackage.api mypackage.core.module_a --highlight
```

Only add `--repo`, `--out`, or `--snapshot` when you need to override the
built-in defaults.

If you also want source graph files, ask for them explicitly:

```bash
importscope analyze --repo . --out output/importscope --format dot --format mmd
```

If you are new to the tool, use the docs in this order:

1. Run the [sample demo repo walkthrough](./docs/quickstart.md) to learn the baseline workflow.
2. Then open the [real-repo examples](./docs/learn/guides/index.md) to see how the same CLI is scoped differently on larger codebases.

## What It Does

`importscope` statically analyzes Python source trees and produces:

- module and package dependency graphs
- symbol import graphs
- CSV and JSON evidence tables
- Markdown architecture summaries
- policy-aware views for layer violations, private imports, and helper boundaries

It is designed to run inside any local cloned repository and can be configured
for import direction rules, exceptions, private import policy, grouping, graph
selection, and output format.

The main pattern is:

- start with one structural run, often with no config
- add a small `.importscope.yml` when you need meaningful grouping or policy checks
- narrow the analysis scope on larger repos so the output answers one architectural question at a time

## CLI

```bash
importscope analyze
importscope profiles
importscope init
importscope config show
importscope inspect module importscope.cli
importscope check
```

Main workflows:

- `importscope analyze`
  Analyze a repo and write graphs, tables, snapshot JSON, and summary Markdown.
- `importscope profiles`
  List built-in output profiles.
- `importscope init`
  Write a starter YAML config.
- `importscope config`
  Edit common config fields without hand-editing YAML.
- `importscope inspect`
  Query a saved snapshot for edges, modules, paths, cycles, or symbols.
- `importscope check`
  Validate discovery, config, and toolchain readiness.

## License

BSD-3-Clause. See [LICENSE](./LICENSE).
