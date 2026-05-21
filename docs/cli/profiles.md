# `importscope profiles`

Use this to inspect the available output bundles for the current repo and
config before analysis.

```bash
importscope profiles
importscope profiles --format json
```

## Default Behavior

When run as plain `importscope profiles`, it uses:

- repo: current directory
- config: auto-discovered `.importscope.yml` when present
- output format: table

Useful flags:

- `--repo`: repository root to inspect; profiles can vary with repo-local config
- `--config`: config file to load first
- `--format`: `table` or `json`

Profiles define:

- which graph families are generated
- which formats are emitted
- whether a summary report is written

Use `profiles` when:

- you want to see how much a named profile generates
- you want to compare `overview`, `policy`, `symbols`, and `all`
- you want to inspect profile definitions in JSON form

You can skip `profiles` entirely if you already know which graphs and formats
you want to request with `analyze`.

Typical examples:

```bash
importscope profiles
importscope profiles --format json
```
