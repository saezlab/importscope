# Installation

`importscope` is designed to be used with `uv`.

## Prerequisites

Install:

- Python `3.10` or newer
- `uv`
- Graphviz `dot` if you want rendered SVG output
- `git` if you plan to analyze local clones directly

Useful checks:

```bash
python3 --version
uv --version
dot -V
git --version
```

## Install the CLI

From a local checkout:

```bash
git clone https://github.com/saezlab/importscope.git
cd importscope
uv sync
```

After that, use the installed command directly:

```bash
importscope profiles
importscope analyze --dry-run --json
```

## Install for development

If you are working on this repository itself:

```bash
uv sync --group dev --group tests
```

That creates `.venv` and installs the package plus the development
dependencies.

The rest of the docs assume the CLI is installed and available as
`importscope`.

## Use on any local repository

Once installed, point `importscope` at any local clone:

```bash
importscope analyze \
  --repo /path/to/target-repo \
  --out /tmp/importscope-output
```

## SVG rendering

If `dot` is installed, `importscope` can render SVG directly from generated DOT
files.

If Graphviz is missing, use source formats only:

```bash
importscope analyze --repo . --format dot --format mmd
```

## Verify the setup

Before a larger run:

```bash
importscope check --repo .
```
