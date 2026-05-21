# Developer Guide

Thank you for considering contributing to `importscope`.

## Small contributions

For a small fix, you can usually open a pull request directly.

## Larger contributions

For a larger change, start from the [Join us](./index.md#how-we-work) page and
open a short discussion first.

## Development environment

`importscope` uses [uv](https://docs.astral.sh/uv/) for local environments.

```bash
git clone https://github.com/saezlab/importscope.git
cd importscope
uv sync --group dev --group tests
```

Run commands through `uv run`:

```bash
uv run pytest
uv run ruff check importscope tests
uv run mkdocs build --strict
```

## Code quality

The main local tools are:

- [Ruff](https://docs.astral.sh/ruff/) for linting and formatting
- [pre-commit](https://pre-commit.com/) for repository hooks

To install hooks:

```bash
uv run pre-commit install
uv run pre-commit run --all-files
```

## Testing

Use the test dependency group and run `pytest` through `uv`:

```bash
uv sync --group tests
uv run pytest
```

Please add or update tests for behavior changes.

## Pull requests

For non-trivial changes:

- reference an issue or discussion
- keep the PR focused
- make sure tests and docs still build

If you are contributing through a fork:

```bash
git clone https://github.com/your-user-name/importscope.git
cd importscope
git remote add upstream https://github.com/saezlab/importscope.git
git fetch upstream
git checkout -b my-change
```
