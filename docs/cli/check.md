# `importscope check`

Use this to validate the repo, config, selected profile, and rendering
toolchain before a full run.

```bash
importscope check
importscope check --config .importscope.yml
importscope check --format json
```

## Default Behavior

When run as plain `importscope check`, it uses:

- repo: current directory
- config: auto-discovered `.importscope.yml` when present
- output format: text

Useful flags:

- `--repo`: repository root to inspect
- `--config`: explicit config file path
- `--profile`: validate a specific profile
- `--format`: `text` or `json`

Use `check` when:

- you are not sure discovery will find the right package
- you just edited `.importscope.yml`
- you want to confirm Graphviz is available before asking for SVG output

Typical examples:

```bash
importscope check
importscope check --config .importscope.yml
importscope check --format json
```
