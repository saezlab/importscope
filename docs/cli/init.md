# `importscope init`

Use this to create a starter `.importscope.yml`.

```bash
importscope init
importscope init --full
importscope init --stdout
```

## Default Behavior

When run as plain `importscope init`, it writes:

- config path: `.importscope.yml`
- a compact starter config
- repo defaults: current directory
- package name when it can be inferred safely

Useful flags:

- `--repo`: repository root used for defaults
- `--path`: output path for the config file
- `--profile`: initialize around a specific profile
- `--full`: write the expanded built-in template instead of the compact starter
- `--stdout`: print instead of writing
- `--force`: overwrite an existing file

Use `init` when:

- you want a small checked-in starting point
- you want to add `exclude`, `include`, or `forbid` rules incrementally with `importscope config`
- you want to defer hand-editing YAML until there is a real reason

Typical examples:

```bash
importscope init
importscope init --stdout
importscope init --full
```
