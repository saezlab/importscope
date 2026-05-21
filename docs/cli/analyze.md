# `importscope analyze`

Use this to generate graphs, reports, and optional machine-readable artifacts.

```bash
importscope analyze
importscope analyze --config .importscope.yml --profile overview
importscope analyze --repo . --format json
importscope analyze --profile all --format dot --format mmd
importscope analyze --config .importscope.yml --policy
importscope analyze --config .importscope.yml --no-policy
importscope analyze --dry-run --json
```

## Default Behavior

When run as plain `importscope analyze`, it uses:

- repo: current directory
- output directory: `.cache/importscope`
- profile: repo default profile or built-in `overview`
- config: auto-discovered `.importscope.yml` when present

That is the command to start with on most repos.

Useful flags:

- `--repo`: repository root to analyze
- `--out`: output directory
- `--config`: YAML config file
- `--profile`: named profile such as `overview`, `policy`, `symbols`, or `all`
- `--graph`: select one graph id from the chosen profile
- `--format`: request explicit formats such as `svg`, `md`, `json`, `csv`, `dot`, or `mmd`
- `--render`: `svg`, `source`, or `both`
- `--package`: restrict analysis to one package namespace
- `--module-root`: add explicit module roots
- `--include`: include glob
- `--exclude`: exclude glob
- `--summary`: `none`, `short`, or `full`
- `--policy`: force policy mode on for one run
- `--no-policy`: force policy mode off for one run
- `--max-symbol-edges`: cap the symbol graph size
- `--dry-run`: print the run plan without executing it
- `--json`: print machine-readable command output
- `--fail-on`: exit non-zero on `cycles`, `violations`, or `warnings`

Use `analyze` when:

- you want the main package-level or module-level graphs
- you need a JSON snapshot for later `inspect` queries
- you want policy findings from a checked-in config
- you want CI to fail on cycles or violations

Typical examples:

Minimal default run:

```bash
importscope analyze
```

Generate a snapshot for later `inspect` queries:

```bash
importscope analyze --format json
```

Ask for source graph files explicitly:

```bash
importscope analyze --format dot --format mmd
```

Focus on one package inside a larger repo:

```bash
importscope analyze \
  --repo . \
  --package mypackage \
  --out .cache/importscope-mypackage
```

Fail CI on forbidden imports:

```bash
importscope analyze \
  --repo . \
  --config .importscope.yml \
  --policy \
  --fail-on violations
```
